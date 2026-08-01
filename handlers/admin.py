# -*- coding: utf-8 -*-
"""👑 پنل مدیریت حرفه‌ای «قیومی‌بات» — مخفی، فقط با /admin

ورود: /admin ← نام‌کاربری ← رمز عبور (۳ تلاش اشتباه = بلاک ۱۰ دقیقه‌ای)
بخش‌ها: آمار زنده، پیام همگانی، مدیریت کاربران (لیست/جستجو/کارت/پیام تکی/حذف)،
خروجی CSV + بکاپ دیتابیس، کانال‌های جوین، دکمه هدر منو، راه‌های ارتباطی،
موقعیت‌های شغلی، متن سؤال‌ها، ریست دیتابیس (با بکاپ پیش‌دیفالتی).

همه‌چیز در «همان یک پیام» ویرایش می‌شود — تمیز، ساده و فوق‌حرفه‌ای.
"""

import asyncio
import csv
import io
import json
import logging
import os
from datetime import datetime, timedelta

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, ErrorEvent, Message

import config
from keyboards import admin as akb
from services import content
from services import broadcast as bcast
from services import db
from states.admin import AdminStates

log = logging.getLogger(__name__)
router = Router(name="admin")
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")

LOGGED_IN: set[int] = set()
_ATTEMPTS: dict[int, int] = {}
_BLOCKED: dict[int, datetime] = {}
MAX_ATTEMPTS = 3
BLOCK_MINUTES = 10
SEP = "➖➖➖➖➖➖➖➖"


# ════════════════════════ ابزارهای کمکی ════════════════════════
def is_admin(user_id: int) -> bool:
    return user_id in LOGGED_IN or user_id in config.ADMIN_USER_IDS


async def _guard(cb: CallbackQuery) -> bool:
    if not is_admin(cb.from_user.id):
        await cb.answer("⛔ دسترسی غیرمجاز!", show_alert=True)
        return False
    return True


async def _edit(cb: CallbackQuery, text: str, kb=None) -> None:
    """ویرایش همان پیام؛ اگر نشد (مثلاً پیام رسانه‌ای است) پیام جدید."""
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc):
            pass
        else:
            await cb.message.answer(text, reply_markup=kb)


async def _home_text(title: str = "👑 پنل مدیریت «قیومی‌بات»") -> str:
    now = datetime.now()
    users = await db.count_users()
    resumes = await db.count_resumes()
    new_24h = await db.count_users_since((now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"))
    new_7d = await db.count_users_since((now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"))
    return "\n".join([
        title,
        SEP,
        f"👥 کاربران: {users}  |  🆕 ۲۴ساعت: {new_24h}  |  🗓 ۷روز: {new_7d}",
        f"📄 رزومه‌های ثبت‌شده: {resumes}",
        f"🕒 {now:%Y-%m-%d %H:%M}",
        SEP,
        "یک بخش را انتخاب کن 👇",
    ])


@router.errors()
async def adm_errors(event: ErrorEvent) -> bool:
    exc = event.exception
    if exc and "message is not modified" in str(exc):
        cq = event.update.callback_query
        if cq:
            try:
                await cq.answer()
            except Exception:
                pass
        return True
    log.exception("⚠️ خطای پنل: %s", exc)
    return True


# ════════════════════════ ورود (/admin) ════════════════════════
@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    await state.clear()
    uid = message.from_user.id
    until = _BLOCKED.get(uid)
    if until and datetime.now() < until:
        mins = int((until - datetime.now()).total_seconds() // 60) + 1
        await message.answer(f"⛔ به دلیل ۳ تلاش اشتباه، موقتاً بلاک هستی.\n⏳ {mins} دقیقه دیگر تلاش کن.")
        return
    _BLOCKED.pop(uid, None)
    if is_admin(uid):
        await message.answer(await _home_text(), reply_markup=akb.panel_kb())
        return
    await state.set_state(AdminStates.login_username)
    await message.answer("🔐 ورود به پنل مدیریت\n" + SEP + "\nنام‌کاربری را وارد کن:", reply_markup=akb.cancel_kb())


@router.message(AdminStates.login_username, F.text)
async def login_username(message: Message, state: FSMContext) -> None:
    await state.update_data(uname=message.text.strip())
    await state.set_state(AdminStates.login_password)
    await message.answer("🔑 حالا رمز عبور را وارد کن:", reply_markup=akb.cancel_kb())


@router.message(AdminStates.login_password, F.text)
async def login_password(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id
    data = await state.get_data()
    try:
        await message.delete()  # رمز در چت نماند
    except Exception:
        pass
    if data.get("uname") == config.ADMIN_USERNAME and message.text and message.text.strip() == config.ADMIN_PASSWORD:
        LOGGED_IN.add(uid)
        _ATTEMPTS.pop(uid, None)
        await state.clear()
        await message.answer("✅ ورود موفق! خوش اومدی مدیر 👑")
        await message.answer(await _home_text(), reply_markup=akb.panel_kb())
        return
    left = MAX_ATTEMPTS - (_ATTEMPTS.get(uid, 0) + 1)
    _ATTEMPTS[uid] = _ATTEMPTS.get(uid, 0) + 1
    if left <= 0:
        _ATTEMPTS.pop(uid, None)
        _BLOCKED[uid] = datetime.now() + timedelta(minutes=BLOCK_MINUTES)
        await state.clear()
        await message.answer(f"⛔ نام‌کاربری یا رمز اشتباه بود.\nبه دلیل {MAX_ATTEMPTS} تلاش ناموفق، {BLOCK_MINUTES} دقیقه بلاک شدی.")
        return
    await state.set_state(AdminStates.login_username)
    await message.answer(f"❌ اشتباه بود! ({left} تلاش باقی ماند)\nنام‌کاربری را دوباره وارد کن:", reply_markup=akb.cancel_kb())


# ════════════════════════ پایه: پنل / noop / انصراف / خروج ════════════════════════
@router.callback_query(F.data == "ap:panel")
async def cb_panel(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    await state.clear()
    await _edit(cb, await _home_text(), akb.panel_kb())
    await cb.answer()


@router.callback_query(F.data == "ap:noop")
async def cb_noop(cb: CallbackQuery) -> None:
    await cb.answer()


@router.callback_query(F.data.startswith("ap:cancel:"))
async def cb_cancel(cb: CallbackQuery, state: FSMContext) -> None:
    """انصراف از هر فرم = برگشت دقیقاً یک مرحله به همان کارت/بخش (نه خروج از پنل)."""
    if not await _guard(cb):
        return
    payload = cb.data.split(":", 2)[-1]
    await state.clear()
    parts = payload.split(":")
    route = parts[0]
    try:
        if route == "pr" and len(parts) > 1:
            await _show_promo_item(cb, int(parts[1]))
        elif route == "pr":
            await _show_promos(cb)
        elif route == "prl" and len(parts) > 2:
            await _show_promo_link(cb, int(parts[1]), int(parts[2]))
        elif route == "cti" and len(parts) > 1:
            await _show_contact_item(cb, int(parts[1]))
        elif route == "ct":
            await _show_contacts(cb)
        elif route == "chi" and len(parts) > 1:
            await _show_channel_item(cb, int(parts[1]))
        elif route == "ch":
            await _show_channels(cb)
        elif route == "qshow" and len(parts) > 1:
            await _show_question_fixed(cb, parts[1])
        elif route == "cq" and len(parts) > 1:
            await _show_custom_q(cb, parts[1])
        elif route == "qs":
            await _show_questions(cb)
        elif route == "jb":
            await _show_jobs(cb)
        elif route == "uc" and len(parts) > 2:
            u = await db.get_user(int(parts[1]))
            if u:
                rc = await db.count_user_resumes(u[0])
                await _edit(cb, _user_card_text(u, rc), akb.user_card_kb(u[0], int(parts[2])))
            else:
                await _render_users(cb, 0)
        elif route == "users":
            await _render_users(cb, 0)
        else:
            await _edit(cb, await _home_text(), akb.panel_kb())
    except (ValueError, IndexError):
        await _edit(cb, await _home_text(), akb.panel_kb())
    await cb.answer("✖️ لغو شد — برگشتی یک مرحله عقب 🔙")


@router.callback_query(F.data == "ap:logout")
async def cb_logout(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    LOGGED_IN.discard(cb.from_user.id)
    await state.clear()
    await _edit(cb, "👋 از پنل مدیریت خارج شدی.\nبرای ورود دوباره: /admin")
    await cb.answer("خروج انجام شد ✅")


# ════════════════════════ 📊 آمار ربات ════════════════════════
@router.callback_query(F.data == "ap:stats")
async def cb_stats(cb: CallbackQuery, bot: Bot) -> None:
    if not await _guard(cb):
        return
    now = datetime.now()
    users = await db.count_users()
    resumes = await db.count_resumes()
    new_24h = await db.count_users_since((now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"))
    new_7d = await db.count_users_since((now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"))
    lines = [
        "📊 آمار زنده ربات",
        SEP,
        f"👥 کل کاربران: {users}",
        f"🆕 ۲۴ ساعت اخیر: {new_24h}",
        f"🗓 ۷ روز اخیر: {new_7d}",
        f"📄 رزومه‌های ثبت‌شده: {resumes}",
        SEP,
        f"🕒 {now:%Y-%m-%d %H:%M:%S}",
    ]
    await _edit(cb, "\n".join(lines), akb.stats_kb())
    await cb.answer("🔄 بروز شد")


# ════════════════════════ 📢 پیام همگانی ════════════════════════
@router.callback_query(F.data == "ap:bc")
async def cb_bc(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    if bcast.current_job and bcast.current_job.running:
        await cb.answer("⚠️ یک ارسال همگانی در حال انجام است؛ صبر کن تمام شود.", show_alert=True)
        return
    counts = await db.audience_counts()
    await _edit(
        cb,
        "📢 پیام همگانی\n" + SEP + "\nمخاطب را انتخاب کن:\n\n"
        f"👥 همه کاربران: {counts['all']:,} نفر\n"
        f"🔥 فعالان ۳۰ روز گذشته: {counts['active']:,} نفر\n"
        f"🚫 بلاک/حذف‌شده (حذف از ارسال): {counts['blocked']:,} نفر",
        akb.broadcast_audience_kb(counts),
    )
    await cb.answer()


@router.callback_query(F.data.in_({"ap:bc:aud:all", "ap:bc:aud:active"}))
async def cb_bc_audience(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    audience = "all" if cb.data.endswith(":all") else "active"
    label = "👥 همه کاربران" if audience == "all" else "🔥 فعالان ۳۰ روز گذشته"
    await state.update_data(bc_audience=audience, bc_audience_label=label)
    await state.set_state(AdminStates.broadcast_wait_message)
    await _edit(
        cb,
        "📢 پیام همگانی\n" + SEP + f"\n🎯 مخاطب: {label}\n\n"
        "هر نوع محتوایی بفرست (متن، عکس، ویدیو، فایل...)\n"
        "بعد از پیش‌نمایش و تأیید، ارسال شروع می‌شود.",
        akb.cancel_kb(),
    )
    await cb.answer()


@router.message(AdminStates.broadcast_wait_message)
async def bc_got_content(message: Message, bot: Bot, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    audience = data.get("bc_audience", "all")
    ids = await db.broadcast_user_ids(audience)
    await state.update_data(bc_chat=message.chat.id, bc_msg=message.message_id, bc_count=len(ids))
    await state.set_state(AdminStates.broadcast_confirm)
    label = data.get("bc_audience_label", "👥 همه کاربران")
    await message.answer("👁 پیش‌نمایش پیام تو 👇")
    await bot.copy_message(message.chat.id, message.chat.id, message.message_id)
    await message.answer(
        f"☝️ این پیام برای {label} ({len(ids):,} نفر) ارسال شود؟\n\n"
        "ℹ️ ارسال در پس‌زمینه انجام می‌شود و ربات فعال می‌ماند.",
        reply_markup=akb.broadcast_confirm_kb(len(ids)),
    )


@router.callback_query(F.data == "ap:bc:go", AdminStates.broadcast_confirm)
async def bc_send(cb: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    if bcast.current_job and bcast.current_job.running:
        await cb.answer("⚠️ یک ارسال در حال انجام است!", show_alert=True)
        return
    data = await state.get_data()
    src_chat, src_msg = data.get("bc_chat"), data.get("bc_msg")
    audience = data.get("bc_audience", "all")
    await state.clear()
    if not src_msg:
        await cb.answer("⚠️ پیامی برای ارسال نیست!", show_alert=True)
        return
    user_ids = await db.broadcast_user_ids(audience)
    if not user_ids:
        await cb.answer("⚠️ هیچ مخاطبی برای ارسال نیست!", show_alert=True)
        return
    await cb.answer(f"🚀 ارسال به {len(user_ids):,} کاربر آغاز شد")
    await _edit(
        cb,
        "🚀 ارسال همگانی آغاز شد!\n" + SEP + "\n"
        f"👥 هدف: {len(user_ids):,} نفر\n\n"
        "گزارش زنده‌ی پیشرفت را در پیام بعدی دنبال کن 👇\n"
        "می‌توانی هم‌زمان به کارهای دیگه‌ات در پنل برسی.",
        akb.back_kb(),
    )
    asyncio.create_task(
        bcast.run_broadcast(
            bot,
            admin_chat_id=cb.message.chat.id,
            src_chat=src_chat,
            src_msg=src_msg,
            user_ids=user_ids,
            finish_kb=akb.back_kb(),
        )
    )


@router.callback_query(F.data == "ap:bc:stop")
async def bc_stop(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    job = bcast.current_job
    if job and job.running:
        job.stop_requested = True
        await cb.answer("🛑 در حال توقف ارسال...")
    else:
        await cb.answer("ارسال فعالی وجود ندارد.", show_alert=True)


# ════════════════════════ 📥 خروجی و بکاپ ════════════════════════
def _csv_doc(headers: list[str], rows: list[tuple], filename: str) -> BufferedInputFile:
    buf = io.StringIO()
    buf.write("﻿")  # BOM برای اکسل فارسی
    w = csv.writer(buf)
    w.writerow(headers)
    w.writerows(rows)
    return BufferedInputFile(buf.getvalue().encode("utf-8"), filename=filename)


@router.callback_query(F.data == "ap:csv")
async def cb_csv(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    await _edit(cb, "📥 خروجی و بکاپ\n" + SEP + "\nCSVها با اکسل فارسی سازگارند (BOM).", akb.csv_kb())
    await cb.answer()


@router.callback_query(F.data == "ap:csv:users")
async def cb_csv_users(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    rows = await db.list_users(0, 100000)
    doc = _csv_doc(
        ["user_id", "username", "first_name", "last_name", "first_seen", "last_seen"],
        rows, f"users_{datetime.now():%Y%m%d_%H%M}.csv",
    )
    await cb.message.answer_document(doc, caption=f"👥 CSV کاربران — {len(rows)} ردیف")
    await cb.answer("📥 ارسال شد")


@router.callback_query(F.data == "ap:csv:resumes")
async def cb_csv_resumes(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    rows = await db.list_resumes(100000)
    norm = []
    for r in rows:
        extras = r[14] if len(r) > 14 else None
        try:
            pairs = json.loads(extras) if extras else []
            extras_txt = " | ".join(f"{p.get('text','')}: {p.get('answer','')}" for p in pairs)
        except Exception:
            extras_txt = str(extras or "")
        norm.append((*r[:14], extras_txt))
    doc = _csv_doc(
        ["id", "user_id", "username", "job", "fullname", "province", "city", "birthdate",
         "education", "major", "experience", "skills", "resume", "created_at", "extra_answers"],
        norm, f"resumes_{datetime.now():%Y%m%d_%H%M}.csv",
    )
    await cb.message.answer_document(doc, caption=f"📄 CSV رزومه‌ها — {len(rows)} ردیف")
    await cb.answer("📥 ارسال شد")


@router.callback_query(F.data == "ap:csv:db")
async def cb_csv_db(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    if not os.path.exists(db.DB_PATH):
        await cb.answer("⚠️ فایل دیتابیس هنوز ساخته نشده!", show_alert=True)
        return
    with open(db.DB_PATH, "rb") as f:
        payload = f.read()
    doc = BufferedInputFile(payload, filename=f"bot_{datetime.now():%Y%m%d_%H%M}.db")
    await cb.message.answer_document(doc, caption="📦 بکاپ کامل فایل دیتابیس (SQLite)")
    await cb.answer("📦 ارسال شد")


# ════════════════════════ 👥 مدیریت کاربران ════════════════════════
async def _render_users(cb: CallbackQuery, page: int) -> None:
    total = await db.count_users()
    total_pages = max(1, (total + akb.PAGE_SIZE - 1) // akb.PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    users = await db.list_users(page * akb.PAGE_SIZE, akb.PAGE_SIZE)
    if not users:
        await _edit(cb, "👥 هنوز هیچ کاربری ثبت نشده!", akb.back_kb())
        return
    text = f"👥 مدیریت کاربران — {total} نفر\n{SEP}\nروی هر کاربر بزن تا کارتش باز شود 👇"
    await _edit(cb, text, akb.users_page_kb(users, page, total_pages))


@router.callback_query(F.data == "ap:users")
async def cb_users(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    await _render_users(cb, 0)
    await cb.answer()


@router.callback_query(F.data.startswith("ap:users:p:"))
async def cb_users_page(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    await _render_users(cb, int(cb.data.split(":")[-1]))
    await cb.answer()


@router.callback_query(F.data == "ap:users:search")
async def cb_users_search(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    await state.set_state(AdminStates.user_search_query)
    await _edit(cb, "🔍 جستجوی کاربر\n" + SEP + "\nنام، یوزرنیم (با یا بدون @) یا آیدی عددی را بفرست:", akb.cancel_kb("users"))
    await cb.answer()


@router.message(AdminStates.user_search_query, F.text)
async def users_search_query(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    results = await db.search_users(message.text, limit=10)
    if not results:
        await message.answer("🔍 چیزی پیدا نشد! دوباره از لیست تلاش کن 👇", reply_markup=akb.back_kb("users"))
        return
    await message.answer(f"🔍 {len(results)} نتیجه — روی کاربر بزن 👇", reply_markup=akb.search_results_kb(results))


async def _show_contact_item(cb: CallbackQuery, idx: int) -> None:
    items = await content.get_contact_buttons()
    if idx >= len(items):
        await cb.answer("⚠️ دکمه پیدا نشد.", show_alert=True)
        return
    it = items[idx]
    tname = {"url": "🔗 لینک", "webapp": "📱 مینی‌اپ", "alert": "🔔 آلرت"}.get(it.get("type"), it.get("type"))
    text = "\n".join([
        f"📞 دکمه: {it['text']}",
        SEP,
        f"نوع: {tname}",
        f"مقدار: {it['value']}",
        f"ردیف چیدمان: {it.get('row', 99)}",
    ])
    await _edit(cb, text, akb.contact_item_kb(idx))


async def _show_questions(cb: CallbackQuery) -> None:
    customs = await content.get_custom_questions()
    text = (f"📝 متن سؤال‌های فرم استخدام\n{SEP}\n"
            f"۹ سؤال ثابت + {len(customs)} سؤال سفارشی\n"
            "⭐ سؤال‌های سفارشی بعد از سؤال ۹ و به ترتیب پرسیده می‌شوند.\n\nانتخاب کن 👇")
    await _edit(cb, text, akb.questions_kb(list(config.FSM_QUESTIONS), customs))


async def _show_question_fixed(cb: CallbackQuery, key: str) -> None:
    keys = list(config.FSM_QUESTIONS)
    if key not in keys:
        await cb.answer("⚠️ سؤال نامعتبر!", show_alert=True)
        return
    num = keys.index(key) + 1
    text = await content.get_question(key)
    await _edit(cb, f"📝 سؤال {num} از ۹ (ثابت)\n{SEP}\n{text}", akb.question_edit_kb(key))


async def _show_custom_q(cb: CallbackQuery, key: str) -> None:
    customs = await content.get_custom_questions()
    cq = next((c for c in customs if c["key"] == key), None)
    if not cq:
        await cb.answer("⚠️ سؤال پیدا نشد.", show_alert=True)
        return
    idx = customs.index(cq)
    await _edit(cb, f"⭐ سؤال سفارشی {9 + idx + 1} فرم\n{SEP}\n{cq['text']}", akb.custom_question_kb(key))


def _user_card_text(u: tuple, resumes_count: int) -> str:
    uid, username, first_name, last_name, first_seen, last_seen = u
    name = f"{first_name or ''} {last_name or ''}".strip() or "—"
    return "\n".join([
        "👤 کارت کاربر",
        SEP,
        f"🪪 نام: {name}",
        f"🔗 یوزرنیم: {'@' + username if username else '—'}",
        f"🆔 آیدی عددی: {uid}",
        f"📄 رزومه‌ها: {resumes_count}",
        SEP,
        f"📅 اولین ورود: {first_seen or '—'}",
        f"🕓 آخرین بازدید: {last_seen or '—'}",
    ])


@router.callback_query(F.data.startswith("ap:uc:show:"))
async def cb_user_card(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    _, _, _, uid_s, page_s = cb.data.split(":")
    uid, page = int(uid_s), int(page_s)
    u = await db.get_user(uid)
    if not u:
        await cb.answer("⚠️ کاربر پیدا نشد (شاید حذف شده).", show_alert=True)
        return
    rc = await db.count_user_resumes(uid)
    await _edit(cb, _user_card_text(u, rc), akb.user_card_kb(uid, page))
    await cb.answer()


@router.callback_query(F.data.startswith("ap:uc:res:"))
async def cb_user_resumes(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    _, _, _, uid_s, page_s = cb.data.split(":")
    uid, page = int(uid_s), int(page_s)
    resumes = await db.get_user_resumes(uid)
    if not resumes:
        await cb.answer("📄 این کاربر رزومه‌ای ندارد.", show_alert=True)
        return
    await _edit(cb, f"📄 رزومه‌های کاربر {uid}\n{SEP}\nبرای مشاهده کامل روی هر یک بزن 👇", akb.user_resumes_kb(resumes, uid, page))
    await cb.answer()


@router.callback_query(F.data.startswith("ap:uc:resv:"))
async def cb_user_resume_view(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    _, _, _, rid_s, uid_s, page_s = cb.data.split(":")
    rid, uid, page = int(rid_s), int(uid_s), int(page_s)
    r = await db.get_resume(rid)
    if not r:
        await cb.answer("⚠️ رزومه پیدا نشد.", show_alert=True)
        return
    (_id, _uid, uname, job, fullname, province, city, birthdate,
     education, major, experience, skills, resume, created) = r
    text = "\n".join([
        f"📄 رزومه #{_id} | {job}",
        SEP,
        f"👤 نام: {fullname}",
        f"📍 استان/شهر: {province} / {city}",
        f"🎂 تولد: {birthdate}",
        f"🎓 مدرک: {education}",
        f"📚 رشته: {major}",
        f"📌 سابقه: {experience}",
        f"🛠 مهارت‌ها: {skills}",
        f"📝 توضیحات: {resume}",
        SEP,
        f"🔗 {'@' + uname if uname else '—'} | 🆔 {_uid} | 🕒 {created}",
    ])
    await _edit(cb, text[:4000], akb.resume_view_kb(uid, page))
    await cb.answer()


@router.callback_query(F.data.startswith("ap:uc:msg:"))
async def cb_user_message(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    _, _, _, uid_s, page_s = cb.data.split(":")
    await state.update_data(target_uid=int(uid_s), target_page=int(page_s))
    await state.set_state(AdminStates.user_message_text)
    await _edit(cb, f"✉️ ارسال پیام به کاربر {uid_s}\n{SEP}\n💡 مثال: سلام! کلاس جدید از هفته آینده شروع می‌شود 🌱\nمتن پیام را بفرست:", akb.cancel_kb(f"uc:{uid_s}:{page_s}"))
    await cb.answer()


@router.message(AdminStates.user_message_text, F.text)
async def user_message_send(message: Message, bot: Bot, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    await state.clear()
    uid, page = data.get("target_uid"), data.get("target_page", -1)
    try:
        await bot.send_message(uid, f"📩 پیام از مدیریت «قیومی‌بات»:\n{SEP}\n{message.text.strip()}")
        u = await db.get_user(uid)
        rc = await db.count_user_resumes(uid)
        if u:
            await message.answer("✅ پیام ارسال شد!\n\n" + _user_card_text(u, rc), reply_markup=akb.user_card_kb(uid, page))
        else:
            await message.answer("✅ پیام ارسال شد!", reply_markup=akb.back_kb("users"))
    except Exception as exc:
        await message.answer(f"❌ ارسال نشد: {exc}", reply_markup=akb.back_kb("users"))


@router.callback_query(F.data.startswith("ap:uc:del:"))
async def cb_user_delete(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    _, _, _, uid_s, page_s = cb.data.split(":")
    uid, page = int(uid_s), int(page_s)
    await _edit(
        cb,
        f"🗑 حذف کاربر {uid}\n{SEP}\n⚠️ کاربر از لیست حذف می‌شود (رزومه‌هایش در خروجی CSV باقی می‌ماند).\nمطمئنی؟",
        akb.user_delete_confirm_kb(uid, page),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("ap:uc:delok:"))
async def cb_user_delete_ok(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    _, _, _, uid_s, page_s = cb.data.split(":")
    uid, page = int(uid_s), int(page_s)
    done = await db.delete_user(uid)
    if done:
        await cb.answer("🗑 کاربر حذف شد ✅")
        await _render_users(cb, max(0, page))
    else:
        await cb.answer("⚠️ کاربری با این آیدی نبود!", show_alert=True)


# ════════════════════════ 📣 کانال‌های جوین ════════════════════════
def _channels_text(channels: list[dict]) -> str:
    lines = ["📣 کانال‌های جوین اجباری", SEP]
    if not channels:
        lines.append("— هیچ کانالی ثبت نشده (قفل جوین خاموش است) —")
    for i, ch in enumerate(channels, 1):
        lines.append(f"{i}. {ch['username']} | {ch['title']}")
    lines.append(f"{SEP}\nروی هر کانال بزن برای ویرایش/حذف 👇")
    return "\n".join(lines)


async def _show_channels(cb: CallbackQuery) -> None:
    channels = await content.get_channels()
    await _edit(cb, _channels_text(channels), akb.channels_kb(channels))


async def _show_channel_item(cb: CallbackQuery, idx: int) -> None:
    channels = await content.get_channels()
    if idx >= len(channels):
        await cb.answer("⚠️ کانال پیدا نشد.", show_alert=True)
        return
    ch = channels[idx]
    text = "\n".join([
        f"📣 کانال: {ch['title']}",
        SEP,
        f"🔗 یوزرنیم: {ch['username']}",
        f"🔘 متن دکمه: {ch['button']}",
    ])
    await _edit(cb, text, akb.channel_item_kb(idx))


@router.callback_query(F.data == "ap:ch")
async def cb_channels(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    await _show_channels(cb)
    await cb.answer()


@router.callback_query(F.data.startswith("ap:ch:show:"))
async def cb_channel_show(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    await _show_channel_item(cb, int(cb.data.split(":")[-1]))
    await cb.answer()


async def _channel_edit_prompt(cb: CallbackQuery, state: FSMContext, state_name, field_label: str, field_key: str, example: str) -> None:
    idx = int(cb.data.split(":")[-1])
    channels = await content.get_channels()
    if idx >= len(channels):
        await cb.answer("⚠️ کانال پیدا نشد.", show_alert=True)
        return
    current = channels[idx].get(field_key, "—")
    await state.update_data(ch_idx=idx)
    await state.set_state(state_name)
    await _edit(cb, f"{field_label}\n{SEP}\nℹ️ مقدار فعلی:\n«{current}»\n💡 مثال: {example}\n{SEP}\nمقدار جدید را بفرست:", akb.cancel_kb(f"chi:{idx}"))
    await cb.answer()


@router.callback_query(F.data.startswith("ap:ch:et:"))
async def cb_channel_edit_title(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    await _channel_edit_prompt(cb, state, AdminStates.channel_edit_title, "✏️ ویرایش عنوان کانال", "title", "آکادمی آریامیر")


@router.callback_query(F.data.startswith("ap:ch:eu:"))
async def cb_channel_edit_username(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    await _channel_edit_prompt(cb, state, AdminStates.channel_edit_username, "🔗 ویرایش یوزرنیم کانال (با @)", "username", "@MyChannel")


@router.callback_query(F.data.startswith("ap:ch:eb:"))
async def cb_channel_edit_button(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    await _channel_edit_prompt(cb, state, AdminStates.channel_edit_button, "🖊 ویرایش متن دکمه عضویت", "button", "عضویت در کانال آریامیر")


async def _channel_edit_save(message: Message, state: FSMContext, field: str, validator=None, err: str = "") -> None:
    if not is_admin(message.from_user.id):
        return
    if validator and not validator(message.text.strip()):
        await message.answer(err + " دوباره بفرست:")
        return
    data = await state.get_data()
    await state.clear()
    channels = await content.get_channels()
    idx = data.get("ch_idx", -1)
    if 0 <= idx < len(channels):
        channels[idx][field] = message.text.strip()
        await content.set_channels(channels)
        await message.answer(f"✅ ذخیره شد: «{channels[idx][field]}»", reply_markup=akb.back_kb(f"ch:show:{idx}"))
    else:
        await message.answer("⚠️ کانال پیدا نشد.", reply_markup=akb.back_kb("ch"))


@router.message(AdminStates.channel_edit_title, F.text)
async def channel_title_save(message: Message, state: FSMContext) -> None:
    await _channel_edit_save(message, state, "title")


@router.message(AdminStates.channel_edit_username, F.text)
async def channel_username_save(message: Message, state: FSMContext) -> None:
    await _channel_edit_save(
        message, state, "username",
        validator=lambda v: v.startswith("@"),
        err="⚠️ یوزرنیم باید با @ شروع شود!",
    )


@router.message(AdminStates.channel_edit_button, F.text)
async def channel_button_save(message: Message, state: FSMContext) -> None:
    await _channel_edit_save(message, state, "button")


@router.callback_query(F.data.startswith("ap:ch:d:"))
async def cb_channel_delete(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    idx = int(cb.data.split(":")[-1])
    channels = await content.get_channels()
    if idx >= len(channels):
        await cb.answer("⚠️ کانال پیدا نشد.", show_alert=True)
        return
    await _edit(cb, f"🗑 حذف «{channels[idx]['title']}» ({channels[idx]['username']})\n{SEP}\nمطمئنی؟", akb.channel_delete_confirm_kb(idx))
    await cb.answer()


@router.callback_query(F.data.startswith("ap:ch:dok:"))
async def cb_channel_delete_ok(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    idx = int(cb.data.split(":")[-1])
    channels = await content.get_channels()
    if 0 <= idx < len(channels):
        gone = channels.pop(idx)
        await content.set_channels(channels)
        await cb.answer(f"🗑 «{gone['title']}» حذف شد")
    await _show_channels(cb)


@router.callback_query(F.data == "ap:ch:add")
async def cb_channel_add(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    await state.set_state(AdminStates.channel_add_username)
    await _edit(cb, "➕ افزودن کانال — مرحله ۱ از ۳\n" + SEP + "\nیوزرنیم کانال را بفرست (مثل @MyChannel):", akb.cancel_kb("ch"))
    await cb.answer()


@router.message(AdminStates.channel_add_username, F.text)
async def channel_add_username(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    uname = message.text.strip()
    if not uname.startswith("@"):
        await message.answer("⚠️ یوزرنیم باید با @ شروع شود! دوباره بفرست:")
        return
    await state.update_data(new_ch_username=uname)
    await state.set_state(AdminStates.channel_add_title)
    await message.answer("➕ مرحله ۲ از ۳\nعنوان کانال را بفرست (مثل: آکادمی آریامیر):")


@router.message(AdminStates.channel_add_title, F.text)
async def channel_add_title(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.update_data(new_ch_title=message.text.strip())
    await state.set_state(AdminStates.channel_add_button)
    await message.answer("➕ مرحله ۳ از ۳\nمتن دکمه عضویت را بفرست (مثل: عضویت در کانال آکادمی):")


@router.message(AdminStates.channel_add_button, F.text)
async def channel_add_button(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    await state.clear()
    channels = await content.get_channels()
    channels.append({
        "username": data["new_ch_username"],
        "title": data["new_ch_title"],
        "button": message.text.strip(),
    })
    await content.set_channels(channels)
    await message.answer(f"✅ کانال «{data['new_ch_title']}» اضافه شد!", reply_markup=akb.back_kb("ch"))


# ════════════════════════ 🎁 دکمه‌های بالای منو ════════════════════════
def _promos_text(promos: list[dict]) -> str:
    lines = ["🎁 دکمه‌های بالای منو (پیام اول ربات)", SEP]
    if not promos:
        lines.append("— هیچ دکمه‌ای ثبت نشده —")
    for i, p in enumerate(promos, 1):
        n_links = len(p.get("buttons") or [])
        lines.append(f"{i}. {p['button_text']}  (🔗 {n_links} لینک)")
    lines.append(f"{SEP}\nروی هر دکمه بزن تا کارت مدیریتش باز شود 👇")
    return "\n".join(lines)


async def _show_promos(cb: CallbackQuery) -> None:
    promos = await content.get_promos()
    await _edit(cb, _promos_text(promos), akb.promos_kb(promos))


def _promo_item_text(promo: dict) -> str:
    links = promo.get("buttons") or []
    body_prev = (promo.get("body") or "")[:60] + ("…" if len(promo.get("body") or "") > 60 else "")
    lines = [
        f"🎁 کارت دکمه: {promo['button_text']}",
        SEP,
        f"📝 متن محتوا:\n«{body_prev}»",
        f"📎 فایل ضمیمه: {'✅ دارد' if promo.get('file_id') else '❌ ندارد'}",
        f"🔗 لینک‌های پایین متن: {len(links)}",
    ]
    for i, b in enumerate(links, 1):
        icon = "📱" if b.get("type") == "webapp" else "🔗"
        lines.append(f"  {i}. {icon} {b['label']}")
    lines.append(f"{SEP}\nهر بخش را با دکمه‌های زیر مدیریت کن 👇")
    return "\n".join(lines)


async def _show_promo_item(cb: CallbackQuery, idx: int) -> None:
    promos = await content.get_promos()
    if idx >= len(promos):
        await cb.answer("⚠️ دکمه پیدا نشد (شاید حذف شده).", show_alert=True)
        return
    await _edit(cb, _promo_item_text(promos[idx]), akb.promo_item_kb(promos[idx], idx))


def _promo_link_text(promo: dict, li: int) -> str:
    b = promo["buttons"][li]
    btype = "📱 مینی‌اپ" if b.get("type") == "webapp" else "🔗 لینک معمولی"
    return "\n".join([
        f"🔗 کارت لینک «{b['label']}»",
        SEP,
        f"🖊 متن دکمه: {b['label']}",
        f"🌐 آدرس: {b['url']}",
        f"🔀 نوع: {btype}",
        SEP,
        "هر بخش را با دکمه‌های زیر ویرایش کن 👇",
    ])


async def _show_promo_link(cb: CallbackQuery, idx: int, li: int) -> None:
    promos = await content.get_promos()
    if idx >= len(promos) or li >= len(promos[idx].get("buttons") or []):
        await cb.answer("⚠️ لینک پیدا نشد (شاید حذف شده).", show_alert=True)
        return
    await _edit(cb, _promo_link_text(promos[idx], li), akb.promo_link_item_kb(idx, li))


@router.callback_query(F.data == "ap:pr")
async def cb_promos(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    await _show_promos(cb)
    await cb.answer()


@router.callback_query(F.data.startswith("ap:pr:show:"))
async def cb_promo_show(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    await _show_promo_item(cb, int(cb.data.split(":")[-1]))
    await cb.answer()


# ── کارت: ویرایش متن دکمه ──
@router.callback_query(F.data.startswith("ap:pr:eb:"))
async def cb_promo_edit_btn(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    idx = int(cb.data.split(":")[-1])
    await state.update_data(pr_idx=idx)
    promos = await content.get_promos()
    current = promos[idx]["button_text"] if 0 <= idx < len(promos) else "—"
    await state.set_state(AdminStates.promo_edit_btn_text)
    await _edit(cb, "✏️ ویرایش متن دکمه\n" + SEP + f"\nℹ️ متن فعلی: «{current}»\n💡 مثال: [جزوه پیش‌بینی فیزیک دوازدهم نهایی]\n" + SEP + "\nمتن جدید را بفرست:", akb.cancel_kb(f"pr:{idx}"))
    await cb.answer()


@router.message(AdminStates.promo_edit_btn_text, F.text)
async def promo_edit_btn_save(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    await state.clear()
    promos = await content.get_promos()
    idx = data.get("pr_idx", -1)
    if 0 <= idx < len(promos):
        promos[idx]["button_text"] = message.text.strip()
        await content.set_promos(promos)
        await message.answer(f"✅ متن دکمه عوض شد: «{promos[idx]['button_text']}»", reply_markup=akb.back_kb("pr"))
    else:
        await message.answer("⚠️ دکمه پیدا نشد.", reply_markup=akb.back_kb("pr"))


# ── کارت: ویرایش متن محتوا ──
@router.callback_query(F.data.startswith("ap:pr:ebody:"))
async def cb_promo_edit_body(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    idx = int(cb.data.split(":")[-1])
    await state.update_data(pr_idx=idx)
    promos = await content.get_promos()
    cur_body = "—" if not (0 <= idx < len(promos)) else (promos[idx]["body"][:120] + ("…" if len(promos[idx]["body"]) > 120 else ""))
    await state.set_state(AdminStates.promo_edit_body)
    await _edit(cb, "📝 ویرایش متن محتوا\n" + SEP + f"\nℹ️ متن فعلی:\n«{cur_body}»\n" + SEP + "\nمتن جدید را بفرست:", akb.cancel_kb(f"pr:{idx}"))
    await cb.answer()


@router.message(AdminStates.promo_edit_body, F.text)
async def promo_edit_body_save(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    await state.clear()
    promos = await content.get_promos()
    idx = data.get("pr_idx", -1)
    if 0 <= idx < len(promos):
        promos[idx]["body"] = message.text.strip()
        await content.set_promos(promos)
        await message.answer("✅ متن محتوا عوض شد!", reply_markup=akb.back_kb("pr"))
    else:
        await message.answer("⚠️ دکمه پیدا نشد.", reply_markup=akb.back_kb("pr"))


# ── کارت: فایل ضمیمه ──
@router.callback_query(F.data.startswith("ap:pr:fileset:"))
async def cb_promo_fileset(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    idx = int(cb.data.split(":")[-1])
    await state.update_data(pr_idx=idx)
    await state.set_state(AdminStates.promo_set_file)
    await _edit(cb, "📎 ست فایل ضمیمه\n" + SEP + "\nفایل (سند — PDF/زیپ/...) را همین‌جا بفرست:", akb.cancel_kb(f"pr:{idx}"))
    await cb.answer()


@router.message(AdminStates.promo_set_file, F.document)
async def promo_file_save(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    await state.clear()
    promos = await content.get_promos()
    idx = data.get("pr_idx", -1)
    if 0 <= idx < len(promos):
        promos[idx]["file_id"] = message.document.file_id
        await content.set_promos(promos)
        await message.answer("✅ فایل ضمیمه ست شد!", reply_markup=akb.back_kb("pr"))
    else:
        await message.answer("⚠️ دکمه پیدا نشد.", reply_markup=akb.back_kb("pr"))


@router.message(AdminStates.promo_set_file)
async def promo_file_guard(message: Message) -> None:
    if is_admin(message.from_user.id):
        await message.answer("⚠️ لطفاً یک «فایل/سند» بفرست (نه متن/عکس).")


@router.callback_query(F.data.startswith("ap:pr:filedel:"))
async def cb_promo_filedel(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    idx = int(cb.data.split(":")[-1])
    promos = await content.get_promos()
    if idx < len(promos):
        promos[idx]["file_id"] = None
        await content.set_promos(promos)
        await cb.answer("🗑 فایل ضمیمه حذف شد")
    await _show_promo_item(cb, idx)


# ── کارت: لینک‌ها (نمایش/حذف/افزودن) ──
@router.callback_query(F.data.startswith("ap:pr:lshow:"))
async def cb_promo_link_show(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    _, _, _, i_s, li_s = cb.data.split(":")
    await _show_promo_link(cb, int(i_s), int(li_s))
    await cb.answer()


@router.callback_query(F.data.startswith("ap:pr:lel:"))
async def cb_promo_link_edit_label(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    _, _, _, i_s, li_s = cb.data.split(":")
    idx, li = int(i_s), int(li_s)
    promos = await content.get_promos()
    try:
        b = promos[idx]["buttons"][li]
    except (IndexError, KeyError):
        await cb.answer("⚠️ لینک پیدا نشد.", show_alert=True)
        return
    await state.update_data(pr_idx=idx, pr_li=li)
    await state.set_state(AdminStates.promo_link_edit_label)
    await _edit(
        cb,
        f"✏️ ویرایش متن دکمه لینک\n{SEP}\nℹ️ متن فعلی: «{b['label']}»\n💡 مثال: دریافت رایگان جزوه\n{SEP}\nمتن جدید را بفرست:",
        akb.cancel_kb(f"prl:{idx}:{li}"),
    )
    await cb.answer()


@router.message(AdminStates.promo_link_edit_label, F.text)
async def promo_link_edit_label_save(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    await state.clear()
    promos = await content.get_promos()
    idx, li = data.get("pr_idx", -1), data.get("pr_li", -1)
    if 0 <= idx < len(promos) and 0 <= li < len(promos[idx].get("buttons") or []):
        promos[idx]["buttons"][li]["label"] = message.text.strip()
        await content.set_promos(promos)
        await message.answer(f"✅ متن دکمه لینک عوض شد: «{promos[idx]['buttons'][li]['label']}»", reply_markup=akb.back_kb(f"pr:lshow:{idx}:{li}"))
    else:
        await message.answer("⚠️ لینک پیدا نشد.", reply_markup=akb.back_kb("pr"))


@router.callback_query(F.data.startswith("ap:pr:leu:"))
async def cb_promo_link_edit_url(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    _, _, _, i_s, li_s = cb.data.split(":")
    idx, li = int(i_s), int(li_s)
    promos = await content.get_promos()
    try:
        b = promos[idx]["buttons"][li]
    except (IndexError, KeyError):
        await cb.answer("⚠️ لینک پیدا نشد.", show_alert=True)
        return
    await state.update_data(pr_idx=idx, pr_li=li)
    await state.set_state(AdminStates.promo_link_edit_url)
    await _edit(
        cb,
        f"🔗 ویرایش آدرس لینک\n{SEP}\nℹ️ آدرس فعلی:\n«{b['url']}»\n💡 مثال: https://t.me/MyChannel\n{SEP}\nآدرس جدید را بفرست:",
        akb.cancel_kb(f"prl:{idx}:{li}"),
    )
    await cb.answer()


@router.message(AdminStates.promo_link_edit_url, F.text)
async def promo_link_edit_url_save(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    url = message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await message.answer("⚠️ لینک باید با http یا https شروع شود! دوباره بفرست:")
        return
    data = await state.get_data()
    await state.clear()
    promos = await content.get_promos()
    idx, li = data.get("pr_idx", -1), data.get("pr_li", -1)
    if 0 <= idx < len(promos) and 0 <= li < len(promos[idx].get("buttons") or []):
        promos[idx]["buttons"][li]["url"] = url
        await content.set_promos(promos)
        await message.answer(f"✅ آدرس لینک عوض شد!", reply_markup=akb.back_kb(f"pr:lshow:{idx}:{li}"))
    else:
        await message.answer("⚠️ لینک پیدا نشد.", reply_markup=akb.back_kb("pr"))


@router.callback_query(F.data.startswith("ap:pr:ld:"))
async def cb_promo_link_del(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    _, _, _, i_s, li_s = cb.data.split(":")
    promos = await content.get_promos()
    idx, li = int(i_s), int(li_s)
    if idx < len(promos) and li < len(promos[idx].get("buttons") or []):
        gone = promos[idx]["buttons"].pop(li)
        await content.set_promos(promos)
        await cb.answer(f"🗑 «{gone['label']}» حذف شد")
    await _show_promo_item(cb, idx)


@router.callback_query(F.data.startswith("ap:pr:la:"))
async def cb_promo_link_add(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    idx = int(cb.data.split(":")[-1])
    await state.update_data(pr_idx=idx)
    await state.set_state(AdminStates.promo_link_label)
    await _edit(cb, "➕ افزودن لینک — مرحله ۱ از ۳\n" + SEP + "\n💡 مثال: دریافت رایگان جزوه\nمتن دکمه لینک را بفرست:", akb.cancel_kb(f"pr:{idx}"))
    await cb.answer()


@router.message(AdminStates.promo_link_label, F.text)
async def promo_link_label(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.update_data(new_label=message.text.strip())
    await state.set_state(AdminStates.promo_link_type)
    await message.answer("➕ مرحله ۲ از ۳\nنوع دکمه را انتخاب کن:", reply_markup=akb.promo_link_type_kb())


@router.callback_query(F.data.startswith("ap:pr:ltype:"), AdminStates.promo_link_type)
async def promo_link_type(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    await state.update_data(new_type=cb.data.split(":")[-1])
    await state.set_state(AdminStates.promo_link_url)
    _idx = (await state.get_data()).get("pr_idx", 0)
    await _edit(cb, "➕ مرحله ۳ از ۳\n💡 مثال: https://t.me/MyChannel\nلینک (URL) را بفرست:", akb.cancel_kb(f"pr:{_idx}"))
    await cb.answer()


@router.message(AdminStates.promo_link_url, F.text)
async def promo_link_url(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    url = message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await message.answer("⚠️ لینک باید با http یا https شروع شود! دوباره بفرست:")
        return
    data = await state.get_data()
    await state.clear()
    promos = await content.get_promos()
    idx = data.get("pr_idx", -1)
    if 0 <= idx < len(promos):
        promos[idx].setdefault("buttons", []).append({"label": data["new_label"], "url": url, "type": data["new_type"]})
        await content.set_promos(promos)
        await message.answer(f"✅ لینک «{data['new_label']}» اضافه شد!", reply_markup=akb.back_kb("pr"))
    else:
        await message.answer("⚠️ دکمه پیدا نشد.", reply_markup=akb.back_kb("pr"))


# ── کارت: حذف کل دکمه ──
@router.callback_query(F.data.startswith("ap:pr:del:"))
async def cb_promo_delete(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    idx = int(cb.data.split(":")[-1])
    promos = await content.get_promos()
    if idx >= len(promos):
        await cb.answer("⚠️ دکمه پیدا نشد.", show_alert=True)
        return
    await _edit(cb, f"🗑 حذف دکمه «{promos[idx]['button_text']}»\n{SEP}\nاین دکمه با همه لینک‌هاش حذف می‌شود. مطمئنی؟", akb.promo_delete_confirm_kb(idx))
    await cb.answer()


@router.callback_query(F.data.startswith("ap:pr:delok:"))
async def cb_promo_delete_ok(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    idx = int(cb.data.split(":")[-1])
    promos = await content.get_promos()
    if 0 <= idx < len(promos):
        gone = promos.pop(idx)
        await content.set_promos(promos)
        await cb.answer(f"🗑 «{gone['button_text']}» حذف شد")
    await _show_promos(cb)


# ── ➕ افزودن دکمه جدید (مرحله‌به‌مرحله: دکمه ← محتوا ← لینک) ──
@router.callback_query(F.data == "ap:pr:add")
async def cb_promo_add(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    await state.set_state(AdminStates.promo_add_btn_text)
    await _edit(cb, "➕ افزودن دکمه جدید — مرحله ۱ از ۴\n" + SEP + "\nمتن دکمه را بفرست\n(همونی که بالای منو دیده می‌شه — مثل: [جزوه پیش‌بینی فیزیک دوازدهم نهایی]):", akb.cancel_kb("pr"))
    await cb.answer()


@router.message(AdminStates.promo_add_btn_text, F.text)
async def promo_add_btn_text(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.update_data(new_btn_text=message.text.strip())
    await state.set_state(AdminStates.promo_add_body)
    await message.answer("➕ مرحله ۲ از ۴\nمتن محتوا (پیامی که با کلیک روی دکمه نمایش داده می‌شه) را بفرست:")


@router.message(AdminStates.promo_add_body, F.text)
async def promo_add_body(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.update_data(new_body=message.text.strip())
    await state.set_state(AdminStates.promo_add_link_label)
    await message.answer("➕ مرحله ۳ از ۴\nمتن دکمه لینک پایین متن را بفرست (مثل: دریافت از کانال)\nیا فقط «-» بفرست اگر لینک نمی‌خوای:")


@router.message(AdminStates.promo_add_link_label, F.text)
async def promo_add_link_label(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    label = message.text.strip()
    if label == "-":
        await _promo_add_finish(message, state, None, None)
        return
    await state.update_data(new_link_label=label)
    await state.set_state(AdminStates.promo_add_link_url)
    await message.answer("➕ مرحله ۴ از ۴\nلینک (URL با http) را بفرست:")


@router.message(AdminStates.promo_add_link_url, F.text)
async def promo_add_link_url(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    url = message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await message.answer("⚠️ لینک باید با http یا https شروع شود! دوباره بفرست:")
        return
    data = await state.get_data()
    await _promo_add_finish(message, state, data.get("new_link_label"), url)


async def _promo_add_finish(message: Message, state: FSMContext, link_label, link_url) -> None:
    data = await state.get_data()
    await state.clear()
    promos = await content.get_promos()
    promo = {
        "id": f"promo_{int(datetime.now().timestamp())}",
        "button_text": data["new_btn_text"],
        "body": data["new_body"],
        "file_id": None,
        "buttons": [],
    }
    if link_label and link_url:
        promo["buttons"].append({"label": link_label, "url": link_url, "type": "url"})
    promos.append(promo)
    await content.set_promos(promos)
    await message.answer(
        f"🎉 دکمه «{promo['button_text']}» ساخته و به بالای منو اضافه شد!\nاز کارتش می‌تونی لینک‌های بیشتر (۲ تا یا بیشتر) و فایل هم اضافه کنی ✨",
        reply_markup=akb.back_kb("pr"),
    )


# ════════════════════════ 📞 راه‌های ارتباطی ════════════════════════
def _contacts_text(items: list[dict]) -> str:
    icons = {"url": "🔗", "webapp": "📱", "alert": "🔔"}
    lines = ["📞 دکمه‌های «راه‌های ارتباطی»", SEP]
    if not items:
        lines.append("— هیچ دکمه‌ای ثبت نشده —")
    for i, it in enumerate(items, 1):
        lines.append(f"{i}. {icons.get(it.get('type'), '🔗')} {it['text']} (ردیف {it.get('row', 99)})")
    lines.append(f"{SEP}\nروی هر دکمه بزن برای ویرایش/حذف 👇")
    return "\n".join(lines)


async def _show_contacts(cb: CallbackQuery) -> None:
    items = await content.get_contact_buttons()
    await _edit(cb, _contacts_text(items), akb.contacts_kb(items))


@router.callback_query(F.data == "ap:ct")
async def cb_contacts(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    await _show_contacts(cb)
    await cb.answer()


@router.callback_query(F.data.startswith("ap:ct:show:"))
async def cb_contact_show(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    idx = int(cb.data.split(":")[-1])
    items = await content.get_contact_buttons()
    if idx >= len(items):
        await cb.answer("⚠️ دکمه پیدا نشد.", show_alert=True)
        return
    it = items[idx]
    tname = {"url": "🔗 لینک", "webapp": "📱 مینی‌اپ", "alert": "🔔 آلرت"}.get(it.get("type"), it.get("type"))
    text = "\n".join([
        f"📞 دکمه: {it['text']}",
        SEP,
        f"نوع: {tname}",
        f"مقدار: {it['value']}",
        f"ردیف چیدمان: {it.get('row', 99)}",
    ])
    await _edit(cb, text, akb.contact_item_kb(idx))
    await cb.answer()


@router.callback_query(F.data.startswith("ap:ct:et:"))
async def cb_contact_edit_text(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    idx = int(cb.data.split(":")[-1])
    await state.update_data(ct_idx=idx)
    items = await content.get_contact_buttons()
    current = items[idx]["text"] if 0 <= idx < len(items) else "—"
    await state.set_state(AdminStates.contact_edit_text)
    await _edit(cb, f"✏️ ویرایش متن دکمه\n{SEP}\nℹ️ متن فعلی: «{current}»\n💡 مثال: پشتیبانی آنلاین کاربران\n{SEP}\nمتن جدید را بفرست:", akb.cancel_kb(f"cti:{idx}"))
    await cb.answer()


@router.message(AdminStates.contact_edit_text, F.text)
async def contact_edit_text_save(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    await state.clear()
    items = await content.get_contact_buttons()
    idx = data.get("ct_idx", -1)
    if 0 <= idx < len(items):
        items[idx]["text"] = message.text.strip()
        await content.set_contact_buttons(items)
        await message.answer("✅ متن دکمه عوض شد!", reply_markup=akb.back_kb(f"ct:show:{idx}"))
    else:
        await message.answer("⚠️ دکمه پیدا نشد.", reply_markup=akb.back_kb("ct"))


@router.callback_query(F.data.startswith("ap:ct:ev:"))
async def cb_contact_edit_value(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    idx = int(cb.data.split(":")[-1])
    await state.update_data(ct_idx=idx)
    items = await content.get_contact_buttons()
    current = items[idx]["value"] if 0 <= idx < len(items) else "—"
    await state.set_state(AdminStates.contact_edit_value)
    await _edit(cb, f"🔗 ویرایش مقدار دکمه\n{SEP}\nℹ️ مقدار فعلی:\n«{current}»\n💡 مثال: https://site.com یا متن پاپ‌آپ\n{SEP}\nمقدار جدید را بفرست:", akb.cancel_kb(f"cti:{idx}"))
    await cb.answer()


@router.message(AdminStates.contact_edit_value, F.text)
async def contact_edit_value_save(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    await state.clear()
    items = await content.get_contact_buttons()
    idx = data.get("ct_idx", -1)
    if 0 <= idx < len(items):
        items[idx]["value"] = message.text.strip()
        await content.set_contact_buttons(items)
        await message.answer("✅ مقدار دکمه عوض شد!", reply_markup=akb.back_kb(f"ct:show:{idx}"))
    else:
        await message.answer("⚠️ دکمه پیدا نشد.", reply_markup=akb.back_kb("ct"))


@router.callback_query(F.data.startswith("ap:ct:d:"))
async def cb_contact_delete(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    idx = int(cb.data.split(":")[-1])
    items = await content.get_contact_buttons()
    if 0 <= idx < len(items):
        gone = items.pop(idx)
        await content.set_contact_buttons(items)
        await cb.answer(f"🗑 «{gone['text']}» حذف شد")
    await _show_contacts(cb)


@router.callback_query(F.data == "ap:ct:add")
async def cb_contact_add(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    await state.set_state(AdminStates.contact_add_text)
    await _edit(cb, "➕ افزودن دکمه — مرحله ۱ از ۴\n" + SEP + "\nمتن دکمه را بفرست:", akb.cancel_kb("ct"))
    await cb.answer()


@router.message(AdminStates.contact_add_text, F.text)
async def contact_add_text(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.update_data(new_text=message.text.strip())
    await state.set_state(AdminStates.contact_add_type)
    await message.answer("➕ مرحله ۲ از ۴\nنوع دکمه را انتخاب کن:", reply_markup=akb.contact_type_kb())


@router.callback_query(F.data.startswith("ap:ct:atype:"), AdminStates.contact_add_type)
async def contact_add_type(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    ctype = cb.data.split(":")[-1]
    await state.update_data(new_type=ctype)
    await state.set_state(AdminStates.contact_add_value)
    hint = "لینک (با http)" if ctype != "alert" else "متن پاپ‌آپ"
    await _edit(cb, f"➕ مرحله ۳ از ۴\nمقدار را بفرست ({hint}):", akb.cancel_kb("ct"))
    await cb.answer()


@router.message(AdminStates.contact_add_value, F.text)
async def contact_add_value(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    value = message.text.strip()
    if data.get("new_type") != "alert" and not (value.startswith("http://") or value.startswith("https://")):
        await message.answer("⚠️ لینک باید با http یا https شروع شود! دوباره بفرست:")
        return
    await state.update_data(new_value=value)
    await state.set_state(AdminStates.contact_add_row)
    await message.answer("➕ مرحله ۴ از ۴\nشماره ردیف چیدمان را بفرست (عدد؛ دکمه‌های هم‌ردیف کنار هم می‌افتند — مثلاً ۹۹):")


@router.message(AdminStates.contact_add_row, F.text)
async def contact_add_row(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    row_s = message.text.strip()
    if not row_s.isdigit():
        await message.answer("⚠️ فقط عدد! دوباره بفرست:")
        return
    data = await state.get_data()
    await state.clear()
    items = await content.get_contact_buttons()
    items.append({"text": data["new_text"], "type": data["new_type"], "value": data["new_value"], "row": int(row_s)})
    await content.set_contact_buttons(items)
    await message.answer(f"✅ دکمه «{data['new_text']}» اضافه شد!", reply_markup=akb.back_kb("ct"))


# ════════════════════════ 💼 موقعیت‌های شغلی ════════════════════════
def _jobs_text(jobs: list[dict]) -> str:
    lines = ["💼 موقعیت‌های شغلی فرم همکاری", SEP]
    if not jobs:
        lines.append("— هیچ موقعیتی ثبت نشده —")
    for i, j in enumerate(jobs, 1):
        lines.append(f"{i}. {j['text']}")
    lines.append(f"{SEP}\n✏️ ویرایش | 🗑 حذف")
    return "\n".join(lines)


async def _show_jobs(cb: CallbackQuery) -> None:
    jobs = await content.get_jobs()
    await _edit(cb, _jobs_text(jobs), akb.jobs_admin_kb(jobs))


@router.callback_query(F.data == "ap:jb")
async def cb_jobs(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    await _show_jobs(cb)
    await cb.answer()


@router.callback_query(F.data == "ap:jb:add")
async def cb_job_add(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    await state.set_state(AdminStates.job_add_text)
    await _edit(cb, "➕ افزودن موقعیت شغلی\n" + SEP + "\n💡 مثال: پشتیبان درس عربی\nعنوان موقعیت را بفرست:", akb.cancel_kb("jb"))
    await cb.answer()


@router.message(AdminStates.job_add_text, F.text)
async def job_add_save(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    jobs = await content.get_jobs()
    jid = f"job_custom_{len(jobs) + 1}_{int(datetime.now().timestamp())}"
    jobs.append({"id": jid, "text": message.text.strip()})
    await content.set_jobs(jobs)
    await message.answer("✅ موقعیت جدید اضافه شد!", reply_markup=akb.back_kb("jb"))


@router.callback_query(F.data.startswith("ap:jb:e:"))
async def cb_job_edit(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    jid = cb.data.split(":", 3)[-1]
    jobs = await content.get_jobs()
    cur_job = next((j["text"] for j in jobs if j["id"] == jid), "—")
    await state.update_data(job_id=jid)
    await state.set_state(AdminStates.job_edit_text)
    await _edit(cb, f"✏️ ویرایش موقعیت شغلی\n{SEP}\nℹ️ عنوان فعلی: «{cur_job}»\n{SEP}\nعنوان جدید را بفرست:", akb.cancel_kb("jb"))
    await cb.answer()


@router.message(AdminStates.job_edit_text, F.text)
async def job_edit_save(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    await state.clear()
    jobs = await content.get_jobs()
    for j in jobs:
        if j["id"] == data.get("job_id"):
            j["text"] = message.text.strip()
            await content.set_jobs(jobs)
            await message.answer("✅ عنوان موقعیت ویرایش شد!", reply_markup=akb.back_kb("jb"))
            return
    await message.answer("⚠️ موقعیت پیدا نشد.", reply_markup=akb.back_kb("jb"))


@router.callback_query(F.data.startswith("ap:jb:d:"))
async def cb_job_delete(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    jid = cb.data.split(":", 3)[-1]
    jobs = await content.get_jobs()
    job = next((j for j in jobs if j["id"] == jid), None)
    if not job:
        await cb.answer("⚠️ موقعیت پیدا نشد.", show_alert=True)
        return
    await _edit(cb, f"🗑 حذف «{job['text']}»\n{SEP}\nمطمئنی؟", akb.job_delete_confirm_kb(jid))
    await cb.answer()


@router.callback_query(F.data.startswith("ap:jb:dok:"))
async def cb_job_delete_ok(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    jid = cb.data.split(":", 4)[-1]
    jobs = await content.get_jobs()
    new_jobs = [j for j in jobs if j["id"] != jid]
    if len(new_jobs) != len(jobs):
        await content.set_jobs(new_jobs)
        await cb.answer("🗑 حذف شد")
    await _show_jobs(cb)


# ════════════════════════ 📝 متن سؤال‌های فرم ════════════════════════
@router.callback_query(F.data == "ap:qs")
async def cb_questions(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    customs = await content.get_custom_questions()
    n_fixed = len(config.FSM_QUESTIONS)
    text = (f"📝 متن سؤال‌های فرم استخدام\n{SEP}\n"
            f"۹ سؤال ثابت + {len(customs)} سؤال سفارشی\n"
            "⭐ سؤال‌های سفارشی بعد از سؤال ۹ و به ترتیب پرسیده می‌شوند.\n\nانتخاب کن 👇")
    await _edit(cb, text, akb.questions_kb(list(config.FSM_QUESTIONS), customs))
    await cb.answer()


@router.callback_query(F.data.startswith("ap:qs:show:"))
async def cb_question_show(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    key = cb.data.split(":")[-1]
    keys = list(config.FSM_QUESTIONS)
    if key not in keys:
        await cb.answer("⚠️ سؤال نامعتبر!", show_alert=True)
        return
    num = keys.index(key) + 1
    text = await content.get_question(key)
    await _edit(cb, f"📝 سؤال {num} از ۹ (ثابت)\n{SEP}\n{text}", akb.question_edit_kb(key))
    await cb.answer()


@router.callback_query(F.data.startswith("ap:qs:edit:"))
async def cb_question_edit(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    key = cb.data.split(":")[-1]
    if key not in config.FSM_QUESTIONS:
        await cb.answer("⚠️ سؤال نامعتبر!", show_alert=True)
        return
    cur_q = await content.get_question(key)
    await state.update_data(q_key=key)
    await state.set_state(AdminStates.question_edit_text)
    await _edit(cb, f"✏️ ویرایش سؤال\n{SEP}\nℹ️ متن فعلی:\n«{cur_q}»\n{SEP}\nمتن جدید را بفرست:", akb.cancel_kb(f"qshow:{key}"))
    await cb.answer()


@router.message(AdminStates.question_edit_text, F.text)
async def question_edit_save(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    await state.clear()
    ok = await content.set_question(data.get("q_key", ""), message.text.strip())
    if ok:
        num = list(config.FSM_QUESTIONS).index(data["q_key"]) + 1
        await message.answer(f"✅ متن سؤال {num} ویرایش شد!", reply_markup=akb.back_kb("qs"))
    else:
        await message.answer("⚠️ سؤال نامعتبر!", reply_markup=akb.back_kb("qs"))


# ── سؤال‌های سفارشی: افزودن / نمایش / ویرایش / حذف ──
@router.callback_query(F.data == "ap:qs:add")
async def cb_custom_q_add(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    await state.set_state(AdminStates.custom_q_add_text)
    await _edit(cb, "➕ افزودن سؤال سفارشی\n" + SEP + "\n💡 مثال: چه ساعاتی در هفته آزاد هستید؟\nمتن سؤال را بفرست (بعد از سؤال ۹ پرسیده می‌شود):", akb.cancel_kb("qs"))
    await cb.answer()


@router.message(AdminStates.custom_q_add_text, F.text)
async def custom_q_add_save(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    customs = await content.get_custom_questions()
    customs.append({"key": f"cq_{int(datetime.now().timestamp())}", "text": message.text.strip()})
    await content.set_custom_questions(customs)
    await message.answer(f"✅ سؤال سفارشی اضافه شد (سؤال {9 + len(customs)} فرم)!", reply_markup=akb.back_kb("qs"))


@router.callback_query(F.data.startswith("ap:qs:cshow:"))
async def cb_custom_q_show(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    key = cb.data.split(":")[-1]
    customs = await content.get_custom_questions()
    cq = next((c for c in customs if c["key"] == key), None)
    if not cq:
        await cb.answer("⚠️ سؤال پیدا نشد.", show_alert=True)
        return
    idx = customs.index(cq)
    await _edit(cb, f"⭐ سؤال سفارشی {9 + idx + 1} فرم\n{SEP}\n{cq['text']}", akb.custom_question_kb(key))
    await cb.answer()


@router.callback_query(F.data.startswith("ap:qs:cedit:"))
async def cb_custom_q_edit(cb: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(cb):
        return
    cq_key = cb.data.split(":")[-1]
    customs = await content.get_custom_questions()
    cur_cq = next((c["text"] for c in customs if c["key"] == cq_key), "—")
    await state.update_data(cq_key=cq_key)
    await state.set_state(AdminStates.custom_q_edit_text)
    await _edit(cb, f"✏️ ویرایش سؤال سفارشی\n{SEP}\nℹ️ متن فعلی:\n«{cur_cq}»\n{SEP}\nمتن جدید را بفرست:", akb.cancel_kb(f"cq:{cq_key}"))
    await cb.answer()


@router.message(AdminStates.custom_q_edit_text, F.text)
async def custom_q_edit_save(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    await state.clear()
    customs = await content.get_custom_questions()
    for cq in customs:
        if cq["key"] == data.get("cq_key"):
            cq["text"] = message.text.strip()
            await content.set_custom_questions(customs)
            await message.answer("✅ سؤال سفارشی ویرایش شد!", reply_markup=akb.back_kb("qs"))
            return
    await message.answer("⚠️ سؤال پیدا نشد.", reply_markup=akb.back_kb("qs"))


@router.callback_query(F.data.startswith("ap:qs:cdel:"))
async def cb_custom_q_del(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    key = cb.data.split(":")[-1]
    customs = await content.get_custom_questions()
    new_qs = [c for c in customs if c["key"] != key]
    if len(new_qs) != len(customs):
        await content.set_custom_questions(new_qs)
        await cb.answer("🗑 سؤال حذف شد")
    customs = await content.get_custom_questions()
    n_fixed = len(config.FSM_QUESTIONS)
    await _edit(cb, f"📝 متن سؤال‌های فرم استخدام\n{SEP}\n۹ سؤال ثابت + {len(customs)} سؤال سفارشی\nانتخاب کن 👇", akb.questions_kb(list(config.FSM_QUESTIONS), customs))


# ════════════════════════ 🗄 ریست دیتابیس ════════════════════════
@router.callback_query(F.data == "ap:rs")
async def cb_reset(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    await _edit(
        cb,
        "🗄 ریست و پاک‌سازی\n" + SEP + "\n🧹 «پاک‌سازی تاریخچه» = حذف همه کاربران + رزومه‌ها (تنظیمات/کانال‌ها/دکمه‌ها می‌ماند)\n☠️ «ریست کارخانه» = همه‌چیز به حالت اول برمی‌گردد\n\n💡 توصیه: اول بکاپ CSV بگیر!",
        akb.reset_kb(),
    )
    await cb.answer()


@router.callback_query(F.data == "ap:rs:backup")
async def cb_reset_backup(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    users = await db.list_users(0, 100000)
    resumes = await db.list_resumes(100000)
    stamp = f"{datetime.now():%Y%m%d_%H%M}"
    await cb.message.answer_document(_csv_doc(
        ["user_id", "username", "first_name", "last_name", "first_seen", "last_seen"],
        users, f"backup_users_{stamp}.csv"), caption=f"👥 بکاپ کاربران — {len(users)} ردیف")
    norm = []
    for r in resumes:
        extras = r[14] if len(r) > 14 else None
        try:
            pairs = json.loads(extras) if extras else []
            extras_txt = " | ".join(f"{p.get('text','')}: {p.get('answer','')}" for p in pairs)
        except Exception:
            extras_txt = str(extras or "")
        norm.append((*r[:14], extras_txt))
    await cb.message.answer_document(_csv_doc(
        ["id", "user_id", "username", "job", "fullname", "province", "city", "birthdate",
         "education", "major", "experience", "skills", "resume", "created_at", "extra_answers"],
        norm, f"backup_resumes_{stamp}.csv"), caption=f"📄 بکاپ رزومه‌ها — {len(resumes)} ردیف")
    await cb.answer("📦 بکاپ‌ها ارسال شد ✅")


@router.callback_query(F.data == "ap:rs:wipe")
async def cb_reset_wipe(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    users = await db.count_users()
    resumes = await db.count_resumes()
    await _edit(cb, f"🧹 پاک‌سازی تاریخچه\n{SEP}\n{users} کاربر و {resumes} رزومه حذف می‌شوند!\nتنظیمات (کانال‌ها/دکمه‌ها/سؤال‌ها) دست‌نخورده می‌ماند.\nمطمئنی؟", akb.wipe_confirm_kb())
    await cb.answer()


@router.callback_query(F.data == "ap:rs:wipeok")
async def cb_reset_wipe_ok(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    u, r = await db.wipe_history()
    await _edit(cb, f"✅ تاریخچه پاک شد!\n{SEP}\n🗑 {u} کاربر و {r} رزومه حذف شدند.\nتنظیمات سالم است ✨", akb.back_kb())
    await cb.answer("انجام شد ✅")


@router.callback_query(F.data == "ap:rs:factory")
async def cb_reset_factory(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    await _edit(cb, "☠️ ریست کامل کارخانه\n" + SEP + "\n⚠️ همه‌چیز (کاربران، رزومه‌ها، کانال‌ها، دکمه‌ها، متن‌ها) به حالت اولیه برمی‌گردد!\nاین کار قابل برگشت نیست. مطمئنی؟", akb.factory_confirm_kb())
    await cb.answer()


@router.callback_query(F.data == "ap:rs:factoryok")
async def cb_reset_factory_ok(cb: CallbackQuery) -> None:
    if not await _guard(cb):
        return
    await db.reset_db()
    await content.seed_if_needed()
    await _edit(cb, "✅ ریست کارخانه انجام شد — ربات به حالت اولیه برگشت 🏭", akb.back_kb())
    await cb.answer("ریست شد ✅")
