# 🧪 تست‌های قیومی‌بات

این تست‌ها **کاملاً آفلاین** هستند (FakeBot شبیه‌سازی‌شده) — هیچ پیام واقعی‌ای به
تلگرام یا کاربران ارسال نمی‌شود؛ پس اجرایشان روی سرور کاملاً امن است.

## اجرا روی VPS (با venv پروژه)

```bash
cd /opt/Ghayoomibot
.venv/bin/python tests/test_joinlock_audit.py
.venv/bin/python tests/test_private_channel_fix.py
.venv/bin/python tests/stress_broadcast_30k.py
```

خروجی سالم:

| تست | خط موفقیت |
|---|---|
| `test_joinlock_audit.py` | `نتیجه ممیزی: 36/36 PASS` |
| `test_private_channel_fix.py` | `نتیجه: 21/21 PASS` |
| `stress_broadcast_30k.py` | `🟢 همه‌ی تست‌ها PASS` |

## هر تست چی چک می‌کند؟

| فایل | موضوع |
|---|---|
| `test_joinlock_audit.py` | ورودی انعطاف‌پذیر کانال‌ها (@user, t.me/user, آیدی عددی)، رد لینک دعوت با راهنما، dedup، restricted member، فلوی دکمه «بررسی عضویت» (۳۶ کیس) |
| `test_private_channel_fix.py` | کانال پرایوت با آیدی عددی -100... + لینک دعوت در دکمه عضویت (۲۱ کیس) |
| `stress_broadcast_30k.py` | ارسال همگانی به ۳۰٬۰۰۰ کاربر — سقف ۲۵/ثانیه، 429+retry_after، بلاک‌شده‌ها، توقف میانی (۱۲ کیس) ~۱ دقیقه |

## اجرای خودکار روی گیت‌هاب
ورکفلوی `.github/workflows/tests.yml` همان سه تست را اجرا می‌کند:
- **دستی:** تب Actions → «🧪 GhayoomiBot Tests» → دکمه «Run workflow» (شاخه main)
- **خودکار:** بعد از هر push روی main
