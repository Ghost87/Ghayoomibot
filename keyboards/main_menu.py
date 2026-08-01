# -*- coding: utf-8 -*-
"""منوی اصلی و کیبوردهای زیرمنوها — مطابق چیدمان و لیبل‌های ربات اصلی."""

from urllib.parse import quote

from aiogram.types import (
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config

BACK_BTN_TEXT = "بازگشت به منوی اصلی"


def main_menu_kb(promos: list[dict] | None = None) -> InlineKeyboardMarkup:
    """منوی اصلی — دکمه‌های بالای منو (تبلیغاتی) هرکدام یک ردیف؛ بعد بقیه ثابت."""
    promos = promos or []
    kb = InlineKeyboardBuilder()
    for p in promos:
        kb.button(text=p["button_text"], callback_data=f"promo:view:{p['id']}")
    kb.button(text="👤 اطلاعات کاربری", callback_data="menu_user_info")
    kb.button(text="📩 ارسال پیام ناشناس", callback_data="menu_anonymous_msg")
    kb.button(text="🔗 دعوت دوستان", callback_data="menu_invite_friends")
    kb.button(text="📞 راه‌های ارتباطی", callback_data="menu_contact_us")
    kb.button(text="[ 🌏 سایت کالج آموزش زبان علی قیومی 👈 ]", url=config.SITE_URL)
    kb.button(text="🗂 جزوات دوره‌ها", web_app=WebAppInfo(url=config.WEBAPP_URLS["jozvat_app"]))
    kb.button(text="🔐 لایسنس دوره‌ها", web_app=WebAppInfo(url=config.WEBAPP_URLS["license_app"]))
    kb.button(text="🤝 همکاری با ما", callback_data="menu_cooperation")
    kb.adjust(*([1] * len(promos)), 2, 2, 1, 2, 1)
    return kb.as_markup()


def promo_links_kb(promo: dict | None = None) -> InlineKeyboardMarkup:
    """کیبورد پیام تبلیغاتی — دکمه‌های لینک (🔗 / 📱) زیر متن؛ هرکدام یک ردیف."""
    kb = InlineKeyboardBuilder()
    buttons = (promo or {}).get("buttons") or []
    for btn in buttons:
        if btn.get("type") == "webapp":
            kb.button(text=btn["label"], web_app=WebAppInfo(url=btn["url"]))
        else:
            kb.button(text=btn["label"], url=btn["url"])
    kb.button(text=BACK_BTN_TEXT, callback_data="back_to_main")
    kb.adjust(*([1] * (len(buttons) + 1)))
    return kb.as_markup()


def user_info_kb() -> InlineKeyboardMarkup:
    """کیبورد اطلاعات کاربری — ویرایش مشخصات + پنل دانش‌آموزی (مینی‌اپ) + پروفایل."""
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 ویرایش مشخصات من", web_app=WebAppInfo(url=config.WEBAPP_URLS["profile_edit"]))
    kb.button(text="🖥 ورود به پنل دانش‌آموزی", web_app=WebAppInfo(url=config.WEBAPP_URLS["student_panel"]))
    kb.button(text="📇 پروفایل من (ثبت‌نام)", callback_data="menu_user_profile")
    kb.button(text=BACK_BTN_TEXT, callback_data="back_to_main")
    kb.adjust(2, 1, 1)
    return kb.as_markup()


def anonymous_msg_kb() -> InlineKeyboardMarkup:
    """کیبورد پیام ناشناس — ثبت تیکت + ارسال پیام ناشناس (مینی‌اپ)."""
    kb = InlineKeyboardBuilder()
    kb.button(text="⌨️ ثبت تیکت پشتیبانی", web_app=WebAppInfo(url=config.WEBAPP_URLS["support_ticket"]))
    kb.button(text="📩 ارسال پیام ناشناس", web_app=WebAppInfo(url=config.WEBAPP_URLS["anonymous_msg"]))
    kb.button(text=BACK_BTN_TEXT, callback_data="back_to_main")
    kb.adjust(2, 1)
    return kb.as_markup()


def invite_friends_kb(bot_username: str) -> InlineKeyboardMarkup:
    """کیبورد دعوت دوستان — دکمه اشتراک‌گذاری (دیپ‌لینک share) + بازگشت."""
    bot_link = f"https://t.me/{bot_username}"
    share_url = (
        "https://t.me/share/url?url=" + quote(bot_link, safe="")
        + "&text=" + quote(config.MESSAGES["INVITE_FRIENDS_SHARE_TEXT"], safe="")
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="📤 ارسال برای دوستان", url=share_url)
    kb.button(text=BACK_BTN_TEXT, callback_data="back_to_main")
    kb.adjust(1)
    return kb.as_markup()


def back_to_main_kb() -> InlineKeyboardMarkup:
    """فقط یک دکمه این‌لاین بازگشت به منوی اصلی."""
    kb = InlineKeyboardBuilder()
    kb.button(text=BACK_BTN_TEXT, callback_data="back_to_main")
    kb.adjust(1)
    return kb.as_markup()


def reply_back_kb() -> ReplyKeyboardMarkup:
    """کیبورد ریپلای «بازگشت به منوی اصلی» — بعد از اتمام فرم نمایش داده می‌شود
    (مطابق اسکرین‌شات ربات اصلی)."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BACK_BTN_TEXT)]],
        resize_keyboard=True,
    )
