# -*- coding: utf-8 -*-
"""تست ممیزی جوین‌لاک: نرمالایزر ورودی، dedup، restricted member، و هندلر cb_check_join."""
import asyncio
import sys
from types import SimpleNamespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.check_membership import check_membership, _is_joined
from handlers.admin import _normalize_channel_ref, _validate_channel_ref, _is_invite_link, _find_channel_dup

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("✅" if cond else "❌"), name)


# ── ۱) نرمالایزر ──
def out(t):
    return _normalize_channel_ref(t)

check("@username", out("@MyChannel") == ("@MyChannel", None))
check("t.me/user", out("t.me/MyChannel") == ("@MyChannel", None))
check("https t.me/user", out("https://t.me/MyChannel") == ("@MyChannel", None))
check("https t.me/user/ ـskew", out("https://t.me/MyChannel/") == ("@MyChannel", None))
check("http www.telegram.me", out("http://www.telegram.me/MyChan_1") == ("@MyChan_1", None))
check("telegram.dog", out("telegram.dog/MyChannel") == ("@MyChannel", None))
check("آیدی عددی", out("-1001234567890") == ("-1001234567890", None))
check("گروه منفی کوتاه", out("-99887766") == ("-99887766", None))
r, e = out("+yNPkOZVvQK9jYWVk"); check("invite +hash رد", r is None and "آیدی عددی" in e)
r, e = out("https://t.me/+yNPkOZVvQK9jYWVk"); check("invite t.me/+ رد", r is None and e)
r, e = out("@+yNPk"); check("@+hash رد", r is None and e)
r, e = out("https://t.me/joinchat/ABCDEF"); check("joinchat رد", r is None and e)
r, e = out("https://t.me/c/1234567890"); check("t.me/c رد", r is None and e)
r, e = out("1234567890"); check("عدد مثبت → راهنمای -100", r is None and "-100" in e)
r, e = out("@ab"); check("یوزرنیم کوتاه رد", r is None and e)
r, e = out("@سلام"); check("یوزرنیم فارسی رد", r is None and e)
r, e = out("salam"); check("متن نامفهوم رد", r is None and e)

# ── ۲) ولیدیتور سازگاری ──
check("validator تطابق", bool(_validate_channel_ref("https://t.me/FooBar")))
check("validator رد", _validate_channel_ref("t.me/c/1") is None)

# ── ۳) dedup ──
chs = [{"username": "@MyChannel"}, {"username": "-1001234567890"}]
check("dup یوزرنیم", _find_channel_dup(chs, "@mychannel"))          # case-insensitive
check("dup عددی", _find_channel_dup(chs, "-1001234567890"))
check("dup نه", not _find_channel_dup(chs, "@OtherOne"))

# ── ۴) restricted member ──
class M:
    def __init__(self, status, is_member=None):
        self.status = status
        if is_member is not None:
            self.is_member = is_member

check("member", _is_joined(M("member")))
check("creator", _is_joined(M("creator")))
check("restricted+member", _is_joined(M("restricted", True)))
check("restricted+not", not _is_joined(M("restricted", False)))
check("left", not _is_joined(M("left")))
check("kicked", not _is_joined(M("kicked")))

# ── ۵) هندلر cb_check_join ──
import config
import handlers.start as st

PUB = {"username": "@Ariamir_academy", "title": "اکادمی", "button": "عضویت آکادمی"}
PRIV = {"username": "-1001234567890", "title": "پرایوت", "button": "عضویت پرایوت", "url": "https://t.me/+yNPkOZVvQK9jYWVk"}
CHS = [PUB, PRIV]


class FakeBot:
    def __init__(self, joined):
        self.joined = {str(x) for x in joined}

    async def get_chat_member(self, chat_id, user_id):
        return M("member" if str(chat_id) in self.joined else "left")


class FakeMsg:
    def __init__(self):
        self.edits = []
        self.answers = []

    async def edit_text(self, text, reply_markup=None, **kw):
        self.edits.append((text, reply_markup))

    async def answer(self, text, reply_markup=None, **kw):
        self.answers.append(text)


class FakeCb:
    def __init__(self):
        self.from_user = SimpleNamespace(id=42, first_name="تست")
        self.message = FakeMsg()
        self.alerts = []

    async def answer(self, text, show_alert=False):
        self.alerts.append(text)


class FakeState:
    async def get_data(self): return {}
    async def clear(self): pass
    async def set_state(self, s): pass
    async def update_data(self, **kw): pass


# monkeypatch ماژول‌ها
_old_gc, _old_gp, _old_reg = st.content.get_channels, st.content.get_promos, st.database.is_registered
async def _gc(): return [dict(c) for c in CHS]
async def _gp(): return []
st.content.get_channels, st.content.get_promos = _gc, _gp

async def _run_case(registered, joined):
    async def _reg(uid): return registered
    st.database.is_registered = _reg
    cb = FakeCb()
    await st.cb_check_join(cb, FakeBot(joined), FakeState())
    return cb

# کیس A: عضو همه + ثبت‌نام‌شده → تأیید + منوی اصلی (بدون لینک‌ی جوین)
cb = asyncio.run(_run_case(True, {"@Ariamir_academy", -1001234567890}))
check("A: آلرت تأیید", cb.alerts == [config.ALERT_JOINED_OK])
dump = cb.message.edits[0][1].model_dump() if cb.message.edits else {}
urls = str(dump)
check("A: منو اصلی اومد (بدون دکمه کانال)", cb.message.edits and "t.me/+yNPk" not in urls and "t.me/Ariamir_academy" not in urls)

# کیس B: فقط عمومی عضو → آلرت خطا + کیبورد فقط با کانال پرایوتِ باقی‌مونده
cb = asyncio.run(_run_case(True, {"@Ariamir_academy"}))
check("B: آلرت عضو‌نشده", cb.alerts == [config.ALERT_NOT_JOINED])
dump = str(cb.message.edits[0][1].model_dump()) if cb.message.edits else ""
check("B: کانال پرایوت مونده تو لیست", "t.me/+yNPkOZVvQK9jYWVk" in dump)
check("B: کانال عمومیِ عضوشده حذف شده", "t.me/Ariamir_academy" not in dump)
check("B: دکمه بررسی هست", "check_join_status" in dump)

# کیس C: هیچ‌کانال عضو نیست → هر دو باقی
cb = asyncio.run(_run_case(True, set()))
dump = str(cb.message.edits[0][1].model_dump()) if cb.message.edits else ""
check("C: هر دو کانال باقی", "t.me/+yNPk" in dump and "t.me/Ariamir_academy" in dump)

# کیس D: عضو همه ولی ثبت‌نام‌نشده → تأیید + ورود به ثبت‌نام (بدون ادیت منو)
cb = asyncio.run(_run_case(False, {"@Ariamir_academy", -1001234567890}))
check("D: آلرت تأیید", cb.alerts == [config.ALERT_JOINED_OK])

st.content.get_channels, st.content.get_promos, st.database.is_registered = _old_gc, _old_gp, _old_reg

print(f"\n═══ نتیجه ممیزی: {len(PASS)}/{len(PASS)+len(FAIL)} PASS ═══")
sys.exit(1 if FAIL else 0)
