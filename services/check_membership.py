# -*- coding: utf-8 -*-
"""سرویس بررسی عضویت کاربر در کانال‌های جوین اجباری (لیست داینامیک از دیتابیس).

نکته: برای کانال‌های عمومی (دارای @username) تلگرام اجازه بررسی عضویت را
می‌دهد؛ برای کانال خصوصی ربات باید عضو/ادمین آن باشد.
"""

import logging

from aiogram import Bot

from config import REQUIRED_CHANNELS

log = logging.getLogger(__name__)

JOINED_STATUSES = {"member", "administrator", "creator"}


async def check_membership(bot: Bot, user_id: int, channels: list[dict] | None = None) -> bool:
    """True اگر کاربر عضو همه‌ی کانال‌های اجباری باشد."""
    for channel in (channels if channels is not None else REQUIRED_CHANNELS):
        try:
            member = await bot.get_chat_member(chat_id=channel["username"], user_id=user_id)
            if member.status not in JOINED_STATUSES:
                return False
        except Exception as exc:
            log.warning("membership check failed: user=%s channel=%s error=%s", user_id, channel["username"], exc)
            return False
    return True


async def get_unjoined_channels(bot: Bot, user_id: int, channels: list[dict] | None = None) -> list[dict]:
    """فهرست کانال‌هایی که کاربر در آن‌ها عضو نیست (یا بررسی ناموفق بود)."""
    unjoined: list[dict] = []
    for channel in (channels if channels is not None else REQUIRED_CHANNELS):
        try:
            member = await bot.get_chat_member(chat_id=channel["username"], user_id=user_id)
            if member.status not in JOINED_STATUSES:
                unjoined.append(channel)
        except Exception:
            unjoined.append(channel)
    return unjoined
