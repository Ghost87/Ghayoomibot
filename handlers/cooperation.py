# -*- coding: utf-8 -*-
"""فرم استخدام «همکاری با ما» — پایپ‌لاین داینامیک و تست‌شده.

جریان: ارسال رزومه ← انتخاب موقعیت ← سؤال‌ها (۹ ثابت + سفارشی‌های پنل) یکی‌یکی
با دکمه‌های ریپلای «↩️ سؤال قبلی» و «🔙 انصراف از فرم» ← ارسال به گروه ادمین.
"""

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove, User

import config
from keyboards.cooperation import (
    COOP_BACK_TEXT,
    COOP_CANCEL_TEXT,
    coop_form_reply_kb,
    coop_jobs_kb,
)
from keyboards.main_menu import main_menu_kb, reply_back_kb
from services import content
from services import db as database
from services.admin_notify import send_resume_to_admin
from states.cooperation import CooperationFSM

log = logging.getLogger(__name__)
router = Router(name="cooperation")
router.message.filter(F.chat.type == "private")

STEP_FIELDS = [
    "fullname", "province", "city", "birthdate",
    "education", "major", "experience", "skills", "resume",
]
_ANY_STATE = StateFilter(CooperationFSM.choosing_job, CooperationFSM.entering_form)


def _first_name(user: User | None) -> str:
    return (user.first_name or "کاربر") if user else "کاربر"


async def _get_steps() -> list[dict]:
    """لیست کامل مراحل: ۹ سؤال ثابت + سؤال‌های سفارشی پنل (هرکدام {"field","text"})."""
    steps = [{"field": f, "text": await content.get_question(f)} for f in STEP_FIELDS]
    for cq in await content.get_custom_questions():
        steps.append({"field": cq["key"], "text": cq["text"]})
    return steps


async def _ask(message: Message, step_text: str, step_idx: int, total: int) -> None:
    """پرسیدن سؤال مرحله با کیبورد مناسب (سؤال قبلی از مرحله دوم فعال است)."""
    header = f"📝 سؤال {step_idx + 1} از {total}\n➖➖➖➖➖➖\n"
    await message.answer(header + step_text, reply_markup=coop_form_reply_kb(with_back=step_idx > 0))


async def _finish_form(message: Message, bot: Bot, state: FSMContext) -> None:
    """پایان فرم: ذخیره رزومه + ارسال به گروه ادمین + پیام موفقیت."""
    data = await state.get_data()
    await state.clear()
    answers = data.get("answers", {})
    payload = {"job": data.get("job", "")}
    for f in STEP_FIELDS:
        payload[f] = answers.get(f, "")
    extra = []
    for cq in await content.get_custom_questions():
        ans = answers.get(cq["key"], "")
        if ans:
            extra.append({"text": cq["text"], "answer": ans})
    resume_id = await database.save_resume(message.from_user, payload, extra)
    log.info("رزومه #%s کاربر %s ذخیره شد (%s سؤال سفارشی).", resume_id, message.from_user.id, len(extra))

    sent = await send_resume_to_admin(bot, message.from_user, payload, extra)
    if not sent:
        log.warning("رزومه‌ی کاربر %s به گروه ادمین نرسید.", message.from_user.id)

    await message.answer(
        config.MESSAGES["COOP_SUCCESS_TEXT"].format(first_name=_first_name(message.from_user)),
        reply_markup=ReplyKeyboardRemove(),
    )
    promos = await content.get_promos()
    await message.answer(
        "🏠 هر وقت خواستی دوباره سر بزن 👇",
        reply_markup=main_menu_kb(promos),
    )


# ───────────── انصراف و برگشت — در تمام مراحل ─────────────
async def _cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❎ فرم ارسال رزومه لغو شد.", reply_markup=ReplyKeyboardRemove())
    promos = await content.get_promos()
    await message.answer(
        config.MESSAGES["START_WELCOME"].format(first_name=_first_name(message.from_user)),
        reply_markup=main_menu_kb(promos),
    )


@router.message(_ANY_STATE, F.text == COOP_CANCEL_TEXT)
async def coop_cancel_btn(message: Message, state: FSMContext) -> None:
    await coop_cancel_reply(message, state)


@router.message(Command("cancel"))
async def coop_cancel_cmd(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        return
    await _cancel(message, state)


async def coop_cancel_reply(message: Message, state: FSMContext) -> None:
    await _cancel(message, state)


@router.message(CooperationFSM.entering_form, F.text == COOP_BACK_TEXT)
async def coop_back_step(message: Message, state: FSMContext) -> None:
    """برگشت به سؤال قبلی — پاسخ قبلی حفظ می‌شود و قابل بازنویسی است."""
    data = await state.get_data()
    step = max(0, int(data.get("step", 0)) - 1)
    await state.update_data(step=step)
    steps = await _get_steps()
    await _ask(message, steps[step]["text"], step, len(steps))


# ───────────── شروع فرم و انتخاب شغل ─────────────
@router.callback_query(F.data == "coop_send_resume")
async def cb_start_cooperation(callback: CallbackQuery, state: FSMContext) -> None:
    jobs = await content.get_jobs()
    if not jobs:
        await callback.answer("فعلاً موقعیت شغلی فعالی ثبت نشده است.", show_alert=True)
        return
    await state.set_state(CooperationFSM.choosing_job)
    await callback.message.answer(
        config.MESSAGES["COOP_START_TEXT"].format(first_name=_first_name(callback.from_user)),
        reply_markup=coop_jobs_kb(jobs),
    )
    await callback.message.answer(
        "ℹ️ در هر مرحله می‌تونی با دکمه‌های پایین صفحه، به سؤال قبلی برگردی یا فرم رو لغو کنی 👇",
        reply_markup=coop_form_reply_kb(with_back=False),
    )
    await callback.answer()


@router.callback_query(CooperationFSM.choosing_job, F.data.startswith("job_"))
async def cb_job_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    jobs = await content.get_jobs()
    job = next((j for j in jobs if j["id"] == callback.data), None)
    if not job:
        await callback.answer("موقعیت شغلی نامعتبر است.", show_alert=True)
        return
    await state.update_data(job=job["text"], step=0, answers={})
    await state.set_state(CooperationFSM.entering_form)
    steps = await _get_steps()
    await _ask(callback.message, steps[0]["text"], 0, len(steps))
    await callback.answer()


# ───────────── موتور مرحله‌به‌مرحله فرم ─────────────
@router.message(CooperationFSM.entering_form, F.text)
async def coop_form_step(message: Message, bot: Bot, state: FSMContext) -> None:
    data = await state.get_data()
    step = int(data.get("step", 0))
    answers = data.get("answers", {})
    steps = await _get_steps()
    if step >= len(steps):
        await _finish_form(message, bot, state)
        return
    answers[steps[step]["field"]] = message.text.strip()
    step += 1
    if step >= len(steps):
        await state.update_data(answers=answers)
        await _finish_form(message, bot, state)
        return
    await state.update_data(step=step, answers=answers)
    await _ask(message, steps[step]["text"], step, len(steps))


# ───────────── گارد ورودی غیرمتنی ─────────────
@router.message(CooperationFSM.entering_form)
@router.message(CooperationFSM.choosing_job)
async def coop_text_only_guard(message: Message) -> None:
    await message.answer(config.TEXT_ONLY_MSG)
