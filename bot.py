# -*- coding: utf-8 -*-
"""
قیومی‌بات | GhayoomiBot
========================
بازسازی بر اساس اسکرین‌شات‌های ربات اصلی + کانال‌های جوین اجباری اختصاصی

اجرا:
    pip install -r requirements.txt
    export BOT_TOKEN="..." ADMIN_GROUP_ID="-100..."
    python bot.py
"""

import asyncio
import logging
import time

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

import config
from handlers import all_routers
from services.content import seed_if_needed
from services.db import get_stats, init_db, touch_activity

log = logging.getLogger("ghayoomibot")


class ActivityMiddleware(BaseMiddleware):
    """ثبت آخرین فعالیت کاربر (last_seen) — سقف یک‌بار در دقیقه برای هر کاربر."""

    _touched: dict[int, float] = {}

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user and not user.is_bot:
            now = time.monotonic()
            if now - self._touched.get(user.id, 0) > 60:
                self._touched[user.id] = now
                try:
                    await touch_activity(user.id)
                except Exception:
                    pass
        return await handler(event, data)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    if config.BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        raise RuntimeError("BOT_TOKEN تنظیم نشده است! آن را در .env یا متغیر محیطی قرار دهید.")

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    for router in all_routers():
        dp.include_router(router)

    dp.message.middleware(ActivityMiddleware())
    dp.callback_query.middleware(ActivityMiddleware())

    await bot.set_my_commands([
        BotCommand(command="start", description="شروع ربات و منوی اصلی"),
    ])
    # متن‌های پروفایل ربات (از اسکرین‌شات صفحه «این ربات چه می‌کند؟»)
    await bot.set_my_short_description(config.BOT_ABOUT_TEXT)
    await bot.set_my_description(config.BOT_DESCRIPTION_TEXT)

    await bot.delete_webhook(drop_pending_updates=True)

    await init_db()
    await seed_if_needed()  # seed تنظیمات داینامیک (کانال‌ها/دکمه‌ها/مشاغل) در اولین اجرا
    stats = await get_stats()
    log.info("دیتابیس آماده است 🗄 (users=%s, resumes=%s)", stats["users"], stats["resumes"])

    log.info("قیومی‌بات روشن شد ✅ (long polling)")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("خاموش شد.")
