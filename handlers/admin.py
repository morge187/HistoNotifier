import os
from aiogram import Router
from datetime import datetime
from aiogram import F
from keyboards import adminboard
from database.requests import get_user, save_event, get_all_users, get_last_event_id
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import Message, ContentType, InlineKeyboardButton, CallbackQuery
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
        points = int(message.text)
        
        if points <= 0:
            await message.answer("Количество очков должно быть положительным числом. Введите еще раз:")
            return
            
        await state.update_data(points=points)
        await message.answer(
            "✅ Количество очков сохранено!\n\n"
            "Шаг 5/5: Отправьте картинку для события (фото):"
        )
        await state.set_state(CreateEvent.image)
        
    except ValueError:
        await message.answer("Пожалуйста, введите число (например: 10, 50, 100):")

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
        keyboard.add(InlineKeyboardButton(
            text="🎯 Участвовать", 
            callback_data=f"participate_{event_id}"
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