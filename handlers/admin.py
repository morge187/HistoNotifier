import os
from aiogram import Router
from datetime import datetime
from aiogram import F
from keyboards import adminboard
from database.requests import get_user, save_event, get_all_users, get_last_event_id
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import Message, ContentType, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()

admin = Router()

class CreateEvent(StatesGroup):
    id = State()           # Айди
    change_is = State()    # Режим измения
    name = State()         # Название события
    description = State()  # Описание события
    datetime = State()     # Дата и время проведения
    points = State()       # Количество очков за посещение
    image = State()        # Картинка для события

# 1. Функция для начала создания события
@admin.message(F.text == "Добавить ивент")
@admin.message(Command("create_event"))
async def start_create_event(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if user.status != 'admin':
        await message.answer("Отказано в правах доступа")
        return
    
    await message.answer(
        "📝 Давайте создадим новое событие!\n\n"
        "Шаг 1/5: Введите название события:"
    )
    await state.set_state(CreateEvent.name)

# 2. Функция для получения названия
@admin.message(CreateEvent.name)
async def get_event_name(message: Message, state: FSMContext):
    if len(message.text) < 3:
        await message.answer("Название слишком короткое. Введите название минимум из 3 символов:")
        return
    
    await state.update_data(name=message.text)
    await message.answer(
        "✅ Название сохранено!\n\n"
        "Шаг 2/5: Введите описание события:"
    )
    await state.set_state(CreateEvent.description)

# 3. Функция для получения описания
@admin.message(CreateEvent.description)
async def get_event_description(message: Message, state: FSMContext):
    if len(message.text) < 5:
        await message.answer("Описание слишком короткое. Введите более подробное описание:")
        return
    
    await state.update_data(description=message.text)
    await message.answer(
        "✅ Описание сохранено!\n\n"
        "Шаг 3/5: Введите дату и время проведения события.\n"
        "Формат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Пример: 15.12.2024 18:30"
    )
    await state.set_state(CreateEvent.datetime)

# 4. Функция для получения даты и времени
@admin.message(CreateEvent.datetime)
async def get_event_datetime(message: Message, state: FSMContext):
    try:
        # Парсим дату и время
        event_datetime = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        
        # Проверяем, что дата не в прошлом
        if event_datetime < datetime.now():
            await message.answer("Дата не может быть в прошлом. Введите корректную дату:")
            return
            
        await state.update_data(
            datetime_str=message.text,
            datetime_obj=event_datetime
        )
        await message.answer(
            "✅ Дата и время сохранены!\n\n"
            "Шаг 4/5: Введите количество очков за посещение события:"
        )
        await state.set_state(CreateEvent.points)
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат даты!\n"
            "Пожалуйста, введите дату и время в формате:\n"
            "ДД.ММ.ГГГГ ЧЧ:ММ\n"
            "Пример: 15.12.2024 18:30"
        )

# 5. Функция для получения количества очков
@admin.message(CreateEvent.points)
async def get_event_points(message: Message, state: FSMContext):
    try:
        raw = message.text.strip().replace(',', '.')
        points = round(float(raw), 2)
        if '.' in raw and len(raw.split('.')[-1]) > 2:
            await message.answer("Максимум 2 знака после запятой. Введите ещё раз:")
            return
        if points <= 0:
            await message.answer("Количество очков должно быть положительным числом. Введите ещё раз:")
            return

        await state.update_data(points=points)
        await message.answer(
            "✅ Количество очков сохранено!\n\n"
            "Шаг 5/5: Отправьте картинку для события (фото):"
        )
        await state.set_state(CreateEvent.image)

    except ValueError:
        await message.answer("Пожалуйста, введите число (например: 10, 5.5, 0.25):")

# 6. Функция для получения картинки
@admin.message(CreateEvent.image, F.content_type == ContentType.PHOTO)
async def get_event_image(message: Message, state: FSMContext):
    # Получаем самую качественную версию фото
    photo = message.photo[-1]
    file_id = photo.file_id
    
    # Получаем все данные из состояния
    data = await state.get_data()
    
    # Сохраняем file_id картинки
    await state.update_data(image_file_id=file_id)
    
    # Формируем итоговое сообщение с информацией о событии
    event_info = (
        "🎉 Событие успешно создано!\n\n"
        f"📌 Название: {data['name']}\n"
        f"📝 Описание: {data['description']}\n"
        f"📅 Дата и время: {data['datetime_str']}\n"
        f"🏆 Очков за посещение: {data['points']}\n"
        f"🖼️ Картинка: отправлена"
    )
    
    # Отправляем подтверждение с картинкой
    await message.answer_photo(
        photo=file_id,
        caption=event_info
    )

    # В функции get_event_image:
    event_data = {
        'id': -1,  # Можно убрать или использовать None
        'name': data['name'],
        'description': data['description'],  # Убедитесь что это строка
        'datetime': data['datetime_obj'],
        'points': data['points'],
        'image_file_id': file_id,
        'created_by': message.from_user.id
    }
    await save_event(event_data)
    
    # Отправляем всем пользователям уведомление
    users = await get_all_users()

    event_id = await get_last_event_id()
    
    for user in users:
        keyboard = InlineKeyboardBuilder()
        # Добавляем кнопку только если событие еще в будущем
        if data['datetime_obj'] > datetime.now():
            keyboard.add(InlineKeyboardButton(
                text="🎯 Участвовать", 
                callback_data=f"participate:{event_id}"
            ))
    
        await message.bot.send_photo(
            chat_id=user.tg_id,
            photo=file_id,
            caption=event_info,
            reply_markup=keyboard.as_markup()
        )
    
    await state.clear()
    
    # Дополнительная кнопка для действий
    await message.answer(
        "Что дальше?\n"
        "• /create_event - создать еще одно событие\n"
        "• /events - посмотреть все события\n"
        "• /change_event - изменить ивент ",
        reply_markup=adminboard  # ваша пользовательская клавиатура
    )

# 7. Функция для обработки случая, когда отправлен не фото
@admin.message(CreateEvent.image)
async def wrong_image_format(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, отправьте именно фото (картинку) для события:")

# handlers/fine.py - написать с нуля
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from database.requests import (
    is_admin,
    # users
    get_user_by_name,
    get_user_by_id,
    get_all_users_ordered,
    get_users_with_fines,
    get_users_with_fines_by_event,
    # events
    get_all_events,
    get_event_by_index,
    get_event_participants,
    # points
    set_user_points_value,
    decrease_user_points,
    reset_user_points,
    # fines
    set_user_fine,
)

admin = Router()


# ---------- CallbackData ----------

class FineMenuCb(CallbackData, prefix="fine_menu"):
    action: str  # all | event | nick


class FineAdminCb(CallbackData, prefix="fine_adm"):
    action: str  # points_zero | points_set | points_dec | fine_add
    user_id: int


class BackCb(CallbackData, prefix="back"):
    target: str  # to_main


# ---------- FSM ----------

class FineStates(StatesGroup):
    # mode event selection
    wait_event_number = State()
    # mode nick input
    wait_nick_search = State()
    # admin: choose user from list by number (all / event)
    wait_pick_user_number = State()
    # admin: points edit
    wait_points_set_value = State()
    wait_points_dec_value = State()
    # admin: fine text input
    wait_fine_text = State()


# ---------- Render helpers ----------

def render_public_user(user) -> str:
    fine = (getattr(user, "fine", None) or "").strip()
    return f"{user.name} - {fine}"


def render_admin_user(user) -> str:
    fine = (getattr(user, "fine", None) or "").strip() or "нет"
    points = getattr(user, "points", None) or 0
    status = getattr(user, "status", None)
    tg_id = getattr(user, "tg_id", None)

    lines = [
        f"Игрок: {user.name}",
        f"Штраф: {fine}",
        f"Очки: {points}",
    ]
    if status is not None:
        lines.append(f"Статус: {status}")
    if tg_id is not None:
        lines.append(f"tg_id: {tg_id}")
    return "\n".join(lines)


# ---------- Keyboards ----------

def kb_search_menu(is_admin_user: bool):
    kb = InlineKeyboardBuilder()
    kb.button(text="Все игроки", callback_data=FineMenuCb(action="all").pack())
    kb.button(text="По ивенту", callback_data=FineMenuCb(action="event").pack())
    kb.button(text="По нику", callback_data=FineMenuCb(action="nick").pack())
    kb.adjust(1)
    return kb.as_markup()


def kb_admin_user_actions(user_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="Обнулить очки", callback_data=FineAdminCb(action="points_zero", user_id=user_id).pack())
    kb.button(text="Задать очки", callback_data=FineAdminCb(action="points_set", user_id=user_id).pack())
    kb.button(text="Убавить очки", callback_data=FineAdminCb(action="points_dec", user_id=user_id).pack())
    kb.button(text="Добавить штраф", callback_data=FineAdminCb(action="fine_add", user_id=user_id).pack())
    kb.button(text="Назад", callback_data=BackCb(target="to_main").pack())
    kb.adjust(1)
    return kb.as_markup()


# ---------- Entry ----------

@admin.message(F.text == "матч-штрафы")
async def fine_entry(message: Message, state: FSMContext):
    await state.clear()
    is_admin_user = await is_admin(message.from_user.id)
    await message.answer("режим поиска", reply_markup=kb_search_menu(is_admin_user))


@admin.callback_query(BackCb.filter(F.target == "to_main"))
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin_user = await is_admin(callback.from_user.id)
    await callback.message.edit_text("режим поиска", reply_markup=kb_search_menu(is_admin_user))
    await callback.answer()


# ---------- Menu: ALL ----------

@admin.callback_query(FineMenuCb.filter(F.action == "all"))
async def mode_all(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin_user = await is_admin(callback.from_user.id)

    # ADMIN: show ALL users, then allow pick any
    if is_admin_user:
        users = await get_all_users_ordered()
        if not users:
            await callback.message.answer("Пользователей нет.")
            await callback.answer()
            return

        await state.set_state(FineStates.wait_pick_user_number)
        await state.update_data(pick_ids=[u.id for u in users])

        lines = [f"{i}. {u.name} (очки: {u.points or 0})" for i, u in enumerate(users, start=1)]
        await callback.message.answer("\n".join(lines) + "\n\nВведи номер игрока:")
        await callback.answer()
        return

    # USER: only fined
    users = await get_users_with_fines()
    if not users:
        await callback.message.answer("Игроки с штрафом отсутствуют")
        await callback.answer()
        return

    lines = [f"{i}. {u.name} - {u.fine}" for i, u in enumerate(users, start=1)]
    await callback.message.answer("\n".join(lines))
    await callback.answer()


# ---------- Menu: EVENT ----------

@admin.callback_query(FineMenuCb.filter(F.action == "event"))
async def mode_event_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(FineStates.wait_event_number)

    events = await get_all_events()
    if not events:
        await callback.message.answer("Ивентов нет.")
        await callback.answer()
        await state.clear()
        return

    lines = []
    for i, e in enumerate(events, start=1):
        dt = e.time.strftime("%d.%m.%Y %H:%M") if getattr(e, "time", None) else ""
        lines.append(f"{i}. {e.name} {dt}".strip())

    await state.update_data(events_count=len(events))
    await callback.message.answer("\n".join(lines) + "\n\nВведи номер ивента:")
    await callback.answer()


@admin.message(FineStates.wait_event_number)
async def mode_event_apply(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        idx = int(message.text.strip())
    except ValueError:
        await message.answer("Нужно число (номер ивента).")
        return

    events_count = data.get("events_count", 0)
    if idx < 1 or idx > events_count:
        await message.answer("Неверный номер ивента.")
        return

    event = await get_event_by_index(idx)
    if not event:
        await message.answer("Ивент не найден.")
        await state.clear()
        return

    is_admin_user = await is_admin(message.from_user.id)

    # ADMIN: can select ANY participant (fine/no fine)
    if is_admin_user:
        users = await get_event_participants(event.id)
        if not users:
            await message.answer("Участников ивента нет.")
            await state.clear()
            return

        await state.set_state(FineStates.wait_pick_user_number)
        await state.update_data(pick_ids=[u.id for u in users])

        lines = [f"{i}. {u.name} (очки: {u.points or 0})" for i, u in enumerate(users, start=1)]
        await message.answer("\n".join(lines) + "\n\nВведи номер игрока:")
        return

    # USER: only fined participants
    users = await get_users_with_fines_by_event(event.id)
    if not users:
        await message.answer("Игроки с штрафом отсутствуют")
        await state.clear()
        return

    lines = [f"{i}. {u.name} - {u.fine}" for i, u in enumerate(users, start=1)]
    await message.answer("\n".join(lines))
    await state.clear()


# ---------- Menu: NICK ----------

@admin.callback_query(FineMenuCb.filter(F.action == "nick"))
async def mode_nick_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(FineStates.wait_nick_search)
    await callback.message.answer("Введи ник пользователя")
    await callback.answer()


@admin.message(FineStates.wait_nick_search)
async def mode_nick_apply(message: Message, state: FSMContext):
    nick = message.text.strip()
    user = await get_user_by_name(nick)

    if not user:
        await message.answer("Нету игрока с таким ником")
        await state.clear()
        return

    is_admin_user = await is_admin(message.from_user.id)

    # ADMIN: always full card + buttons (fine/no fine)
    if is_admin_user:
        await message.answer(render_admin_user(user), reply_markup=kb_admin_user_actions(user.id))
        await state.clear()
        return

    # USER: only if fined, and only nick+fine
    fine = (user.fine or "").strip()
    if not fine:
        await message.answer("Игрок не получал штрафов")
    else:
        await message.answer(render_public_user(user))
    await state.clear()


# ---------- Admin: pick user by number ----------

@admin.message(FineStates.wait_pick_user_number)
async def pick_user_number(message: Message, state: FSMContext):
    # Only admin allowed to pick any user
    if not await is_admin(message.from_user.id):
        await state.clear()
        await message.answer("Доступно только администратору.")
        return

    data = await state.get_data()
    ids = data.get("pick_ids", [])

    try:
        idx = int(message.text.strip())
    except ValueError:
        await message.answer("Нужно число (номер игрока).")
        return

    if idx < 1 or idx > len(ids):
        await message.answer("Неверный номер.")
        return

    user_id = ids[idx - 1]
    user = await get_user_by_id(user_id)
    if not user:
        await state.clear()
        await message.answer("Игрок не найден.")
        return

    await state.clear()
    await message.answer(render_admin_user(user), reply_markup=kb_admin_user_actions(user.id))


# ---------- Admin buttons (safe for public clicks) ----------

@admin.callback_query(FineAdminCb.filter())
async def admin_buttons(callback: CallbackQuery, callback_data: FineAdminCb, state: FSMContext):
    user = await get_user_by_id(callback_data.user_id)
    if not user:
        await callback.answer("Игрок не найден.", show_alert=True)
        return

    # PUBLIC CLICK: do not change anything; show only nick+fine and only if fine exists
    if not await is_admin(callback.from_user.id):
        fine = (user.fine or "").strip()
        if fine:
            await callback.message.answer(render_public_user(user))
            await callback.answer()
        else:
            await callback.answer("У игрока нет штрафов.", show_alert=True)
        return

    # ADMIN actions:
    if callback_data.action == "points_zero":
        await reset_user_points(user.id)
        user = await get_user_by_id(user.id)
        await callback.message.edit_text(
            "✅ Очки обнулены.\n\n" + render_admin_user(user),
            reply_markup=kb_admin_user_actions(user.id)
        )
        await callback.answer()
        return

    if callback_data.action == "points_set":
        await state.set_state(FineStates.wait_points_set_value)
        await state.update_data(target_user_id=user.id)
        await callback.message.answer("Введи число. Очки пользователя станут равны этому числу:")
        await callback.answer()
        return

    if callback_data.action == "points_dec":
        await state.set_state(FineStates.wait_points_dec_value)
        await state.update_data(target_user_id=user.id)
        await callback.message.answer("Введи число. На столько очков будет уменьшено:")
        await callback.answer()
        return

    if callback_data.action == "fine_add":
        await state.set_state(FineStates.wait_fine_text)
        await state.update_data(target_user_id=user.id)
        await callback.message.answer(f"Введи текст штрафа для {user.name}:")
        await callback.answer()
        return

    await callback.answer("Неизвестное действие.", show_alert=True)


# ---------- Admin: points set/dec apply ----------

@admin.message(FineStates.wait_points_set_value)
async def points_set_apply(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await state.clear()
        await message.answer("Доступно только администратору.")
        return

    data = await state.get_data()
    user_id = data.get("target_user_id")

    try:
        raw = message.text.strip().replace(',', '.')
        value = round(float(raw), 2)
        if '.' in raw and len(raw.split('.')[-1]) > 2:
            await message.answer("Максимум 2 знака после запятой.")
            return
    except ValueError:
        await message.answer("Нужно число.")
        return

    await set_user_points_value(user_id, value)
    user = await get_user_by_id(user_id)
    await message.answer(
        f"✅ Очки установлены на {value}.\n\n" + render_admin_user(user),
        reply_markup=kb_admin_user_actions(user.id)
    )
    await state.clear()


@admin.message(FineStates.wait_points_dec_value)
async def points_dec_apply(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await state.clear()
        await message.answer("Доступно только администратору.")
        return

    data = await state.get_data()
    user_id = data.get("target_user_id")

    try:
        raw = message.text.strip().replace(',', '.')
        delta = round(float(raw), 2)
        if '.' in raw and len(raw.split('.')[-1]) > 2:
            await message.answer("Максимум 2 знака после запятой.")
            return
    except ValueError:
        await message.answer("Нужно число.")
        return

    await decrease_user_points(user_id, delta)
    user = await get_user_by_id(user_id)
    await message.answer(
        f"✅ Очки уменьшены на {delta}.\n\n" + render_admin_user(user),
        reply_markup=kb_admin_user_actions(user.id)
    )
    await state.clear()


# ---------- Admin: fine add apply ----------

@admin.message(FineStates.wait_fine_text)
async def fine_add_apply(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await state.clear()
        await message.answer("Доступно только администратору.")
        return

    data = await state.get_data()
    user_id = data.get("target_user_id")
    fine_text = message.text.strip()

    if not fine_text:
        await message.answer("Текст штрафа не может быть пустым.")
        return

    ok = await set_user_fine(user_id, fine_text)
    if not ok:
        await state.clear()
        await message.answer("❌ Не удалось установить штраф.")
        return

    user = await get_user_by_id(user_id)
    await message.answer("✅ Штраф установлен.\n\n" + render_admin_user(user), reply_markup=kb_admin_user_actions(user.id))
    await state.clear()
