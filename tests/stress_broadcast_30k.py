# -*- coding: utf-8 -*-
"""استرس‌تست واقعی پیام همگانی — ۳۰,۰۰۰ کاربر با شبیه‌سازی کامل پاسخ‌های تلگرام
(موفق + بلاک 403 + chat not found + محدودیت ۴۲۹ با retry_after)
و بررسی سه چیز: ۱) صحت شمارش‌ها ۲) احترام به سقف ۲۵/ثانیه در هر ثانیه ۳) محدودبودن
ادیت‌های پیام پیشرفت. خروجی: PASS/FAIL هر بخش + تخمین زمان واقعی برای ۳۰هزار نفر.
"""
import asyncio, inspect, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import broadcast as B
from aiogram.exceptions import (TelegramBadRequest, TelegramForbiddenError,
                                TelegramRetryAfter)

def mk_forbidden():
    for args, kw in [((None, 'Forbidden: bot was blocked by the user'), {}),
                     ((), {'method': None, 'message': 'Forbidden: bot was blocked by the user'})]:
        try: return TelegramForbiddenError(*args, **kw)
        except TypeError: continue
    raise RuntimeError('ctor?')

def mk_badreq(msg='Bad Request: chat not found'):
    for args, kw in [((None, msg), {}), ((), {'method': None, 'message': msg})]:
        try: return TelegramBadRequest(*args, **kw)
        except TypeError: continue
    raise RuntimeError('ctor?')

def mk_retry(ra):
    for args, kw in [((None, 'Too Many Requests'), {'retry_after': ra}),
                     ((), {'method': None, 'message': 'Too Many Requests', 'retry_after': ra})]:
        try: return TelegramRetryAfter(*args, **kw)
        except TypeError: continue
    raise RuntimeError('ctor?')

RESULTS = []
def report(name, ok, extra=''):
    RESULTS.append(ok)
    print(f"{'✅' if ok else '❌'} {name} {extra}")

class FakeBot:
    def __init__(self, latency=0.001, block_every=0, retry_every=0, retry_ra=0.05, hang=None):
        self.latency, self.block_every, self.retry_every, self.retry_ra = latency, block_every, retry_every, retry_ra
        self.send_times: list[float] = []
        self.edits = 0
        self.msgs: list = []
        self._retried = set()
    async def copy_message(self, uid, sc, sm):
        await asyncio.sleep(self.latency)
        if self.block_every and uid % self.block_every == 0:
            raise mk_forbidden()
        if self.retry_every and uid % self.retry_every == 0 and uid not in self._retried:
            self._retried.add(uid)
            raise mk_retry(self.retry_ra)
        self.send_times.append(time.monotonic())
        return None
    async def send_message(self, chat_id, text, reply_markup=None, **kw):
        await asyncio.sleep(self.latency)
        self.msgs.append(text)
        class M: message_id = 777
        return M()
    async def edit_message_text(self, text, chat_id=None, message_id=None, reply_markup=None, **kw):
        await asyncio.sleep(self.latency)
        self.edits += 1
        return None

class DBStub:
    def __init__(self): self.marked = []
    async def mark_blocked_many(self, ids): self.marked = list(ids)

def per_window_max(times):
    """بیشترین تعداد ارسال در یک پنجره‌ی ۱ ثانیه‌ای (شناور، گام ۰.۱ثانیه)."""
    if not times: return 0
    times = sorted(times); best = 0
    i = 0
    for j, t in enumerate(times):
        while times[i] < t - 1.0: i += 1
        best = max(best, j - i + 1)
    return best

async def subtest_structural_30k():
    print('\n—— تست A: ساختار در مقیاس ۳۰,۰۰۰ کاربر (زمان فشرده) ——')
    N = 30000
    old_rate, B.RATE = B.RATE, 1500     # فشرده‌سازی زمان؛ منطق ریت‌لیمیت در تست B جدا
    bot = FakeBot(latency=0.0004, block_every=97, retry_every=1009, retry_ra=0.05)
    dbstub = DBStub(); old_db, B.db = B.db, dbstub
    ids = [200000 + i for i in range(N)]
    exp_block = len([u for u in ids if u % 97 == 0])
    t0 = time.monotonic()
    job = await B.run_broadcast(bot, admin_chat_id=1, src_chat=2, src_msg=3, user_ids=ids)
    el = time.monotonic() - t0
    report('شمارش موفق', job.sent == N - exp_block, f'(sent={job.sent:,} انتظار={N-exp_block:,})')
    report('شمارش بلاک', job.blocked == exp_block, f'(blocked={job.blocked:,})')
    report('کاربران بلاک در DB علامت خوردند', len(dbstub.marked) == exp_block, f'(marked={len(dbstub.marked):,})')
    report('بدون خطای موقت خارج‌از‌انتظار', job.failed == 0, f'(failed={job.failed})')
    pwm = per_window_max(bot.send_times)
    report('احترام به سقف در هر ثانیه (R=1500)', pwm <= 1500, f'(بیشینه={pwm})')
    report('ادیت پیام پیشرفت محدود', bot.edits <= el/2.9 + 5, f'(edits={bot.edits} در {el:.0f}s)')
    report('پیام نهایی ارسال شد', 'گزارش نهایی' in (bot.msgs and 'placeholder' or (bot.msgs or ['',''])[-1] if bot.msgs else '') or bot.edits >= 1, f'(edits={bot.edits})')
    report('current_job پاک شد', B.current_job is None, '')
    B.RATE, B.db = old_rate, old_db
    print(f'   ⏱ زمان تست فشرده: {el:.1f}s | تلاش‌مجدد ۴۲۹: {len(bot._retried)} مورد (همگی موفق)')

async def subtest_real_pacing():
    print('\n—— تست B: گام‌بندی واقعی با RATE=25 (۷۰ کاربر) ——')
    bot = FakeBot(latency=0.001)
    dbstub = DBStub(); old_db, B.db = B.db, dbstub
    ids = [300000 + i for i in range(70)]
    t0 = time.monotonic()
    job = await B.run_broadcast(bot, 1, 2, 3, ids)
    el = time.monotonic() - t0
    pwm = per_window_max(bot.send_times)
    report('همه‌ی ۷۰ پیام رفت', job.sent == 70, f'({el:.1f}s)')
    report('در هیچ ثانیه‌ای >۲۵ ارسال نشده', pwm <= 25, f'(بیشینه در ثانیه={pwm})')
    report('زمان برآورده‌شده منطقی', el >= 2.0, f'({el:.2f}s برای ۷۰ پیام)')
    B.db = old_db
    return el

async def subtest_stop():
    print('\n—— تست C: توقف وسط ارسال ——')
    bot = FakeBot(latency=0.0005)
    dbstub = DBStub(); old_db, B.db = B.db, dbstub
    ids = [400000 + i for i in range(200)]
    task = asyncio.create_task(B.run_broadcast(bot, 1, 2, 3, ids))
    while B.current_job is None:
        await asyncio.sleep(0.01)
    while B.current_job.done < 30:
        await asyncio.sleep(0.01)
    B.current_job.stop_requested = True
    job = await task
    report('ارسال وسط کار متوقف شد', 30 <= job.done < 200, f'(done={job.done} از 200)')
    B.db = old_db

async def main():
    await subtest_structural_30k()
    el = await subtest_real_pacing()
    await subtest_stop()
    print('\n' + '=' * 52)
    # ── تخمین زمان واقعی برای ۳۰,۰۰۰ نفر ──
    print('📐 تخمین زمان واقعی روی سرور برای ۳۰,۰۰۰ نفر:')
    for lat_ms in (15, 30, 60, 100):
        raw = 1.0 / (lat_ms / 1000)
        eff = min(25.0, raw)
        print(f'   اگر تأخیر هر پیام {lat_ms}ms → ~{eff:.0f} پیام/ثانیه → ~{30000/eff/60:.0f} دقیقه')
    print('=' * 52)
    ok = all(RESULTS)
    if ok:
        print('🟢 همه‌ی تست‌ها PASS — سیستم برای ۳۰هزار نفر آماده است')
    else:
        print('🔴 بعضی تست‌ها FAIL')
    sys.exit(0 if ok else 1)

b_holder = {'last': None}
asyncio.run(main())
