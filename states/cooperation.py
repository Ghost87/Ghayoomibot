# -*- coding: utf-8 -*-
"""ماشین حالت فرم استخدام — پایپ‌لاین داینامیک: انتخاب شغل ← مرحله‌به‌مرحله با ایندکس.

تمام سؤال‌ها (۹ سؤال ثابت + سؤال‌های سفارشی پنل) داخل یک استیت واحد `entering_form`
با شمارنده‌ی `step` در داده‌ی FSM حرکت می‌کنند؛ پس «سؤال قبلی/انصراف» همیشه کار می‌کند.
"""

from aiogram.fsm.state import State, StatesGroup


class CooperationFSM(StatesGroup):
    choosing_job = State()   # انتخاب موقعیت شغلی (Inline Keyboard)
    entering_form = State()  # پاسخ به سؤال‌ها — شماره مرحله در data["step"]
