# -*- coding: utf-8 -*-
"""کیبوردهای پنل مدیریت حرفه‌ای «قیومی‌بات» — ساده، جذاب و یک‌دست.

اصول طراحی:
- چیدمان ۲ ستونه برای بخش‌ها؛ دکمه‌های رنگی (primary/success/danger)
- بازگشت همیشه «یک مرحله» و در همان پیام (edit)
- کاربران به‌صورت دکمه‌های کلیک‌شدنی با نام + یوزرنیم و صفحه‌بندی
"""

from aiogram.types import InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

BACK_TEXT = "🔙 بازگشت"
CANCEL_TEXT = "✖️ انصراف"
PAGE_SIZE = 8


# ═════════════════════════ صفحه اصلی پنل ═════════════════════════
def panel_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 آمار ربات", callback_data="ap:stats", style="success")
    kb.button(text="📢 پیام همگانی", callback_data="ap:bc", style="primary")
    kb.button(text="👥 مدیریت کاربران", callback_data="ap:users")
    kb.button(text="📥 خروجی و بکاپ", callback_data="ap:csv")
    kb.button(text="📣 کانال‌های جوین", callback_data="ap:ch")
    kb.button(text="🎁 دکمه‌های بالای منو", callback_data="ap:pr")
    kb.button(text="📞 راه‌های ارتباطی", callback_data="ap:ct")
    kb.button(text="💼 موقعیت‌های شغلی", callback_data="ap:jb")
    kb.button(text="📝 متن سؤال‌ها", callback_data="ap:qs")
    kb.button(text="🗄 ریست دیتابیس", callback_data="ap:rs", style="danger")
    kb.button(text="🚪 خروج از پنل", callback_data="ap:logout", style="danger")
    kb.adjust(2, 2, 2, 2, 2, 1)
    return kb.as_markup()


def back_kb(target: str = "panel") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=BACK_TEXT, callback_data=f"ap:{target}" if target != "panel" else "ap:panel")
    kb.adjust(1)
    return kb.as_markup()


def cancel_kb(back_to: str = "panel") -> InlineKeyboardMarkup:
    """دکمه انصرافِ فرم‌های چندمرحله‌ای — بعدش به همان بخش برمی‌گردد."""
    kb = InlineKeyboardBuilder()
    kb.button(text=CANCEL_TEXT, callback_data=f"ap:cancel:{back_to}")
    kb.adjust(1)
    return kb.as_markup()


# ═════════════════════════ آمار ربات ═════════════════════════
def stats_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 بروزرسانی", callback_data="ap:stats", style="primary")
    kb.button(text=BACK_TEXT, callback_data="ap:panel")
    kb.adjust(1, 1)
    return kb.as_markup()


# ═════════════════════════ پیام همگانی ═════════════════════════
def broadcast_audience_kb(counts: dict) -> InlineKeyboardMarkup:
    """انتخاب مخاطب ارسال همگانی — همه یا فعالان ۳۰ روز گذشته."""
    kb = InlineKeyboardBuilder()
    kb.button(text=f"👥 همه کاربران ({counts['all']:,})", callback_data="ap:bc:aud:all", style="primary")
    kb.button(text=f"🔥 فعالان ۳۰ روز گذشته ({counts['active']:,})", callback_data="ap:bc:aud:active", style="primary")
    kb.button(text=CANCEL_TEXT, callback_data="ap:cancel:panel", style="danger")
    kb.adjust(1)
    return kb.as_markup()


def broadcast_confirm_kb(count: int = 0) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=f"🚀 شروع ارسال ({count:,} نفر)", callback_data="ap:bc:go", style="success")
    kb.button(text=CANCEL_TEXT, callback_data="ap:cancel:panel", style="danger")
    kb.adjust(1)
    return kb.as_markup()


# ═════════════════════════ خروجی و بکاپ ═════════════════════════
def csv_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="👥 CSV کاربران", callback_data="ap:csv:users", style="primary")
    kb.button(text="📄 CSV رزومه‌ها", callback_data="ap:csv:resumes", style="primary")
    kb.button(text="📦 دانلود فایل دیتابیس", callback_data="ap:csv:db")
    kb.button(text=BACK_TEXT, callback_data="ap:panel")
    kb.adjust(1, 1, 1, 1)
    return kb.as_markup()


# ═════════════════════════ مدیریت کاربران ═════════════════════════
def _user_label(u: tuple) -> str:
    _, username, first_name, last_name, _, _ = u
    name = f"{first_name or ''} {last_name or ''}".strip() or "بدون‌نام"
    uname = f"@{username}" if username else "—"
    return f"👤 {name[:18]} | {uname}"[:45]


def users_page_kb(users: list[tuple], page: int, total_pages: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for u in users:
        kb.button(text=_user_label(u), callback_data=f"ap:uc:show:{u[0]}:{page}")
    nav_count = 0
    if page > 0:
        kb.button(text="\u25c0\ufe0f \u0642\u0628\u0644\u06cc", callback_data=f"ap:users:p:{page - 1}")
        nav_count += 1
    kb.button(text=f"\U0001f4c4 {page + 1}/{total_pages}", callback_data="ap:noop")
    nav_count += 1
    if page < total_pages - 1:
        kb.button(text="\u0628\u0639\u062f\u06cc \u25b6\ufe0f", callback_data=f"ap:users:p:{page + 1}")
        nav_count += 1
    kb.button(text="\U0001f50d \u062c\u0633\u062a\u062c\u0648\u06cc \u06a9\u0627\u0631\u0628\u0631", callback_data="ap:users:search", style="primary")
    kb.button(text=BACK_TEXT, callback_data="ap:panel")
    kb.adjust(*([1] * len(users)), nav_count, 2)
    return kb.as_markup()


def search_results_kb(users: list[tuple]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for u in users:
        kb.button(text=_user_label(u), callback_data=f"ap:uc:show:{u[0]}:-1")
    kb.button(text="🔙 بازگشت به لیست", callback_data="ap:users")
    kb.adjust(*([1] * (len(users) + 1)))
    return kb.as_markup()


def user_card_kb(user_id: int, page: int) -> InlineKeyboardMarkup:
    back_cb = "ap:users" if page < 0 else f"ap:users:p:{page}"
    kb = InlineKeyboardBuilder()
    kb.button(text="📄 رزومه‌های کاربر", callback_data=f"ap:uc:res:{user_id}:{page}")
    kb.button(text="✉️ ارسال پیام", callback_data=f"ap:uc:msg:{user_id}:{page}", style="primary")
    kb.button(text="🗑 حذف کاربر", callback_data=f"ap:uc:del:{user_id}:{page}", style="danger")
    kb.button(text="🔙 بازگشت به لیست", callback_data=back_cb)
    kb.adjust(1, 1, 1, 1)
    return kb.as_markup()


def user_delete_confirm_kb(user_id: int, page: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⚠️ بله، حذف کن", callback_data=f"ap:uc:delok:{user_id}:{page}", style="danger")
    kb.button(text=CANCEL_TEXT, callback_data=f"ap:uc:show:{user_id}:{page}")
    kb.adjust(2)
    return kb.as_markup()


def user_resumes_kb(resumes: list[tuple], user_id: int, page: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for rid, job, _fn, created in resumes:
        kb.button(text=f"📄 #{rid} | {job[:20]} | {str(created)[:10]}", callback_data=f"ap:uc:resv:{rid}:{user_id}:{page}")
    kb.button(text="🔙 بازگشت به کارت", callback_data=f"ap:uc:show:{user_id}:{page}")
    kb.adjust(*([1] * (len(resumes) + 1)))
    return kb.as_markup()


def resume_view_kb(user_id: int, page: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 بازگشت به رزومه‌ها", callback_data=f"ap:uc:res:{user_id}:{page}")
    kb.adjust(1)
    return kb.as_markup()


# ═════════════════════════ کانال‌های جوین ═════════════════════════
def channels_kb(channels: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i, ch in enumerate(channels):
        kb.button(text=f"📣 {ch['title'][:28]}", callback_data=f"ap:ch:show:{i}")
    kb.button(text="➕ افزودن کانال", callback_data="ap:ch:add", style="success")
    kb.button(text=BACK_TEXT, callback_data="ap:panel")
    kb.adjust(*([1] * len(channels)), 1, 1)
    return kb.as_markup()


def channel_item_kb(idx: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ ویرایش عنوان", callback_data=f"ap:ch:et:{idx}", style="primary")
    kb.button(text="🔗 ویرایش شناسه (@ یا -100...)", callback_data=f"ap:ch:eu:{idx}", style="primary")
    kb.button(text="🖊 ویرایش متن دکمه", callback_data=f"ap:ch:eb:{idx}", style="primary")
    kb.button(text="🌐 ویرایش لینک دعوت (پرایوت)", callback_data=f"ap:ch:el:{idx}", style="primary")
    kb.button(text="🗑 حذف کانال", callback_data=f"ap:ch:d:{idx}", style="danger")
    kb.button(text=BACK_TEXT, callback_data="ap:ch")
    kb.adjust(1, 1, 1, 1, 1, 1)
    return kb.as_markup()


def channel_delete_confirm_kb(idx: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⚠️ بله، حذف کن", callback_data=f"ap:ch:dok:{idx}", style="danger")
    kb.button(text=CANCEL_TEXT, callback_data="ap:ch")
    kb.adjust(2)
    return kb.as_markup()


# ═════════════════════════ 🎁 دکمه‌های بالای منو ═════════════════════════
def promos_kb(promos: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i, p in enumerate(promos):
        kb.button(text=f"🎁 {p['button_text'][:28]}", callback_data=f"ap:pr:show:{i}")
    kb.button(text="➕ افزودن دکمه جدید", callback_data="ap:pr:add", style="success")
    kb.button(text=BACK_TEXT, callback_data="ap:panel")
    kb.adjust(*([1] * len(promos)), 1, 1)
    return kb.as_markup()


def promo_item_kb(promo: dict, idx: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ متن دکمه", callback_data=f"ap:pr:eb:{idx}", style="primary")
    kb.button(text="📝 متن محتوا", callback_data=f"ap:pr:ebody:{idx}", style="primary")
    if promo.get("file_id"):
        kb.button(text="🗑 حذف فایل", callback_data=f"ap:pr:filedel:{idx}", style="danger")
    else:
        kb.button(text="📎 فایل ضمیمه", callback_data=f"ap:pr:fileset:{idx}")
    for i, b in enumerate(promo.get("buttons") or []):
        icon = "📱" if b.get("type") == "webapp" else "🔗"
        kb.button(text=f"{icon} {b['label'][:22]}", callback_data=f"ap:pr:lshow:{idx}:{i}")
        kb.button(text="🗑", callback_data=f"ap:pr:ld:{idx}:{i}", style="danger")
    kb.button(text="➕ افزودن لینک", callback_data=f"ap:pr:la:{idx}", style="success")
    kb.button(text="🗑 حذف این دکمه", callback_data=f"ap:pr:del:{idx}", style="danger")
    kb.button(text=BACK_TEXT, callback_data="ap:pr")
    n_links = len(promo.get("buttons") or [])
    kb.adjust(3, *([2] * n_links), 1, 1, 1)
    return kb.as_markup()


def promo_link_item_kb(idx: int, li: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ متن دکمه", callback_data=f"ap:pr:lel:{idx}:{li}", style="primary")
    kb.button(text="🔗 ویرایش لینک", callback_data=f"ap:pr:leu:{idx}:{li}", style="primary")
    kb.button(text="🗑 حذف لینک", callback_data=f"ap:pr:ld:{idx}:{li}", style="danger")
    kb.button(text="🔙 بازگشت به کارت", callback_data=f"ap:pr:show:{idx}")
    kb.adjust(2, 1, 1)
    return kb.as_markup()


def promo_delete_confirm_kb(idx: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⚠️ بله، حذف کن", callback_data=f"ap:pr:delok:{idx}", style="danger")
    kb.button(text=CANCEL_TEXT, callback_data=f"ap:pr:show:{idx}")
    kb.adjust(2)
    return kb.as_markup()


def promo_link_type_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔗 لینک معمولی", callback_data="ap:pr:ltype:url", style="primary")
    kb.button(text="📱 مینی‌اپ", callback_data="ap:pr:ltype:webapp", style="primary")
    kb.button(text=CANCEL_TEXT, callback_data="ap:cancel:pr", style="danger")
    kb.adjust(2, 1)
    return kb.as_markup()


# ═════════════════════════ راه‌های ارتباطی ═════════════════════════
def contacts_kb(items: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    icons = {"url": "🔗", "webapp": "📱", "alert": "🔔"}
    for i, it in enumerate(items):
        kb.button(text=f"{icons.get(it.get('type'), '🔗')} {it['text'][:24]}", callback_data=f"ap:ct:show:{i}")
    kb.button(text="➕ افزودن دکمه", callback_data="ap:ct:add", style="success")
    kb.button(text=BACK_TEXT, callback_data="ap:panel")
    kb.adjust(*([1] * len(items)), 1, 1)
    return kb.as_markup()


def contact_item_kb(idx: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ ویرایش متن", callback_data=f"ap:ct:et:{idx}")
    kb.button(text="🔗 ویرایش مقدار", callback_data=f"ap:ct:ev:{idx}")
    kb.button(text="🗑 حذف", callback_data=f"ap:ct:d:{idx}", style="danger")
    kb.button(text=BACK_TEXT, callback_data="ap:ct")
    kb.adjust(2, 1, 1)
    return kb.as_markup()


def contact_type_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔗 لینک", callback_data="ap:ct:atype:url", style="primary")
    kb.button(text="📱 مینی‌اپ", callback_data="ap:ct:atype:webapp", style="primary")
    kb.button(text="🔔 آلرت (پاپ‌آپ)", callback_data="ap:ct:atype:alert", style="primary")
    kb.button(text=CANCEL_TEXT, callback_data="ap:cancel:ct", style="danger")
    kb.adjust(3, 1)
    return kb.as_markup()


# ═════════════════════════ موقعیت‌های شغلی ═════════════════════════
def jobs_admin_kb(jobs: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for j in jobs:
        kb.button(text=f"✏️ {j['text'][:26]}", callback_data=f"ap:jb:e:{j['id']}")
        kb.button(text="🗑", callback_data=f"ap:jb:d:{j['id']}", style="danger")
    kb.button(text="➕ افزودن موقعیت", callback_data="ap:jb:add", style="success")
    kb.button(text=BACK_TEXT, callback_data="ap:panel")
    kb.adjust(*([2] * len(jobs)), 1, 1)
    return kb.as_markup()


def job_delete_confirm_kb(job_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⚠️ بله، حذف کن", callback_data=f"ap:jb:dok:{job_id}", style="danger")
    kb.button(text=CANCEL_TEXT, callback_data="ap:jb")
    kb.adjust(2)
    return kb.as_markup()


# ═════════════════════════ متن سؤال‌ها ═════════════════════════
def questions_kb(fixed_keys: list[str], custom_questions: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i, key in enumerate(fixed_keys, 1):
        kb.button(text=f"📝 سؤال {i}", callback_data=f"ap:qs:show:{key}")
    for cq in custom_questions:
        kb.button(text=f"⭐ {cq['text'][:24]}", callback_data=f"ap:qs:cshow:{cq['key']}")
    kb.button(text="➕ افزودن سؤال", callback_data="ap:qs:add", style="success")
    kb.button(text=BACK_TEXT, callback_data="ap:panel")
    fixed_rows = [2] * (len(fixed_keys) // 2) + ([1] if len(fixed_keys) % 2 else [])
    kb.adjust(*(fixed_rows + [1] * (len(custom_questions) + 2)))
    return kb.as_markup()


def question_edit_kb(key: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ ویرایش این سؤال", callback_data=f"ap:qs:edit:{key}", style="primary")
    kb.button(text=BACK_TEXT, callback_data="ap:qs")
    kb.adjust(1, 1)
    return kb.as_markup()


def custom_question_kb(key: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ ویرایش متن", callback_data=f"ap:qs:cedit:{key}", style="primary")
    kb.button(text="🗑 حذف سؤال", callback_data=f"ap:qs:cdel:{key}", style="danger")
    kb.button(text=BACK_TEXT, callback_data="ap:qs")
    kb.adjust(2, 1)
    return kb.as_markup()


# ═════════════════════════ ریست دیتابیس ═════════════════════════
def reset_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📦 اول بکاپ CSV بگیر", callback_data="ap:rs:backup", style="success")
    kb.button(text="🧹 پاک‌سازی تاریخچه (کاربران+رزومه)", callback_data="ap:rs:wipe", style="danger")
    kb.button(text="🗄 ریست کامل کارخانه", callback_data="ap:rs:factory", style="danger")
    kb.button(text=BACK_TEXT, callback_data="ap:panel")
    kb.adjust(1, 1, 1, 1)
    return kb.as_markup()


def wipe_confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⚠️ بله، تاریخچه پاک شود", callback_data="ap:rs:wipeok", style="danger")
    kb.button(text=CANCEL_TEXT, callback_data="ap:rs")
    kb.adjust(1, 1)
    return kb.as_markup()


def factory_confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="☠️ بله، همه‌چیز ریست شود", callback_data="ap:rs:factoryok", style="danger")
    kb.button(text=CANCEL_TEXT, callback_data="ap:rs")
    kb.adjust(1, 1)
    return kb.as_markup()
