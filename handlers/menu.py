# -*- coding: utf-8 -*-
"""هندلرهای منوی اصلی و زیرمنوها — محتوا از دیتابیس (قابل ویرایش با پنل ادمین).

UX: ناوبری «عقب/جلو» روی همان پیام انجام می‌شود (edit) نه پیام جدید؛
فقط جاهایی که پیام قابل ویرایش نیست (مثل سند) پیام تازه می‌آید.
"""

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

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


async def edit_or_answer(callback: CallbackQuery, text: str, reply_markup=None, **kwargs) -> None:
    """ناوبری روی همان پیام؛ اگر قابل ویرایش نبود (مثل پیام حاوی فایل)، پیام جدید."""
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, **kwargs)
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=reply_markup, **kwargs)


async def flash_message(bot: Bot, chat_id: int, text: str) -> None:
    """ارسال پیام موقت با حذف کیبورد ریپلای و پاک‌کردن خود پیام — چت تمیز می‌ماند."""
    m = await bot.send_message(chat_id, text, reply_markup=ReplyKeyboardRemove())
    try:
        await bot.delete_message(chat_id, m.message_id)
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "back_to_main")
async def cb_back_to_main(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    prev_state = await state.get_state()
    await state.clear()
    promos = await content.get_promos()
    if prev_state and prev_state.startswith(("RegistrationFSM:", "ProfileEditFSM:")):
        # وسط ثبت‌نام/ویرایش بود: کیبورد ریپلای پاک شود (پیام موقت، خودش پاک می‌شود)
        await flash_message(bot, callback.message.chat.id, "↩️ برگشتی به منوی اصلی.")
    await edit_or_answer(
        callback,
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
        # فایل باید پیام جدید باشد — دکمه بازگشتش با edit_or_answer به منو برمی‌گردد
        await callback.message.answer_document(
            promo["file_id"], caption=promo["body"], reply_markup=promo_links_kb(promo)
        )
    else:
        await edit_or_answer(callback, promo["body"], reply_markup=promo_links_kb(promo))
    await callback.answer()


@router.callback_query(F.data == "menu_user_info")
async def cb_user_info(callback: CallbackQuery) -> None:
    await edit_or_answer(callback, config.MESSAGES["USER_INFO_TEXT"], reply_markup=user_info_kb())
    await callback.answer()


@router.callback_query(F.data == "menu_anonymous_msg")
async def cb_anonymous_msg(callback: CallbackQuery) -> None:
    # ستاره‌های متن در ربات اصلی حروفی نمایش داده می‌شوند — بدون parse_mode
    await edit_or_answer(callback, config.MESSAGES["ANONYMOUS_MSG_TEXT"], reply_markup=anonymous_msg_kb())
    await callback.answer()


@router.callback_query(F.data == "menu_invite_friends")
async def cb_invite_friends(callback: CallbackQuery, bot: Bot) -> None:
    bot_me = await bot.get_me()
    bot_link = f"https://t.me/{bot_me.username}"
    text = config.MESSAGES["INVITE_FRIENDS_TEXT"].format(bot_link=bot_link)
    await edit_or_answer(callback, text, reply_markup=invite_friends_kb(bot_me.username),
                         disable_web_page_preview=True)
    await callback.answer()


@router.callback_query(F.data == "menu_contact_us")
async def cb_contact_us(callback: CallbackQuery) -> None:
    items = await content.get_contact_buttons()
    await edit_or_answer(callback, config.MESSAGES["CONTACT_US_TEXT"], reply_markup=contact_us_kb(items))
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
    await edit_or_answer(callback, config.MESSAGES["COOP_CALL_TEXT"], reply_markup=coop_intro_kb())
    await callback.answer()
