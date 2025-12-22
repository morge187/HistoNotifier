from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
import re

from database.requests import (
    get_user, get_future_events, get_event_by_id, 
    get_event_by_index, add_user_to_event, 
    get_event_participants, update_user_points,
    get_all_events, delete_event_by_id
)
from database.models import User

events_router = Router()

class EventStates(StatesGroup):
    waiting_event_number = State()
    waiting_admin_action = State()
    waiting_participant_numbers = State()
    waiting_event_to_delete = State()

# Общая функция для отображения списка событий
async def show_events_list(message: Message, is_admin=False):
    events = await get_future_events()
    
    if not events:
        await message.answer("📅 На данный момент нет предстоящих событий.")
        return None
    
    response = "📋 Список предстоящих событий:\n\n"
    for i, event in enumerate(events, 1):
        response += f"{i}. {event.name}\n"
        response += f"   📅 {event.time.strftime('%d.%m.%Y %H:%M')}\n"
        response += f"   🏆 {event.cost} очков\n\n"
    
    response += "Введите номер события для подробной информации:"
    await message.answer(response)
    
    return events

# Команда для просмотра событий
@events_router.message(F.text == "Список ивентов")
@events_router.message(Command('list_event'))
async def list_event(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйтесь с помощью /start")
        return
    
    events = await show_events_list(message, is_admin=(user.status == 'admin'))
    if events:
        await state.update_data(events=events, is_admin=(user.status == 'admin'))
        await state.set_state(EventStates.waiting_event_number)

# Обработка выбора события
@events_router.message(EventStates.waiting_event_number)
async def process_event_number(message: Message, state: FSMContext):
    try:
        event_number = int(message.text.strip())
    except ValueError:
        await message.answer("Пожалуйста, введите номер цифрой:")
        return
    
    data = await state.get_data()
    events = data.get('events', [])
    is_admin = data.get('is_admin', False)
    
    if not (1 <= event_number <= len(events)):
        await message.answer(f"Пожалуйста, введите номер от 1 до {len(events)}:")
        return
    
    # Получаем выбранное событие
    event = events[event_number - 1]
    
    # Сохраняем выбранное событие в состоянии
    await state.update_data(selected_event=event, event_number=event_number)
    
    # Формируем карточку события
    event_card = (
        f"🎯 <b>{event.name}</b>\n\n"
        f"📝 {event.discription}\n\n"
        f"📅 <b>Дата и время:</b> {event.time.strftime('%d.%m.%Y %H:%M')}\n"
        f"🏆 <b>Очки за посещение:</b> {event.cost}\n"
        f"🆔 <b>ID события:</b> {event.id}"
    )
    
    if is_admin:
        # Для админа показываем участников
        participants = await get_event_participants(event.id)
        
        if participants:
            participants_list = "📋 Участники:\n"
            for i, participant in enumerate(participants, 1):
                participants_list += f"{i}. {participant.name or 'Без имени'} (ID: {participant.id})\n"
            event_card += f"\n\n{participants_list}"
        else:
            event_card += "\n\n👥 Участников пока нет."
        
        # Клавиатура для админа
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(
            text="✅ Принять всех", 
            callback_data=f"accept_all_{event.id}"
        ))
        keyboard.add(InlineKeyboardButton(
            text="🔢 Принять по номерам", 
            callback_data=f"accept_by_numbers_{event.id}"
        ))
        keyboard.add(InlineKeyboardButton(
            text="📋 Обновить список", 
            callback_data=f"refresh_{event.id}"
        ))
        
        await message.answer_photo(
            photo=event.photo_id,
            caption=event_card,
            reply_markup=keyboard.as_markup()
        )
        await state.set_state(EventStates.waiting_admin_action)
        
    else:
        # Для обычного пользователя кнопка "Участвовать"
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(
            text="🎯 Участвовать", 
            callback_data=f"participate_{event.id}"
        ))
        
        await message.answer_photo(
            photo=event.photo_id,
            caption=event_card,
            reply_markup=keyboard.as_markup()
        )
        await state.clear()

# Обработка нажатия "Участвовать"
@events_router.callback_query(F.data.startswith("participate_"))
async def process_participation(callback: CallbackQuery):
    event_id = int(callback.data.split("_")[1])
    user = await get_user(callback.from_user.id)
    
    if not user:
        await callback.answer("Сначала зарегистрируйтесь!")
        return
    
    success = await add_user_to_event(user.id, event_id)
    
    if success:
        await callback.answer("✅ Вы успешно записались на событие!")
        await callback.message.edit_caption(
            caption=callback.message.caption + "\n\n✅ Вы записаны на это событие!"
        )
    else:
        await callback.answer("⚠️ Вы уже записаны на это событие!")

# Обработка действий админа
@events_router.callback_query(F.data.startswith("accept_all_"))
async def accept_all_participants(callback: CallbackQuery):
    event_id = int(callback.data.split("_")[2])
    event = await get_event_by_id(event_id)
    
    participants = await get_event_participants(event_id)
    
    if not participants:
        await callback.answer("Нет участников для начисления очков!")
        return
    
    for participant in participants:
        await update_user_points(participant.id, event.cost)
    
    await callback.answer(f"✅ Начислено очки всем {len(participants)} участникам!")
    
    # Обновляем сообщение
    participants = await get_event_participants(event_id)
    caption = callback.message.caption.split("\n\n👥")[0]
    if participants:
        participants_list = "\n\n👥 Участники (очки начислены):\n"
        for i, participant in enumerate(participants, 1):
            participants_list += f"{i}. {participant.name or 'Без имени'} (ID: {participant.id})\n"
        caption += participants_list
    
    await callback.message.edit_caption(caption=caption)

@events_router.callback_query(F.data.startswith("accept_by_numbers_"))
async def accept_by_numbers(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split("_")[3])
    event = await get_event_by_id(event_id)
    
    participants = await get_event_participants(event_id)
    
    if not participants:
        await callback.answer("Нет участников для начисления очков!")
        return
    
    participants_list = "Введите номера участников через запятую:\n\n"
    for i, participant in enumerate(participants, 1):
        participants_list += f"{i}. {participant.name or 'Без имени'}\n"
    
    await callback.message.answer(participants_list)
    await state.update_data(event_id=event_id, event_cost=event.cost, participants=participants)
    await state.set_state(EventStates.waiting_participant_numbers)
    await callback.answer()

@events_router.callback_query(F.data.startswith("refresh_"))
async def refresh_participants(callback: CallbackQuery):
    event_id = int(callback.data.split("_")[1])
    event = await get_event_by_id(event_id)
    participants = await get_event_participants(event_id)
    
    # Обновляем список участников в сообщении
    caption_parts = callback.message.caption.split("\n\n👥")
    base_caption = caption_parts[0]
    
    if participants:
        participants_list = "\n\n👥 Участники:\n"
        for i, participant in enumerate(participants, 1):
            participants_list += f"{i}. {participant.name or 'Без имени'} (ID: {participant.id})\n"
        new_caption = base_caption + participants_list
    else:
        new_caption = base_caption + "\n\n👥 Участников пока нет."
    
    await callback.message.edit_caption(caption=new_caption)
    await callback.answer("✅ Список обновлен!")

# Обработка ввода номеров участников
@events_router.message(EventStates.waiting_participant_numbers)
async def process_participant_numbers(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get('event_id')
    event_cost = data.get('event_cost')
    participants = data.get('participants', [])
    
    try:
        # Парсим номера через запятую
        numbers_str = message.text.strip()
        numbers = [int(num.strip()) for num in numbers_str.split(',')]
        
        # Проверяем, что все номера в диапазоне
        invalid_numbers = [num for num in numbers if not (1 <= num <= len(participants))]
        if invalid_numbers:
            await message.answer(f"Неверные номера: {invalid_numbers}. Введите номера от 1 до {len(participants)}:")
            return
        
        # Начисляем очки выбранным участникам
        for num in numbers:
            participant = participants[num - 1]
            await update_user_points(participant.id, event_cost)
        
        await message.answer(f"✅ Очки начислены {len(numbers)} участникам!")
        
        # Показываем обновленный список
        participants = await get_event_participants(event_id)
        participants_list = "Обновленный список участников:\n\n"
        for i, participant in enumerate(participants, 1):
            marker = "✅ " if (i in numbers) else ""
            participants_list += f"{i}. {marker}{participant.name or 'Без имени'}\n"
        
        await message.answer(participants_list)
        
    except ValueError:
        await message.answer("Неверный формат. Введите номера через запятую (например: 1,3,5):")
        return
    
    await state.clear()

@events_router.message(F.text == "Удалить ивент")
@events_router.message(Command('delete_event'))
async def delete_event_command(message: Message, state: FSMContext):
    # Проверяем права админа
    user = await get_user(message.from_user.id)
    if not user or user.status != "admin":
        await message.answer("❌ У вас нет прав для удаления ивентов!")
        return
        
    # Получаем все ивенты
    events = await get_all_events()
        
    if not events:
        await message.answer("📭 Нет доступных ивентов для удаления.")
        return
        
    # Формируем список ивентов
    events_list = "📋 Список ивентов для удаления:\n\n"
    for i, event in enumerate(events, 1):
        events_list += f"{i}. 🆔 {event.id} | {event.name}\n"
        events_list += f"   📅 {event.time.strftime('%d.%m.%Y %H:%M')}\n"
        events_list += f"   🏆 {event.cost} очков\n\n"
        
    events_list += "Введите номер ивента для удаления (или 'отмена' для отмены):"
        
    # Сохраняем список ивентов в состоянии
    await state.update_data(events_for_deletion=events)
    await state.set_state(EventStates.waiting_event_to_delete)
    await message.answer(events_list)

# Обработка выбора ивента
@events_router.message(EventStates.waiting_event_to_delete)
async def process_event_deletion(message: Message, state: FSMContext):
    user_input = message.text.strip().lower()
    
    # Проверяем отмену
    if user_input in ['отмена', 'cancel', 'стоп']:
        await message.answer("❌ Удаление отменено.")
        await state.clear()
        return
    
    try:
        event_number = int(user_input)
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите номер цифрой или 'отмена' для отмены:")
        return
    
    data = await state.get_data()
    events = data.get('events_for_deletion', [])
    
    if not (1 <= event_number <= len(events)):
        await message.answer(f"⚠️ Пожалуйста, введите номер от 1 до {len(events)}:")
        return
    
    # Получаем выбранный ивент
    event_to_delete = events[event_number - 1]
    
    # Создаем клавиатуру для подтверждения
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{event_to_delete.id}"),
        InlineKeyboardButton(text="❌ Нет, отменить", callback_data="cancel_delete")
    )
    
    confirmation_message = (
        f"⚠️ ВНИМАНИЕ: Вы уверены, что хотите удалить этот ивент?\n\n"
        f"🎯 {event_to_delete.name}\n"
        f"📅 Дата: {event_to_delete.time.strftime('%d.%m.%Y %H:%M')}\n"
        f"🏆 Очки: {event_to_delete.cost}\n"
        f"🆔 ID: {event_to_delete.id}\n\n"
        f"Это действие невозможно отменить!"
    )
    
    await message.answer(confirmation_message, reply_markup=keyboard.as_markup())
    await state.clear()

# Обработка подтверждения удаления ивента
@events_router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_event_deletion(callback: CallbackQuery):
    event_id = int(callback.data.split("_")[2])
    
    # Удаляем ивент
    success = await delete_event_by_id(event_id)
    
    if success:
        await callback.answer(f"✅ Ивент ID {event_id} успешно удален!")
    else:
        await callback.message.edit_text(f"❌ Ошибка при удалении ивента ID {event_id}")
        await callback.answer("Произошла ошибка!")

@events_router.callback_query(F.data == "cancel_delete")
async def cancel_event_deletion(callback: CallbackQuery):
    await callback.message.edit_text("❌ Удаление отменено.")
    await callback.answer()