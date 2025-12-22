from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import Message, ContentType, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
import re

from database.requests import get_user, get_all_events, get_event_by_id, update_event

admin_edit_router = Router()

class EditEventStates(StatesGroup):
    waiting_event_id = State()
    waiting_fields_to_edit = State()
    waiting_name = State()
    waiting_description = State()
    waiting_datetime = State()
    waiting_points = State()
    waiting_image = State()

# Команда для редактирования события
@admin_edit_router.message(F.text == "Редактировать ивент")
@admin_edit_router.message(Command("edit_event"))
async def edit_event_start(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user or user.status != 'admin':
        await message.answer("❌ Отказано в правах доступа")
        return
    
    events = await get_all_events()
    
    if not events:
        await message.answer("📭 Нет доступных событий для редактирования.")
        return
    
    response = "📋 Список всех событий:\n\n"
    for event in events:
        status = "✅ Будущее" if event.time >= datetime.now() else "❌ Прошедшее"
        response += f"🆔 ID: {event.id}\n"
        response += f"📌 Название: {event.name}\n"
        response += f"📅 Дата: {event.time.strftime('%d.%m.%Y %H:%M')}\n"
        response += f"📊 Статус: {status}\n"
        response += "─" * 30 + "\n"
    
    response += "\nВведите ID события для редактирования:"
    await message.answer(response)
    await state.set_state(EditEventStates.waiting_event_id)

# Обработка выбора ID события
@admin_edit_router.message(EditEventStates.waiting_event_id)
async def process_event_id(message: Message, state: FSMContext):
    try:
        event_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Пожалуйста, введите числовой ID события:")
        return
    
    event = await get_event_by_id(event_id)
    if not event:
        await message.answer("❌ Событие с таким ID не найдено. Попробуйте еще раз:")
        return
    
    # Сохраняем выбранное событие в состоянии
    await state.update_data(event_id=event_id, current_event=event)
    
    # Показываем карточку события и варианты редактирования
    event_card = (
        f"🎯 Текущие данные события:\n\n"
        f"1. 📌 Название: {event.name}\n"
        f"2. 📝 Описание: {event.discription}\n"
        f"3. 📅 Дата и время: {event.time.strftime('%d.%m.%Y %H:%M')}\n"
        f"4. 🏆 Очки за посещение: {event.cost}\n"
        f"5. 🖼️ Картинка: {'Есть' if event.photo_id else 'Нет'}\n\n"
    )
    
    options_text = (
        "Что хотите отредактировать?\n"
        "Введите номера полей через запятую (например: 1,3,5):\n\n"
        "1 - Название\n"
        "2 - Описание\n"
        "3 - Дата и время\n"
        "4 - Количество очков\n"
        "5 - Картинка\n\n"
        "❕ Можно выбрать несколько полей"
    )
    
    await message.answer_photo(
        photo=event.photo_id,
        caption=event_card + options_text
    )
    await state.set_state(EditEventStates.waiting_fields_to_edit)

# Обработка выбора полей для редактирования
@admin_edit_router.message(EditEventStates.waiting_fields_to_edit)
async def process_fields_to_edit(message: Message, state: FSMContext):
    fields_input = message.text.strip()
    
    # Проверяем формат ввода
    if not re.match(r'^[1-5](,\s*[1-5])*$', fields_input):
        await message.answer(
            "❌ Неверный формат.\n"
            "Введите номера от 1 до 5 через запятую (например: 1,3,5):"
        )
        return
    
    # Получаем список полей
    field_numbers = [int(num.strip()) for num in fields_input.split(',')]
    field_numbers = list(set(field_numbers))  # Удаляем дубликаты
    
    # Сохраняем выбранные поля в состоянии
    await state.update_data(fields_to_edit=field_numbers)
    
    # Начинаем последовательный запрос данных для каждого поля
    await request_next_field(message, state)

async def request_next_field(message: Message, state: FSMContext):
    data = await state.get_data()
    fields_to_edit = data.get('fields_to_edit', [])
    current_event = data.get('current_event')
    
    if not fields_to_edit:
        # Все поля обработаны
        await finish_editing(message, state)
        return
    
    field_num = fields_to_edit[0]
    
    # Сохраняем текущее поле и убираем его из очереди
    await state.update_data(current_field=field_num, fields_to_edit=fields_to_edit[1:])
    
    # Запрашиваем данные в зависимости от поля
    if field_num == 1:  # Название
        await message.answer(
            f"📌 Введите новое название события:\n"
            f"Текущее: {current_event.name}"
        )
        await state.set_state(EditEventStates.waiting_name)
        
    elif field_num == 2:  # Описание
        await message.answer(
            f"📝 Введите новое описание:\n"
            f"Текущее: {current_event.discription}"
        )
        await state.set_state(EditEventStates.waiting_description)
        
    elif field_num == 3:  # Дата и время
        await message.answer(
            f"📅 Введите новую дату и время:\n"
            f"Текущее: {current_event.time.strftime('%d.%m.%Y %H:%M')}\n"
            f"Формат: ДД.ММ.ГГГГ ЧЧ:ММ (например: 25.12.2024 18:30)"
        )
        await state.set_state(EditEventStates.waiting_datetime)
        
    elif field_num == 4:  # Очки
        await message.answer(
            f"🏆 Введите новое количество очков:\n"
            f"Текущее: {current_event.cost}"
        )
        await state.set_state(EditEventStates.waiting_points)
        
    elif field_num == 5:  # Картинка
        await message.answer(
            f"🖼️ Отправьте новую картинку для события:\n"
            f"Текущая картинка ниже 👇"
        )
        await message.answer_photo(
            photo=current_event.photo_id,
            caption="Текущая картинка события"
        )
        await state.set_state(EditEventStates.waiting_image)

# Обработка нового названия
@admin_edit_router.message(EditEventStates.waiting_name)
async def process_new_name(message: Message, state: FSMContext):
    new_name = message.text.strip()
    
    if len(new_name) < 3:
        await message.answer("❌ Название слишком короткое. Минимум 3 символа. Попробуйте еще раз:")
        return
    
    await state.update_data(new_name=new_name)
    await message.answer(f"✅ Новое название сохранено: {new_name}")
    await request_next_field(message, state)

# Обработка нового описания
@admin_edit_router.message(EditEventStates.waiting_description)
async def process_new_description(message: Message, state: FSMContext):
    new_description = message.text.strip()
    
    if len(new_description) < 5:
        await message.answer("❌ Описание слишком короткое. Минимум 5 символов. Попробуйте еще раз:")
        return
    
    await state.update_data(new_description=new_description)
    await message.answer(f"✅ Новое описание сохранено")
    await request_next_field(message, state)

# Обработка новой даты
@admin_edit_router.message(EditEventStates.waiting_datetime)
async def process_new_datetime(message: Message, state: FSMContext):
    try:
        new_datetime = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
        await state.update_data(new_datetime=new_datetime)
        await message.answer(f"✅ Новая дата сохранена: {new_datetime.strftime('%d.%m.%Y %H:%M')}")
        await request_next_field(message, state)
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат даты!\n"
            "Пожалуйста, введите в формате: ДД.ММ.ГГГГ ЧЧ:ММ\n"
            "Пример: 25.12.2024 18:30"
        )

# Обработка новых очков
@admin_edit_router.message(EditEventStates.waiting_points)
async def process_new_points(message: Message, state: FSMContext):
    try:
        new_points = int(message.text.strip())
        
        if new_points <= 0:
            await message.answer("❌ Количество очков должно быть положительным числом. Попробуйте еще раз:")
            return
        
        await state.update_data(new_points=new_points)
        await message.answer(f"✅ Новое количество очков сохранено: {new_points}")
        await request_next_field(message, state)
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число (например: 10, 50, 100):")

# Обработка новой картинки
@admin_edit_router.message(EditEventStates.waiting_image, F.content_type == ContentType.PHOTO)
async def process_new_image(message: Message, state: FSMContext):
    photo = message.photo[-1]
    new_image_file_id = photo.file_id
    
    await state.update_data(new_image_file_id=new_image_file_id)
    await message.answer("✅ Новая картинка сохранена")
    await request_next_field(message, state)

# Если отправлено не фото
@admin_edit_router.message(EditEventStates.waiting_image)
async def wrong_image_format(message: Message, state: FSMContext):
    await message.answer("❌ Пожалуйста, отправьте именно фото (картинку):")

# Завершение редактирования и сохранение
async def finish_editing(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get('event_id')
    
    # Формируем словарь с обновлениями
    update_data = {}
    
    if 'new_name' in data:
        update_data['name'] = data['new_name']
    if 'new_description' in data:
        update_data['description'] = data['new_description']
    if 'new_datetime' in data:
        update_data['datetime'] = data['new_datetime']
    if 'new_points' in data:
        update_data['points'] = data['new_points']
    if 'new_image_file_id' in data:
        update_data['image_file_id'] = data['new_image_file_id']
    
    # Обновляем событие в базе
    success = await update_event(event_id, update_data)
    
    if success:
        # Получаем обновленное событие
        updated_event = await get_event_by_id(event_id)
        
        # Формируем новую карточку
        new_card = (
            f"🎉 Событие успешно обновлено!\n\n"
            f"🆔 ID: {updated_event.id}\n"
            f"📌 Название: {updated_event.name}\n"
            f"📝 Описание: {updated_event.discription}\n"
            f"📅 Дата и время: {updated_event.time.strftime('%d.%m.%Y %H:%M')}\n"
            f"🏆 Очков за посещение: {updated_event.cost}\n"
            f"🖼️ Картинка: обновлена\n\n"
            f"✅ Все изменения сохранены!"
        )
        
        await message.answer_photo(
            photo=updated_event.photo_id,
            caption=new_card
        )
        
        # Предлагаем дальнейшие действия
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(
            text="✏️ Редактировать другое событие",
            callback_data="edit_another_event"
        ))
        
        await message.answer(
            "Что дальше?",
            reply_markup=keyboard.as_markup()
        )
        
    else:
        await message.answer("❌ Произошла ошибка при обновлении события")
    
    await state.clear()

# Обработка кнопок после редактирования
@admin_edit_router.callback_query(F.data == "edit_another_event")
async def edit_another_event(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await edit_event_start(callback.message, state)

@admin_edit_router.callback_query(F.data == "back_to_events_list")
async def back_to_events_list(callback: CallbackQuery):
    await callback.answer()
    # Можно вызвать команду просмотра событий
    await callback.message.answer("Используйте /list_event для просмотра событий")

# Кнопка отмены редактирования
@admin_edit_router.message(Command("cancel_edit"))
async def cancel_edit(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer("❌ Редактирование отменено")
    else:
        await message.answer("Нет активного процесса редактирования")