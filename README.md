# قیومی‌بات | GhayoomiBot 🤖

ربات رسمی **کالج آموزش زبان علی قیومی** — بازنویسی کامل و حرفه‌ای
با معماری Async و **aiogram 3.x**

---

## ✨ امکانات اصلی

| بخش | توضیح |
|-----|-------|
| 🔒 جوین اجباری | قفل عضویت روی ۴ کانال + دکمه بررسی (کاملاً از پنل قابل ویرایش) |
| 🏠 منوی شیشه‌ای | منوی این‌لاین + دکمه‌های تبلیغاتی نامحدود «بالای منو» |
| 📱 مینی‌اپ‌ها | پنل دانش‌آموزی، جزوات، لایسنس، پیام ناشناس، پشتیبانی آنلاین |
| 📞 راه‌های ارتباطی | تماس/سایت/شبکه‌های اجتماعی — مدیریت کامل از پنل |
| 🔗 دعوت دوستان | پیام آماده + لینک اشتراک‌گذاری یک‌کلیکی |
| 🤝 فرم استخدام | ۹ سؤال مرحله‌ای + موقعیت‌های شغلی قابل‌مدیریت + ارسال رزومه به گروه ادمین |
| 👑 پنل ادمین مخفی | ورود با `/admin` — آمار، ارسال همگانی، کاربران، CSV، کانال‌ها، دکمه‌ها، ریست |
| 📢 Broadcast حرفه‌ای | ریت‌لیمیت امن ~۲۵/ثانیه، فیلتر مخاطب (همه/فعالان ۳۰ روز)، گزارش زنده، توقف، حذف خودکار بلاک‌شدگان |

## 🚀 اجرا (روی VPS)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# فایل .env را با مقادیر خود پر کنید:
# BOT_TOKEN / ADMIN_GROUP_ID / ADMIN_USERNAME / ADMIN_PASSWORD / ADMIN_USER_IDS

python bot.py
```

برای سرویس دائمی (systemd) فایل راهنمای جداگانه‌ی نصب روی VPS را ببینید.

## 📁 ساختار

```
├── bot.py              ← نقطه ورود + میدل‌ور فعالیت کاربر
├── config.py           ← متن‌ها، کانال‌ها، لینک‌ها (Verbatim از اصل)
├── handlers/           ← start · admin · menu · cooperation · fallback
├── keyboards/          ← main_menu · admin · join · contact · cooperation
├── services/           ← db · content · broadcast · membership · notify
├── states/             ← وضعیت‌های FSM
└── data/bot.db         ← دیتابیس SQLite (خودکار ساخته می‌شود)
```

---

💬 توسعه: **ARIAMIR** — تلگرام [@ARIAMIR_IR](https://t.me/ARIAMIR_IR) — [کانال آکادمی](https://t.me/Ariamir_academy)
