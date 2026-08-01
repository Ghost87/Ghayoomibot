# -*- coding: utf-8 -*-
"""کیبوردهای بخش «همکاری با ما» — رزومه، مشاغل و کیبورد مراحل فرم (با سؤال قبلی/انصراف)."""

from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.main_menu import BACK_BTN_TEXT

COOP_CANCEL_TEXT = "🔙 انصراف از فرم"
COOP_BACK_TEXT = "↩️ سؤال قبلی"


def coop_form_reply_kb(with_back: bool = False) -> ReplyKeyboardMarkup:
    """کیبورد ریپلای مراحل فرم — «انصراف» همیشه؛ «سؤال قبلی» از مرحله دوم به بعد."""
    row = [KeyboardButton(text=COOP_BACK_TEXT), KeyboardButton(text=COOP_CANCEL_TEXT)] if with_back \
        else [KeyboardButton(text=COOP_CANCEL_TEXT)]
    return ReplyKeyboardMarkup(keyboard=[row], resize_keyboard=True)


def coop_intro_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="ارسال رزومه", callback_data="coop_send_resume")
    kb.button(text=BACK_BTN_TEXT, callback_data="back_to_main")
    kb.adjust(1, 1)
    return kb.as_markup()


def coop_jobs_kb(jobs: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for job in jobs:
        kb.button(text=job["text"], callback_data=job["id"])
    rows = [2] * (len(jobs) // 2) + ([1] if len(jobs) % 2 else [])
    kb.adjust(*(rows or [1]))
    return kb.as_markup()
