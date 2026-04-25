from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ContentType, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards import adminboard
from database.requests import get_user, create_battle, get_all_fronts, get_battles_by_front, get_battle_by_id, delete_battle

admin_battles = Router()


class CreateBattle(StatesGroup):
    name = State()
    front = State()
    date_str = State()
    map_photo = State()
    description = State()
    equipment_text = State()


class EditBattle(StatesGroup):
    choose_front = State()
    choose_battle = State()
    choose_field = State()
    new_name = State()
    new_front = State()
    new_date = State()
    new_map = State()
    new_description = State()
    new_equipment = State()


class DeleteBattle(StatesGroup):
    choose_front = State()
    choose_battle = State()
    confirm = State()


# ── Start ────────────────────────────────────────────────────────────────────

@admin_battles.message(F.text == "Добавить сражение")
async def start_create_battle(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user or user.status != "admin":
        await message.answer("Отказано в правах доступа")
        return

    await message.answer(
        "⚔️ <b>Создание нового сражения</b>\n\n"
        "Шаг 1/6: Введите название сражения:",
        parse_mode="HTML",
    )
    await state.set_state(CreateBattle.name)


# ── Step 1: Name ─────────────────────────────────────────────────────────────

@admin_battles.message(CreateBattle.name)
async def get_battle_name(message: Message, state: FSMContext):
    if len(message.text.strip()) < 3:
        await message.answer("Название слишком короткое. Введите не менее 3 символов:")
        return

    await state.update_data(name=message.text.strip())
    await message.answer(
        "✅ Название сохранено!\n\n"
        "Шаг 2/6: Введите название фронта\n"
        "(например: Восточный фронт, Западный фронт):"
    )
    await state.set_state(CreateBattle.front)


# ── Step 2: Front ─────────────────────────────────────────────────────────────

@admin_battles.message(CreateBattle.front)
async def get_battle_front(message: Message, state: FSMContext):
    if len(message.text.strip()) < 2:
        await message.answer("Слишком короткое. Введите название фронта:")
        return

    await state.update_data(front=message.text.strip())
    await message.answer(
        "✅ Фронт сохранён!\n\n"
        "Шаг 3/6: Введите дату сражения\n"
        "(например: 30.09.1941 – 20.04.1942):"
    )
    await state.set_state(CreateBattle.date_str)


# ── Step 3: Date ──────────────────────────────────────────────────────────────

@admin_battles.message(CreateBattle.date_str)
async def get_battle_date(message: Message, state: FSMContext):
    if len(message.text.strip()) < 2:
        await message.answer("Введите дату сражения:")
        return

    await state.update_data(date_str=message.text.strip())
    await message.answer(
        "✅ Дата сохранена!\n\n"
        "Шаг 4/6: Отправьте карту сражения (фото):"
    )
    await state.set_state(CreateBattle.map_photo)


# ── Step 4: Map photo ─────────────────────────────────────────────────────────

@admin_battles.message(CreateBattle.map_photo, F.content_type == ContentType.PHOTO)
async def get_battle_map(message: Message, state: FSMContext):
    photo = message.photo[-1]
    await state.update_data(map_photo_id=photo.file_id)
    await message.answer(
        "✅ Карта сохранена!\n\n"
        "Шаг 5/6: Введите описание сражения (история, план боя и т.д.):"
    )
    await state.set_state(CreateBattle.description)


@admin_battles.message(CreateBattle.map_photo)
async def wrong_map_format(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, отправьте именно фото (карту сражения):")


# ── Step 5: Description ───────────────────────────────────────────────────────

@admin_battles.message(CreateBattle.description)
async def get_battle_description(message: Message, state: FSMContext):
    if len(message.text.strip()) < 5:
        await message.answer("Описание слишком короткое. Введите подробнее:")
        return

    await state.update_data(description=message.text.strip())
    await message.answer(
        "✅ Описание сохранено!\n\n"
        "Шаг 6/6: Введите список техники, участвовавшей в сражении:"
    )
    await state.set_state(CreateBattle.equipment_text)


# ── Step 6: Equipment ─────────────────────────────────────────────────────────

@admin_battles.message(CreateBattle.equipment_text)
async def get_battle_equipment(message: Message, state: FSMContext):
    if len(message.text.strip()) < 2:
        await message.answer("Введите список техники:")
        return

    data = await state.get_data()
    equipment_text = message.text.strip()

    success = await create_battle(
        name=data["name"],
        front=data["front"],
        date_str=data["date_str"],
        description=data["description"],
        map_photo_id=data.get("map_photo_id"),
        equipment_text=equipment_text,
    )

    await state.clear()

    if success:
        await message.answer(
            f"✅ <b>Сражение добавлено!</b>\n\n"
            f"⚔️ <b>Название:</b> {data['name']}\n"
            f"🗺️ <b>Фронт:</b> {data['front']}\n"
            f"📅 <b>Дата:</b> {data['date_str']}\n"
            f"📝 Описание: сохранено\n"
            f"⚙️ Техника: сохранена",
            parse_mode="HTML",
            reply_markup=adminboard,
        )
    else:
        await message.answer(
            "❌ Ошибка при сохранении. Попробуйте ещё раз.",
            reply_markup=adminboard,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# УДАЛИТЬ СРАЖЕНИЕ
# ═══════════════════════════════════════════════════════════════════════════════

async def _send_fronts_list(message: Message, state: FSMContext, next_state):
    fronts = await get_all_fronts()
    if not fronts:
        await message.answer("⚔️ Сражений в базе нет.", reply_markup=adminboard)
        await state.clear()
        return False
    text = "🗺️ <b>Выберите фронт (введите номер):</b>\n\n"
    for i, f in enumerate(fronts, 1):
        text += f"{i}. {f}\n"
    await state.update_data(fronts=fronts)
    await message.answer(text, parse_mode="HTML")
    await state.set_state(next_state)
    return True


async def _send_battles_list(message: Message, state: FSMContext, front: str, next_state):
    battles = await get_battles_by_front(front)
    if not battles:
        await message.answer("🚫 В этом фронте нет сражений.", reply_markup=adminboard)
        await state.clear()
        return False
    text = f"⚔️ <b>{front}</b>\n\nВыберите сражение (введите номер):\n\n"
    for i, b in enumerate(battles, 1):
        text += f"{i}. {b.name} ({b.date_str})\n"
    await state.update_data(battles=[b.id for b in battles], battle_names=[b.name for b in battles])
    await message.answer(text, parse_mode="HTML")
    await state.set_state(next_state)
    return True


# ── Удалить: старт ────────────────────────────────────────────────────────────

@admin_battles.message(F.text == "Удалить сражение")
async def start_delete_battle(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user or user.status != "admin":
        await message.answer("Отказано в правах доступа")
        return
    await _send_fronts_list(message, state, DeleteBattle.choose_front)


@admin_battles.message(DeleteBattle.choose_front)
async def delete_choose_front(message: Message, state: FSMContext):
    data = await state.get_data()
    fronts = data.get("fronts", [])
    try:
        idx = int(message.text.strip()) - 1
        assert 0 <= idx < len(fronts)
    except (ValueError, AssertionError):
        await message.answer(f"Введите номер от 1 до {len(fronts)}:")
        return
    front = fronts[idx]
    await state.update_data(selected_front=front)
    await _send_battles_list(message, state, front, DeleteBattle.choose_battle)


@admin_battles.message(DeleteBattle.choose_battle)
async def delete_choose_battle(message: Message, state: FSMContext):
    data = await state.get_data()
    battle_ids = data.get("battles", [])
    battle_names = data.get("battle_names", [])
    try:
        idx = int(message.text.strip()) - 1
        assert 0 <= idx < len(battle_ids)
    except (ValueError, AssertionError):
        await message.answer(f"Введите номер от 1 до {len(battle_ids)}:")
        return

    battle_id = battle_ids[idx]
    name = battle_names[idx]
    await state.update_data(target_battle_id=battle_id, target_battle_name=name)

    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"del_battle_yes_{battle_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="del_battle_no"),
    )
    await message.answer(
        f"⚠️ Удалить сражение <b>«{name}»</b>? Это действие необратимо.",
        parse_mode="HTML",
        reply_markup=kb.as_markup(),
    )
    await state.set_state(DeleteBattle.confirm)


@admin_battles.callback_query(F.data.startswith("del_battle_yes_"))
async def confirm_delete_battle(callback: CallbackQuery, state: FSMContext):
    battle_id = int(callback.data.split("_")[-1])
    success = await delete_battle(battle_id)
    data = await state.get_data()
    name = data.get("target_battle_name", "")
    await state.clear()
    if success:
        await callback.message.edit_text(f"✅ Сражение <b>«{name}»</b> удалено.", parse_mode="HTML")
    else:
        await callback.message.edit_text("❌ Ошибка при удалении.")
    await callback.answer()


@admin_battles.callback_query(F.data == "del_battle_no")
async def cancel_delete_battle(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Удаление отменено.")
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ИЗМЕНИТЬ СРАЖЕНИЕ
# ═══════════════════════════════════════════════════════════════════════════════

_EDIT_FIELDS = {
    "1": "название",
    "2": "фронт",
    "3": "дату",
    "4": "карту",
    "5": "описание",
    "6": "технику",
}


@admin_battles.message(F.text == "Изменить сражение")
async def start_edit_battle(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user or user.status != "admin":
        await message.answer("Отказано в правах доступа")
        return
    await _send_fronts_list(message, state, EditBattle.choose_front)


@admin_battles.message(EditBattle.choose_front)
async def edit_choose_front(message: Message, state: FSMContext):
    data = await state.get_data()
    fronts = data.get("fronts", [])
    try:
        idx = int(message.text.strip()) - 1
        assert 0 <= idx < len(fronts)
    except (ValueError, AssertionError):
        await message.answer(f"Введите номер от 1 до {len(fronts)}:")
        return
    front = fronts[idx]
    await state.update_data(selected_front=front)
    await _send_battles_list(message, state, front, EditBattle.choose_battle)


@admin_battles.message(EditBattle.choose_battle)
async def edit_choose_battle(message: Message, state: FSMContext):
    data = await state.get_data()
    battle_ids = data.get("battles", [])
    battle_names = data.get("battle_names", [])
    try:
        idx = int(message.text.strip()) - 1
        assert 0 <= idx < len(battle_ids)
    except (ValueError, AssertionError):
        await message.answer(f"Введите номер от 1 до {len(battle_ids)}:")
        return

    await state.update_data(target_battle_id=battle_ids[idx], target_battle_name=battle_names[idx])
    await message.answer(
        f"✏️ <b>Сражение: {battle_names[idx]}</b>\n\n"
        "Что изменить?\n"
        "1 — Название\n"
        "2 — Фронт\n"
        "3 — Дату\n"
        "4 — Карту (фото)\n"
        "5 — Описание\n"
        "6 — Технику",
        parse_mode="HTML",
    )
    await state.set_state(EditBattle.choose_field)


@admin_battles.message(EditBattle.choose_field)
async def edit_choose_field(message: Message, state: FSMContext):
    choice = message.text.strip()
    if choice not in _EDIT_FIELDS:
        await message.answer("Введите цифру от 1 до 6:")
        return
    await state.update_data(edit_field=choice)
    prompts = {
        "1": "Введите новое название:",
        "2": "Введите новый фронт:",
        "3": "Введите новую дату:",
        "4": "Отправьте новую карту (фото):",
        "5": "Введите новое описание:",
        "6": "Введите новый список техники:",
    }
    next_states = {
        "1": EditBattle.new_name,
        "2": EditBattle.new_front,
        "3": EditBattle.new_date,
        "4": EditBattle.new_map,
        "5": EditBattle.new_description,
        "6": EditBattle.new_equipment,
    }
    await message.answer(prompts[choice])
    await state.set_state(next_states[choice])


async def _apply_edit(message: Message, state: FSMContext, **kwargs):
    data = await state.get_data()
    battle_id = data["target_battle_id"]
    name = data["target_battle_name"]

    from database.requests import async_session
    from database.models import Battle
    from sqlalchemy import select

    async with async_session() as session:
        battle = await session.scalar(select(Battle).where(Battle.id == battle_id))
        if not battle:
            await message.answer("❌ Сражение не найдено.", reply_markup=adminboard)
            await state.clear()
            return
        for field, value in kwargs.items():
            setattr(battle, field, value)
        await session.commit()

    await state.clear()
    await message.answer(
        f"✅ Сражение <b>«{name}»</b> обновлено.",
        parse_mode="HTML",
        reply_markup=adminboard,
    )


@admin_battles.message(EditBattle.new_name)
async def edit_new_name(message: Message, state: FSMContext):
    if len(message.text.strip()) < 3:
        await message.answer("Слишком короткое. Введите название:")
        return
    await _apply_edit(message, state, name=message.text.strip())


@admin_battles.message(EditBattle.new_front)
async def edit_new_front(message: Message, state: FSMContext):
    if len(message.text.strip()) < 2:
        await message.answer("Введите название фронта:")
        return
    await _apply_edit(message, state, front=message.text.strip())


@admin_battles.message(EditBattle.new_date)
async def edit_new_date(message: Message, state: FSMContext):
    if len(message.text.strip()) < 2:
        await message.answer("Введите дату:")
        return
    await _apply_edit(message, state, date_str=message.text.strip())


@admin_battles.message(EditBattle.new_map, F.content_type == ContentType.PHOTO)
async def edit_new_map(message: Message, state: FSMContext):
    await _apply_edit(message, state, map_photo_id=message.photo[-1].file_id)


@admin_battles.message(EditBattle.new_map)
async def edit_new_map_wrong(message: Message):
    await message.answer("Пожалуйста, отправьте фото (карту):")


@admin_battles.message(EditBattle.new_description)
async def edit_new_description(message: Message, state: FSMContext):
    if len(message.text.strip()) < 5:
        await message.answer("Слишком короткое. Введите описание:")
        return
    await _apply_edit(message, state, description=message.text.strip())


@admin_battles.message(EditBattle.new_equipment)
async def edit_new_equipment(message: Message, state: FSMContext):
    if len(message.text.strip()) < 2:
        await message.answer("Введите список техники:")
        return
    await _apply_edit(message, state, equipment_text=message.text.strip())
