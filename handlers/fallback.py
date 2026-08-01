# -*- coding: utf-8 -*-
"""هندلرهای جایگزین:
- دکمه ریپلای «بازگشت به منوی اصلی» (بعد از اتمام فرم)
- هر پیام دیگری خارج از فرم → منوی اصلی / قفل جوین

نکته: این روتر باید آخرین روتر ثبت‌شده باشد.
"""

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.types import Message

import config
from keyboards.join import join_lock_kb
from keyboards.main_menu import BACK_BTN_TEXT, main_menu_kb
from services import content
from services.check_membership import check_membership

router = Router(name="fallback")

# ربات فقط در چت خصوصی پاسخ می‌دهد (در گروه‌ها ساکت است)
router.message.filter(F.chat.type == "private")


async def _welcome(message: Message) -> None:
    promos = await content.get_promos()
    await message.answer(
        config.MESSAGES["START_WELCOME"].format(first_name=message.from_user.first_name or "کاربر"),
        reply_markup=main_menu_kb(promos),
    )


@router.message(StateFilter(None), F.text == BACK_BTN_TEXT)
async def reply_back_to_main(message: Message, bot: Bot) -> None:
    """دکمه ریپلای پایین صفحه → نمایش منوی اصلی."""
    await _welcome(message)


@router.message(StateFilter(None))
async def any_message(message: Message, bot: Bot) -> None:
    channels = await content.get_channels()
    if await check_membership(bot, message.from_user.id, channels):
        await _welcome(message)
    else:
        await message.answer(
            content.build_join_lock_text(channels),
            reply_markup=join_lock_kb(channels),
        )
