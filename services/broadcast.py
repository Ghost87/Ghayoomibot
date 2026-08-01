# -*- coding: utf-8 -*-
"""📢 موتور ارسال همگانی حرفه‌ای — مناسب صدها هزار کاربر روی پلن رایگان.

نکات پیاده‌سازی (بر اساس محدودیت‌های رسمی Bot API):
- سقف تلگرام ~۳۰ پیام در ثانیه است؛ ما با ۲۵/ثانیه (حاشیه امن) کار می‌کنیم.
- به خطای 429 احترام می‌گذاریم و دقیقاً به اندازه retry_after صبر می‌کنیم.
- کاربرانی که ربات را بلاک/حذف کرده‌اند (خطای 403 یا chat not found) بدون
  توقف رد می‌شوند و در دیتابیس علامت می‌خورند تا در ارسال‌های بعدی حذف شوند.
- ارسال در یک Task پس‌زمینه انجام می‌شود تا ربات در حین ارسال کاملاً فعال بماند.
- گزارش زنده‌ی پیشرفت با میله‌ی پیشرفت و تخمین زمان باقی‌مانده.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services import db

log = logging.getLogger(__name__)

RATE = 25            # پیام در ثانیه (حاشیه امن زیر سقف ۳۰ تلگرام)
EDIT_EVERY = 3.0     # حداقل فاصله بین ویرایش‌های پیام پیشرفت (ثانیه)
MAX_RETRIES = 2      # تعداد تلاش مجدد برای خطاهای ۴۲۹

SEP = "➖➖➖➖➖➖➖➖"


def _is_fatal_block(exc: Exception) -> bool:
    """آیا خطا یعنی کاربر دیگر در دسترس نیست؟ (بلاک/حذف حساب/ربات حذف شده)"""
    if isinstance(exc, TelegramForbiddenError):
        return True
    if isinstance(exc, TelegramBadRequest):
        msg = (exc.message or "").lower()
        return any(k in msg for k in (
            "chat not found", "user not found", "user is deactivated",
            "bot was blocked", "have no rights", "kicked", "group chat was deleted",
        ))
    return False


@dataclass
class BroadcastJob:
    """وضعیت یک ارسال همگانی در حال اجرا."""

    total: int
    sent: int = 0
    blocked: int = 0
    failed: int = 0
    stop_requested: bool = False
    running: bool = True
    started_at: float = field(default_factory=time.monotonic)

    @property
    def done(self) -> int:
        return self.sent + self.blocked + self.failed


# فقط یک ارسال همگانی در هر لحظه
current_job: BroadcastJob | None = None


def stop_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🛑 توقف ارسال", callback_data="ap:bc:stop", style="danger")
    kb.adjust(1)
    return kb.as_markup()


def _fmt_dur(seconds: float) -> str:
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _progress_bar(done: int, total: int, width: int = 12) -> str:
    filled = int(width * done / total) if total else 0
    return "🟩" * filled + "⬜️" * (width - filled)


def progress_text(job: BroadcastJob) -> str:
    pct = (job.done * 100 // job.total) if job.total else 100
    elapsed = time.monotonic() - job.started_at
    speed = job.done / elapsed if elapsed > 0 else 0
    eta = (job.total - job.done) / speed if speed > 0 else 0
    return (
        "🚀 در حال ارسال پیام همگانی…\n" + SEP + "\n"
        f"{_progress_bar(job.done, job.total)} {pct}٪\n\n"
        f"📤 ارسال‌شده: {job.done:,} از {job.total:,}\n"
        f"✅ موفق: {job.sent:,}\n"
        f"🚫 بلاک/حذف‌شده: {job.blocked:,}\n"
        f"⚠️ خطای موقت: {job.failed:,}\n\n"
        f"⏱ گذشته: {_fmt_dur(elapsed)}  |  ⏳ باقیمانده≈ {_fmt_dur(eta)}\n"
        f"⚡️ سرعت: {speed:.0f} پیام/ثانیه\n" + SEP + "\n"
        "ℹ️ ربات در حین ارسال کاملاً فعال است."
    )


def final_text(job: BroadcastJob, stopped: bool) -> str:
    elapsed = time.monotonic() - job.started_at
    head = "🛑 ارسال متوقف شد" if stopped else "📢 گزارش نهایی پیام همگانی"
    return (
        f"{head}\n" + SEP + "\n"
        f"👥 هدف: {job.total:,}\n"
        f"📤 بررسی‌شده: {job.done:,}\n" + SEP + "\n"
        f"✅ موفق: {job.sent:,}\n"
        f"🚫 بلاک/حذف‌شده (از ارسال بعدی حذف می‌شوند): {job.blocked:,}\n"
        f"⚠️ ناموفق (خطای موقت): {job.failed:,}\n" + SEP + "\n"
        f"⏱ مدت ارسال: {_fmt_dur(elapsed)}"
    )


async def _safe_copy(bot: Bot, uid: int, src_chat: int, src_msg: int, job: BroadcastJob) -> str:
    """ارسال کپی پیام برای یک کاربر با مدیریت کامل خطاها.
    خروجی: 'ok' | 'blocked' | 'failed'
    """
    tries = 0
    while True:
        try:
            await bot.copy_message(uid, src_chat, src_msg)
            return "ok"
        except Exception as exc:
            if _is_fatal_block(exc):
                return "blocked"
            if isinstance(exc, TelegramRetryAfter) and tries < MAX_RETRIES:
                tries += 1
                # احترام به retry_after تلگرام + کمی حاشیه
                await asyncio.sleep(exc.retry_after + 0.5)
                continue
            log.warning("broadcast send failed uid=%s err=%s", uid, exc)
            return "failed"


async def run_broadcast(
    bot: Bot,
    admin_chat_id: int,
    src_chat: int,
    src_msg: int,
    user_ids: list[int],
    finish_kb: InlineKeyboardMarkup | None = None,
) -> BroadcastJob:
    """اجرای ارسال همگانی در پس‌زمینه با قابلیت گزارش زنده و توقف."""
    global current_job
    job = BroadcastJob(total=len(user_ids))
    current_job = job

    progress_msg = await bot.send_message(
        admin_chat_id, progress_text(job), reply_markup=stop_kb()
    )
    last_edit = 0.0
    window_start = time.monotonic()
    blocked_ids: list[int] = []

    async def _progress(force: bool = False) -> None:
        nonlocal last_edit
        now = time.monotonic()
        if not force and now - last_edit < EDIT_EVERY:
            return
        last_edit = now
        try:
            await bot.edit_message_text(
                progress_text(job),
                chat_id=admin_chat_id,
                message_id=progress_msg.message_id,
                reply_markup=stop_kb(),
            )
        except TelegramBadRequest:
            pass  # متن تغییر نکرده یا کاربر روی پیام دیگری است

    for i, uid in enumerate(user_ids, start=1):
        if job.stop_requested:
            break

        result = await _safe_copy(bot, uid, src_chat, src_msg, job)
        if result == "ok":
            job.sent += 1
        elif result == "blocked":
            job.blocked += 1
            blocked_ids.append(uid)
        else:
            job.failed += 1

        # ── ریت‌لیمیت: هر RATE پیام، تا تکمیل پنجره‌ی ۱ ثانیه صبر کن ──
        if i % RATE == 0:
            elapsed = time.monotonic() - window_start
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)
            window_start = time.monotonic()

        await _progress()

    # علامت‌گذاری کاربران بلاک‌کننده تا در ارسال‌های بعدی حذف شوند
    if blocked_ids:
        try:
            await db.mark_blocked_many(blocked_ids)
        except Exception as exc:
            log.warning("mark_blocked failed: %s", exc)

    job.running = False
    stopped = job.stop_requested
    try:
        await bot.edit_message_text(
            final_text(job, stopped),
            chat_id=admin_chat_id,
            message_id=progress_msg.message_id,
            reply_markup=finish_kb,
        )
    except TelegramBadRequest:
        pass

    log.info(
        "broadcast finished: total=%s ok=%s blocked=%s failed=%s stopped=%s",
        job.total, job.sent, job.blocked, job.failed, stopped,
    )
    if current_job is job:
        current_job = None
    return job
