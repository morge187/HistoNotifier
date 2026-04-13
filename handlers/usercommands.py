from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram import F
from database.requests import get_user, get_events
from keyboards import adminboard, userboard
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

user = Router()


@user.message(F.text == 'Правила')
async def chacge_name(message: Message, state: FSMContext):
    await message.answer(
        "📜 <b>ПРАВИЛА ТУРНИРА</b>\n\n"

        "🔴 <b>1. Запрещённые предметы:</b>\n"
        "• Аптечки, ремкомплекты, огнетушители\n"
        "• Шоколад и доппаёк\n"
        "(Исключения будут прописаны.)\n\n"

        "🔴 <b>2. Стрельба на ходу:</b>\n"
        "• Запрещена при расстоянии &gt;100 метров\n\n"

        "🔴 <b>3. Кружение танков:</b>\n"
        "• Полностью запрещено\n\n"

        "🔴 <b>4. Танкование:</b>\n"
        "• Любые элементы танкования запрещены\n"
        "• Разрешено только ромбование\n\n"

        "🔴 <b>5. Гусление:</b>\n"
        "• Намеренное гусление противника запрещено\n\n"

        "🔴 <b>6. Оборудование:</b>\n"
        "• Использование запрещено\n"
        "(Исключения будут прописаны.)\n\n"

        "🔴 <b>7. Инструкции:</b>\n"
        "• Любые инструкции запрещены\n"
        "(Исключения будут прописаны.)\n\n"

        "🔴 <b>8. Бегство:</b>\n"
        "• Явное бегство от противника запрещено\n\n"

        "🔴 <b>9. Штрафы:</b>\n"
        "• За нарушения — штрафное очко команде\n"
        "• 3 штрафных очка = 1 техническое поражение в раунде\n\n"

        "🔴 <b>10. Таран:</b>\n"
        "• Запрещён\n"
        "• <i>Исключение:</i> техника СССР и японцев\n"
        "• При таране оба танка остаются неподвижными до тех пор, пока кто-то не будет уничтожен\n\n"

        "🔴 <b>11. Камуфляжи:</b>\n"
        "• Историчные камуфляжи разрешены\n"
        "• Перед боем показать танк организаторам\n\n"

        "🔴 <b>12. Захваченная техника:</b>\n"
        "• Помечена значком „°“\n"
        "• Обязательна перекраска в базовый цвет страны\n"
        "• Без покраски не принимается\n\n"

        "🔴 <b>13. Орудия:</b>\n"
        "• Помечены значком „◒“\n"
        "• Передвигаться только на 1-ой скорости\n"
        "• 1 минута на выбор позиции на макс. скорости\n\n"

        "🔴 <b>14. Бензин и масло:</b>\n"
        "• При наличии на танке 100/105-октанового бензина или масла танк не может потушиться, даже имея огнетушитель\n\n"

        "🔴 <b>15. ДОТы:</b>\n"
        "• Танки, помеченные знаком „×”, не могут передвигаться и стоят на одном из указанных мест таким же значком на карте\n"
        "• Такой танк имеет право поставить оборудование:\n"
        "  - Улучшенная закалка\n"
        "  - Противоосколочный подбой\n"
        "  - Изменённая компановка\n"
        "  - Улучшенная вентиляция\n\n"

        "🔴 <b>16. Буксир:</b>\n"
        "• Буксировать можно технику меньшей по массе вашей и орудия\n"
        "• Для этого требуется подъехать к технике (буксируемая техника цепляется к задней части танка) и включить вторую скорость\n"
        "• Буксируемый танк едет на макс. скорости\n\n"

        "🔴 <b>17. Ремонтный танк:</b>\n"
        "• Обозначается знаком „[]“\n"
        "• Может чинить модули (3 модуля за весь бой)\n"
        "• Для починки подъезжает к повреждённому танку и стоит с ним 10 секунд\n"
        "• Оба танка не могут стрелять и двигаться во время ремонта\n\n"

        "🔴 <b>18. Огонь по своим строго запрещён:</b>\n"
        "• За грубое нарушение правил будет выдан матч-штраф\n\n"

        "🔴 <b>19. Уважение организатора:</b>\n"
        "• За грубое, оскорбительное обращение к организатору будет выдан матч-штраф\n\n"

        "❌ <b>Матч-штрафы:</b>\n"
        "• При несоблюдении или нарушении любого пункта правил игрок может получить матч-штраф\n"
        "• Выдаётся организатором за нарушение правил проведения турнира\n\n"

        "👁 <b>НАБЛЮДАТЕЛИ:</b>\n"
        "• Просмотр разрешён:\n"
        "  - Участникам клана [Т-70В]\n"
        "  - Проверенным лицам\n"
        "  - Подписчикам канала TCF\n\n"
        "⚠️ <b>Обязанности наблюдателей:</b>\n"
        "• Молчать во время боя\n"
        "• Любые подсказки запрещены\n"
        "• Нарушения → дисквалификация\n",
        parse_mode="HTML",
    )
    
@user.message(Command('menu'))
async def menu(message: Message):
    user = await get_user(message.from_user.id)
    if user.status == 'admin':
        await message.answer('меню', reply_markup=adminboard)
    else:
        await message.answer('меню`', reply_markup=userboard)

@user.message(F.text == "Мои кадры")
@user.message(Command("my_cadrs"))
async def kadrs(message: Message):
    user = await get_user(message.from_user.id)
    await message.answer(f"У вас {user.points} кадров")

from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

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
@user.message(F.text == 'Список танков')
@user.message(Command('tanks'))
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


@user.callback_query(F.data == "tanks")
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
@user.callback_query(F.data == "tanks_by_nation")
async def tanks_by_nation_menu(callback: CallbackQuery, state: FSMContext):
    nations = await get_all_nations()

    if not nations:
        await callback.message.answer("🚫 В базе данных нет танков.")
        await callback.answer()
        return

    # Сохраняем список наций в state и передаем в callback_data только индекс
    await state.update_data(nations=nations)

    keyboard = InlineKeyboardBuilder()
    for i, nation in enumerate(nations):
        keyboard.add(
            InlineKeyboardButton(text=f"🇺🇳 {nation}", callback_data=f"nation_{i}")
        )

    keyboard.adjust(2)
    keyboard.add(InlineKeyboardButton(text="Назад", callback_data="tanks"))

    await callback.message.edit_text(
        "🎌 <b>Выберите нацию:</b>",
        parse_mode="HTML",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()


# Обработка выбора нации
@user.callback_query(F.data.startswith("nation_"))
async def process_nation_choice(callback: CallbackQuery, state: FSMContext):
    # В callback_data приходит индекс нации (nation_{i})
    try:
        nation_idx = int(callback.data.split("_", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка формата данных")
        return

    data = await state.get_data()
    nations = data.get('nations', [])
    if not nations or not (0 <= nation_idx < len(nations)):
        await callback.answer("❌ Нация не найдена")
        return

    nation = nations[nation_idx]
    tanks = await get_tanks_by_nation(nation)

    if not tanks:
        await callback.answer(f"🚫 Нет танков нации {nation}")
        return

    tank_types = sorted({t.tank_type for t in tanks if t.tank_type})

    # Сохраняем, чтобы дальше кнопки типа были короткими
    await state.update_data(selected_nation=nation, tanks=tanks, tank_types=tank_types)

    if not tank_types:
        await state.update_data(selected_tank_type=None)
        await show_tanks_list(callback.message, tanks, nation, "tanks_by_nation")
        await callback.answer()
        return

    keyboard = InlineKeyboardBuilder()
    for i, tank_type in enumerate(tank_types):
        keyboard.add(InlineKeyboardButton(text=f"🔰 {tank_type}", callback_data=f"type_{nation_idx}_{i}"))

    keyboard.adjust(2)
    keyboard.row(InlineKeyboardButton(text="📋 Все типы", callback_data=f"type_{nation_idx}_all"))
    keyboard.add(InlineKeyboardButton(text="Назад", callback_data="tanks_by_nation"))

    await callback.message.edit_text(
        f"🇺🇳 {nation}\n\n🔰 Выберите класс танка:",
        parse_mode="HTML",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()

@user.callback_query(F.data.startswith("type_"))
async def process_tank_type_choice(callback: CallbackQuery, state: FSMContext):
    # callback_data: type_{nation_idx}_{type_idx} или type_{nation_idx}_all
    parts = callback.data.split('_', 2)
    if len(parts) < 3:
        await callback.answer("❌ Ошибка формата данных")
        return

    _, nation_idx_str, type_part = parts
    try:
        nation_idx = int(nation_idx_str)
    except ValueError:
        await callback.answer("❌ Ошибка формата данных")
        return

    data = await state.get_data()
    nations = data.get('nations', [])
    tank_types = data.get('tank_types', [])

    if not nations or not (0 <= nation_idx < len(nations)):
        await callback.answer("❌ Нация не найдена")
        return

    nation = nations[nation_idx]
    all_tanks = await get_tanks_by_nation(nation)

    if type_part == 'all':
        filtered_tanks = all_tanks
        type_label = 'всех типов'
        selected_type = None
    else:
        try:
            type_idx = int(type_part)
        except ValueError:
            await callback.answer("❌ Ошибка формата данных")
            return

        if not tank_types or not (0 <= type_idx < len(tank_types)):
            await callback.answer("❌ Тип не найден")
            return

        selected_type = tank_types[type_idx]
        filtered_tanks = [t for t in all_tanks if t.tank_type == selected_type]
        type_label = selected_type

    if not filtered_tanks:
        await callback.answer("🚫 Нет танков по выбранному фильтру")
        return

    await state.update_data(
        selected_nation=nation,
        selected_tank_type=selected_type,
        tanks=filtered_tanks,
        current_page=0
    )

    # ✅ ИСПРАВЛЕНО: Кнопка "Назад" теперь ведет на выбор типа
    await show_tanks_list(callback.message, filtered_tanks, nation, f"nation_{nation_idx}", type_label)
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
@user.callback_query(F.data == "show_tank_details")
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
@user.message(TankStates.waiting_tank_number)
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
@user.callback_query(F.data == "tanks_by_year")
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
@user.callback_query(F.data.startswith("year_"))
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
@user.callback_query(F.data.startswith("yearview_"))
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
@user.callback_query(F.data.startswith("yeartype_"))
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
@user.callback_query(F.data == "show_tank_details_year")
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
@user.message(F.text == "Добавить танк")
@user.message(Command('add_tank'))
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


@user.message(TankStates.waiting_tank_name)
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


@user.message(TankStates.waiting_tank_nation)
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


@user.message(TankStates.waiting_tank_type)
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


@user.message(TankStates.waiting_tank_years)
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


@user.message(TankStates.waiting_tank_description)
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


@user.message(TankStates.waiting_tank_image, F.photo)
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


@user.message(TankStates.waiting_tank_image)
async def process_tank_image_invalid(message: Message):
    await message.answer("⚠️ Пожалуйста, отправьте фотографию танка:")


# Изменить танк
@user.message(F.text == "Изменить танк")
@user.message(Command('edit_tank'))
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

@user.message(TankStates.waiting_tank_to_edit)
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

@user.message(TankStates.waiting_edit_choice)
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
@user.message(TankStates.waiting_new_name)
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
@user.message(TankStates.waiting_new_nation)
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
@user.message(TankStates.waiting_new_type)
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
@user.message(TankStates.waiting_new_years)
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
@user.message(TankStates.waiting_new_description)
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
@user.message(TankStates.waiting_new_image, F.photo)
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

@user.message(TankStates.waiting_new_image)
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
@user.message(F.text == "Удалить танк")
@user.message(Command('delete_tank'))
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
@user.message(TankStates.waiting_tank_to_delete)
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
@user.callback_query(F.data == "confirm_delete", TankStates.waiting_delete_confirmation)
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
        if callback.message.caption:
            await callback.message.edit_caption(
                caption=f"✅ <b>Танк успешно удален!</b>\n\n"
                       f"🎖️ {tank.name} ({tank.nation})\n"
                       f"🆔 ID: {tank.id}",
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                text=f"✅ <b>Танк успешно удален!</b>\n\n"
                    f"🎖️ {tank.name} ({tank.nation})\n"
                    f"🆔 ID: {tank.id}",
                parse_mode="HTML"
            )
    else:
        if callback.message.caption:
            await callback.message.edit_caption(
                caption="❌ <b>Не удалось удалить танк.</b>\n"
                       "Попробуйте снова или обратитесь к администратору.",
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                text="❌ <b>Не удалось удалить танк.</b>\n"
                    "Попробуйте снова или обратитесь к администратору.",
                parse_mode="HTML"
            )
    
    await state.clear()
    await callback.answer()


# Обработка отмены удаления
@user.callback_query(F.data == "cancel_delete")
async def cancel_delete_tank(callback: CallbackQuery, state: FSMContext):
    if callback.message.caption:
        await callback.message.edit_caption(
            caption="❌ <b>Удаление отменено.</b>",
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            text="❌ <b>Удаление отменено.</b>",
            parse_mode="HTML"
        )
    await state.clear()
    await callback.answer()