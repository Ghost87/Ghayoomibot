# -*- coding: utf-8 -*-
"""پکیج handlers — هندلرهای ربات به ترتیب اولویت ثبت."""

from aiogram import Router

from . import admin, cooperation, fallback, menu, start


def all_routers() -> list[Router]:
    # ترتیب مهم است: fallback باید آخرین روتر باشد؛ admin قبل از menu.
    return [start.router, admin.router, menu.router, cooperation.router, fallback.router]
