from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict

from database.requests import (
    get_all_tanks, get_tanks_by_nation, get_tank_by_id,
    create_tank, update_tank, delete_tank, get_all_nations,
    get_user, is_admin
)
from database.models import Tank

tank_router = Router()

class TankStates(StatesGroup):
    waiting_tank_nation = State()
    waiting_tank_name = State()
    waiting_tank_description = State()
    waiting_tank_image = State()
    waiting_tank_to_edit = State()
    waiting_edit_choices = State()
    waiting_new_nation = State()
    waiting_new_name = State()
    waiting_new_description = State()
    waiting_new_image = State()
    waiting_tank_to_delete = State()


@tank_router.message(F.text == "Список танков")
@tank_router.message(Command('tanks'))
async def show_tanks_list(message: Message):
    tanks = await get_all_tanks()
    
    if not tanks:
        await message.answer("🚫 В базе данных пока нет танков.")
        return
    
    # Группируем танки по нациям
    tanks_by_nation: Dict[str, List[Tank]] = {}
    for tank in tanks:
        if tank.nation not in tanks_by_nation:
            tanks_by_nation[tank.nation] = []
        tanks_by_nation[tank.nation].append(tank)
    
    response = "🎖️ Список танков по нациям\n\n"
    
    # Получаем все уникальные нации
    nations = await get_all_nations()
    
    for nation in sorted(nations):
        nation_tanks = tanks_by_nation.get(nation, [])
        if nation_tanks:
            response += f"🇺🇳 {nation} ({len(nation_tanks)} танков):\n"
            
            # Показываем первые 3 танка каждой нации
            for i, tank in enumerate(nation_tanks[:3], 1):
                response += f"  {i}. {tank.name}\n"
            
            if len(nation_tanks) > 3:
                response += f"  ... и еще {len(nation_tanks) - 3} танков\n"
            
            response += "\n"
    
    await message.answer(response)
    
    # Отправляем кнопки для выбора нации
    keyboard = InlineKeyboardBuilder()
    for nation in sorted(nations):
        tank_count = len(tanks_by_nation.get(nation, []))
        keyboard.add(InlineKeyboardButton(
            text=f"{nation} ({tank_count})",
            callback_data=f"nation_{nation}"
        ))
    keyboard.adjust(2)  # 2 кнопки в ряду
    
    await message.answer("Выберите нацию для просмотра танков:", 
                        reply_markup=keyboard.as_markup())

@tank_router.callback_query(F.data.startswith("nation_"))
async def show_tanks_by_nation(callback: CallbackQuery):
    nation = callback.data.split("_")[1]
    tanks = await get_tanks_by_nation(nation)
    
    if not tanks:
        await callback.answer(f"🚫 Нет танков нации {nation}")
        return
    
    response = f"🎖️ Танки {nation}\n\n"
    
    for i, tank in enumerate(tanks, 1):
        response += f"{i}. {tank.name}\n"
        if tank.discript:
            response += f"   {tank.discript[:50]}...\n"
        response += "\n"
    
    # Кнопка для просмотра подробностей первого танка
    if tanks:
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(
            text="🔍 Показать подробнее",
            callback_data=f"view_tank_{tanks[0].id}"
        ))
        
        await callback.message.answer(response, reply_markup=keyboard.as_markup())
    
    await callback.answer()

@tank_router.callback_query(F.data.startswith("view_tank_"))
async def show_tank_details(callback: CallbackQuery):
    tank_id = int(callback.data.split("_")[2])
    tank = await get_tank_by_id(tank_id)
    
    if not tank:
        await callback.answer("🚫 Танк не найден!")
        return
    
    caption = (
        f"🎖️ {tank.name}\n"
        f"🇺🇳 Нация: {tank.nation}\n\n"
        f"📝 Описание:\n{tank.discript}\n\n"
        f"🆔 ID: {tank.id}"
    )
    
    try:
        # Пытаемся отправить фото, если оно есть
        await callback.message.answer_photo(
            photo=tank.photo_id,
            caption=caption
        )
    except:
        # Если фото нет или ошибка, отправляем только текст
        await callback.message.answer(caption)
    
    await callback.answer()

# Добавление танка
@tank_router.message(F.text == "Добавить танк")
@tank_router.message(Command('add_tank'))
async def add_tank_command(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для добавления танков!")
        return
    
    await message.answer("🎖️ Давайте добавим новый танк!\n\nВведите нацию танка (например: СССР, Германия, США):")
    await state.set_state(TankStates.waiting_tank_nation)

@tank_router.message(TankStates.waiting_tank_nation)
async def process_tank_nation(message: Message, state: FSMContext):
    await state.update_data(nation=message.text.strip())
    await message.answer("📝 Введите название танка:")
    await state.set_state(TankStates.waiting_tank_name)

@tank_router.message(TankStates.waiting_tank_name)
async def process_tank_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("📄 Введите описание танка:")
    await state.set_state(TankStates.waiting_tank_description)

@tank_router.message(TankStates.waiting_tank_description)
async def process_tank_description(message: Message, state: FSMContext):
    await state.update_data(discript=message.text.strip())
    await message.answer("🖼️ Отправьте фотографию танка:")
    await state.set_state(TankStates.waiting_tank_image)

@tank_router.message(TankStates.waiting_tank_image, F.photo)
async def process_tank_image(message: Message, state: FSMContext):
    data = await state.get_data()
    
    # Сохраняем file_id фотографии
    photo_id = message.photo[-1].file_id
    
    # Создаем танк
    success = await create_tank(
        name=data['name'],
        nation=data['nation'],
        discript=data['discript'],
        photo_id=photo_id
    )
    
    if success:
        await message.answer_photo(
            photo=photo_id,
            caption=f"✅ Танк успешно добавлен!\n\n"
                   f"🎖️ {data['name']}\n"
                   f"🇺🇳 Нация: {data['nation']}\n"
                   f"📝 Описание: {data['discript'][:100]}..."
        )
    else:
        await message.answer("❌ Не удалось добавить танк. Попробуйте снова.")
    
    await state.clear()

@tank_router.message(TankStates.waiting_tank_image)
async def process_tank_image_invalid(message: Message):
    await message.answer("⚠️ Пожалуйста, отправьте фотографию!")


@tank_router.message(F.text == "Изменить танк")
@tank_router.message(Command('edit_tank'))
async def edit_tank_command(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для изменения танков!")
        return
    
    tanks = await get_all_tanks()
    
    if not tanks:
        await message.answer("🚫 Нет доступных танков для изменения.")
        return
    
    # Формируем список танков
    tanks_list = "🎖️ Список танков для изменения\n\n"
    for i, tank in enumerate(tanks, 1):
        tanks_list += f"{i}. 🆔 {tank.id} | {tank.name}\n"
        tanks_list += f"   🇺🇳 {tank.nation}\n\n"
    
    tanks_list += "Введите номер танка для изменения (или 'отмена' для отмены):"
    
    await state.update_data(tanks=tanks)
    await state.set_state(TankStates.waiting_tank_to_edit)
    await message.answer(tanks_list)

@tank_router.message(TankStates.waiting_tank_to_edit)
async def process_tank_to_edit(message: Message, state: FSMContext):
    user_input = message.text.strip().lower()
    
    if user_input in ['отмена', 'cancel', 'стоп']:
        await message.answer("❌ Изменение отменено.")
        await state.clear()
        return
    
    try:
        tank_number = int(user_input)
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите номер цифрой или 'отмена' для отмены:")
        return
    
    data = await state.get_data()
    tanks = data.get('tanks', [])
    
    if not (1 <= tank_number <= len(tanks)):
        await message.answer(f"⚠️ Пожалуйста, введите номер от 1 до {len(tanks)}:")
        return
    
    # Получаем выбранный танк
    tank = tanks[tank_number - 1]
    
    # Показываем что можно изменить
    edit_options = (
        "📝 Что вы хотите изменить? (введите номера через запятую)\n\n"
        "1. 🇺🇳 Нация\n"
        "2. ✏️ Название\n"
        "3. 📄 Описание\n"
        "4. 🖼️ Фотография\n\n"
        "Например: 1,3 или просто 2"
    )
    
    await state.update_data(selected_tank=tank, tank_id=tank.id)
    await message.answer_photo(
        photo=tank.photo_id,
        caption=f"🎖️ {tank.name}\n"
               f"🇺🇳 Нация: {tank.nation}\n"
               f"📝 Описание: {tank.discript[:100]}..."
    )
    await message.answer(edit_options)
    await state.set_state(TankStates.waiting_edit_choices)

@tank_router.message(TankStates.waiting_edit_choices)
async def process_tank_edit_choices(message: Message, state: FSMContext):
    try:
        choices = [int(choice.strip()) for choice in message.text.strip().split(',')]
        
        # Проверяем валидность выбора
        invalid_choices = [c for c in choices if not (1 <= c <= 4)]
        if invalid_choices:
            await message.answer(f"⚠️ Неверные номера: {invalid_choices}. Введите номера от 1 до 4:")
            return
        
        data = await state.get_data()
        tank_id = data.get('tank_id')
        
        # Сохраняем выбранные опции
        await state.update_data(edit_choices=choices)
        
        # Обрабатываем каждую выбранную опцию
        for choice in sorted(set(choices)):  # Убираем дубликаты
            if choice == 1:
                await message.answer("🇺🇳 Введите новую нацию танка:")
                await state.set_state(TankStates.waiting_new_nation)
                return
            elif choice == 2:
                await message.answer("✏️ Введите новое название танка:")
                await state.set_state(TankStates.waiting_new_name)
                return
            elif choice == 3:
                await message.answer("📄 Введите новое описание танка:")
                await state.set_state(TankStates.waiting_new_description)
                return
            elif choice == 4:
                await message.answer("🖼️ Отправьте новую фотографию танка:")
                await state.set_state(TankStates.waiting_new_image)
                return
        
    except ValueError:
        await message.answer("⚠️ Неверный формат. Введите номера через запятую (например: 1,3 или просто 2):")

@tank_router.message(TankStates.waiting_new_nation)
async def process_new_nation(message: Message, state: FSMContext):
    data = await state.get_data()
    tank_id = data.get('tank_id')
    
    success = await update_tank(tank_id, nation=message.text.strip())
    
    if success:
        await message.answer("✅ Нация обновлена!")
        await continue_tank_editing(message, state, data.get('edit_choices', []), 1)
    else:
        await message.answer("❌ Не удалось обновить нацию")

@tank_router.message(TankStates.waiting_new_name)
async def process_new_name(message: Message, state: FSMContext):
    data = await state.get_data()
    tank_id = data.get('tank_id')
    
    success = await update_tank(tank_id, name=message.text.strip())
    
    if success:
        await message.answer("✅ Название обновлено!")
        await continue_tank_editing(message, state, data.get('edit_choices', []), 2)
    else:
        await message.answer("❌ Не удалось обновить название")

@tank_router.message(TankStates.waiting_new_description)
async def process_new_description(message: Message, state: FSMContext):
    data = await state.get_data()
    tank_id = data.get('tank_id')
    
    success = await update_tank(tank_id, discript=message.text.strip())
    
    if success:
        await message.answer("✅ Описание обновлено!")
        await continue_tank_editing(message, state, data.get('edit_choices', []), 3)
    else:
        await message.answer("❌ Не удалось обновить описание")

@tank_router.message(TankStates.waiting_new_image, F.photo)
async def process_new_image(message: Message, state: FSMContext):
    data = await state.get_data()
    tank_id = data.get('tank_id')
    
    photo_id = message.photo[-1].file_id
    success = await update_tank(tank_id, photo_id=photo_id)
    
    if success:
        await message.answer("✅ Фотография обновлена!")
        await continue_tank_editing(message, state, data.get('edit_choices', []), 4)
    else:
        await message.answer("❌ Не удалось обновить фотографию")

@tank_router.message(TankStates.waiting_new_image)
async def process_new_image_invalid(message: Message):
    await message.answer("⚠️ Пожалуйста, отправьте фотографию!")

async def continue_tank_editing(message: Message, state: FSMContext, choices: list, processed_choice: int):
    data = await state.get_data()
    tank_id = data.get('tank_id')
    
    # Убираем обработанный пункт
    remaining_choices = [c for c in choices if c != processed_choice]
    
    if not remaining_choices:
        # Все изменения завершены
        tank = await get_tank_by_id(tank_id)
        if tank:
            await message.answer_photo(
                photo=tank.photo_id,
                caption=f"✅ Танк обновлен!\n\n"
                       f"🎖️ {tank.name}\n"
                       f"🇺🇳 Нация: {tank.nation}\n"
                       f"📝 Описание: {tank.discript[:100]}..."
            )
        await state.clear()
        return
    
    # Сохраняем оставшиеся пункты
    await state.update_data(edit_choices=remaining_choices)
    
    # Переходим к следующему пункту
    next_choice = sorted(set(remaining_choices))[0]
    if next_choice == 1:
        await message.answer("🇺🇳 Введите новую нацию танка:")
        await state.set_state(TankStates.waiting_new_nation)
    elif next_choice == 2:
        await message.answer("✏️ Введите новое название танка:")
        await state.set_state(TankStates.waiting_new_name)
    elif next_choice == 3:
        await message.answer("📄 Введите новое описание танка:")
        await state.set_state(TankStates.waiting_new_description)
    elif next_choice == 4:
        await message.answer("🖼️ Отправьте новую фотографию танка:")
        await state.set_state(TankStates.waiting_new_image)

# Удалить танк
@tank_router.message(F.text == "Удалить танк")
@tank_router.message(Command('delete_tank'))
async def delete_tank_command(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для удаления танков!")
        return
    
    tanks = await get_all_tanks()
    
    if not tanks:
        await message.answer("🚫 Нет доступных танков для удаления.")
        return
    
    # Формируем список танков
    tanks_list = "🎖️ Список танков для удаления\n\n"
    for i, tank in enumerate(tanks, 1):
        tanks_list += f"{i}. 🆔 {tank.id} | {tank.name}\n"
        tanks_list += f"   🇺🇳 {tank.nation}\n\n"
    
    tanks_list += "Введите номер танка для удаления (или 'отмена' для отмены):"
    
    await state.update_data(tanks=tanks)
    await state.set_state(TankStates.waiting_tank_to_delete)
    await message.answer(tanks_list)

@tank_router.message(TankStates.waiting_tank_to_delete)
async def process_tank_to_delete(message: Message, state: FSMContext):
    user_input = message.text.strip().lower()
    
    if user_input in ['отмена', 'cancel', 'стоп']:
        await message.answer("❌ Удаление отменено.")
        await state.clear()
        return
    
    try:
        tank_number = int(user_input)
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите номер цифрой или 'отмена' для отмены:")
        return
    
    data = await state.get_data()
    tanks = data.get('tanks', [])
    
    if not (1 <= tank_number <= len(tanks)):
        await message.answer(f"⚠️ Пожалуйста, введите номер от 1 до {len(tanks)}:")
        return
    
    # Получаем выбранный танк
    tank = tanks[tank_number - 1]
    
    # Создаем клавиатуру для подтверждения
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_tank_{tank.id}"),
        InlineKeyboardButton(text="❌ Нет, отменить", callback_data="cancel_delete_tank")
    )
    
    confirmation_message = (
        f"⚠️ ВНИМАНИЕ: Вы уверены, что хотите удалить этот танк?\n\n"
        f"🎖️ {tank.name}\n"
        f"🇺🇳 Нация: {tank.nation}\n"
        f"🆔 ID: {tank.id}\n\n"
        f"Это действие невозможно отменить!"
    )
    
    try:
        await message.answer_photo(
            photo=tank.photo_id,
            caption=confirmation_message,
            reply_markup=keyboard.as_markup()
        )
    except:
        await message.answer(confirmation_message, reply_markup=keyboard.as_markup())
    
    await state.clear()

@tank_router.callback_query(F.data.startswith("confirm_delete_tank_"))
async def confirm_tank_deletion(callback: CallbackQuery):
    tank_id = int(callback.data.split("_")[3])
    
    success = await delete_tank(tank_id)
    
    if success:
        await callback.message.edit_caption(caption="✅ Танк успешно удален!")
        await callback.answer("Танк удален!")
    else:
        await callback.message.edit_caption(caption="❌ Ошибка при удалении танка")
        await callback.answer("Произошла ошибка!")

@tank_router.callback_query(F.data == "cancel_delete_tank")
async def cancel_tank_deletion(callback: CallbackQuery):
    await callback.message.edit_caption(caption="❌ Удаление отменено.")
    await callback.answer()

# Поиск Танка
@tank_router.message(Command('find_tank'))
async def find_tank_command(message: Message, state: FSMContext):
    tanks = await get_all_tanks()
    
    if not tanks:
        await message.answer("🚫 В базе данных нет танков.")
        return
    
    response = (
        "🔍 Поиск танка\n\n"
        "Введите часть названия танка для поиска.\n"
        "Например: 'Т-34' или 'Тигр'"
    )
    
    await message.answer(response)
    
    # Кнопки с популярными танками для быстрого поиска
    keyboard = InlineKeyboardBuilder()
    popular_tanks = ["Т-34", "Тигр", "Шерман", "Пантера", "ИС-2"]
    
    for tank_name in popular_tanks:
        if any(t.name.lower() == tank_name.lower() for t in tanks):
            keyboard.add(InlineKeyboardButton(
                text=tank_name,
                callback_data=f"quick_search_{tank_name}"
            ))
    
    if keyboard.buttons:
        keyboard.adjust(3)
        await message.answer("Быстрый поиск:", reply_markup=keyboard.as_markup())

@tank_router.callback_query(F.data.startswith("quick_search_"))
async def quick_search_tank(callback: CallbackQuery):
    tank_name = callback.data.split("_")[2]
    tanks = await get_all_tanks()
    
    found_tanks = [t for t in tanks if tank_name.lower() in t.name.lower()]
    
    if not found_tanks:
        await callback.answer(f"🚫 Не найдено танков с названием '{tank_name}'")
        return
    
    response = f"🔍 Найдено танков с '{tank_name}':\n\n"
    
    for i, tank in enumerate(found_tanks, 1):
        response += f"{i}. {tank.name} ({tank.nation})\n"
    
    # Кнопка для просмотра первого найденного танка
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(
        text="🔍 Показать первый",
        callback_data=f"view_tank_{found_tanks[0].id}"
    ))
    
    await callback.message.answer(response, reply_markup=keyboard.as_markup())
    await callback.answer()

# Команда помощи
@tank_router.message(Command('tank_help'))
async def tank_help_command(message: Message):
    user = await get_user(message.from_user.id)
    is_admin_user = user and user.status == 'admin'
    
    help_text = "🎖️ Система управления танками\n\n"
    help_text += "Доступные команды:\n\n"
    
    help_text += "👤 Для всех пользователей:\n"
    help_text += "/tanks - Показать список танков по нациям\n"
    help_text += "/find_tank - Поиск танка по названию\n"
    help_text += "Список танков - Показать список танков (кнопка)\n\n"
    
    if is_admin_user:
        help_text += "👑 Для администраторов:\n"
        help_text += "/add_tank - Добавить новый танк\n"
        help_text += "/edit_tank - Изменить существующий танк\n"
        help_text += "/delete_tank - Удалить танк\n"
        help_text += "/tank_stats - Статистика танков\n\n"
    
    help_text += "💡 Как использовать:\n"
    help_text += "1. Используйте /tanks для просмотра всех танков\n"
    help_text += "2. Выберите нацию для детального просмотра\n"
    help_text += "3. Используйте поиск для быстрого нахождения танка\n"
    
    await message.answer(help_text)