"""Поиск техники по названию или ID.

Одноимённых танков в базе много (StuG III G, Renault FT, Т-34-85 …), поэтому
поиск всегда показывает все совпадения вместе с нацией и даёт выбрать нужный.
"""

from html import escape

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.requests import get_tank_by_id, get_tank_years, search_tanks_by_name
from keyboards import is_menu_input

search_router = Router(name="search")

SEARCH_BUTTON = "🔍 Поиск"
MAX_RESULTS = 25
MAX_CARD_LEN = 3900  # запас до лимита Telegram в 4096 символов
CANCEL_WORDS = {"отмена", "отменить", "стоп", "cancel", "выход"}

PROMPT = (
    "🔍 <b>Поиск техники</b>\n\n"
    "Введите <b>название танка</b> или его <b>ID</b>.\n"
    "<i>Например: Т-34-85 или 42</i>\n\n"
    "<i>Чтобы выйти из поиска — напишите «отмена».</i>"
)


class SearchStates(StatesGroup):
    waiting_query = State()


# ── Клавиатуры и тексты ──────────────────────────────────────────────────────

def _cancel_keyboard():
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="❌ Отмена", callback_data="srch_cancel"))
    return kb.as_markup()


def _results_keyboard(items: list):
    kb = InlineKeyboardBuilder()
    for i, item in enumerate(items, 1):
        title = f"{i}) {item['name']} ({item['nation']})"
        if len(title) > 60:
            title = title[:57] + "..."
        kb.add(InlineKeyboardButton(text=title, callback_data=f"srch_t_{item['id']}"))
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text="🔍 Новый поиск", callback_data="srch_new_0"))
    return kb.as_markup()


def _results_text(query: str, items: list, total: int) -> str:
    lines = [f"🔍 <b>По запросу «{escape(query)}» найдено:</b> {total}", ""]
    for i, item in enumerate(items, 1):
        lines.append(f"{i}) <b>{escape(item['name'])}</b> ({escape(item['nation'])})")
    if total > len(items):
        lines.append(f"\n<i>Показаны первые {len(items)}. Уточните запрос.</i>")
    lines.append("\n👇 Выберите танк кнопкой ниже.")
    return "\n".join(lines)


def _card_keyboard(photo_msg_id: int):
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data=f"srch_back_{photo_msg_id}"),
        InlineKeyboardButton(text="🔍 Новый поиск", callback_data=f"srch_new_{photo_msg_id}"),
    )
    return kb.as_markup()


async def _tank_card_text(tank) -> str:
    years = await get_tank_years(tank.id)
    years_str = ", ".join(map(str, years)) if years else "Не указаны"

    card = (
        f"🎖️ <b>{escape(tank.name)}</b>\n\n"
        f"🇺🇳 <b>Нация:</b> {escape(tank.nation)}\n"
        f"🔰 <b>Тип:</b> {escape(tank.tank_type or 'Не указан')}\n"
        f"📅 <b>Годы:</b> {years_str}\n"
        f"🆔 <b>ID:</b> {tank.id}\n\n"
        f"📝 <b>Описание:</b>\n{escape(tank.discript or 'Нет описания')}"
    )
    if len(card) > MAX_CARD_LEN:
        card = card[:MAX_CARD_LEN] + "…"
    return card


async def _send_photo(message: Message, tank) -> int:
    """Отправляет фото танка отдельным сообщением, возвращает его message_id."""
    if not tank.photo_id:
        return 0
    try:
        sent = await message.answer_photo(photo=tank.photo_id)
        return sent.message_id
    except Exception:
        return 0


async def _delete_message(message: Message, message_id: int):
    if not message_id:
        return
    try:
        await message.bot.delete_message(chat_id=message.chat.id, message_id=message_id)
    except Exception:
        pass


async def _find_tanks(query: str) -> list:
    """Сначала пробуем ID, затем название. Дубликаты не повторяются."""
    found = []
    if query.isdigit():
        tank = await get_tank_by_id(int(query))
        if tank:
            found.append(tank)

    for tank in await search_tanks_by_name(query):
        if all(tank.id != other.id for other in found):
            found.append(tank)

    return found


# ── Вход в поиск ─────────────────────────────────────────────────────────────

@search_router.message(F.text == SEARCH_BUTTON)
@search_router.message(Command("search"))
async def search_entry(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(SearchStates.waiting_query)
    await message.answer(PROMPT, parse_mode="HTML", reply_markup=_cancel_keyboard())


# ── Обработка запроса ────────────────────────────────────────────────────────

@search_router.message(SearchStates.waiting_query)
async def process_search_query(message: Message, state: FSMContext):
    text = (message.text or "").strip()

    if not text:
        await message.answer(
            "⚠️ Отправьте <b>текстом</b> название танка или его ID.",
            parse_mode="HTML",
        )
        return

    # Команда или кнопка меню — выходим из поиска и отдаём событие дальше
    if is_menu_input(text):
        await state.clear()
        raise SkipHandler()

    if text.lower() in CANCEL_WORDS:
        await state.clear()
        await message.answer("❌ Поиск закрыт.")
        return

    tanks = await _find_tanks(text)

    if not tanks:
        await message.answer(
            f"🚫 По запросу «{escape(text)}» ничего не найдено.\n"
            "Проверьте название или введите ID танка.",
            parse_mode="HTML",
            reply_markup=_cancel_keyboard(),
        )
        return

    items = [{"id": t.id, "name": t.name, "nation": t.nation} for t in tanks]
    shown = items[:MAX_RESULTS]
    await state.update_data(
        search_query=text,
        search_results=shown,
        search_total=len(items),
    )

    # Единственное совпадение — сразу карточка танка
    if len(tanks) == 1:
        tank = tanks[0]
        photo_msg_id = await _send_photo(message, tank)
        await message.answer(
            await _tank_card_text(tank),
            parse_mode="HTML",
            reply_markup=_card_keyboard(photo_msg_id),
        )
        return

    await message.answer(
        _results_text(text, shown, len(items)),
        parse_mode="HTML",
        reply_markup=_results_keyboard(shown),
    )


# ── Выбор танка из списка ────────────────────────────────────────────────────

@search_router.callback_query(F.data.startswith("srch_t_"))
async def show_found_tank(callback: CallbackQuery, state: FSMContext):
    try:
        tank_id = int(callback.data.rsplit("_", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка формата данных")
        return

    tank = await get_tank_by_id(tank_id)
    if not tank:
        await callback.answer("❌ Танк не найден", show_alert=True)
        return

    photo_msg_id = await _send_photo(callback.message, tank)

    await callback.message.edit_text(
        await _tank_card_text(tank),
        parse_mode="HTML",
        reply_markup=_card_keyboard(photo_msg_id),
    )
    await callback.answer()


# ── Назад: карточка → список результатов ─────────────────────────────────────

@search_router.callback_query(F.data.startswith("srch_back_"))
async def back_to_results(callback: CallbackQuery, state: FSMContext):
    try:
        photo_msg_id = int(callback.data.rsplit("_", 1)[1])
    except (ValueError, IndexError):
        photo_msg_id = 0

    await _delete_message(callback.message, photo_msg_id)

    data = await state.get_data()
    items = data.get("search_results") or []
    query = data.get("search_query") or ""
    total = data.get("search_total", len(items))

    await state.set_state(SearchStates.waiting_query)

    if len(items) > 1:
        await callback.message.edit_text(
            _results_text(query, items, total),
            parse_mode="HTML",
            reply_markup=_results_keyboard(items),
        )
    else:
        # Список не из чего восстановить (один результат или бот перезапускался)
        await callback.message.edit_text(
            PROMPT, parse_mode="HTML", reply_markup=_cancel_keyboard()
        )

    await callback.answer()


# ── Новый поиск ──────────────────────────────────────────────────────────────

@search_router.callback_query(F.data.startswith("srch_new_"))
async def new_search(callback: CallbackQuery, state: FSMContext):
    try:
        photo_msg_id = int(callback.data.rsplit("_", 1)[1])
    except (ValueError, IndexError):
        photo_msg_id = 0

    await _delete_message(callback.message, photo_msg_id)

    await state.update_data(search_query="", search_results=[], search_total=0)
    await state.set_state(SearchStates.waiting_query)

    await callback.message.edit_text(
        PROMPT, parse_mode="HTML", reply_markup=_cancel_keyboard()
    )
    await callback.answer()


# ── Отмена ───────────────────────────────────────────────────────────────────

@search_router.callback_query(F.data == "srch_cancel")
async def cancel_search(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Поиск закрыт.")
    await callback.answer()
