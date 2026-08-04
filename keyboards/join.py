# -*- coding: utf-8 -*-
"""کیبورد قفل جوین اجباری — با لیست کانال‌های داینامیک (از پنل ادمین قابل ویرایش)."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def channel_join_url(channel: dict) -> str:
    """لینک دکمه عضویت.

    - کانال عمومی (@username) → https://t.me/<username>
    - کانال خصوصی (آیدی عددی) → لینک دعوت ذخیره‌شده (url)؛ در نبودش،
      لینک داخلی https://t.me/c/<id> به‌عنوان fallback.
    """
    ref = str(channel.get("username") or "").strip()
    if ref.lstrip("-").isdigit():
        if channel.get("url"):
            return channel["url"]
        digits = ref.lstrip("-")
        short = digits[3:] if ref.startswith("-100") else digits
        return f"https://t.me/c/{short}"
    return f"https://t.me/{ref.lstrip('@')}"


def join_lock_kb(channels: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for channel in channels:
        kb.button(text=channel["button"], url=channel_join_url(channel))
    kb.button(text="✅ بررسی عضویت", callback_data="check_join_status")
    kb.adjust(*([1] * len(channels)), 1)
    return kb.as_markup()
