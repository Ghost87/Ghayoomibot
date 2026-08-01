# -*- coding: utf-8 -*-
"""ارسال اطلاعات رزومه‌ی «همکاری با ما» به گروه ادمین (شامل سؤال‌های سفارشی)."""

import logging
from html import escape

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import User

import config

log = logging.getLogger(__name__)


def build_resume_caption(user: User, data: dict, extra: list | None = None) -> str:
    """قالب پیام رزومه برای واحد امور انسانی + پاسخ سؤال‌های سفارشی."""
    username = f"@{user.username}" if user.username else "ندارد"
    e = lambda k: escape(str(data.get(k, "نامشخص")))  # noqa: E731
    lines = [
        "📋 <b>رزومه جدید دریافت شد</b>",
        "",
        f"👤 <b>نام و نام خانوادگی:</b> {e('fullname')}",
        f"💼 <b>موقعیت شغلی:</b> {e('job')}",
        f"📍 <b>استان:</b> {e('province')}",
        f"🏙 <b>شهر:</b> {e('city')}",
        f"🎂 <b>تاریخ تولد:</b> {e('birthdate')}",
        f"🎓 <b>مدرک تحصیلی:</b> {e('education')}",
        f"📚 <b>رشته:</b> {e('major')}",
        f"📌 <b>سابقه همکاری:</b> {e('experience')}",
        f"🛠 <b>مهارت‌ها:</b> {e('skills')}",
        f"📝 <b>توضیحات تکمیلی:</b> {e('resume')}",
    ]
    for item in extra or []:
        lines.append(f"❓ <b>{escape(str(item.get('text', 'سؤال')))}:</b> {escape(str(item.get('answer', '—')))}")
    lines += [
        "",
        f"👤 <b>کاربر:</b> {username} | ID: <code>{user.id}</code>",
    ]
    return "\n".join(lines)


async def send_resume_to_admin(bot: Bot, user: User, data: dict, extra: list | None = None) -> bool:
    """ارسال فرم تکمیل‌شده به گروه ادمین. در صورت موفقیت True برمی‌گرداند."""
    if not config.ADMIN_GROUP_ID:
        log.warning("ADMIN_GROUP_ID تنظیم نشده؛ رزومه‌ی کاربر %s ارسال نشد.", user.id)
        return False
    try:
        await bot.send_message(
            config.ADMIN_GROUP_ID,
            build_resume_caption(user, data, extra),
            parse_mode=ParseMode.HTML,
        )
        return True
    except Exception as exc:
        log.error("ارسال رزومه به گروه ادمین ناموفق بود: %s", exc)
        return False
