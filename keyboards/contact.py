# -*- coding: utf-8 -*-
"""کیبورد «📞 راه‌های ارتباطی» — داینامیک؛ آیتم‌ها از پنل ادمین قابل ویرایش‌اند.

مدل آیتم: {"text": str, "type": "url"|"webapp"|"alert", "value": str, "row": int}
"""

from aiogram.types import InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.main_menu import BACK_BTN_TEXT


def contact_us_kb(items: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    rows: list[int] = []
    current_row = None
    for idx, item in enumerate(items):
        if current_row is None or item["row"] != current_row:
            rows.append(0)
            current_row = item["row"]
        rows[-1] += 1
        itype = item.get("type", "url")
        if itype == "webapp":
            kb.button(text=item["text"], web_app=WebAppInfo(url=item["value"]))
        elif itype == "alert":
            kb.button(text=item["text"], callback_data=f"ct_alert:{idx}")
        else:
            kb.button(text=item["text"], url=item["value"])
    kb.button(text=BACK_BTN_TEXT, callback_data="back_to_main")
    kb.adjust(*rows, 1)
    return kb.as_markup()
