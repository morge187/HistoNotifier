from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.requests import get_all_fronts, get_battles_by_front, get_battle_by_id

battles_router = Router()


# -- Keyboards ----------------------------------------------------------------

def _fronts_keyboard(fronts: list):
    kb = InlineKeyboardBuilder()
    for i, front in enumerate(fronts):
        kb.add(InlineKeyboardButton(text=f"⚔️ {front}", callback_data=f"bfront_{i}"))
    kb.adjust(1)
    return kb.as_markup()


def _battles_keyboard(battles: list, front_idx: int):
    kb = InlineKeyboardBuilder()
    for battle in battles:
        kb.add(InlineKeyboardButton(text=f"🔹 {battle.name}", callback_data=f"bitem_{battle.id}"))
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data=f"bback_{front_idx}"))
    return kb.as_markup()


# -- Entry point --------------------------------------------------------------

@battles_router.message(F.text == "Список сражений")
async def show_battles_entry(message: Message):
    fronts = await get_all_fronts()
    if not fronts:
        await message.answer("⚔️ Список сражений пока пуст.")
        return
    await message.answer(
        "⚔️ <b>Список сражений</b>\n\nВыберите фронт:",
        parse_mode="HTML",
        reply_markup=_fronts_keyboard(fronts),
    )


# -- Front selected -> list of battles ----------------------------------------

@battles_router.callback_query(F.data.startswith("bfront_"))
async def show_front_battles(callback: CallbackQuery):
    try:
        front_idx = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка формата данных")
        return

    fronts = await get_all_fronts()
    if not fronts or not (0 <= front_idx < len(fronts)):
        await callback.answer("❌ Фронт не найден")
        return

    front = fronts[front_idx]
    battles = await get_battles_by_front(front)
    if not battles:
        await callback.answer("🚫 Нет сражений для этого фронта", show_alert=True)
        return

    await callback.message.edit_text(
        f"⚔️ <b>{front}</b>\n\nВыберите сражение:",
        parse_mode="HTML",
        reply_markup=_battles_keyboard(battles, front_idx),
    )
    await callback.answer()


# -- Back button: battle list -> fronts (or specific front) -------------------

@battles_router.callback_query(F.data.startswith("bback_"))
async def back_handler(callback: CallbackQuery):
    parts = callback.data.split("_")
    try:
        front_idx = int(parts[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка формата данных")
        return

    # Delete photo if its message_id was encoded in callback_data
    if len(parts) >= 3:
        try:
            photo_msg_id = int(parts[2])
            if photo_msg_id:
                await callback.bot.delete_message(
                    chat_id=callback.message.chat.id,
                    message_id=photo_msg_id,
                )
        except Exception:
            pass

    fronts = await get_all_fronts()
    if not fronts:
        await callback.message.edit_text("⚔️ Список сражений пока пуст.")
        await callback.answer()
        return

    if len(parts) >= 3 and 0 <= front_idx < len(fronts):
        # came from battle detail → go back to battles list
        front = fronts[front_idx]
        battles = await get_battles_by_front(front)
        await callback.message.edit_text(
            f"⚔️ <b>{front}</b>\n\nВыберите сражение:",
            parse_mode="HTML",
            reply_markup=_battles_keyboard(battles, front_idx),
        )
    else:
        # came from battles list → go back to fronts
        await callback.message.edit_text(
            "⚔️ <b>Список сражений</b>\n\nВыберите фронт:",
            parse_mode="HTML",
            reply_markup=_fronts_keyboard(fronts),
        )
    await callback.answer()


# -- Battle selected -> detail ------------------------------------------------

@battles_router.callback_query(F.data.startswith("bitem_"))
async def show_battle_detail(callback: CallbackQuery):
    try:
        battle_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка формата данных")
        return

    battle = await get_battle_by_id(battle_id)
    if not battle:
        await callback.answer("❌ Сражение не найдено")
        return

    fronts = await get_all_fronts()
    try:
        front_idx = fronts.index(battle.front)
    except ValueError:
        front_idx = 0

    detail_text = (
        f"⚔️ <b>{battle.name}</b>\n\n"
        f"🗺️ <b>Фронт:</b> {battle.front}\n"
        f"📅 <b>Дата:</b> {battle.date_str}\n\n"
        f"📝 <b>Описание:</b>\n{battle.description}"
    )

    photo_msg_id = 0
    if battle.map_photo_id:
        sent = await callback.message.answer_photo(photo=battle.map_photo_id)
        photo_msg_id = sent.message_id

    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data=f"bback_{front_idx}_{photo_msg_id}"),
        InlineKeyboardButton(text="⚙️ Список техники", callback_data=f"bequip_{battle.id}"),
    )

    await callback.message.edit_text(
        detail_text,
        parse_mode="HTML",
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


# -- Equipment ----------------------------------------------------------------

@battles_router.callback_query(F.data.startswith("bequip_"))
async def show_battle_equipment(callback: CallbackQuery):
    try:
        battle_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка формата данных")
        return

    battle = await get_battle_by_id(battle_id)
    if not battle:
        await callback.answer("❌ Сражение не найдено")
        return

    if not battle.equipment_text:
        await callback.answer("⚠️ Список техники не указан", show_alert=True)
        return

    await callback.message.answer(
        f"⚙️ <b>Техника в сражении «{battle.name}»</b>\n\n{battle.equipment_text}",
        parse_mode="HTML",
    )
    await callback.answer()