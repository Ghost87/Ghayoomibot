# -*- coding: utf-8 -*-
"""کیبورد قفل جوین اجباری — با لیست کانال‌های داینامیک (از پنل ادمین قابل ویرایش)."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def join_lock_kb(channels: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for channel in channels:
        kb.button(text=channel["button"], url=f"https://t.me/{channel['username'].lstrip('@')}")
    kb.button(text="✅ بررسی عضویت", callback_data="check_join_status")
    kb.adjust(*([1] * len(channels)), 1)
    return kb.as_markup()
