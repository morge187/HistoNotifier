"""Матч-штрафы: поиск игроков, карточка игрока для админа, штрафы и очки."""
from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.fines import add_fine, get_active_fines, get_users_with_active_fines, remove_fine
from database.requests import (
    decrease_user_points,
    get_all_events,
    get_all_users_ordered,
    get_event_by_index,
    get_event_participants,
    get_user_by_id,
    get_user_by_name,
    is_admin,
    reset_user_points,
    set_user_points_value,
)
from utils import fmt_points, parse_amount

fines_router = Router()

FINES_BUTTONS = ("Матч-штрафы", "матч-штрафы")  # второй — со старых клавиатур
NO_FINES_TEXT = "Игроки с штрафом отсутствуют"


# ---------- CallbackData ----------

class FineMenuCb(CallbackData, prefix="fine_menu"):
    action: str  # all | event | nick


class FineAdminCb(CallbackData, prefix="fine_adm"):
    action: str  # card | points_zero | points_set | points_dec | fine_add | fines_list
    user_id: int


class FineRemoveCb(CallbackData, prefix="fine_rm"):
    fine_id: int
    user_id: int


class BackCb(CallbackData, prefix="back"):
    target: str  # to_main


# ---------- FSM ----------

class FineStates(StatesGroup):
    wait_event_number = State()
    wait_nick_search = State()
    wait_pick_user_number = State()
    wait_points_set_value = State()
    wait_points_dec_value = State()
    wait_fine_text = State()
    wait_fine_cost = State()


# ---------- Render ----------

def fine_line(fine) -> str:
    cost = f" — {fmt_points(fine.cost)} кадров" if fine.cost else ""
    return f"{fine.description}{cost}"


def render_public_fines(user, fines) -> str:
    return f"{user.name} — " + "; ".join(f.description for f in fines)


def render_public_list(rows) -> str:
    return "\n".join(f"{i}. {render_public_fines(u, fs)}" for i, (u, fs) in enumerate(rows, start=1))


async def render_admin_user(user) -> str:
    fines = await get_active_fines(user.id)
    lines = [
        f"Игрок: {user.name}",
        f"Очки: {fmt_points(user.points)}",
        f"Активных штрафов: {len(fines)}",
    ]
    if user.is_banned:
        lines.append("🚫 Заблокирован")
    if user.status is not None:
        lines.append(f"Статус: {user.status}")
    if user.tg_id is not None:
        lines.append(f"tg_id: {user.tg_id}")
    return "\n".join(lines)


def render_fines_list(user, fines) -> str:
    if not fines:
        return f"У игрока {user.name} нет активных штрафов."
    lines = [f"Активные штрафы {user.name}:"]
    lines += [f"{i}. {fine_line(f)}" for i, f in enumerate(fines, start=1)]
    return "\n".join(lines)


# ---------- Keyboards ----------

def kb_search_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="Все игроки", callback_data=FineMenuCb(action="all").pack())
    kb.button(text="По ивенту", callback_data=FineMenuCb(action="event").pack())
    kb.button(text="По нику", callback_data=FineMenuCb(action="nick").pack())
    kb.adjust(1)
    return kb.as_markup()


def kb_admin_user_actions(user):
    kb = InlineKeyboardBuilder()
    for text, action in (
        ("Обнулить очки", "points_zero"),
        ("Задать очки", "points_set"),
        ("Убавить очки", "points_dec"),
        ("Добавить штраф", "fine_add"),
        ("Штрафы игрока", "fines_list"),
    ):
        kb.button(text=text, callback_data=FineAdminCb(action=action, user_id=user.id).pack())
    kb.button(text="Назад", callback_data=BackCb(target="to_main").pack())
    kb.adjust(1)
    return kb.as_markup()


def kb_fines_list(user_id: int, fines):
    kb = InlineKeyboardBuilder()
    for i, fine in enumerate(fines, start=1):
        kb.button(text=f"Снять №{i}", callback_data=FineRemoveCb(fine_id=fine.id, user_id=user_id).pack())
    kb.button(text="◀️ К игроку", callback_data=FineAdminCb(action="card", user_id=user_id).pack())
    kb.adjust(1)
    return kb.as_markup()


# ---------- Helpers ----------

async def send_admin_card(message: Message, user, prefix: str = ""):
    await message.answer(prefix + await render_admin_user(user), reply_markup=kb_admin_user_actions(user))


async def deny_non_admin(message: Message, state: FSMContext) -> bool:
    """True — не админ, обработку надо прекратить."""
    if await is_admin(message.from_user.id):
        return False
    await state.clear()
    await message.answer("Доступно только администратору.")
    return True


async def safe_edit(message: Message, text: str, reply_markup=None):
    """edit_text, но повторный тап по устаревшей кнопке не должен ронять хендлер.

    Telegram отвечает `TelegramBadRequest: message is not modified`, если текст
    и клавиатура не изменились (двойной тап, тап по старой клавиатуре). Это
    штатная ситуация — проглатываем именно её, всё остальное — наружу.
    """
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


# ---------- Entry ----------

@fines_router.message(F.text.in_(FINES_BUTTONS))
async def fine_entry(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("режим поиска", reply_markup=kb_search_menu())


@fines_router.callback_query(BackCb.filter(F.target == "to_main"))
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(callback.message, "режим поиска", kb_search_menu())
    await callback.answer()


# ---------- Menu: ALL ----------

@fines_router.callback_query(FineMenuCb.filter(F.action == "all"))
async def mode_all(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    if await is_admin(callback.from_user.id):
        users = await get_all_users_ordered()
        if not users:
            await callback.message.answer("Пользователей нет.")
            await callback.answer()
            return
        await state.set_state(FineStates.wait_pick_user_number)
        await state.update_data(pick_ids=[u.id for u in users])
        lines = [f"{i}. {u.name} (очки: {fmt_points(u.points)})" for i, u in enumerate(users, start=1)]
        await callback.message.answer("\n".join(lines) + "\n\nВведи номер игрока:")
        await callback.answer()
        return

    rows = await get_users_with_active_fines()
    await callback.message.answer(render_public_list(rows) if rows else NO_FINES_TEXT)
    await callback.answer()


# ---------- Menu: EVENT ----------

@fines_router.callback_query(FineMenuCb.filter(F.action == "event"))
async def mode_event_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    events = await get_all_events()
    if not events:
        await callback.message.answer("Ивентов нет.")
        await callback.answer()
        return

    lines = []
    for i, e in enumerate(events, start=1):
        dt = e.time.strftime("%d.%m.%Y %H:%M") if getattr(e, "time", None) else ""
        lines.append(f"{i}. {e.name} {dt}".strip())

    await state.set_state(FineStates.wait_event_number)
    await state.update_data(events_count=len(events))
    await callback.message.answer("\n".join(lines) + "\n\nВведи номер ивента:")
    await callback.answer()


@fines_router.message(FineStates.wait_event_number)
async def mode_event_apply(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        idx = int((message.text or "").strip())
    except ValueError:
        await message.answer("Нужно число (номер ивента).")
        return

    if idx < 1 or idx > data.get("events_count", 0):
        await message.answer("Неверный номер ивента.")
        return

    event = await get_event_by_index(idx)
    if not event:
        await message.answer("Ивент не найден.")
        await state.clear()
        return

    if await is_admin(message.from_user.id):
        users = await get_event_participants(event.id)
        if not users:
            await message.answer("Участников ивента нет.")
            await state.clear()
            return
        await state.set_state(FineStates.wait_pick_user_number)
        await state.update_data(pick_ids=[u.id for u in users])
        lines = [f"{i}. {u.name} (очки: {fmt_points(u.points)})" for i, u in enumerate(users, start=1)]
        await message.answer("\n".join(lines) + "\n\nВведи номер игрока:")
        return

    rows = await get_users_with_active_fines(event.id)
    await message.answer(render_public_list(rows) if rows else NO_FINES_TEXT)
    await state.clear()


# ---------- Menu: NICK ----------

@fines_router.callback_query(FineMenuCb.filter(F.action == "nick"))
async def mode_nick_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(FineStates.wait_nick_search)
    await callback.message.answer("Введи ник пользователя")
    await callback.answer()


@fines_router.message(FineStates.wait_nick_search)
async def mode_nick_apply(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user_by_name((message.text or "").strip())
    if not user:
        await message.answer("Нету игрока с таким ником")
        return

    if await is_admin(message.from_user.id):
        await send_admin_card(message, user)
        return

    fines = await get_active_fines(user.id)
    await message.answer(render_public_fines(user, fines) if fines else "Игрок не получал штрафов")


# ---------- Admin: pick user by number ----------

@fines_router.message(FineStates.wait_pick_user_number)
async def pick_user_number(message: Message, state: FSMContext):
    if await deny_non_admin(message, state):
        return

    ids = (await state.get_data()).get("pick_ids", [])
    try:
        idx = int((message.text or "").strip())
    except ValueError:
        await message.answer("Нужно число (номер игрока).")
        return
    if idx < 1 or idx > len(ids):
        await message.answer("Неверный номер.")
        return

    await state.clear()
    user = await get_user_by_id(ids[idx - 1])
    if not user:
        await message.answer("Игрок не найден.")
        return
    await send_admin_card(message, user)


# ---------- Admin buttons (безопасно для чужих нажатий) ----------

@fines_router.callback_query(FineAdminCb.filter())
async def admin_buttons(callback: CallbackQuery, callback_data: FineAdminCb, state: FSMContext):
    user = await get_user_by_id(callback_data.user_id)
    if not user:
        await callback.answer("Игрок не найден.", show_alert=True)
        return

    # Не админ нажал на кнопку из пересланного сообщения — только показываем штрафы
    if not await is_admin(callback.from_user.id):
        fines = await get_active_fines(user.id)
        if fines:
            await callback.message.answer(render_public_fines(user, fines))
            await callback.answer()
        else:
            await callback.answer("У игрока нет штрафов.", show_alert=True)
        return

    action = callback_data.action

    if action == "card":
        await callback.answer()
        await safe_edit(callback.message, await render_admin_user(user), kb_admin_user_actions(user))
        return

    if action == "points_zero":
        await reset_user_points(user.id)
        user = await get_user_by_id(user.id)
        await callback.answer()
        await safe_edit(
            callback.message,
            "✅ Очки обнулены.\n\n" + await render_admin_user(user),
            kb_admin_user_actions(user),
        )
        return

    if action in ("points_set", "points_dec"):
        await state.set_state(FineStates.wait_points_set_value if action == "points_set" else FineStates.wait_points_dec_value)
        await state.update_data(target_user_id=user.id)
        prompt = ("Введи число. Очки пользователя станут равны этому числу:" if action == "points_set"
                  else "Введи число. На столько очков будет уменьшено:")
        await callback.message.answer(prompt)
        await callback.answer()
        return

    if action == "fine_add":
        await state.set_state(FineStates.wait_fine_text)
        await state.update_data(target_user_id=user.id)
        await callback.message.answer(f"Введи описание штрафа для {user.name}:")
        await callback.answer()
        return

    if action == "fines_list":
        fines = await get_active_fines(user.id)
        await callback.message.answer(render_fines_list(user, fines), reply_markup=kb_fines_list(user.id, fines))
        await callback.answer()
        return

    await callback.answer("Неизвестное действие.", show_alert=True)


# ---------- Admin: remove fine ----------

@fines_router.callback_query(FineRemoveCb.filter())
async def fine_remove(callback: CallbackQuery, callback_data: FineRemoveCb):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступно только администратору.", show_alert=True)
        return

    if not await remove_fine(callback_data.fine_id, callback.from_user.id):
        await callback.answer("Штраф уже закрыт.", show_alert=True)
    else:
        await callback.answer("✅ Штраф снят")

    user = await get_user_by_id(callback_data.user_id)
    if not user:
        return
    fines = await get_active_fines(user.id)
    await safe_edit(callback.message, render_fines_list(user, fines), kb_fines_list(user.id, fines))


# ---------- Admin: points set/dec apply ----------

@fines_router.message(FineStates.wait_points_set_value)
async def points_set_apply(message: Message, state: FSMContext):
    if await deny_non_admin(message, state):
        return
    try:
        value = parse_amount(message.text)
    except ValueError as e:
        await message.answer(str(e))
        return

    user_id = (await state.get_data()).get("target_user_id")
    await state.clear()
    await set_user_points_value(user_id, value)
    user = await get_user_by_id(user_id)
    await send_admin_card(message, user, f"✅ Очки установлены на {fmt_points(value)}.\n\n")


@fines_router.message(FineStates.wait_points_dec_value)
async def points_dec_apply(message: Message, state: FSMContext):
    if await deny_non_admin(message, state):
        return
    try:
        delta = parse_amount(message.text)
    except ValueError as e:
        await message.answer(str(e))
        return

    user_id = (await state.get_data()).get("target_user_id")
    await state.clear()
    await decrease_user_points(user_id, delta)
    user = await get_user_by_id(user_id)
    await send_admin_card(message, user, f"✅ Очки уменьшены на {fmt_points(delta)}.\n\n")


# ---------- Admin: add fine (описание → стоимость) ----------

@fines_router.message(FineStates.wait_fine_text)
async def fine_text_apply(message: Message, state: FSMContext):
    if await deny_non_admin(message, state):
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer("Описание штрафа не может быть пустым.")
        return
    await state.update_data(fine_text=text)
    await state.set_state(FineStates.wait_fine_cost)
    await message.answer("Стоимость штрафа в кадрах (0 — без оплаты, снимает только админ):")


@fines_router.message(FineStates.wait_fine_cost)
async def fine_cost_apply(message: Message, state: FSMContext):
    if await deny_non_admin(message, state):
        return
    try:
        cost = parse_amount(message.text)
    except ValueError as e:
        await message.answer(str(e))
        return

    data = await state.get_data()
    await state.clear()
    fine = await add_fine(data.get("target_user_id"), data.get("fine_text"), cost)
    if not fine:
        await message.answer("❌ Не удалось добавить штраф.")
        return
    user = await get_user_by_id(fine.user_id)
    await send_admin_card(message, user, "✅ Штраф добавлен.\n\n")
