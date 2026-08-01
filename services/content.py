# -*- coding: utf-8 -*-
"""محتوای داینامیک ربات — هر بخشی که از پنل ادمین قابل ویرایش است.

مقادیر در جدول settings به‌صورت JSON ذخیره می‌شوند؛ در صورت خالی بودن،
پیش‌فرض‌ها از config.py (ربات اصلی) seed می‌شوند.
"""

import json

import config
from services.db import get_setting, set_setting

# ────────────────────────────── defaults ─────────────────────────────
DEFAULT_PROMOS: list[dict] = [{
    "id": "promo_physics",
    "button_text": "[جزوه پیش‌بینی فیزیک دوازدهم نهایی]",
    "body": config.MESSAGES["PHYSICS_JOZVE_TEXT"],
    "file_id": None,  # در صورت ست شدن، سند به‌جای متن ساده ارسال می‌شود
    "buttons": [
        {"label": "دریافت رایگان جزوات فیزیک نهایی", "url": config.PHYSICS_JOZVE_URL, "type": "url"},
    ],
}]

DEFAULT_CONTACT_BUTTONS: list[dict] = [
    {"text": f"📞 تماس تلفنی {config.PHONE_NUMBER}", "type": "alert",
     "value": config.CONTACT_PHONE_ALERT, "row": 0},
    {"text": "[ 🌏 سایت کالج آموزش زبان علی قیومی 👈 ]", "type": "url",
     "value": config.SITE_URL, "row": 1},
    {"text": "کانال ایتا", "type": "url", "value": config.LINK_EITA, "row": 2},
    {"text": "کانال روبیکا", "type": "url", "value": config.LINK_RUBIKA, "row": 2},
    {"text": "کانال بله", "type": "url", "value": config.LINK_BALE, "row": 2},
    {"text": "رسانه آپارات", "type": "url", "value": config.LINK_APARAT, "row": 3},
    {"text": "قیومیکست", "type": "url", "value": config.LINK_GHAYOOMICAST, "row": 3},
    {"text": "اینستاگرام استاد قیومی", "type": "url", "value": config.LINK_INSTAGRAM, "row": 4},
    {"text": "پشتیبانی آنلاین کاربران", "type": "webapp",
     "value": config.WEBAPP_URLS["online_support"], "row": 5},
]

_QUESTION_KEYS = list(config.FSM_QUESTIONS.keys())


async def _get(key: str, default):
    raw = await get_setting(key)
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return default


async def _set(key: str, value) -> None:
    await set_setting(key, json.dumps(value, ensure_ascii=False))


async def seed_if_needed() -> None:
    """اگر تنظیماتی خالی بود، با پیش‌فرض‌های ربات اصلی پرش کن."""
    if await get_setting("channels") is None:
        await _set("channels", config.REQUIRED_CHANNELS)
    if await get_setting("promo_buttons") is None:
        old = await get_setting("physics")  # مهاجرت از نسخه تک‌دکمه‌ای
        if old:
            try:
                p = json.loads(old)
                await _set("promo_buttons", [{
                    "id": "promo_physics",
                    "button_text": p.get("menu_button_text") or p.get("button_text", "[دکمه]"),
                    "body": p.get("body", ""),
                    "file_id": p.get("file_id"),
                    "buttons": p.get("buttons") or [],
                }])
            except Exception:
                await _set("promo_buttons", DEFAULT_PROMOS)
        else:
            await _set("promo_buttons", DEFAULT_PROMOS)
    if await get_setting("contact_buttons") is None:
        await _set("contact_buttons", DEFAULT_CONTACT_BUTTONS)
    if await get_setting("jobs") is None:
        await _set("jobs", config.JOB_POSITIONS)
    if await get_setting("question_overrides") is None:
        await _set("question_overrides", {})
    if await get_setting("custom_questions") is None:
        await _set("custom_questions", [])


# ─────────────── کانال‌های جوین اجباری ───────────────
async def get_channels() -> list[dict]:
    return await _get("channels", config.REQUIRED_CHANNELS)


async def set_channels(channels: list[dict]) -> None:
    await _set("channels", channels)


def build_join_lock_text(channels: list[dict]) -> str:
    return "\n".join([
        'کاربر گرامی؛ برای استفاده از خدمات "قیومی‌بات | GhayoomiBot" باید عضو کانال‌های زیر باشید.',
        "➖➖➖➖➖",
        *[f'📣 {c["username"]} | "{c["title"]}"' for c in channels],
    ])


# ─────────────── دکمه‌های بالای منو (تبلیغاتی — چندتایی) ───────────────
async def get_promos() -> list[dict]:
    return await _get("promo_buttons", DEFAULT_PROMOS)


async def set_promos(promos: list[dict]) -> None:
    await _set("promo_buttons", promos)


def promo_link_rows(promo: dict) -> list:
    return promo.get("buttons") or []


# ─────────────── دکمه‌های صفحه راه‌های ارتباطی ───────────────# ─────────────── دکمه‌های صفحه راه‌های ارتباطی ───────────────
async def get_contact_buttons() -> list[dict]:
    items = await _get("contact_buttons", DEFAULT_CONTACT_BUTTONS)
    return sorted(items, key=lambda b: (b.get("row", 99),))


async def set_contact_buttons(items: list[dict]) -> None:
    # فقط مرتب‌سازی بر اساس ردیف؛ گروه‌بندی ردیف‌ها دست‌نخورده حفظ می‌شود
    await _set("contact_buttons", sorted(items, key=lambda b: (b.get("row", 99),)))


# ─────────────── موقعیت‌های شغلی ───────────────
async def get_jobs() -> list[dict]:
    return await _get("jobs", config.JOB_POSITIONS)


async def set_jobs(jobs: list[dict]) -> None:
    await _set("jobs", jobs)


# ─────────────── متن سؤال‌های فرم ───────────────
async def get_question(key: str) -> str:
    overrides = await _get("question_overrides", {})
    return overrides.get(key) or config.FSM_QUESTIONS.get(key, key)


async def set_question(key: str, text: str) -> bool:
    if key not in _QUESTION_KEYS:
        return False
    overrides = await _get("question_overrides", {})
    overrides[key] = text
    await _set("question_overrides", overrides)
    return True


# ─────────────── سؤال‌های سفارشی فرم (افزودنی از پنل) ───────────────
async def get_custom_questions() -> list[dict]:
    """لیست سؤال‌های سفارشی: [{"key": "cq_...", "text": "..."}] — به ترتیب افزودن."""
    return await _get("custom_questions", [])


async def set_custom_questions(items: list[dict]) -> None:
    await _set("custom_questions", items)
