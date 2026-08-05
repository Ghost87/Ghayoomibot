# -*- coding: utf-8 -*-
"""سرویس بررسی عضویت کاربر در کانال‌های جوین اجباری (لیست داینامیک از دیتابیس).

نکته: برای کانال‌های عمومی (دارای @username) تلگرام اجازه بررسی عضویت را
می‌دهد؛ برای کانال خصوصی «ربات باید عضو/ادمین آن باشد» و شناسه‌ی چت باید
«آیدی عددی» (-100...) باشد — لینک‌های دعوت (t.me/+...) از طریق Bot API
قابل بررسی نیستند.
"""

import logging

from aiogram import Bot

from config import REQUIRED_CHANNELS

log = logging.getLogger(__name__)

JOINED_STATUSES = {"member", "administrator", "creator"}


def resolve_chat_ref(channel: dict) -> int | str:
    """مرجع چت برای Bot API: آیدی عددی (خصوصی) → int، یوزرنیم (عمومی) → @username."""
    ref = str(channel.get("username") or "").strip()
    if ref.lstrip("-").isdigit():
        return int(ref)
    if ref and not ref.startswith("@"):
        return "@" + ref
    return ref


def _is_joined(member) -> bool:
    """عضو به حساب می‌آید؟ — restricted با is_member=True هم عضو واقعی است (سوپرگروه‌ها)."""
    if member.status in JOINED_STATUSES:
        return True
    if member.status == "restricted" and getattr(member, "is_member", False):
        return True
    return False


async def check_membership(bot: Bot, user_id: int, channels: list[dict] | None = None) -> bool:
    """True اگر کاربر عضو همه‌ی کانال‌های اجباری باشد."""
    for channel in (channels if channels is not None else REQUIRED_CHANNELS):
        ref = resolve_chat_ref(channel)
        try:
            member = await bot.get_chat_member(chat_id=ref, user_id=user_id)
            if not _is_joined(member):
                return False
        except Exception as exc:
            log.warning("membership check failed: user=%s channel=%s error=%s", user_id, ref, exc)
            return False
    return True


async def get_unjoined_channels(bot: Bot, user_id: int, channels: list[dict] | None = None) -> list[dict]:
    """فهرست کانال‌هایی که کاربر در آن‌ها عضو نیست (یا بررسی ناموفق بود)."""
    unjoined: list[dict] = []
    for channel in (channels if channels is not None else REQUIRED_CHANNELS):
        try:
            member = await bot.get_chat_member(chat_id=resolve_chat_ref(channel), user_id=user_id)
            if not _is_joined(member):
                unjoined.append(channel)
        except Exception:
            unjoined.append(channel)
    return unjoined
