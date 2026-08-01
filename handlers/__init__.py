# -*- coding: utf-8 -*-
"""پکیج handlers — هندلرهای ربات به ترتیب اولویت ثبت."""

from aiogram import Router

from . import admin, cooperation, fallback, menu, registration, start


def all_routers() -> list[Router]:
    # ترتیب مهم است: fallback باید آخرین روتر باشد؛ registration بعد از start
    # (فلوی ثبت‌نام از /start لانچ می‌شود) و قبل از menu/fallback.
    return [start.router, admin.router, menu.router, cooperation.router, registration.router, fallback.router]
