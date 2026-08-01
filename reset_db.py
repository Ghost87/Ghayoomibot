# -*- coding: utf-8 -*-
"""ریست کامل دیتابیس ربات — اجرا: python reset_db.py"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.db import get_stats, reset_db


if __name__ == "__main__":
    print(asyncio.run(reset_db()))
    print("آمار پس از ریست:", asyncio.run(get_stats()))
