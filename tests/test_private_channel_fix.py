# -*- coding: utf-8 -*-
"""تست فیکس کانال‌های جوین اجباری پرایوت (آیدی عددی -100... + لینک دعوت)."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.check_membership import resolve_chat_ref, check_membership, get_unjoined_channels
from keyboards.join import channel_join_url, join_lock_kb
from handlers.admin import _validate_channel_ref, _is_invite_link

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("✅" if cond else "❌"), name)


class Member:
    def __init__(self, status):
        self.status = status


class FakeBot:
    def __init__(self, joined_refs):
        self.joined = {str(r) for r in joined_refs}
        self.calls = []

    async def get_chat_member(self, chat_id, user_id):
        self.calls.append(chat_id)
        return Member("member" if str(chat_id) in self.joined else "left")


PRIV = {"username": "-1001234567890", "title": "کانال پرایوت", "button": "عضویت", "url": "https://t.me/+yNPkOZVvQK9jYWVk"}
PUB = {"username": "@Ariamir_academy", "title": "اکادمی", "button": "عضویت"}

# ۱) ریزالور
check("resolver @username", resolve_chat_ref(PUB) == "@Ariamir_academy")
r = resolve_chat_ref(PRIV)
check("resolver numeric → int", r == -1001234567890 and isinstance(r, int))
check("resolver بدون @ → میچسبونه", resolve_chat_ref({"username": "MyChannel"}) == "@MyChannel")

# ۲) ولیدیتورهای پنل
check("validator @ ok", bool(_validate_channel_ref("@MyChannel")))
check("validator -100 ok", bool(_validate_channel_ref("-1001234567890")))
check("validator لینک دعوت رد", _validate_channel_ref("+yNPkOZVvQK9jYWVk") is None)
check("validator @+hash رد", _validate_channel_ref("@+yNPkOZVvQK9jYWVk") is None)
check("validator متن رد", _validate_channel_ref("salam") is None)
check("invite-link detector t.me/+", _is_invite_link("https://t.me/+yNPkOZVvQK9jYWVk"))
check("invite-link detector @+hash", _is_invite_link("@+yNPkOZVvQK9jYWVk"))
check("invite-link detector @ عادی نه", not _is_invite_link("@MyChannel"))

# ۳) لینک دکمه عضویت
check("url عمومی", channel_join_url(PUB) == "https://t.me/Ariamir_academy")
check("url پرایوت با لینک دعوت", channel_join_url(PRIV) == "https://t.me/+yNPkOZVvQK9jYWVk")
check("url پرایوت بدون لینک → t.me/c fallback",
      channel_join_url({"username": "-1001234567890"}) == "https://t.me/c/1234567890")


# ۴) بررسی عضویت روی آیدی عددی
async def main():
    bot = FakeBot(joined_refs={-1001234567890, "@Ariamir_academy"})
    ok = await check_membership(bot, 42, [PUB, PRIV])
    check("check_membership هر دو عضو → True", ok)
    check("ریفرنس عددی دقیقاً int صدا خورده", -1001234567890 in bot.calls)

    bot2 = FakeBot(joined_refs={"@Ariamir_academy"})  # پرایوت عضو نیست
    ok2 = await check_membership(bot2, 42, [PUB, PRIV])
    check("عضو پرایوت نیست → False", not ok2)
    unjoined = await get_unjoined_channels(bot2, 42, [PUB, PRIV])
    check("get_unjoined فقط پرایوت", len(unjoined) == 1 and unjoined[0]["username"] == "-1001234567890")

    bot3 = FakeBot(joined_refs={-1001234567890})
    bad = {"username": "@+yNPkOZVvQK9jYWVk", "title": "خراب", "button": "x"}  # دیتای خراب قدیمی
    ok3 = await check_membership(bot3, 42, [bad])
    check("دیتای خراب قدیمی → False (رفتار موردانتظار، باید دستی اصلاح شود)", not ok3)


asyncio.run(main())

# ۵) کیبورد
mk = join_lock_kb([PUB, PRIV])
dump = mk.model_dump()
urls = [b.get("url") for row in dump["inline_keyboard"] for b in row if b.get("url")]
check("کیبورد ۲ دکمه لینک‌دار", len(urls) == 2)
check("دکمه پرایوت لینک دعوت", "https://t.me/+yNPkOZVvQK9jYWVk" in urls)

print(f"\n═══ نتیجه: {len(PASS)}/{len(PASS)+len(FAIL)} PASS ═══")
sys.exit(1 if FAIL else 0)
