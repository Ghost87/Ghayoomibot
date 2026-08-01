# -*- coding: utf-8 -*-
"""لایه دیتابیس SQLite (aiosqlite) — کاربران، رزومه‌ها و تنظیمات داینامیک.

جدول settings تمام محتوای قابل‌ویرایش از پنل ادمین را نگه می‌دارد
(کانال‌ها، دکمه هدر، دکمه‌های راه‌های ارتباطی، مشاغل، متن سؤال‌ها).
"""

import os
from datetime import datetime, timedelta

import aiosqlite

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "bot.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    first_name  TEXT,
    last_name   TEXT,
    first_seen  TEXT,
    last_seen   TEXT
);

CREATE TABLE IF NOT EXISTS resumes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    username    TEXT,
    job         TEXT,
    fullname    TEXT,
    province    TEXT,
    city        TEXT,
    birthdate   TEXT,
    education   TEXT,
    major       TEXT,
    experience  TEXT,
    skills      TEXT,
    resume      TEXT,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       TEXT
);
"""

RESUME_FIELDS = (
    "job", "fullname", "province", "city", "birthdate",
    "education", "major", "experience", "skills", "resume",
)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─────────────────────────────── init ────────────────────────────────
async def init_db() -> None:
    os.makedirs(DB_DIR, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        try:  # مهاجرت: پاسخ سؤال‌های سفارشی (JSON)
            await db.execute("ALTER TABLE resumes ADD COLUMN extra TEXT")
        except Exception:
            pass
        try:  # مهاجرت: علامت کاربران بلاک‌کننده (برای ارسال همگانی)
            await db.execute("ALTER TABLE users ADD COLUMN is_blocked INTEGER DEFAULT 0")
        except Exception:
            pass
        await db.commit()


# ─────────────────────────────── users ───────────────────────────────
async def upsert_user(user_id: int, username: str | None, first_name: str, last_name: str | None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, username, first_name, last_name, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name,
                last_name  = excluded.last_name,
                last_seen  = excluded.last_seen
            """,
            (user_id, username or "", first_name or "", last_name or "", _now(), _now()),
        )
        await db.commit()


async def list_users(offset: int = 0, limit: int = 8) -> list[tuple]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT user_id, username, first_name, last_name, first_seen, last_seen FROM users "
            "ORDER BY rowid DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return await cur.fetchall()


async def count_users() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        row = await (await db.execute("SELECT COUNT(*) FROM users")).fetchone()
        return row[0]


async def count_users_since(since_iso: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        row = await (await db.execute("SELECT COUNT(*) FROM users WHERE first_seen >= ?", (since_iso,))).fetchone()
        return row[0]


async def all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users")
        return [r[0] for r in await cur.fetchall()]


# ─────────── مخاطبان ارسال همگانی ───────────
async def mark_blocked_many(user_ids: list[int]) -> None:
    """علامت‌گذاری کاربرانی که ربات را بلاک/حذف کرده‌اند."""
    if not user_ids:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            "UPDATE users SET is_blocked = 1 WHERE user_id = ?",
            [(u,) for u in user_ids],
        )
        await db.commit()


async def touch_activity(user_id: int) -> None:
    """به‌روزرسانی last_seen — برای تشخیص کاربران فعال ۳۰ روز اخیر."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_seen = ? WHERE user_id = ?",
            (_now(), user_id),
        )
        await db.commit()


async def broadcast_user_ids(audience: str = "all") -> list[int]:
    """آیدی‌های هدف ارسال همگانی — بلاک‌شده‌ها همیشه حذف می‌شوند.
    audience: 'all' → همه | 'active' → فعالان ۳۰ روز گذشته
    """
    q = "SELECT user_id FROM users WHERE is_blocked = 0"
    params: tuple = ()
    if audience == "active":
        cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        q += " AND last_seen >= ?"
        params = (cutoff,)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(q, params)
        return [r[0] for r in await cur.fetchall()]


async def audience_counts() -> dict:
    """شمارش مخاطبان برای نمایش در پنل: همه / فعال ۳۰ روز / بلاک‌شده."""
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        all_ = await (await db.execute(
            "SELECT COUNT(*) FROM users WHERE is_blocked = 0")).fetchone()
        active = await (await db.execute(
            "SELECT COUNT(*) FROM users WHERE is_blocked = 0 AND last_seen >= ?",
            (cutoff,))).fetchone()
        blocked = await (await db.execute(
            "SELECT COUNT(*) FROM users WHERE is_blocked = 1")).fetchone()
    return {"all": all_[0], "active": active[0], "blocked": blocked[0]}


async def search_users(query: str, limit: int = 10) -> list[tuple]:
    """جستجو بر اساس آیدی عددی دقیق یا تطبیق جزئی نام/یوزرنیم."""
    query = query.strip().lstrip("@")
    rows: list[tuple] = []
    async with aiosqlite.connect(DB_PATH) as db:
        if query.isdigit():
            cur = await db.execute(
                "SELECT user_id, username, first_name, last_name, first_seen, last_seen FROM users WHERE user_id = ?",
                (int(query),),
            )
            rows = await cur.fetchall()
        if not rows:
            like = f"%{query}%"
            cur = await db.execute(
                "SELECT user_id, username, first_name, last_name, first_seen, last_seen FROM users "
                "WHERE username LIKE ? OR first_name LIKE ? OR last_name LIKE ? "
                "ORDER BY rowid DESC LIMIT ?",
                (like, like, like, limit),
            )
            rows = await cur.fetchall()
    return rows


async def get_user(user_id: int) -> tuple | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT user_id, username, first_name, last_name, first_seen, last_seen FROM users WHERE user_id = ?",
            (user_id,),
        )
        return await cur.fetchone()


# ────────────────────────────── resumes ──────────────────────────────
async def save_resume(user, data: dict, extra: list | None = None) -> int:
    """extra: پاسخ سؤال‌های سفارشی — [{"text": سؤال, "answer": جواب}]"""
    import json as _json
    values = [str(data.get(k, "")) for k in RESUME_FIELDS]
    extra_json = _json.dumps(extra or [], ensure_ascii=False)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            INSERT INTO resumes (user_id, username, job, fullname, province, city, birthdate,
                                 education, major, experience, skills, resume, created_at, extra)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user.id, user.username or "", *values, _now(), extra_json),
        )
        await db.commit()
        return cur.lastrowid or 0


async def count_resumes() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        row = await (await db.execute("SELECT COUNT(*) FROM resumes")).fetchone()
        return row[0]


async def list_resumes(limit: int = 5000) -> list[tuple]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, user_id, username, job, fullname, province, city, birthdate, education, "
            "major, experience, skills, resume, created_at, extra FROM resumes ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return await cur.fetchall()


async def get_user_resumes(user_id: int) -> list[tuple]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, job, fullname, created_at FROM resumes WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        )
        return await cur.fetchall()


async def get_resume(resume_id: int) -> tuple | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, user_id, username, job, fullname, province, city, birthdate, education, "
            "major, experience, skills, resume, created_at, extra FROM resumes WHERE id = ?",
            (resume_id,),
        )
        return await cur.fetchone()


async def get_stats() -> dict:
    return {"users": await count_users(), "resumes": await count_resumes()}


# ────────────────────────────── settings ─────────────────────────────
async def get_setting(key: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cur.fetchone()
        return row[0] if row else None


async def set_setting(key: str, value: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await db.commit()


# ─────────────────────────────── reset ───────────────────────────────
async def reset_db() -> str:
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    await init_db()
    return "✅ دیتابیس ریست شد (users, resumes و تنظیمات خالی شدند)"


# ───────────────────── ابزارهای پنل حرفه‌ای (جدید) ─────────────────────
async def delete_user(user_id: int) -> bool:
    """حذف یک کاربر از جدول users (رزومه‌ها برای آرشیو CSV باقی می‌مانند)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()
        return cur.rowcount > 0


async def count_user_resumes(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        row = await (await db.execute("SELECT COUNT(*) FROM resumes WHERE user_id = ?", (user_id,))).fetchone()
        return row[0]


async def wipe_history() -> tuple[int, int]:
    """پاک‌سازی تاریخچه: همه کاربران و رزومه‌ها — تنظیمات (کانال‌ها/دکمه‌ها) دست‌نخورده می‌ماند."""
    async with aiosqlite.connect(DB_PATH) as db:
        u = await (await db.execute("SELECT COUNT(*) FROM users")).fetchone()
        r = await (await db.execute("SELECT COUNT(*) FROM resumes")).fetchone()
        await db.execute("DELETE FROM users")
        await db.execute("DELETE FROM resumes")
        await db.commit()
        return (u[0], r[0])
