# -*- coding: utf-8 -*-
"""هندلرهای منوی اصلی و زیرمنوها — محتوا از دیتابیس (قابل ویرایش با پنل ادمین).

UX ربات اصلی: پاسخ‌ها به‌صورت «پیام جدید» ارسال می‌شوند (نه ویرایش).
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ReplyKeyboardRemove

import config
from keyboards.contact import contact_us_kb
from keyboards.cooperation import coop_intro_kb
from keyboards.main_menu import (
    anonymous_msg_kb,
    back_to_main_kb,
    invite_friends_kb,
    main_menu_kb,
    promo_links_kb,
    user_info_kb,
)
from services import content

router = Router(name="menu")


@router.callback_query(F.data == "back_to_main")
async def cb_back_to_main(callback: CallbackQuery, state: FSMContext) -> None:
    prev_state = await state.get_state()
    if prev_state and prev_state.startswith(("RegistrationFSM:", "ProfileEditFSM:")):
        # اگر وسط ثبت‌نام/ویرایش پروفایل بود، کیبورد ریپلای هم پاک شود
        await callback.message.answer("↩️ برگشتی به منوی اصلی.", reply_markup=ReplyKeyboardRemove())
    await state.clear()
    promos = await content.get_promos()
    await callback.message.answer(
        config.MESSAGES["START_WELCOME"].format(first_name=callback.from_user.first_name or "کاربر"),
        reply_markup=main_menu_kb(promos),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("promo:view:"))
async def cb_promo_view(callback: CallbackQuery) -> None:
    """نمایش پیام دکمه بالای منو — متن/فایل/لینک‌ها همه از پنل ادمین قابل کنترل‌اند."""
    pid = callback.data.split(":")[-1]
    promos = await content.get_promos()
    promo = next((p for p in promos if p["id"] == pid), None)
    if not promo:
        await callback.answer("این دکمه دیگر موجود نیست 🙁", show_alert=True)
        return
    if promo.get("file_id"):
        await callback.message.answer_document(
            promo["file_id"], caption=promo["body"], reply_markup=promo_links_kb(promo)
        )
    else:
        await callback.message.answer(promo["body"], reply_markup=promo_links_kb(promo))
    await callback.answer()


@router.callback_query(F.data == "menu_user_info")
async def cb_user_info(callback: CallbackQuery) -> None:
    await callback.message.answer(config.MESSAGES["USER_INFO_TEXT"], reply_markup=user_info_kb())
    await callback.answer()


@router.callback_query(F.data == "menu_anonymous_msg")
async def cb_anonymous_msg(callback: CallbackQuery) -> None:
    # ستاره‌های متن در ربات اصلی حروفی نمایش داده می‌شوند — بدون parse_mode
    await callback.message.answer(config.MESSAGES["ANONYMOUS_MSG_TEXT"], reply_markup=anonymous_msg_kb())
    await callback.answer()


@router.callback_query(F.data == "menu_invite_friends")
async def cb_invite_friends(callback: CallbackQuery) -> None:
    bot_me = await callback.bot.get_me()
    bot_link = f"https://t.me/{bot_me.username}"
    text = config.MESSAGES["INVITE_FRIENDS_TEXT"].format(bot_link=bot_link)
    await callback.message.answer(text, reply_markup=invite_friends_kb(bot_me.username), disable_web_page_preview=True)
    await callback.answer()


@router.callback_query(F.data == "menu_contact_us")
async def cb_contact_us(callback: CallbackQuery) -> None:
    items = await content.get_contact_buttons()
    await callback.message.answer(config.MESSAGES["CONTACT_US_TEXT"], reply_markup=contact_us_kb(items))
    await callback.answer()


@router.callback_query(F.data.startswith("ct_alert:"))
async def cb_contact_alert(callback: CallbackQuery) -> None:
    """دکمه‌های از نوع «آلرت» (مثل نمایش شماره تلفن)."""
    try:
        idx = int(callback.data.split(":")[-1])
        items = await content.get_contact_buttons()
        await callback.answer(items[idx]["value"], show_alert=True)
    except (ValueError, IndexError, KeyError):
        await callback.answer("خطا!", show_alert=True)


@router.callback_query(F.data == "menu_cooperation")
async def cb_menu_cooperation(callback: CallbackQuery, state: FSMContext) -> None:
    """نمایش متن فراخوان همکاری + دکمه «ارسال رزومه»."""
    await state.clear()
    await callback.message.answer(config.MESSAGES["COOP_CALL_TEXT"], reply_markup=coop_intro_kb())
    await callback.answer()
