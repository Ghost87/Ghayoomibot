# -*- coding: utf-8 -*-
"""کیبوردهای فرآیند ثبت‌نام + بخش پروفایل کاربر."""

from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config

CANCEL_EDIT_BTN = "🔙 انصراف از ویرایش"

# ─────────────── ثبت‌نام ───────────────
def share_phone_kb(with_cancel: bool = False) -> ReplyKeyboardMarkup:
    """دکمه «📱 ارسال شماره تماس» — در حالت ویرایش، انصراف هم دارد."""
    rows = [[KeyboardButton(text=config.SHARE_PHONE_BTN, request_contact=True)]]
    if with_cancel:
        rows.append([KeyboardButton(text=CANCEL_EDIT_BTN)])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def cancel_edit_kb() -> ReplyKeyboardMarkup:
    """فقط دکمه‌ی انصراف — برای مراحل متنی ویرایش."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_EDIT_BTN)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def grade_kb(prefix: str = "reg:grade:") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for val, label in config.GRADES:
        kb.button(text=label, callback_data=f"{prefix}{val}")
    kb.adjust(2, 2)
    return kb.as_markup()


def major_kb(prefix: str = "reg:major:") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for val, label in config.MAJORS:
        kb.button(text=label, callback_data=f"{prefix}{val}")
    kb.adjust(1)
    return kb.as_markup()


def province_kb(prefix: str = "reg:prov:") -> InlineKeyboardMarkup:
    """۳۱ استان توی شبکه‌ی ۳ تایی؛ تهران تنها بالا."""
    kb = InlineKeyboardBuilder()
    for p in config.PROVINCES:
        kb.button(text=p, callback_data=f"{prefix}{p}")
    kb.adjust(1, *([3] * 10))
    return kb.as_markup()


# ─────────────── پروفایل کاربر ───────────────
def profile_home_kb() -> InlineKeyboardMarkup:
    """کارت پروفایل — ابتدا دکمه‌ی «✏️ ویرایش اطلاعات»، بعد گزینه‌های مردود."""
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ ویرایش اطلاعات", callback_data="prof:open_edit", style="primary")
    kb.button(text="🔙 بازگشت به اطلاعات کاربری", callback_data="menu_user_info")
    kb.adjust(1)
    return kb.as_markup()


def profile_fields_kb() -> InlineKeyboardMarkup:
    """انتخاب فیلد برای ویرایش — داخل منوی «ویرایش اطلاعات»."""
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ نام", callback_data="pedit:ask:name")
    kb.button(text="📱 شماره", callback_data="pedit:ask:phone")
    kb.button(text="🎓 پایه", callback_data="pedit:ask:grade")
    kb.button(text="📚 رشته", callback_data="pedit:ask:major")
    kb.button(text="🌐 استان", callback_data="pedit:ask:province")
    kb.button(text="🔙 بازگشت به پروفایل", callback_data="menu_user_profile")
    kb.adjust(2, 2, 1, 1)
    return kb.as_markup()
