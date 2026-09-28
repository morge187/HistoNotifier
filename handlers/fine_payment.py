"""Оплата матч-штрафов: кадрами или Telegram Stars (1 кадр = 5 ⭐)."""
import logging
from aiogram import Router, F
from aiogram.exceptions import TelegramAPIError
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.fines import get_active_fines, get_fine, mark_fine_paid_stars, pay_fine_with_cadrs
from database.requests import get_admin_tg_ids, get_user
from utils import fine_payload, fine_stars, fmt_points, parse_fine_payload

logger = logging.getLogger(__name__)

fine_payment_router = Router()

STARS_CURRENCY = "XTR"
CLOSED_TEXT = "Штраф уже закрыт."

CADRS_RESULT_TEXT = {
    "no_points": "Недостаточно кадров.",
    "not_active": CLOSED_TEXT,
    "free": "Этот штраф снимает только администратор.",
    "not_found": "Штраф не найден.",
}


class FinePayCb(CallbackData, prefix="fpay"):
    action: str  # list | choose | cadrs | stars
    fine_id: int = 0


async def load_payable(callback: CallbackQuery, fine_id: int):
    """(user, fine) для активного платного штрафа этого пользователя, иначе alert и None."""
    user = await get_user(callback.from_user.id)
    fine = await get_fine(fine_id)
    if not user or not fine or fine.user_id != user.id or fine.status != "active" or not fine.cost:
        await callback.answer(CLOSED_TEXT, show_alert=True)
        return None
    return user, fine


@fine_payment_router.callback_query(FinePayCb.filter(F.action == "list"))
async def pay_list(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    fines = [f for f in await get_active_fines(user.id) if f.cost] if user else []
    if not fines:
        await callback.answer("Нет штрафов для оплаты.", show_alert=True)
        return

    kb = InlineKeyboardBuilder()
    for i, fine in enumerate(fines, start=1):
        kb.button(
            text=f"{i}. {fine.description[:40]} — {fmt_points(fine.cost)} кадров",
            callback_data=FinePayCb(action="choose", fine_id=fine.id).pack(),
        )
    kb.adjust(1)
    await callback.message.answer("Выбери штраф для оплаты:", reply_markup=kb.as_markup())
    await callback.answer()


@fine_payment_router.callback_query(FinePayCb.filter(F.action == "choose"))
async def pay_choose(callback: CallbackQuery, callback_data: FinePayCb):
    loaded = await load_payable(callback, callback_data.fine_id)
    if not loaded:
        return
    user, fine = loaded
    stars = fine_stars(fine.cost)

    kb = InlineKeyboardBuilder()
    kb.button(text=f"🎞 Кадрами — {fmt_points(fine.cost)}", callback_data=FinePayCb(action="cadrs", fine_id=fine.id).pack())
    kb.button(text=f"⭐ Звёздами — {stars}", callback_data=FinePayCb(action="stars", fine_id=fine.id).pack())
    kb.adjust(1)
    await callback.message.answer(
        f"Штраф: {fine.description}\n"
        f"Стоимость: {fmt_points(fine.cost)} кадров или {stars} ⭐\n"
        f"На счёте: {fmt_points(user.points)} кадров",
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@fine_payment_router.callback_query(FinePayCb.filter(F.action == "cadrs"))
async def pay_cadrs(callback: CallbackQuery, callback_data: FinePayCb):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала зарегистрируйтесь с помощью /start", show_alert=True)
        return
    fine = await get_fine(callback_data.fine_id)
    result = await pay_fine_with_cadrs(callback_data.fine_id, user.id)
    if result != "ok":
        await callback.answer(CADRS_RESULT_TEXT[result], show_alert=True)
        return
    await callback.answer("✅ Штраф оплачен")
    await callback.message.answer(f"✅ Штраф оплачен. Списано {fmt_points(fine.cost)} кадров.")


@fine_payment_router.callback_query(FinePayCb.filter(F.action == "stars"))
async def pay_stars(callback: CallbackQuery, callback_data: FinePayCb):
    loaded = await load_payable(callback, callback_data.fine_id)
    if not loaded:
        return
    user, fine = loaded
    await callback.message.answer_invoice(
        title="Оплата матч-штрафа",
        description=fine.description[:255],
        payload=fine_payload(fine.id, user.id),
        currency=STARS_CURRENCY,
        prices=[LabeledPrice(label="Матч-штраф", amount=fine_stars(fine.cost))],
    )
    await callback.answer()


@fine_payment_router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    try:
        parsed = parse_fine_payload(query.invoice_payload)
        user = await get_user(query.from_user.id)
        fine = await get_fine(parsed[0]) if parsed else None
        ok = bool(
            parsed and user and fine
            and fine.user_id == user.id == parsed[1]
            and fine.status == "active" and fine.cost
            and query.currency == STARS_CURRENCY
            and query.total_amount == fine_stars(fine.cost)
        )
        if ok:
            await query.answer(ok=True)
        else:
            await query.answer(ok=False, error_message="Штраф уже закрыт или изменился. Открой личный кабинет заново.")
    except Exception:
        logger.exception("pre_checkout validation error")
        await query.answer(ok=False, error_message="Не удалось проверить штраф. Попробуйте позже.")


@fine_payment_router.message(F.successful_payment)
async def successful_payment(message: Message):
    payment = message.successful_payment
    parsed = parse_fine_payload(payment.invoice_payload)
    fine_id = parsed[0] if parsed else 0
    if parsed and await mark_fine_paid_stars(fine_id, payment.total_amount, payment.telegram_payment_charge_id):
        await message.answer(f"✅ Штраф оплачен: {payment.total_amount} ⭐. Спасибо!")
        return

    # Штраф закрыли между pre_checkout и оплатой — звёзды нужно вернуть вручную
    await message.answer("⚠️ Оплата получена, но штраф уже был закрыт. Администратор вернёт звёзды.")
    note = (
        f"⚠️ Оплата за закрытый штраф #{fine_id}\n"
        f"Пользователь tg_id: {message.from_user.id}\n"
        f"Звёзд: {payment.total_amount}\n"
        f"charge_id: {payment.telegram_payment_charge_id}"
    )
    for tg_id in await get_admin_tg_ids():
        try:
            await message.bot.send_message(tg_id, note)
        except TelegramAPIError:
            pass
