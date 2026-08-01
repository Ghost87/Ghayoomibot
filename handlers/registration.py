# -*- coding: utf-8 -*-
"""📝 هندلر فرآیند ثبت‌نام + نمایش/ویرایش پروفایل کاربر (سمت کاربر).

فلوی ثبت‌نام (بعد از عضویت در کانال‌ها) — زنجیره‌ای:
شماره ← نام ← پایه ← رشته ← استان ← پایان ← منوی اصلی

پروفایل: «اطلاعات کاربری» ← «📇 پروفایل من» ← «✏️ ویرایش اطلاعات» ←
انتخاب فیلد (هر بخش مستقل) ← ذخیره ← بازگشت به کارت پروفایل.
در هنگام انصراف/خروج، کیبورد «📱 ارسال شماره» هم حذف می‌شود.
"""

import re

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

import config
from keyboards.main_menu import main_menu_kb
from keyboards.registration import (
    CANCEL_EDIT_BTN,
    cancel_edit_kb,
    grade_kb,
    major_kb,
    profile_fields_kb,
    profile_home_kb,
    province_kb,
    share_phone_kb,
)
from services import content
from services import db
from states.registration import ProfileEditFSM, RegistrationFSM

router = Router(name="registration")
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")

_PHONE_RE = re.compile(r"^(?:\+?98|0)?9\d{9}$")


def _norm_phone(raw: str) -> str | None:
    """نرمالایز به 09xxxxxxxxx — معتبر: 09…، +989…، 989…، 9…"""
    raw = re.sub(r"[\s\-()]", "", raw.strip())
    if not _PHONE_RE.match(raw):
        return None
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("98") and len(digits) == 12:
        digits = digits[2:]
    if digits.startswith("9") and len(digits) == 10:
        digits = "0" + digits
    return digits if len(digits) == 11 and digits.startswith("09") else None


async def _show_menu(message: Message) -> None:
    promos = await content.get_promos()
    await message.answer(
        config.MESSAGES["START_WELCOME"].format(first_name="عزیز"),
        reply_markup=main_menu_kb(promos),
    )


# ═══════════════════ فلوی ثبت‌نام (زنجیره‌ای) ═══════════════════
async def start_registration(message: Message, state: FSMContext) -> None:
    """ورودی از start.py — کاربر تازه عضو شده، رجیستر را شروع کن."""
    await state.set_state(RegistrationFSM.entering_phone)
    await message.answer(config.REG_WELCOME, reply_markup=share_phone_kb())


async def _reg_phone_ok(message: Message, state: FSMContext, phone: str) -> None:
    await db.set_profile_field(message.from_user.id, "phone", phone)
    await state.set_state(RegistrationFSM.entering_name)
    await message.answer(config.REG_PHONE_OK, reply_markup=ReplyKeyboardRemove())


@router.message(RegistrationFSM.entering_phone, F.contact)
async def reg_phone_contact(message: Message, state: FSMContext) -> None:
    if message.contact.user_id != message.from_user.id:
        await message.answer(
            "⚠️ لطفاً شماره‌ی خودت رو بفرست، نه شماره‌ی کسی دیگه!",
            reply_markup=share_phone_kb(),
        )
        return
    phone = _norm_phone(message.contact.phone_number)
    if not phone:
        await message.answer(config.REG_PHONE_BAD, reply_markup=share_phone_kb())
        return
    await _reg_phone_ok(message, state, phone)


@router.message(RegistrationFSM.entering_phone, F.text)
async def reg_phone_text(message: Message, state: FSMContext) -> None:
    phone = _norm_phone(message.text or "")
    if not phone:
        await message.answer(config.REG_PHONE_BAD, reply_markup=share_phone_kb())
        return
    await _reg_phone_ok(message, state, phone)


@router.message(RegistrationFSM.entering_phone)
async def reg_phone_other(message: Message, state: FSMContext) -> None:
    await message.answer(config.REG_PHONE_BAD, reply_markup=share_phone_kb())


@router.message(RegistrationFSM.entering_name, F.text)
async def reg_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 3 or len(name) > 60:
        await message.answer(
            "⚠️ نام و نام‌خانوادگی باید بین ۳ تا ۶۰ کاراکتر باشه؛ دوباره بفرست:"
        )
        return
    await db.set_profile_field(message.from_user.id, "fullname", name)
    await state.set_state(RegistrationFSM.choosing_grade)
    await message.answer(config.REG_NAME_OK, reply_markup=grade_kb())


@router.message(RegistrationFSM.entering_name)
async def reg_name_other(message: Message, state: FSMContext) -> None:
    await message.answer("⚠️ لطفاً نام و نام‌خانوادگی رو به‌صورت متن بفرست:")


@router.callback_query(F.data.startswith("reg:grade:"), RegistrationFSM.choosing_grade)
async def reg_grade(cb: CallbackQuery, state: FSMContext) -> None:
    grade = cb.data.split(":", 2)[-1]
    await db.set_profile_field(cb.from_user.id, "grade", grade)
    await state.set_state(RegistrationFSM.choosing_major)
    await cb.message.edit_text(config.REG_GRADE_OK, reply_markup=major_kb())
    await cb.answer(f"پایه: {grade} ✅")


@router.callback_query(F.data.startswith("reg:major:"), RegistrationFSM.choosing_major)
async def reg_major(cb: CallbackQuery, state: FSMContext) -> None:
    major = cb.data.split(":", 2)[-1]
    await db.set_profile_field(cb.from_user.id, "major", major)
    await state.set_state(RegistrationFSM.choosing_province)
    await cb.message.edit_text(config.REG_MAJOR_OK, reply_markup=province_kb())
    await cb.answer(f"رشته: {major} ✅")


@router.callback_query(F.data.startswith("reg:prov:"), RegistrationFSM.choosing_province)
async def reg_province(cb: CallbackQuery, state: FSMContext) -> None:
    province = cb.data.split(":", 2)[-1]
    await db.set_profile_field(cb.from_user.id, "province", province)
    await state.clear()
    await cb.message.edit_text(config.REG_DONE)
    await cb.answer(f"استان: {province} ✅")
    await _show_menu(cb.message)


# ═══════════════════ پروفایل (سمت کاربر) ═══════════════════
def _profile_text(p: dict) -> str:
    return (
        "📇 پروفایل ثبت‌نامی تو\n➖➖➖➖➖➖➖➖\n"
        f"📱 شماره تماس: {p.get('phone') or '—'}\n"
        f"🪪 نام: {p.get('fullname') or '—'}\n"
        f"🎓 پایه تحصیلی: {p.get('grade') or '—'}\n"
        f"📚 رشته: {p.get('major') or '—'}\n"
        f"🌐 استان: {p.get('province') or '—'}\n"
        f"🗓 تاریخ ثبت‌نام: {p.get('registered_at') or '—'}"
    )


@router.callback_query(F.data == "menu_user_profile")
async def cb_user_profile(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    p = await db.get_profile(cb.from_user.id)
    if not p:
        await cb.answer("هنوز ثبت‌نام نکردی!", show_alert=True)
        return
    await cb.message.answer(_profile_text(p), reply_markup=profile_home_kb())
    await cb.answer()


@router.callback_query(F.data == "prof:open_edit")
async def prof_open_edit(cb: CallbackQuery) -> None:
    """ورود به منوی «✏️ ویرایش اطلاعات» — اول دکمه، بعد انتخاب فیلد."""
    await cb.message.edit_text(
        "✏️ ویرایش اطلاعات\n➖➖➖➖➖➖➖➖\n"
        "کدوم بخش رو می‌خوای ویرایش کنی؟",
        reply_markup=profile_fields_kb(),
    )
    await cb.answer()


# ─────────── انتخاب فیلد برای ویرایش (مستقل از هم) ───────────
@router.callback_query(F.data.startswith("pedit:ask:"))
async def pedit_ask(cb: CallbackQuery, state: FSMContext) -> None:
    field = cb.data.split(":")[-1]
    prompts: dict = {
        "phone": (
            "📱 شماره‌ی جدیدت رو به‌صورت عدد ۱۱ رقمی بفرست یا از دکمه‌ی «📱 ارسال شماره تماس» استفاده کن:",
            share_phone_kb(with_cancel=True),
            ProfileEditFSM.editing_phone,
        ),
        "name": (
            "✏️ نام و نام‌خانوادگی جدیدت رو بفرست:",
            cancel_edit_kb(),
            ProfileEditFSM.editing_name,
        ),
        "grade": ("🎓 پایه تحصیلی‌ت رو از دکمه‌های زیر انتخاب کن:", grade_kb("pedit:grade:"), None),
        "major": ("📚 رشته تحصیلی‌ت رو از دکمه‌های زیر انتخاب کن:", major_kb("pedit:major:"), None),
        "province": ("🌐 استان محل زندگی‌ت رو انتخاب کن:", province_kb("pedit:prov:"), None),
    }
    text, kb, st = prompts.get(field, (None, None, None))
    if kb is None:
        await cb.answer("خطا!", show_alert=True)
        return
    if st:  # state-based (phone/name) — پیام جدید با کیبورد ریپلای
        await state.set_state(st)
        await cb.message.answer(text, reply_markup=kb)
    else:   # inline-based (grade/major/province) — ویرایش همین پیام
        await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()


# ─────────── ذخیره‌ی فیلدهای انتخابی (پایه/رشته/استان) ───────────
@router.callback_query(F.data.startswith("pedit:grade:"))
async def pedit_grade(cb: CallbackQuery) -> None:
    grade = cb.data.split(":", 2)[-1]
    await db.set_profile_field(cb.from_user.id, "grade", grade)
    await cb.answer(f"پایه ویرایش شد: {grade} ✅")
    await _back_to_profile_card(cb)


@router.callback_query(F.data.startswith("pedit:major:"))
async def pedit_major(cb: CallbackQuery) -> None:
    major = cb.data.split(":", 2)[-1]
    await db.set_profile_field(cb.from_user.id, "major", major)
    await cb.answer(f"رشته ویرایش شد: {major} ✅")
    await _back_to_profile_card(cb)


@router.callback_query(F.data.startswith("pedit:prov:"))
async def pedit_prov(cb: CallbackQuery) -> None:
    province = cb.data.split(":", 2)[-1]
    await db.set_profile_field(cb.from_user.id, "province", province)
    await cb.answer(f"استان ویرایش شد: {province} ✅")
    await _back_to_profile_card(cb)


async def _back_to_profile_card(cb: CallbackQuery) -> None:
    """برگشت به کارت پروفایل بعد از هر ویرایش موفق."""
    p = await db.get_profile(cb.from_user.id)
    if p:
        await cb.message.edit_text(_profile_text(p), reply_markup=profile_home_kb())


# ─────────── ویرایش شماره (state-based) ───────────
@router.message(ProfileEditFSM.editing_phone, F.contact)
async def pedit_phone_contact(message: Message, state: FSMContext) -> None:
    if message.contact.user_id != message.from_user.id:
        await message.answer(
            "⚠️ لطفاً شماره‌ی خودت رو بفرست!",
            reply_markup=share_phone_kb(with_cancel=True),
        )
        return
    phone = _norm_phone(message.contact.phone_number)
    if not phone:
        await message.answer(config.REG_PHONE_BAD, reply_markup=share_phone_kb(with_cancel=True))
        return
    await _finish_edit(message, state, "phone", phone, "شماره تماس")


@router.message(ProfileEditFSM.editing_phone, F.text)
async def pedit_phone_text(message: Message, state: FSMContext) -> None:
    if (message.text or "").strip() == CANCEL_EDIT_BTN:
        await _cancel_edit(message, state)
        return
    phone = _norm_phone(message.text or "")
    if not phone:
        await message.answer(config.REG_PHONE_BAD, reply_markup=share_phone_kb(with_cancel=True))
        return
    await _finish_edit(message, state, "phone", phone, "شماره تماس")


@router.message(ProfileEditFSM.editing_phone)
async def pedit_phone_other(message: Message, state: FSMContext) -> None:
    await message.answer(config.REG_PHONE_BAD, reply_markup=share_phone_kb(with_cancel=True))


# ─────────── ویرایش نام (state-based) ───────────
@router.message(ProfileEditFSM.editing_name, F.text)
async def pedit_name(message: Message, state: FSMContext) -> None:
    if (message.text or "").strip() == CANCEL_EDIT_BTN:
        await _cancel_edit(message, state)
        return
    name = (message.text or "").strip()
    if len(name) < 3 or len(name) > 60:
        await message.answer(
            "⚠️ نام باید بین ۳ تا ۶۰ کاراکتر باشه؛ دوباره بفرست:",
            reply_markup=cancel_edit_kb(),
        )
        return
    await _finish_edit(message, state, "fullname", name, "نام")


@router.message(ProfileEditFSM.editing_name)
async def pedit_name_other(message: Message, state: FSMContext) -> None:
    await message.answer("⚠️ لطفاً نام رو به‌صورت متن بفرست:", reply_markup=cancel_edit_kb())


# ─────────── اتمام/انصراف ویرایش ───────────
async def _finish_edit(message: Message, state: FSMContext, field: str, value: str, label: str) -> None:
    """ذخیره + پاک‌کردن کیبورد + نمایش کارت پروفایل آپدیت‌شده."""
    await db.set_profile_field(message.from_user.id, field, value)
    await state.clear()
    await message.answer(
        f"✅ {label} با موفقیت ویرایش شد!",
        reply_markup=ReplyKeyboardRemove(),
    )
    p = await db.get_profile(message.from_user.id)
    if p:
        await message.answer(_profile_text(p), reply_markup=profile_home_kb())


async def _cancel_edit(message: Message, state: FSMContext) -> None:
    """انصراف — کیبورد «📱 ارسال شماره»/«انصراف» حذف و کارت پروفایل برمی‌گردد."""
    await state.clear()
    await message.answer("✖️ ویرایش لغو شد.", reply_markup=ReplyKeyboardRemove())
    p = await db.get_profile(message.from_user.id)
    if p:
        await message.answer(_profile_text(p), reply_markup=profile_home_kb())
