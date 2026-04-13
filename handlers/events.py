from __future__ import annotations

from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession


from database.requests import (
    get_user, get_future_events, get_event_by_id,
    add_user_to_event, get_event_participants, update_user_points,
    get_all_events, delete_event_by_id, get_events,
    create_event, get_all_users, get_last_event_id
)

events_router = Router()


class EventStates(StatesGroup):
    waiting_event_number = State()
    waiting_participant_numbers = State()
    waiting_event_to_delete = State()


class AddEventStates(StatesGroup):
    name = State()
    time = State()
    cost = State()
    description = State()
    photo = State()


CANCEL_WORDS = {"отмена", "cancel", "стоп"}


def is_cancel(text: str | None) -> bool:
    return (text or "").strip().lower() in CANCEL_WORDS


@events_router.message(F.text.func(lambda t: (t or "").strip().lower() in CANCEL_WORDS))
async def cancel_any_flow(message: Message, state: FSMContext):
    current = await state.get_state()
    if current is None:
        await message.answer("Нечего отменять.")
        return
    await state.clear()
    await message.answer("❌ Действие отменено.")


def parse_dt_ru(text: str) -> datetime | None:
    try:
        return datetime.strptime(text.strip(), "%d.%m.%Y %H:%M")
    except Exception:
        return None


async def show_events_list(message: Message, user) -> list | None:
    events = await (get_events() if user.status != "user" else get_future_events())

    if not events:
        await message.answer("📅 На данный момент нет предстоящих событий.")
        return None

    response = "📋 Список событий:\n\n"
    for i, event in enumerate(events, 1):
        response += f"{i}. {event.name}\n"
        response += f"   📅 {event.time.strftime('%d.%m.%Y %H:%M')}\n"
        response += f"   🏆 {event.cost} очков\n\n"

    response += "Введите номер события для подробной информации (или 'отмена'):"
    await message.answer(response)
    return events


def build_event_caption(event) -> str:
    return (
        f"🎯 <b>{event.name}</b>\n\n"
        f"📅 <b>Дата и время:</b> {event.time.strftime('%d.%m.%Y %H:%M')}\n"
        f"🏆 <b>Очки за посещение:</b> {event.cost}\n"
        f"🆔 <b>ID события:</b> {event.id}"
    )


@events_router.message(F.text == "Список ивентов")
@events_router.message(Command("list_event"))
async def list_event(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйтесь с помощью /start")
        return

    events = await show_events_list(message, user)
    if events:
        await state.update_data(events=events, is_admin=(user.status == "admin"))
        await state.set_state(EventStates.waiting_event_number)


@events_router.message(EventStates.waiting_event_number)
async def process_event_number(message: Message, state: FSMContext):
    if is_cancel(message.text):
        await state.clear()
        await message.answer("❌ Выбор события отменён.")
        return

    data = await state.get_data()
    events = data.get("events") or []
    is_admin = data.get("is_admin", False)

    try:
        event_number = int(message.text.strip())
    except ValueError:
        await message.answer("Пожалуйста, введите номер цифрой (или 'отмена'):")
        return

    if not (1 <= event_number <= len(events)):
        await message.answer(f"Пожалуйста, введите номер от 1 до {len(events)} (или 'отмена'):")
        return

    event = events[event_number - 1]
    caption = build_event_caption(event)

    keyboard = InlineKeyboardBuilder()
    if is_admin:
        participants = await get_event_participants(event.id)
        if participants:
            text = "\n\n👥 Участники:\n"
            for i, p in enumerate(participants, 1):
                text += f"{i}. {p.name or 'Без имени'} (ID: {p.id})\n"
            caption += text
        else:
            caption += "\n\n👥 Участников пока нет."

        keyboard.add(InlineKeyboardButton(text="✅ Принять всех", callback_data=f"accept_all:{event.id}"))
        keyboard.add(InlineKeyboardButton(text="🔢 Принять по номерам", callback_data=f"accept_nums:{event.id}"))
        keyboard.add(InlineKeyboardButton(text="📋 Обновить список", callback_data=f"refresh:{event.id}"))

        await message.answer_photo(photo=event.photo_id, caption=caption, reply_markup=keyboard.as_markup())
        await message.answer(f"📝 {event.discription}")
    else:
        # Проверяем, не прошло ли время события
        if event.time > datetime.now():
            keyboard.add(InlineKeyboardButton(text="🎯 Участвовать", callback_data=f"participate:{event.id}"))
        await message.answer_photo(photo=event.photo_id, caption=caption, reply_markup=keyboard.as_markup(), parse_mode="html")
        await message.answer(f"📝 {event.discription}", parse_mode="html")
        await state.clear()


@events_router.callback_query(F.data.startswith("participate:"))
async def process_participation(callback: CallbackQuery):
    event_id = int(callback.data.split(":")[1])
    user = await get_user(callback.from_user.id)

    if not user:
        await callback.answer("Сначала зарегистрируйтесь!")
        return

    success = await add_user_to_event(user.id, event_id)
    if success:
        await callback.answer("✅ Вы успешно записались на событие!")
        await callback.message.edit_caption(caption=(callback.message.caption or "") + "\n\n✅ Вы записаны на это событие!")
    else:
        await callback.answer("⚠️ Вы уже записаны на это событие!")


@events_router.callback_query(F.data.startswith("accept_all:"))
async def accept_all_participants(callback: CallbackQuery):
    event_id = int(callback.data.split(":")[1])
    event = await get_event_by_id(event_id)
    participants = await get_event_participants(event_id)

    if not participants:
        await callback.answer("Нет участников для начисления очков!")
        return

    for p in participants:
        await update_user_points(p.id, event.cost)

    await callback.answer(f"✅ Начислено очки всем {len(participants)} участникам!")

    updated = await get_event_participants(event_id)
    base_caption = build_event_caption(event)

    if updated:
        text = "\n\n👥 Участники (очки начислены):\n"
        for i, p in enumerate(updated, 1):
            text += f"{i}. {p.name or 'Без имени'} (ID: {p.id})\n"
        await callback.message.edit_caption(caption=base_caption + text)
    else:
        await callback.message.edit_caption(caption=base_caption + "\n\n👥 Участников пока нет.")


@events_router.callback_query(F.data.startswith("accept_nums:"))
async def accept_by_numbers(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split(":")[1])
    event = await get_event_by_id(event_id)
    participants = await get_event_participants(event_id)

    if not participants:
        await callback.answer("Нет участников для начисления очков!")
        return

    text = "Введите номера участников через запятую (например: 1,3,5) или 'отмена':\n\n"
    for i, p in enumerate(participants, 1):
        text += f"{i}. {p.name or 'Без имени'}\n"

    await state.update_data(event_id=event_id, event_cost=event.cost, participants=participants)
    await state.set_state(EventStates.waiting_participant_numbers)

    await callback.message.answer(text)
    await callback.answer()


@events_router.message(EventStates.waiting_participant_numbers)
async def process_participant_numbers(message: Message, state: FSMContext):
    if is_cancel(message.text):
        await state.clear()
        await message.answer("❌ Начисление очков отменено.")
        return

    data = await state.get_data()
    event_id = data.get("event_id")
    event_cost = data.get("event_cost")
    participants = data.get("participants") or []

    try:
        numbers = [int(x.strip()) for x in (message.text or "").split(",") if x.strip()]
    except ValueError:
        await message.answer("Неверный формат. Введите номера через запятую (например: 1,3,5) или 'отмена':")
        return

    if not numbers:
        await message.answer("Вы не указали номера. Пример: 1,3,5 (или 'отмена'):")
        return

    invalid = [n for n in numbers if not (1 <= n <= len(participants))]
    if invalid:
        await message.answer(f"Неверные номера: {invalid}. Введите номера от 1 до {len(participants)} (или 'отмена'):")
        return

    for n in numbers:
        p = participants[n - 1]
        await update_user_points(p.id, event_cost)

    await message.answer(f"✅ Очки начислены {len(numbers)} участникам!")

    updated = await get_event_participants(event_id)
    chosen = set(numbers)
    text = "Обновленный список участников:\n\n"
    for i, p in enumerate(updated, 1):
        marker = "✅ " if i in chosen else ""
        text += f"{i}. {marker}{p.name or 'Без имени'}\n"
    await message.answer(text)

    await state.clear()


@events_router.callback_query(F.data.startswith("refresh:"))
async def refresh_participants(callback: CallbackQuery):
    event_id = int(callback.data.split(":")[1])
    event = await get_event_by_id(event_id)
    participants = await get_event_participants(event_id)

    base_caption = build_event_caption(event)

    if participants:
        text = "\n\n👥 Участники:\n"
        for i, p in enumerate(participants, 1):
            text += f"{i}. {p.name or 'Без имени'} (ID: {p.id})\n"
        new_caption = base_caption + text
    else:
        new_caption = base_caption + "\n\n👥 Участников пока нет."

    await callback.message.edit_caption(caption=new_caption)
    await callback.answer("✅ Список обновлен!")


@events_router.message(F.text == "Удалить ивент")
@events_router.message(Command("delete_event"))
async def delete_event_command(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user or user.status != "admin":
        await message.answer("❌ У вас нет прав для удаления ивентов!")
        return

    events = await get_all_events()
    if not events:
        await message.answer("📭 Нет доступных ивентов для удаления.")
        return

    text = "📋 Список ивентов для удаления:\n\n"
    for i, e in enumerate(events, 1):
        text += f"{i}. 🆔 {e.id} | {e.name}\n"
        text += f"   📅 {e.time.strftime('%d.%m.%Y %H:%M')}\n"
        text += f"   🏆 {e.cost} очков\n\n"
    text += "Введите номер ивента для удаления (или 'отмена'):"

    await state.update_data(events_for_deletion=events)
    await state.set_state(EventStates.waiting_event_to_delete)
    await message.answer(text)


@events_router.message(EventStates.waiting_event_to_delete)
async def process_event_deletion(message: Message, state: FSMContext):
    if is_cancel(message.text):
        await state.clear()
        await message.answer("❌ Удаление отменено.")
        return

    data = await state.get_data()
    events = data.get("events_for_deletion") or []

    try:
        event_number = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Введите номер цифрой (или 'отмена'):")
        return

    if not (1 <= event_number <= len(events)):
        await message.answer(f"⚠️ Введите номер от 1 до {len(events)} (или 'отмена'):")
        return

    event_to_delete = events[event_number - 1]

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete:{event_to_delete.id}"),
        InlineKeyboardButton(text="❌ Нет, отменить", callback_data="cancel_delete"),
    )

    text = (
        "⚠️ ВНИМАНИЕ: Вы уверены, что хотите удалить этот ивент?\n\n"
        f"🎯 {event_to_delete.name}\n"
        f"📅 Дата: {event_to_delete.time.strftime('%d.%m.%Y %H:%M')}\n"
        f"🏆 Очки: {event_to_delete.cost}\n"
        f"🆔 ID: {event_to_delete.id}\n\n"
        "Это действие невозможно отменить!"
    )
    await message.answer(text, reply_markup=keyboard.as_markup())
    await state.clear()


@events_router.callback_query(F.data.startswith("confirm_delete:"))
async def confirm_event_deletion(callback: CallbackQuery):
    event_id = int(callback.data.split(":")[1])
    success = await delete_event_by_id(event_id)

    if success:
        await callback.message.edit_text(f"✅ Ивент ID {event_id} успешно удален!")
        await callback.answer()
    else:
        await callback.message.edit_text(f"❌ Ошибка при удалении ивента ID {event_id}")
        await callback.answer("Произошла ошибка!")


@events_router.callback_query(F.data == "cancel_delete")
async def cancel_event_deletion(callback: CallbackQuery):
    await callback.message.edit_text("❌ Удаление отменено.")
    await callback.answer()


@events_router.message(F.text == "Добавить ивент")
@events_router.message(Command("add_event"))
async def add_event_start(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user or user.status != "admin":
        await message.answer("❌ У вас нет прав для добавления ивентов!")
        return

    await state.clear()
    await state.set_state(AddEventStates.name)
    await message.answer("Введите название ивента (или 'отмена'):")


@events_router.message(AddEventStates.name)
async def add_event_name(message: Message, state: FSMContext):
    if is_cancel(message.text):
        await state.clear()
        await message.answer("❌ Добавление ивента отменено.")
        return

    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Слишком короткое название. Введите снова (или 'отмена'):")
        return

    await state.update_data(name=name)
    await state.set_state(AddEventStates.time)
    await message.answer("Введите дату и время в формате DD.MM.YYYY HH:MM (или 'отмена'):")


@events_router.message(AddEventStates.time)
async def add_event_time(message: Message, state: FSMContext):
    if is_cancel(message.text):
        await state.clear()
        await message.answer("❌ Добавление ивента отменено.")
        return

    dt = parse_dt_ru(message.text or "")
    if not dt:
        await message.answer("Неверный формат даты. Пример: 31.01.2026 18:30 (или 'отмена'):")
        return

    await state.update_data(time=dt)
    await state.set_state(AddEventStates.cost)
    await message.answer("Введите стоимость (очки), число (или 'отмена'):")


@events_router.message(AddEventStates.cost)
async def add_event_cost(message: Message, state: FSMContext):
    if is_cancel(message.text):
        await state.clear()
        await message.answer("❌ Добавление ивента отменено.")
        return

    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("Нужно число. Пример: 10 (или 'отмена'):")
        return

    cost = int(text)
    if cost <= 0:
        await message.answer("Очки должны быть > 0. Введите снова (или 'отмена'):")
        return

    await state.update_data(cost=cost)
    await state.set_state(AddEventStates.description)
    await message.answer("Введите описание ивента (или 'отмена'):")


@events_router.message(AddEventStates.description)
async def add_event_description(message: Message, state: FSMContext):
    if is_cancel(message.text):
        await state.clear()
        await message.answer("❌ Добавление ивента отменено.")
        return

    description = (message.text or "").strip()
    if len(description) < 5:
        await message.answer("Описание слишком короткое. Введите снова (или 'отмена'):")
        return

    await state.update_data(description=description)
    await state.set_state(AddEventStates.photo)
    await message.answer("Отправьте фото ивента (или 'отмена'):")


@events_router.message(AddEventStates.photo)
async def add_event_photo(message: Message, state: FSMContext):
    if message.text and is_cancel(message.text):
        await state.clear()
        await message.answer("❌ Добавление ивента отменено.")
        return

    if not message.photo:
        await message.answer("Нужно отправить фото (как картинку) (или 'отмена'):")
        return

    photo_id = message.photo[-1].file_id
    data = await state.get_data()

    event = await create_event(
        name=data["name"],
        time=data["time"],
        cost=data["cost"],
        discription=data["description"],
        photo_id=photo_id,
    )

    # Отправляем уведомление всем пользователям
    users = await get_all_users()
    
    event_info = (
        f"🎯 <b>{event.name}</b>\n\n"
        f"📅 <b>Дата и время:</b> {event.time.strftime('%d.%m.%Y %H:%M')}\n"
        f"🏆 <b>Очки за посещение:</b> {event.cost}\n"
        f"🆔 <b>ID события:</b> {event.id}"
    )
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(
        text="🎯 Участвовать", 
        callback_data=f"participate:{event.id}"
    ))
    
    for user in users:
        try:
            await message.bot.send_photo(
                chat_id=user.tg_id,
                photo=photo_id,
                caption=event_info,
                reply_markup=keyboard.as_markup(),
                parse_mode="html"
            )
        except Exception as e:
            print(f"Ошибка при отправке уведомления пользователю {user.tg_id}: {e}")
    
    await message.answer(f"📝 {data['description']}")

    await state.clear()
    await message.answer("✅ Ивент создан и отправлен всем пользователям!")
