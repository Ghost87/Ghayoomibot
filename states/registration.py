# -*- coding: utf-8 -*-
"""ماشین‌های حالت ثبت‌نام و ویرایش پروفایل — کاملاً مستقل از هم."""

from aiogram.fsm.state import State, StatesGroup


class RegistrationFSM(StatesGroup):
    """ثبت‌نام اولیه — زنجیره‌ای: شماره ← نام ← پایه ← رشته ← استان."""
    entering_phone = State()
    entering_name = State()
    choosing_grade = State()
    choosing_major = State()
    choosing_province = State()


class ProfileEditFSM(StatesGroup):
    """ویرایش تک‌فیلدی پروفایل — هر فیلد مستقل؛ بعد از ذخیره برمی‌گردی به پروفایل."""
    editing_phone = State()
    editing_name = State()
