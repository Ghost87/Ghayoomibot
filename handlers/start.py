# -*- coding: utf-8 -*-
"""هندلر /start و قفل جوین اجباری — کانال‌ها از دیتابیس (قابل ویرایش با پنل ادمین)."""

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove, User

import config
from keyboards.join import join_lock_kb
from handlers.registration import start_registration
from keyboards.main_menu import main_menu_kb
from services import content
from services import db as database
from services.check_membership import check_membership

router = Router(name="start")

# ربات فقط در چت خصوصی پاسخ می‌دهد (در گروه‌ها ساکت است)
router.message.filter(F.chat.type == "private")


def _first_name(user: User | None) -> str:
    return (user.first_name or "کاربر") if user else "کاربر"


def _reg_or_edit_state(state_name: str | None) -> bool:
    """آیا استیت فعلی مربوط به فلوی ثبت‌نام یا ویرایش پروفایل است؟"""
    return bool(state_name and state_name.startswith(("RegistrationFSM:", "ProfileEditFSM:")))


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, state: FSMContext) -> None:
    prev_state = await state.get_state()
    if _reg_or_edit_state(prev_state):
        # کاربر وسط ثبت‌نام/ویرایش بوده و /start زده — کیبورد «ارسال شماره» پاک شود
        await message.answer("↩️ از فرآیند خارج شدی.", reply_markup=ReplyKeyboardRemove())
    await state.clear()
    u = message.from_user
    await database.upsert_user(u.id, u.username, u.first_name, u.last_name)

    channels = await content.get_channels()
    if not await check_membership(bot, u.id, channels):
        await message.answer(
            content.build_join_lock_text(channels),
            reply_markup=join_lock_kb(channels),
        )
        return

    if not await database.is_registered(u.id):
        await start_registration(message, state)
        return

    promos = await content.get_promos()
    await message.answer(
        config.MESSAGES["START_WELCOME"].format(first_name=_first_name(u)),
        reply_markup=main_menu_kb(promos),
    )


@router.callback_query(F.data == "check_join_status")
async def cb_check_join(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    """بررسی مجدد عضویت بعد از فشردن «✅ بررسی عضویت»."""
    channels = await content.get_channels()
    if not await check_membership(bot, callback.from_user.id, channels):
        await callback.answer(config.ALERT_NOT_JOINED, show_alert=True)
        return

    await callback.answer(config.ALERT_JOINED_OK)
    if not await database.is_registered(callback.from_user.id):
        await start_registration(callback.message, state)
        return

    promos = await content.get_promos()
    await callback.message.answer(
        config.MESSAGES["START_WELCOME"].format(first_name=_first_name(callback.from_user)),
        reply_markup=main_menu_kb(promos),
    )
