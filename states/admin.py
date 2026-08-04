# -*- coding: utf-8 -*-
"""ماشین حالت پنل ادمین — ورود و فرم‌های چندمرحله‌ای بخش‌های مختلف پنل."""

from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    # ── ورود (/admin ← نام‌کاربری ← رمز) ──
    login_username = State()
    login_password = State()

    # ── پیام همگانی ──
    broadcast_wait_message = State()
    broadcast_confirm = State()

    # ── کاربران ──
    user_search_query = State()
    user_message_text = State()

    # ── کانال‌های جوین اجباری ──
    channel_add_username = State()
    channel_add_title = State()
    channel_add_button = State()
    channel_add_link = State()
    channel_edit_title = State()
    channel_edit_username = State()
    channel_edit_button = State()
    channel_edit_link = State()

    # ── دکمه‌های بالای منو (تبلیغاتی) ──
    promo_edit_btn_text = State()
    promo_edit_body = State()
    promo_link_label = State()
    promo_link_type = State()
    promo_link_url = State()
    promo_set_file = State()
    promo_add_btn_text = State()
    promo_add_body = State()
    promo_add_link_label = State()
    promo_add_link_url = State()
    promo_link_edit_label = State()
    promo_link_edit_url = State()

    # ── دکمه‌های راه‌های ارتباطی ──
    contact_add_text = State()
    contact_add_type = State()
    contact_add_value = State()
    contact_add_row = State()
    contact_edit_text = State()
    contact_edit_value = State()

    # ── موقعیت‌های شغلی ──
    job_add_text = State()
    job_edit_text = State()

    # ── متن سؤال‌های فرم ──
    question_edit_text = State()
    custom_q_add_text = State()
    custom_q_edit_text = State()
