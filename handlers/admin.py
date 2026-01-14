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

from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.requests import (
    get_all_tanks, get_tanks_by_nation, get_tank_by_id,
    create_tank, update_tank, delete_tank, get_all_nations,
    is_admin, get_tanks_by_year_and_type, get_all_years,
    get_tanks_by_year, get_tank_types_by_year,
    get_tank_years, update_tank_years, delete_tank_years
)

# Определяем состояния для FSM
class TankStates(StatesGroup):
    # Состояния для списка танков
    waiting_nation_choice = State()
    waiting_tank_type_choice = State()
    waiting_tank_number = State()
    
    # Состояния для добавления танка
    waiting_tank_name = State()
    waiting_tank_nation = State()
    waiting_tank_type = State()
    waiting_tank_description = State()
    waiting_tank_image = State()
    waiting_tank_years = State()
    
    # Состояния для изменения танка
    waiting_tank_to_edit = State()
    waiting_edit_choice = State()
    waiting_new_name = State()
    waiting_new_nation = State()
    waiting_new_type = State()
    waiting_new_description = State()
    waiting_new_image = State()
    waiting_new_years = State()

    waiting_year_choice = State()
    waiting_year_view_type = State()
    waiting_year_tank_type = State()
    waiting_year_tank_number = State()
    
    # Состояния для удаления танка
    waiting_tank_to_delete = State()
    waiting_delete_confirmation = State()

    nothing = State()

# Список танков
@admin.message(F.text == 'Список танков')
@admin.message(Command('tanks'))
async def show_tanks_menu(message: Message, state: FSMContext):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="🎌 По нациям", callback_data="tanks_by_nation"),
        InlineKeyboardButton(text="📅 По годам", callback_data="tanks_by_year")
    )
    keyboard.adjust(1)
    
    await message.answer(
        "🎖️ <b>Список танков</b>\n\n"
        "Выберите способ просмотра:",
        parse_mode="HTML",
        reply_markup=keyboard.as_markup()
    )


@admin.callback_query(F.data == "tanks")
async def show_tanks_menu2(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="🎌 По нациям", callback_data="tanks_by_nation"),
        InlineKeyboardButton(text="📅 По годам", callback_data="tanks_by_year")
    )
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        "🎖️ <b>Список танков</b>\n\n"
        "Выберите способ просмотра:",
        parse_mode="HTML",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()


# Список танков по нациям
@admin.callback_query(F.data == "tanks_by_nation")
async def tanks_by_nation_menu(callback: CallbackQuery, state: FSMContext):
    nations = await get_all_nations()
    
    if not nations:
        await callback.message.answer("🚫 В базе данных нет танков.")
        await callback.answer()
        return
    
    keyboard = InlineKeyboardBuilder()
    for nation in nations:
        keyboard.add(
            InlineKeyboardButton(text=f"🇺🇳 {nation}", callback_data=f"nation_{nation}")
        )
    keyboard.adjust(2)
    keyboard.add(
        InlineKeyboardButton(text="Назад", callback_data="tanks")
    )
    
    await callback.message.edit_text(
        "🎌 <b>Выберите нацию:</b>",
        parse_mode="HTML",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()


# Обработка выбора нации
@admin.callback_query(F.data.startswith("nation_"))
async def process_nation_choice(callback: CallbackQuery, state: FSMContext):
    nation = callback.data.split("_", 1)[1]
    
    tanks = await get_tanks_by_nation(nation)
    
    if not tanks:
        await callback.answer(f"🚫 Нет танков нации {nation}")
        return
    
    tank_types = list(set(tank.tank_type for tank in tanks if tank.tank_type))
    
    if not tank_types:
        await state.update_data(
            selected_nation=nation,
            tanks=tanks,
            selected_tank_type=None
        )
        await show_tanks_list(callback.message, tanks, nation, "tanks_by_nation")
    else:
        keyboard = InlineKeyboardBuilder()
        for tank_type in sorted(tank_types):
            keyboard.add(
                InlineKeyboardButton(
                    text=f"🔰 {tank_type}", 
                    callback_data=f"type_{nation}_{tank_type}"
                )
            )
        keyboard.adjust(2)
        
        keyboard.row(
            InlineKeyboardButton(
                text="📋 Все типы", 
                callback_data=f"type_{nation}_all"
            )
        )
        keyboard.add(
            InlineKeyboardButton(text="Назад", callback_data="tanks_by_nation")
        )   
        
        await callback.message.edit_text(
            f"🇺🇳 <b>{nation}</b>\n\n"
            "🔰 <b>Выберите класс танка:</b>",
            parse_mode="HTML",
            reply_markup=keyboard.as_markup()
        )
    
    await callback.answer()


# Обработка выбора типа танка
@admin.callback_query(F.data.startswith("type_"))
async def process_tank_type_choice(callback: CallbackQuery, state: FSMContext):
    _, nation, tank_type = callback.data.split("_", 2)
    
    all_tanks = await get_tanks_by_nation(nation)
    
    if tank_type != "all":
        filtered_tanks = [tank for tank in all_tanks if tank.tank_type == tank_type]
        type_label = tank_type
    else:
        filtered_tanks = all_tanks
        type_label = "всех типов"
    
    if not filtered_tanks:
        await callback.answer(f"🚫 Нет танков типа {tank_type}")
        return
    
    await state.update_data(
        selected_nation=nation,
        selected_tank_type=tank_type if tank_type != "all" else None,
        tanks=filtered_tanks,
        current_page=0
    )
    
    await show_tanks_list(callback.message, filtered_tanks, nation, "tanks_by_nation", type_label)
    await callback.answer()


async def show_tanks_list(message: Message, tanks, nation, back_callback="tanks", type_label=""):
    response = f"🎖️ <b>Танки {nation}</b>"
    if type_label:
        response += f" ({type_label})"
    response += f"\n\n📊 Всего: {len(tanks)}\n\n"
    
    for i, tank in enumerate(tanks, 1):
        response += f"{i}. <b>{tank.name}</b>\n"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(
            text="🔍 Подробнее о танке", 
            callback_data="show_tank_details"
        )
    )
    keyboard.add(
        InlineKeyboardButton(
            text="Назад", 
            callback_data=back_callback
        )
    )
    
    await message.edit_text(
        response,
        parse_mode="HTML",
        reply_markup=keyboard.as_markup()
    )


# Обработка кнопки "Подробнее"
@admin.callback_query(F.data == "show_tank_details")
async def ask_for_tank_number(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tanks = data.get('tanks', [])
    
    if not tanks:
        await callback.answer("🚫 Список танков пуст")
        return
    
    max_number = len(tanks)
    
    await callback.message.answer(
        f"🔢 <b>Введите номер танка (от 1 до {max_number}):</b>",
        parse_mode="HTML"
    )
    
    await state.set_state(TankStates.waiting_tank_number)
    await callback.answer()


# Обработка ввода номера танка
@admin.message(TankStates.waiting_tank_number)
async def process_tank_number(message: Message, state: FSMContext):
    try:
        tank_number = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите номер цифрой:")
        return
    
    data = await state.get_data()
    tanks = data.get('tanks', [])
    max_number = len(tanks)
    
    if not (1 <= tank_number <= max_number):
        await message.answer(f"⚠️ Пожалуйста, введите номер от 1 до {max_number}:")
        return
    
    selected_tank = tanks[tank_number - 1]
    years = await get_tank_years(selected_tank.id)
    years_str = ", ".join(map(str, years)) if years else "Не указаны"
    
    tank_card = (
        f"🎖️ <b>{selected_tank.name}</b>\n\n"
        f"🇺🇳 <b>Нация:</b> {selected_tank.nation}\n"
        f"🔰 <b>Тип:</b> {selected_tank.tank_type or 'Не указан'}\n"
        f"📅 <b>Годы:</b> {years_str}\n"
        f"🆔 <b>ID:</b> {selected_tank.id}\n\n"
    )
    
    await message.answer_photo(
        photo=selected_tank.photo_id,
        caption=tank_card,
        parse_mode="HTML"
    )
    await message.answer(
        f"📝 <b>Описание:</b>\n{selected_tank.discript}\n\n",
        parse_mode='HTML'
    )
    
    await state.clear()


# Список танков по годам
@admin.callback_query(F.data == "tanks_by_year")
async def tanks_by_year_menu(callback: CallbackQuery, state: FSMContext):
    years = await get_all_years()
    
    if not years:
        await callback.message.edit_text("🚫 В базе данных нет танков.")
        await callback.answer()
        return
    
    keyboard = InlineKeyboardBuilder()
    for year in sorted(years, reverse=True):
        keyboard.add(
            InlineKeyboardButton(text=f"📅 {year}", callback_data=f"year_{year}")
        )
    keyboard.adjust(3)
    keyboard.add(
        InlineKeyboardButton(text="Назад", callback_data="tanks")
    )
    
    await callback.message.edit_text(
        "📅 <b>Выберите год создания:</b>",
        parse_mode="HTML",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()


# Обработка выбора года
@admin.callback_query(F.data.startswith("year_"))
async def process_year_choice(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    
    if len(parts) < 2:
        await callback.answer("❌ Ошибка формата данных")
        return
    
    try:
        year = int(parts[1])
    except ValueError:
        await callback.answer("❌ Некорректный формат года")
        return
    
    await state.update_data(selected_year=year)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="📋 Все", callback_data=f"yearview_{year}_all"),
        InlineKeyboardButton(text="🔰 По классам", callback_data=f"yearview_{year}")
    )
    keyboard.adjust(1)
    keyboard.add(
        InlineKeyboardButton(text="Назад", callback_data="tanks_by_year")
    )
    
    await callback.message.edit_text(
        f"📅 <b>Танки {year} года</b>\n\n"
        "Выберите способ просмотра:",
        parse_mode="HTML",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()


# Обработка выбора типа просмотра для года
@admin.callback_query(F.data.startswith("yearview_"))
async def process_year_view_choice(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    
    try:
        year = int(parts[-1])
        
        tank_types = await get_tank_types_by_year(year)
        
        if not tank_types:
            await callback.answer(f"🚫 Нет типов танков для {year} года")
            return
        
        keyboard = InlineKeyboardBuilder()
        for tank_type in sorted(tank_types):
            keyboard.add(
                InlineKeyboardButton(
                    text=f"🔰 {tank_type}", 
                    callback_data=f"yeartype_{year}_{tank_type}"
                )
            )
        keyboard.adjust(2)
        keyboard.add(
            InlineKeyboardButton(text="Назад", callback_data=f"year_{year}")
        )
        
        await callback.message.edit_text(
            f"📅 <b>Танки {year} года</b>\n\n"
            "🔰 <b>Выберите класс танка:</b>",
            parse_mode="HTML",
            reply_markup=keyboard.as_markup()
        )
            
    except Exception:
        year = parts[-2]
        tanks = await get_tanks_by_year(year)
        
        if not tanks:
            await callback.answer(f"🚫 Нет танков {year} года")
            return
        
        response = f"📅 <b>Танки {year} года</b>\n\n"
        response += f"📊 Всего: {len(tanks)}\n\n"
        
        for i, tank in enumerate(tanks, 1):
            tank_years = await get_tank_years(tank.id)
            years_str = f" ({', '.join(map(str, tank_years))})" if tank_years else ""
            response += f"{i}. ID: {tank.id} | <b>{tank.name}</b> ({tank.nation}){years_str}\n"
        
        await state.update_data(
            selected_year=year,
            tanks=tanks,
            view_type="all",
            current_page=0
        )
        
        keyboard = InlineKeyboardBuilder()
        keyboard.add(
            InlineKeyboardButton(text="🔍 Подробнее", callback_data="show_tank_details_year")
        )
        keyboard.add(
            InlineKeyboardButton(text="Назад", callback_data=f"year_{year}")
        )
        
        await callback.message.edit_text(
            response,
            parse_mode="HTML",
            reply_markup=keyboard.as_markup()
        )
    
    await callback.answer()


# Обработка выбора типа танка для года
@admin.callback_query(F.data.startswith("yeartype_"))
async def process_year_tank_type_choice(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_", 2)
    
    if len(parts) < 3:
        await callback.answer("❌ Ошибка формата данных")
        return
    
    _, year_str, tank_type = parts
    
    try:
        year = int(year_str)
    except ValueError:
        await callback.answer("❌ Некорректный формат года")
        return
    
    tanks = await get_tanks_by_year_and_type(year, tank_type)
    
    if not tanks:
        await callback.answer(f"🚫 Нет танков типа {tank_type} для {year} года")
        return
    
    response = f"📅 <b>Танки {year} года</b>\n🔰 <b>Класс: {tank_type}</b>\n\n"
    response += f"📊 Всего: {len(tanks)}\n\n"
    
    for i, tank in enumerate(tanks, 1):
        tank_years = await get_tank_years(tank.id)
        years_str = f" ({', '.join(map(str, tank_years))})" if tank_years else ""
        response += f"{i}. ID: {tank.id} | <b>{tank.name}</b> ({tank.nation}){years_str}\n"
    
    await state.update_data(
        selected_year=year,
        selected_tank_type=tank_type,
        tanks=tanks,
        view_type="by_type",
        current_page=0
    )
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="🔍 Подробнее", callback_data="show_tank_details_year")
    )
    keyboard.add(
        InlineKeyboardButton(text="Назад", callback_data=f"yearview_{year}")
    )
    
    await callback.message.edit_text(
        response,
        parse_mode="HTML",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()


# Обработка кнопки "Подробнее" для поиска по годам
@admin.callback_query(F.data == "show_tank_details_year")
async def ask_for_tank_number_year(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tanks = data.get('tanks', [])
    
    if not tanks:
        await callback.answer("🚫 Список танков пуст")
        return
    
    max_number = len(tanks)
    
    await callback.message.answer(
        f"🔢 <b>Введите номер танка (от 1 до {max_number}):</b>",
        parse_mode="HTML"
    )
    
    await state.set_state(TankStates.waiting_tank_number)
    await callback.answer()


# Добавить танк
@admin.message(F.text == "Добавить танк")
@admin.message(Command('add_tank'))
async def start_add_tank(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для добавления танков!")
        return
    
    await message.answer(
        "🎖️ <b>Добавление нового танка</b>\n\n"
        "📝 Шаг 1/6: Введите название танка:\n"
        "<i>Пример: Т-34, Тигр I, Шерман M4</i>",
        parse_mode="HTML"
    )
    await state.set_state(TankStates.waiting_tank_name)


@admin.message(TankStates.waiting_tank_name)
async def process_tank_name(message: Message, state: FSMContext):
    if message.text == "отмена":
        await state.clear()
        return
    await state.update_data(name=message.text.strip())
    
    await message.answer(
        "✅ Название сохранено!\n\n"
        "🌍 Шаг 2/6: Введите нацию танка:\n"
        "<i>Пример: СССР, Германия, США, Великобритания</i>",
        parse_mode="HTML"
    )
    await state.set_state(TankStates.waiting_tank_nation)


@admin.message(TankStates.waiting_tank_nation)
async def process_tank_nation(message: Message, state: FSMContext):
    if message.text == "отмена":
        await state.clear()
        return
    await state.update_data(nation=message.text.strip())
    
    await message.answer(
        "✅ Нация сохранена!\n\n"
        "🔰 Шаг 3/6: Введите тип/класс танка:\n"
        "<i>Пример: Средний танк, Тяжелый танк, ПТ-САУ, САУ</i>",
        parse_mode="HTML"
    )
    await state.set_state(TankStates.waiting_tank_type)


@admin.message(TankStates.waiting_tank_type)
async def process_tank_type(message: Message, state: FSMContext):
    if message.text == "отмена":
        await state.clear()
        return
    await state.update_data(tank_type=message.text.strip())
    
    await message.answer(
        "✅ Тип сохранен!\n\n"
        "📅 Шаг 4/6: Введите годы создания танка через запятую:\n"
        "<i>Пример: 1939, 1940, 1941</i>\n"
        "<i>Или один год: 1942</i>",
        parse_mode="HTML"
    )
    await state.set_state(TankStates.waiting_tank_years)


@admin.message(TankStates.waiting_tank_years)
async def process_tank_years(message: Message, state: FSMContext):
    if message.text == "отмена":
        await state.clear()
        return
    years_input = message.text.strip()
    
    try:
        years_list = [y.strip() for y in years_input.split(',')]
        valid_years = []
        
        for year_str in years_list:
            if not year_str:
                continue
            year = int(year_str)
            if 1900 <= year <= datetime.now().year:
                valid_years.append(year)
            else:
                await message.answer(
                    f"⚠️ Год {year} некорректен. Годы должны быть от 1900 до {datetime.now().year}.\n"
                    "Пожалуйста, введите годы через запятую еще раз:"
                )
                return
        
        if not valid_years:
            await message.answer("⚠️ Не указано ни одного корректного года. Введите годы через запятую:")
            return
        
        valid_years = sorted(list(set(valid_years)))
        
        await state.update_data(years=valid_years)
        
        await message.answer(
            f"✅ Годы сохранены: {', '.join(map(str, valid_years))}\n\n"
            "📄 Шаг 5/6: Введите описание танка:",
            parse_mode="HTML"
        )
        await state.set_state(TankStates.waiting_tank_description)
        
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите годы цифрами через запятую (например: 1939, 1940, 1941):")
        return


@admin.message(TankStates.waiting_tank_description)
async def process_tank_description(message: Message, state: FSMContext):
    if message.text == "отмена":
        await state.clear()
        return
    await state.update_data(discript=message.text.strip())
    
    await message.answer(
        "✅ Описание сохранено!\n\n"
        "🖼️ Шаг 6/6: Отправьте фотографию танка:",
        parse_mode="HTML"
    )
    await state.set_state(TankStates.waiting_tank_image)


@admin.message(TankStates.waiting_tank_image, F.photo)
async def process_tank_image(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    
    success = await create_tank(
        name=data['name'],
        nation=data['nation'],
        discript=data['discript'],
        photo_id=photo_id,
        tank_type=data["tank_type"],
        years=data["years"]
    )
    
    if success:
        await message.answer_photo(
            photo=photo_id,
            caption=(
                "✅ <b>Танк успешно добавлен!</b>\n\n"
                f"🎖️ <b>Название:</b> {data['name']}\n"
                f"🇺🇳 <b>Нация:</b> {data['nation']}\n"
                f"🔰 <b>Тип:</b> {data.get('tank_type', 'Не указан')}\n"
                f"📅 <b>Годы:</b> {', '.join(map(str, data['years']))}\n"
                f"📝 <b>Описание:</b>\n{data['discript']}"
            ),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ <b>Не удалось добавить танк.</b>\n"
            "Попробуйте снова или обратитесь к администратору.",
            parse_mode="HTML"
        )
    
    await state.clear()


@admin.message(TankStates.waiting_tank_image)
async def process_tank_image_invalid(message: Message):
    await message.answer("⚠️ Пожалуйста, отправьте фотографию танка:")


# Добавить танк
@admin.message(F.text == "Добавить танк")
@admin.message(Command('add_tank'))
async def start_add_tank(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для добавления танков!")
        return
    
    await message.answer(
        "🎖️ <b>Добавление нового танка</b>\n\n"
        "📝 Шаг 1/6: Введите название танка:\n"
        "<i>Пример: Т-34, Тигр I, Шерман M4</i>",
        parse_mode="HTML"
    )
    await state.set_state(TankStates.waiting_tank_name)

@admin.message(TankStates.waiting_tank_name)
async def process_tank_name(message: Message, state: FSMContext):
    if message.text == "отмена":
        await state.set_state(TankStates.nothing)
        return
    await state.update_data(name=message.text.strip())
    
    await message.answer(
        "✅ Название сохранено!\n\n"
        "🌍 Шаг 2/6: Введите нацию танка:\n"
        "<i>Пример: СССР, Германия, США, Великобритания</i>",
        parse_mode="HTML"
    )
    await state.set_state(TankStates.waiting_tank_nation)

@admin.message(TankStates.waiting_tank_nation)
async def process_tank_nation(message: Message, state: FSMContext):
    if message.text == "отмена":
        await state.set_state(TankStates.nothing)
        return
    await state.update_data(nation=message.text.strip())
    
    await message.answer(
        "✅ Нация сохранена!\n\n"
        "🔰 Шаг 3/6: Введите тип/класс танка:\n"
        "<i>Пример: Средний танк, Тяжелый танк, ПТ-САУ, САУ</i>",
        parse_mode="HTML"
    )
    await state.set_state(TankStates.waiting_tank_type)

@admin.message(TankStates.waiting_tank_type)
async def process_tank_type(message: Message, state: FSMContext):
    if message.text == "отмена":
        await state.set_state(TankStates.nothing)
        return
    await state.update_data(tank_type=message.text.strip())
    
    await message.answer(
        "✅ Тип сохранен!\n\n"
        "📅 Шаг 4/6: Введите годы создания танка через запятую:\n"
        "<i>Пример: 1939, 1940, 1941</i>\n"
        "<i>Или один год: 1942</i>",
        parse_mode="HTML"
    )
    await state.set_state(TankStates.waiting_tank_years)

@admin.message(TankStates.waiting_tank_years)
async def process_tank_years(message: Message, state: FSMContext):
    if message.text == "отмена":
        await state.set_state(TankStates.nothing)
        return
    years_input = message.text.strip()
    
    # Проверяем и парсим годы
    try:
        years_list = [y.strip() for y in years_input.split(',')]
        valid_years = []
        
        for year_str in years_list:
            if not year_str:
                continue
            year = int(year_str)
            if 1900 <= year <= datetime.now().year:
                valid_years.append(year)
            else:
                await message.answer(
                    f"⚠️ Год {year} некорректен. Годы должны быть от 1900 до {datetime.now().year}.\n"
                    "Пожалуйста, введите годы через запятую еще раз:"
                )
                return
        
        if not valid_years:
            await message.answer("⚠️ Не указано ни одного корректного года. Введите годы через запятую:")
            return
        
        # Убираем дубликаты и сортируем
        valid_years = sorted(list(set(valid_years)))
        
        await state.update_data(years=valid_years)
        
        await message.answer(
            f"✅ Годы сохранены: {', '.join(map(str, valid_years))}\n\n"
            "📄 Шаг 5/6: Введите описание танка:",
            parse_mode="HTML"
        )
        await state.set_state(TankStates.waiting_tank_description)
        
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите годы цифрами через запятую (например: 1939, 1940, 1941):")
        return

@admin.message(TankStates.waiting_tank_description)
async def process_tank_description(message: Message, state: FSMContext):
    if message.text == "отмена":
        await state.set_state(TankStates.nothing)
        return
    await state.update_data(discript=message.text.strip())
    
    await message.answer(
        "✅ Описание сохранено!\n\n"
        "🖼️ Шаг 6/6: Отправьте фотографию танка:",
        parse_mode="HTML"
    )
    await state.set_state(TankStates.waiting_tank_image)

@admin.message(TankStates.waiting_tank_image, F.photo)
async def process_tank_image(message: Message, state: FSMContext):
    if message.text == "отмена":
        await state.set_state(TankStates.nothing)
        return
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    
    success = await create_tank(
        name=data['name'],
        nation=data['nation'],
        discript=data['discript'],
        photo_id=photo_id,
        tank_type=data["tank_type"],
        years=data["years"]  # Теперь это список
    )
    
    if success:
        await message.answer_photo(
            photo=photo_id,
            caption=(
                "✅ <b>Танк успешно добавлен!</b>\n\n"
                f"🎖️ <b>Название:</b> {data['name']}\n"
                f"🇺🇳 <b>Нация:</b> {data['nation']}\n"
                f"🔰 <b>Тип:</b> {data.get('tank_type', 'Не указан')}\n"
                f"📅 <b>Годы:</b> {', '.join(map(str, data['years']))}\n"
                f"📝 <b>Описание:</b>\n{data['discript']}"
            ),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ <b>Не удалось добавить танк.</b>\n"
            "Попробуйте снова или обратитесь к администратору.",
            parse_mode="HTML"
        )
    
    await state.clear()

@admin.message(TankStates.waiting_tank_image)
async def process_tank_image_invalid(message: Message):
    await message.answer("⚠️ Пожалуйста, отправьте фотографию танка:")


@admin.message(F.text == "Изменить танк")
@admin.message(Command('edit_tank'))
async def start_edit_tank(message: Message, state: FSMContext):
    if message.text == "отмена":
        await state.set_state("nothing")
        return
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для изменения танков!")
        return
    
    tanks = await get_all_tanks()
    
    if not tanks:
        await message.answer("🚫 В базе данных нет танков для изменения.")
        return
    
    tanks_list = "🎖️ <b>Список танков для изменения:</b>\n\n"
    for i, tank in enumerate(tanks, 1):
        # Получаем годы танка
        years = await get_tank_years(tank.id)
        years_str = ", ".join(map(str, years)) if years else "Нет годов"
        
        tanks_list += f"{i}. ID: {tank.id} | {tank.name} ({tank.nation}, годы: {years_str})\n"
    
    tanks_list += "\n\n🔢 <b>Введите ID танка для изменения:</b>"
    
    await state.update_data(all_tanks=tanks)
    await state.set_state(TankStates.waiting_tank_to_edit)
    
    await message.answer(tanks_list, parse_mode="HTML")

@admin.message(TankStates.waiting_tank_to_edit)
async def process_tank_to_edit(message: Message, state: FSMContext):
    if (message.text == "отмена" or message.text == '/canel'):
        await state.clear()
        await message.answer("Отмена сработала")
    try:
        tank_id = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите ID танка цифрой:")
        return
    
    data = await state.get_data()
    tanks = data.get('all_tanks', [])
    
    selected_tank = None
    for tank in tanks:
        if tank.id == tank_id:
            selected_tank = tank
            break
    
    if not selected_tank:
        await message.answer("🚫 Танк с таким ID не найден. Попробуйте снова:")
        return
    
    # Получаем годы танка
    years = await get_tank_years(selected_tank.id)
    years_str = ", ".join(map(str, years)) if years else "Нет годов"
    
    await state.update_data(selected_tank=selected_tank, current_years=years)
    
    edit_menu = (
        f"🎖️ <b>Редактирование танка:</b>\n"
        f"ID: {selected_tank.id} | {selected_tank.name}\n\n"
        "📋 <b>Что вы хотите изменить?</b>\n"
        "1. 🎖️ Название\n"
        "2. 🇺🇳 Нация\n"
        "3. 🔰 Тип\n"
        "4. 📅 Годы (через запятую)\n"
        "5. 📝 Описание\n"
        "6. 🖼️ Фотография\n\n"
        "🔢 <b>Введите номера через запятую:</b>"
    )
    
    await message.answer(edit_menu, parse_mode="HTML")
    await state.set_state(TankStates.waiting_edit_choice)

@admin.message(TankStates.waiting_edit_choice)
async def process_edit_choice(message: Message, state: FSMContext):
    try:
        choices = [int(choice.strip()) for choice in message.text.strip().split(',')]
        valid_choices = [1, 2, 3, 4, 5, 6]
        invalid_choices = [c for c in choices if c not in valid_choices]
        
        if invalid_choices:
            await message.answer(f"⚠️ Неверные номера: {invalid_choices}. Введите номера от 1 до 6:")
            return
        
    except ValueError:
        await message.answer("⚠️ Неверный формат. Введите номера через запятую:")
        return
    
    data = await state.get_data()
    selected_tank = data.get('selected_tank')
    current_years = data.get('current_years', [])
    
    await state.update_data(edit_choices=choices)
    
    if 1 in choices:
        await message.answer(
            f"✏️ <b>Текущее название:</b> {selected_tank.name}\n"
            "Введите новое название танка:",
            parse_mode="HTML"
        )
        await state.set_state(TankStates.waiting_new_name)
    elif 2 in choices:
        await message.answer(
            f"🌍 <b>Текущая нация:</b> {selected_tank.nation}\n"
            "Введите новую нацию танка:",
            parse_mode="HTML"
        )
        await state.set_state(TankStates.waiting_new_nation)
    elif 3 in choices:
        await message.answer(
            f"🔰 <b>Текущий тип:</b> {selected_tank.tank_type or 'Не указан'}\n"
            "Введите новый тип танка:",
            parse_mode="HTML"
        )
        await state.set_state(TankStates.waiting_new_type)
    elif 4 in choices:
        years_str = ", ".join(map(str, current_years)) if current_years else "Нет годов"
        await message.answer(
            f"📅 <b>Текущие годы:</b> {years_str}\n"
            "Введите новые годы через запятую:",
            parse_mode="HTML"
        )
        await state.set_state(TankStates.waiting_new_years)
    elif 5 in choices:
        await message.answer(
            f"📝 <b>Текущее описание:</b>\n{selected_tank.discript}\n\n"
            "Введите новое описание танка:",
            parse_mode="HTML"
        )
        await state.set_state(TankStates.waiting_new_description)
    elif 6 in choices:
        await message.answer("🖼️ Отправьте новую фотографию танка:")
        await state.set_state(TankStates.waiting_new_image)

# Обработка изменения названия
@admin.message(TankStates.waiting_new_name)
async def process_new_name(message: Message, state: FSMContext):
    new_name = message.text.strip()
    data = await state.get_data()
    tank = data.get('selected_tank')
    choices = data.get('edit_choices', [])
    
    success = await update_tank(tank.id, name=new_name)
    
    if success:
        await process_remaining_edits(message, state, choices, 1, "✅ Название танка обновлено!")
    else:
        await message.answer("❌ Не удалось обновить название танка.")
        await state.clear()

# Обработка изменения нации
@admin.message(TankStates.waiting_new_nation)
async def process_new_nation(message: Message, state: FSMContext):
    if (message.text == "отмена" or message.text == '/canel'):
        await state.clear()
        await message.answer("Отмена сработала")
    new_nation = message.text.strip()
    data = await state.get_data()
    tank = data.get('selected_tank')
    choices = data.get('edit_choices', [])
    
    success = await update_tank(tank.id, nation=new_nation)
    
    if success:
        await process_remaining_edits(message, state, choices, 2, "✅ Нация танка обновлена!")
    else:
        await message.answer("❌ Не удалось обновить нацию танка.")
        await state.clear()

# Обработка изменения типа
@admin.message(TankStates.waiting_new_type)
async def process_new_type(message: Message, state: FSMContext):
    if message.text == "отмена":
        await state.set_state(TankStates.nothing)
        return
    new_type = message.text.strip()
    data = await state.get_data()
    tank = data.get('selected_tank')
    choices = data.get('edit_choices', [])
    
    success = await update_tank(tank.id, tank_type=new_type)
    
    if success:
        await process_remaining_edits(message, state, choices, 3, "✅ Тип танка обновлен!")
    else:
        await message.answer("❌ Не удалось обновить тип танка.")
        await state.clear()

# Обработка изменения годов
@admin.message(TankStates.waiting_new_years)
async def process_new_years(message: Message, state: FSMContext):
    if message.text == "отмена":
        await state.set_state(TankStates.nothing)
        return
    years_input = message.text.strip()
    data = await state.get_data()
    tank = data.get('selected_tank')
    choices = data.get('edit_choices', [])
    
    try:
        years_list = [y.strip() for y in years_input.split(',')]
        valid_years = []
        
        for year_str in years_list:
            if not year_str:
                continue
            year = int(year_str)
            if 1900 <= year <= datetime.now().year:
                valid_years.append(year)
            else:
                await message.answer(
                    f"⚠️ Год {year} некорректен. Годы должны быть от 1900 до {datetime.now().year}.\n"
                    "Пожалуйста, введите годы через запятую еще раз:"
                )
                return
        
        if not valid_years:
            await message.answer("⚠️ Не указано ни одного корректного года. Введите годы через запятую:")
            return
        
        valid_years = sorted(list(set(valid_years)))
        
        success = await update_tank_years(tank.id, valid_years)
        
        if success:
            await process_remaining_edits(message, state, choices, 4, f"✅ Годы танка обновлены: {', '.join(map(str, valid_years))}")
        else:
            await message.answer("❌ Не удалось обновить годы танка.")
            await state.clear()
            
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите годы цифрами через запятую:")
        return

# Обработка изменения описания
@admin.message(TankStates.waiting_new_description)
async def process_new_description(message: Message, state: FSMContext):
    if message.text == "отмена":
        await state.set_state(TankStates.nothing)
        return
    new_description = message.text.strip()
    data = await state.get_data()
    tank = data.get('selected_tank')
    choices = data.get('edit_choices', [])
    
    success = await update_tank(tank.id, discript=new_description)
    
    if success:
        await process_remaining_edits(message, state, choices, 5, "✅ Описание танка обновлено!")
    else:
        await message.answer("❌ Не удалось обновить описание танка.")
        await state.clear()

# Обработка изменения фотографии
@admin.message(TankStates.waiting_new_image, F.photo)
async def process_new_image(message: Message, state: FSMContext):
    if message.text == "отмена":
        await state.set_state(TankStates.nothing)
        return
        
    new_photo_id = message.photo[-1].file_id
    data = await state.get_data()
    tank = data.get('selected_tank')
    choices = data.get('edit_choices', [])
    
    success = await update_tank(tank.id, photo_id=new_photo_id)
    
    if success:
        await process_remaining_edits(message, state, choices, 6, "✅ Фотография танка обновлена!")
    else:
        await message.answer("❌ Не удалось обновить фотографию танка.")
        await state.clear()

@admin.message(TankStates.waiting_new_image)
async def process_new_image_invalid(message: Message):
    await message.answer("⚠️ Пожалуйста, отправьте фотографию танка:")

async def process_remaining_edits(message: Message, state: FSMContext, choices: list, processed_choice: int, success_message: str):
    remaining_choices = [c for c in choices if c != processed_choice]
    
    if remaining_choices:
        await state.update_data(edit_choices=remaining_choices)
        await process_next_edit_step(message, state, remaining_choices[0])
    else:
        await message.answer(success_message)
        # Показываем обновленный танк
        data = await state.get_data()
        tank = data.get('selected_tank')
        
        if tank:
            updated_tank = await get_tank_by_id(tank.id)
            years = await get_tank_years(tank.id)
            years_str = ", ".join(map(str, years)) if years else "Нет годов"
            
            tank_card = (
                f"✅ <b>Танк успешно обновлен!</b>\n\n"
                f"🎖️ <b>Название:</b> {updated_tank.name}\n"
                f"🇺🇳 <b>Нация:</b> {updated_tank.nation}\n"
                f"🔰 <b>Тип:</b> {updated_tank.tank_type or 'Не указан'}\n"
                f"📅 <b>Годы:</b> {years_str}\n"
                f"🆔 <b>ID:</b> {updated_tank.id}"
            )
            await message.answer(tank_card, parse_mode="HTML")
        
        await state.clear()

async def process_next_edit_step(message: Message, state: FSMContext, next_choice: int):
    data = await state.get_data()
    tank = data.get('selected_tank')
    current_years = data.get('current_years', [])
    
    if next_choice == 1:
        await message.answer(
            f"✏️ Введите новое название танка\nТекущее: {tank.name}:",
            parse_mode="HTML"
        )
        await state.set_state(TankStates.waiting_new_name)
    elif next_choice == 2:
        await message.answer(
            f"🌍 Введите новую нацию танка\nТекущая: {tank.nation}:",
            parse_mode="HTML"
        )
        await state.set_state(TankStates.waiting_new_nation)
    elif next_choice == 3:
        await message.answer(
            f"🔰 Введите новый тип танка\nТекущий: {tank.tank_type or 'Не указан'}:",
            parse_mode="HTML"
        )
        await state.set_state(TankStates.waiting_new_type)
    elif next_choice == 4:
        years_str = ", ".join(map(str, current_years)) if current_years else "Нет годов"
        await message.answer(
            f"📅 Введите новые годы создания танка через запятую\nТекущие: {years_str}:",
            parse_mode="HTML"
        )
        await state.set_state(TankStates.waiting_new_years)
    elif next_choice == 5:
        await message.answer(
            f"📝 Введите новое описание танка\nТекущее: {tank.discript}:",
            parse_mode="HTML"
        )
        await state.set_state(TankStates.waiting_new_description)
    elif next_choice == 6:
        await message.answer("🖼️ Отправьте новую фотографию танка:")
        await state.set_state(TankStates.waiting_new_image)



# Удаление танка
@admin.message(F.text == "Удалить танк")
@admin.message(Command('delete_tank'))
async def start_delete_tank(message: Message, state: FSMContext):
    # Проверка прав администратора
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для удаления танков!")
        return
    
    # Получаем список всех танков
    tanks = await get_all_tanks()
    
    if not tanks:
        await message.answer("🚫 В базе данных нет танков для удаления.")
        return
    
    # Формируем список танков для выбора
    tanks_list = "🗑️ <b>Список танков для удаления:</b>\n\n"
    for i, tank in enumerate(tanks, 1):
        tanks_list += f"{i}. ID: {tank.id} | {tank.name} ({tank.nation})\n"
    
    tanks_list += "\n\n🔢 <b>Введите ID танка для удаления:</b>"
    
    # Сохраняем список танков в состоянии
    await state.update_data(all_tanks=tanks)
    await state.set_state(TankStates.waiting_tank_to_delete)
    
    await message.answer(
        tanks_list,
        parse_mode="HTML"
    )


# Обработка выбора танка для удаления
@admin.message(TankStates.waiting_tank_to_delete)
async def process_tank_to_delete(message: Message, state: FSMContext):
    try:
        tank_id = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите ID танка цифрой:")
        return
    
    data = await state.get_data()
    tanks = data.get('all_tanks', [])
    
    # Ищем танк по ID
    selected_tank = None
    for tank in tanks:
        if tank.id == tank_id:
            selected_tank = tank
            break
    
    if not selected_tank:
        await message.answer("🚫 Танк с таким ID не найден. Попробуйте снова:")
        return
    
    # Сохраняем выбранный танк в состоянии
    await state.update_data(selected_tank=selected_tank)
    
    # Создаем клавиатуру для подтверждения удаления
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data="confirm_delete"),
        InlineKeyboardButton(text="❌ Нет, отменить", callback_data="cancel_delete")
    )
    
    confirmation_message = (
        f"⚠️ <b>ВНИМАНИЕ!</b>\n\n"
        f"Вы уверены, что хотите удалить этот танк?\n\n"
        f"🎖️ <b>Танк:</b> {selected_tank.name}\n"
        f"🇺🇳 <b>Нация:</b> {selected_tank.nation}\n"
        f"🔰 <b>Тип:</b> {selected_tank.tank_type or 'Не указан'}\n"
        f"🆔 <b>ID:</b> {selected_tank.id}\n\n"
        f"<i>Это действие невозможно отменить!</i>"
    )
    
    try:
        # Пытаемся показать фото танка
        await message.answer_photo(
            photo=selected_tank.photo_id,
            caption=confirmation_message,
            parse_mode="HTML",
            reply_markup=keyboard.as_markup()
        )
    except:
        # Если фото нет, отправляем только текст
        await message.answer(
            confirmation_message,
            parse_mode="HTML",
            reply_markup=keyboard.as_markup()
        )
    
    await state.set_state(TankStates.waiting_delete_confirmation)


# Обработка подтверждения удаления
@admin.callback_query(F.data == "confirm_delete", TankStates.waiting_delete_confirmation)
async def confirm_delete_tank(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tank = data.get('selected_tank')
    
    if not tank:
        await callback.answer("🚫 Танк не найден")
        return
    
    # Удаляем танк из базы данных
    success = await delete_tank(tank.id)
    success2 = await delete_tank_years(tank.id)
    
    if success:
        await callback.message.edit_caption(
            caption=f"✅ <b>Танк успешно удален!</b>\n\n"
                   f"🎖️ {tank.name} ({tank.nation})\n"
                   f"🆔 ID: {tank.id}",
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_caption(
            caption="❌ <b>Не удалось удалить танк.</b>\n"
                   "Попробуйте снова или обратитесь к администратору.",
            parse_mode="HTML"
        )
    
    await state.clear()
    await callback.answer()


# Обработка отмены удаления
@admin.callback_query(F.data == "cancel_delete")
async def cancel_delete_tank(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_caption(
        caption="❌ <b>Удаление отменено.</b>",
        parse_mode="HTML"
    )
    await state.clear()
    await callback.answer()

@admin.message(F.text == "отмена")
@admin.message(Command("canel"))
async def stop(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отмена успешна удалась")



# handlers/fine.py - написать с нуля

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext


from database.requests import (
    is_admin,
    get_users_with_fines,
    get_users_with_fines_by_event,
    get_all_events,
    get_user_by_name,
    get_all_users_ordered,
    get_event_by_index,
    set_user_points_value,
    decrease_user_points,
    reset_user_points,
    set_user_fine,
)



# --------- CallbackData ---------


class FineMenuCb(CallbackData, prefix="fine_menu"):
    action: str  # all | event | nick | add



class FineAdminCb(CallbackData, prefix="fine_adm"):
    action: str  # points_menu | points_zero | points_set | points_dec
    user_id: int



class FineAddCb(CallbackData, prefix="fine_add"):
    action: str  # all_users | by_event | by_nick



# --------- FSM ---------


class FineStates(StatesGroup):
    wait_event_number = State()
    wait_nick_search = State()
    wait_points_set_value = State()
    wait_points_dec_value = State()
    wait_admin_add_mode = State()
    wait_admin_add_user_number = State()
    wait_admin_add_fine_text = State()
    wait_admin_add_event_number = State()



# --------- Keyboards ---------


def kb_search_menu(is_admin_user: bool):
    kb = InlineKeyboardBuilder()
    kb.button(text="Все игроки", callback_data=FineMenuCb(action="all").pack())
    kb.button(text="По ивенту", callback_data=FineMenuCb(action="event").pack())
    kb.button(text="По нику", callback_data=FineMenuCb(action="nick").pack())
    if is_admin_user:
        kb.button(
            text="Добавить игрока в список с нарушениями",
            callback_data=FineMenuCb(action="add").pack()
        )
    kb.adjust(1)
    return kb.as_markup()



def kb_admin_user_actions(user_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="Убавить очки", callback_data=FineAdminCb(action="points_menu", user_id=user_id).pack())
    kb.button(text="Назад", callback_data=FineMenuCb(action="all").pack())
    kb.adjust(1)
    return kb.as_markup()



def kb_admin_points_menu(user_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="Обнулить", callback_data=FineAdminCb(action="points_zero", user_id=user_id).pack())
    kb.button(text="Задать значение", callback_data=FineAdminCb(action="points_set", user_id=user_id).pack())
    kb.button(text="Убавить", callback_data=FineAdminCb(action="points_dec", user_id=user_id).pack())
    kb.button(text="Назад", callback_data=FineMenuCb(action="all").pack())
    kb.adjust(1)
    return kb.as_markup()



def kb_admin_add_mode():
    kb = InlineKeyboardBuilder()
    kb.button(text="Все игроки", callback_data=FineAddCb(action="all_users").pack())
    kb.button(text="По ивентам", callback_data=FineAddCb(action="by_event").pack())
    kb.button(text="По нику", callback_data=FineAddCb(action="by_nick").pack())
    kb.button(text="Назад", callback_data=FineMenuCb(action="add").pack())
    kb.adjust(1)
    return kb.as_markup()



# --------- Entry point ---------


@admin.message(F.text == "матч-штрафы")
async def fine_entry(message: Message, state: FSMContext):
    await state.clear()
    is_admin_user = await is_admin(message.from_user.id)
    await message.answer("режим поиска", reply_markup=kb_search_menu(is_admin_user))



# --------- Search menu: All players ---------


@admin.callback_query(FineMenuCb.filter(F.action == "all"))
async def fine_all(callback: CallbackQuery, state: FSMContext):
    is_admin_user = await is_admin(callback.from_user.id)
    users = await get_users_with_fines()

    if not users:
        await callback.message.answer("Игроки с штрафом отсутствуют")
        await callback.answer()
        return

    lines = []
    for i, u in enumerate(users, start=1):
        if is_admin_user:
            lines.append(f"{i}. {u.name} - {u.fine} (очки: {u.points or 0})")
        else:
            lines.append(f"{i}. {u.name} - {u.fine}")

    await callback.message.answer("\n".join(lines))
    await callback.answer()



# --------- Search menu: By event ---------


@admin.callback_query(FineMenuCb.filter(F.action == "event"))
async def fine_by_event_start(callback: CallbackQuery, state: FSMContext):
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
async def fine_by_event_number(message: Message, state: FSMContext):
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
    users = await get_users_with_fines_by_event(event.id)

    if not users:
        await message.answer("Игроки с штрафом отсутствуют")
        await state.clear()
        return

    lines = []
    for i, u in enumerate(users, start=1):
        if is_admin_user:
            lines.append(f"{i}. {u.name} - {u.fine} (очки: {u.points or 0})")
        else:
            lines.append(f"{i}. {u.name} - {u.fine}")

    await message.answer("\n".join(lines))
    await state.clear()



# --------- Search menu: By nick ---------


@admin.callback_query(FineMenuCb.filter(F.action == "nick"))
async def fine_by_nick_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FineStates.wait_nick_search)
    await callback.message.answer("Введи ник пользователя")
    await callback.answer()



@admin.message(FineStates.wait_nick_search)
async def fine_by_nick(message: Message, state: FSMContext):
    nick = message.text.strip()
    user = await get_user_by_name(nick)

    if not user:
        await message.answer("Нету игрока с таким ником")
        await state.clear()
        return

    fine_text = (user.fine or "").strip()
    if not fine_text:
        await message.answer("Игрок не получал штрафов")
        await state.clear()
        return

    is_admin_user = await is_admin(message.from_user.id)
    if is_admin_user:
        await message.answer(
            f"{user.name} - {user.fine} (очки: {user.points or 0})",
            reply_markup=kb_admin_user_actions(user.id)
        )
    else:
        await message.answer(f"{user.name} - {user.fine}")

    await state.clear()



# --------- Admin: Points menu ---------


@admin.callback_query(FineAdminCb.filter(F.action == "points_menu"))
async def admin_points_menu(callback: CallbackQuery, callback_data: FineAdminCb, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    await callback.message.edit_text("Выбери действие:", reply_markup=kb_admin_points_menu(callback_data.user_id))
    await callback.answer()



@admin.callback_query(FineAdminCb.filter(F.action == "points_zero"))
async def admin_points_zero(callback: CallbackQuery, callback_data: FineAdminCb, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    await reset_user_points(callback_data.user_id)
    await callback.message.edit_text("✅ Очки обнулены.", reply_markup=kb_admin_points_menu(callback_data.user_id))
    await callback.answer()



@admin.callback_query(FineAdminCb.filter(F.action == "points_set"))
async def admin_points_set_start(callback: CallbackQuery, callback_data: FineAdminCb, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    await state.set_state(FineStates.wait_points_set_value)
    await state.update_data(target_user_id=callback_data.user_id)
    await callback.message.answer("Введи число. Очки пользователя станут равны этому числу:")
    await callback.answer()



@admin.message(FineStates.wait_points_set_value)
async def admin_points_set_apply(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("Недостаточно прав.")
        await state.clear()
        return

    data = await state.get_data()
    user_id = data.get("target_user_id")

    try:
        value = int(message.text.strip())
    except ValueError:
        await message.answer("Нужно число.")
        return

    await set_user_points_value(user_id, value)
    await message.answer(f"✅ Очки установлены на {value}.")
    await state.clear()



@admin.callback_query(FineAdminCb.filter(F.action == "points_dec"))
async def admin_points_dec_start(callback: CallbackQuery, callback_data: FineAdminCb, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    await state.set_state(FineStates.wait_points_dec_value)
    await state.update_data(target_user_id=callback_data.user_id)
    await callback.message.answer("Введи число. На столько очков будет уменьшено:")
    await callback.answer()



@admin.message(FineStates.wait_points_dec_value)
async def admin_points_dec_apply(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("Недостаточно прав.")
        await state.clear()
        return

    data = await state.get_data()
    user_id = data.get("target_user_id")

    try:
        delta = int(message.text.strip())
    except ValueError:
        await message.answer("Нужно число.")
        return

    await decrease_user_points(user_id, delta)
    await message.answer(f"✅ Очки уменьшены на {delta}.")
    await state.clear()



# --------- Admin: Add user to violations ---------


@admin.callback_query(FineMenuCb.filter(F.action == "add"))
async def admin_add_fine_start(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    await state.set_state(FineStates.wait_admin_add_mode)
    await callback.message.answer("Выбери режим добавления:", reply_markup=kb_admin_add_mode())
    await callback.answer()



# --------- Admin: Add - All users ---------


@admin.callback_query(FineAddCb.filter(F.action == "all_users"))
async def admin_add_all_users(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    users = await get_all_users_ordered()
    if not users:
        await callback.message.answer("Пользователей нет.")
        await callback.answer()
        await state.clear()
        return

    await state.set_state(FineStates.wait_admin_add_user_number)
    await state.update_data(add_users=[u.id for u in users])

    lines = []
    for i, u in enumerate(users, start=1):
        lines.append(f"{i}. {u.name} (очки: {u.points or 0})")

    await callback.message.answer("\n".join(lines) + "\n\nВведи номер пользователя:")
    await callback.answer()



# --------- Admin: Add - By event ---------


@admin.callback_query(FineAddCb.filter(F.action == "by_event"))
async def admin_add_by_event_start(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    events = await get_all_events()
    if not events:
        await callback.message.answer("Ивентов нет.")
        await callback.answer()
        await state.clear()
        return

    await state.set_state(FineStates.wait_admin_add_event_number)

    lines = []
    for i, e in enumerate(events, start=1):
        dt = e.time.strftime("%d.%m.%Y %H:%M") if getattr(e, "time", None) else ""
        lines.append(f"{i}. {e.name} {dt}".strip())

    await state.update_data(events_count=len(events))
    await callback.message.answer("\n".join(lines) + "\n\nВведи номер ивента:")
    await callback.answer()



@admin.message(FineStates.wait_admin_add_event_number)
async def admin_add_event_number(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("Недостаточно прав.")
        await state.clear()
        return

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

    # Получаем участников ивента
    from database.requests import get_event_participants
    users = await get_event_participants(event.id)

    if not users:
        await message.answer("Участников ивента нет.")
        await state.clear()
        return

    await state.set_state(FineStates.wait_admin_add_user_number)
    await state.update_data(add_users=[u.id for u in users])

    lines = []
    for i, u in enumerate(users, start=1):
        lines.append(f"{i}. {u.name} (очки: {u.points or 0})")

    await message.answer("\n".join(lines) + "\n\nВведи номер пользователя:")



# --------- Admin: Add - By nick ---------


@admin.callback_query(FineAddCb.filter(F.action == "by_nick"))
async def admin_add_by_nick_start(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    await state.set_state(FineStates.wait_nick_search)
    await callback.message.answer("Введи ник пользователя:")
    await callback.answer()



@admin.message(FineStates.wait_nick_search)
async def admin_add_by_nick(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("Недостаточно прав.")
        await state.clear()
        return

    nick = message.text.strip()
    user = await get_user_by_name(nick)

    if not user:
        await message.answer("Нету игрока с таким ником")
        await state.clear()
        return

    await state.set_state(FineStates.wait_admin_add_fine_text)
    await state.update_data(target_user_id=user.id)
    await message.answer(f"Введи текст штрафа для {user.name}:")



# --------- Admin: Add - Enter fine text ---------


@admin.message(FineStates.wait_admin_add_user_number)
async def admin_add_user_number(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("Недостаточно прав.")
        await state.clear()
        return

    data = await state.get_data()
    ids = data.get("add_users", [])

    try:
        idx = int(message.text.strip())
    except ValueError:
        await message.answer("Нужно число (номер пользователя).")
        return

    if idx < 1 or idx > len(ids):
        await message.answer("Неверный номер.")
        return

    target_user_id = ids[idx - 1]
    await state.update_data(target_user_id=target_user_id)
    await state.set_state(FineStates.wait_admin_add_fine_text)
    await message.answer("Введи текст штрафа (пункт/причина):")



@admin.message(FineStates.wait_admin_add_fine_text)
async def admin_add_fine_apply(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("Недостаточно прав.")
        await state.clear()
        return

    data = await state.get_data()
    user_id = data.get("target_user_id")
    fine_text = message.text.strip()

    if not fine_text:
        await message.answer("Текст штрафа не может быть пустым.")
        return

    ok = await set_user_fine(user_id, fine_text)
    await message.answer("✅ Штраф установлен." if ok else "❌ Не удалось установить штраф.")
    await state.clear()