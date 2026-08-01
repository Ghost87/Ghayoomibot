# -*- coding: utf-8 -*-
"""پکیج keyboards — تمام کیبوردهای ربات."""

from .contact import contact_us_kb
from .cooperation import coop_intro_kb, coop_jobs_kb
from .join import join_lock_kb
from .main_menu import (
    BACK_BTN_TEXT,
    anonymous_msg_kb,
    back_to_main_kb,
    main_menu_kb,
    promo_links_kb,
    reply_back_kb,
    user_info_kb,
)

__all__ = [
    "BACK_BTN_TEXT",
    "anonymous_msg_kb",
    "back_to_main_kb",
    "contact_us_kb",
    "coop_intro_kb",
    "coop_jobs_kb",
    "join_lock_kb",
    "main_menu_kb",
    "promo_links_kb",
    "reply_back_kb",
    "user_info_kb",
]
