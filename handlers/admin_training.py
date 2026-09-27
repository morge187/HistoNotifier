"""Конструктор тестов: создание, изменение, удаление (только админ)."""
from aiogram import Router, F
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.requests import is_admin
from database.training import (
    MAX_QUESTIONS, add_question, create_test, delete_question, delete_test, get_question,
    get_questions, get_test, get_tests_with_counts, update_question, update_test,
)
from utils import fmt_cost, parse_amount, parse_options

admin_training = Router()

TESTS_ADMIN_BUTTON = "Тесты ⚙️"


class ATestCb(CallbackData, prefix="atest"):
    # create | edit_list | delete_list | edit | delete | delete_yes | cancel
    # | title | cost | questions | add_q | del_q_list
    action: str
    test_id: int = 0


class AQuestionCb(CallbackData, prefix="aq"):
    action: str  # edit | delete
    question_id: int
    test_id: int


class ACorrectCb(CallbackData, prefix="acorr"):
    option: int


class ATestStates(StatesGroup):
    title = State()
    cost = State()
    count = State()
    q_text = State()
    q_options = State()
    q_correct = State()
    new_title = State()
    new_cost = State()


async def admin_only(event, state: FSMContext = None) -> bool:
    """True — можно продолжать; иначе сообщает об отказе и сбрасывает состояние."""
    if await is_admin(event.from_user.id):
        return True
    if state:
        await state.clear()
    if isinstance(event, CallbackQuery):
        await event.answer("Доступно только администратору.", show_alert=True)
    else:
        await event.answer("Доступно только администратору.")
    return False


def kb_main():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Создать", callback_data=ATestCb(action="create").pack())
    kb.button(text="✏️ Изменить", callback_data=ATestCb(action="edit_list").pack())
    kb.button(text="🗑 Удалить", callback_data=ATestCb(action="delete_list").pack())
    kb.adjust(3)
    return kb.as_markup()


async def send_test_menu(message: Message, test_id: int):
    test = await get_test(test_id)
    if not test:
        await message.answer("❌ Тест не найден.")
        return
    count = len(await get_questions(test_id))
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Название", callback_data=ATestCb(action="title", test_id=test_id).pack())
    kb.button(text="💰 Стоимость", callback_data=ATestCb(action="cost", test_id=test_id).pack())
    kb.button(text="📝 Изменить вопрос", callback_data=ATestCb(action="questions", test_id=test_id).pack())
    if count < MAX_QUESTIONS:
        kb.button(text="➕ Добавить вопрос", callback_data=ATestCb(action="add_q", test_id=test_id).pack())
    if count > 1:
        kb.button(text="➖ Удалить вопрос", callback_data=ATestCb(action="del_q_list", test_id=test_id).pack())
    kb.adjust(1)
    await message.answer(
        f"📘 {test.title}\nСтоимость: {fmt_cost(test.cost)}\nВопросов: {count}",
        reply_markup=kb.as_markup(),
    )


async def ask_question_text(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("mode") == "create":
        header = f"Вопрос {len(data['questions']) + 1}/{data['q_total']}"
    else:
        header = "Вопрос"
    await state.set_state(ATestStates.q_text)
    await message.answer(f"{header}: введите текст вопроса:")


# ---------- Entry ----------

@admin_training.message(F.text == TESTS_ADMIN_BUTTON)
async def tests_menu(message: Message, state: FSMContext):
    if not await admin_only(message, state):
        return
    await state.clear()
    await message.answer("⚙️ Управление тестами", reply_markup=kb_main())


# ---------- Create: название → стоимость → количество ----------

@admin_training.callback_query(ATestCb.filter(F.action == "create"))
async def create_start(callback: CallbackQuery, state: FSMContext):
    if not await admin_only(callback, state):
        return
    await state.clear()
    await state.set_state(ATestStates.title)
    await callback.message.answer("Введите название теста:")
    await callback.answer()


@admin_training.message(ATestStates.title)
async def create_title(message: Message, state: FSMContext):
    if not await admin_only(message, state):
        return
    title = (message.text or "").strip()
    if len(title) < 2:
        await message.answer("Название — минимум 2 символа. Введите ещё раз:")
        return
    await state.update_data(title=title)
    await state.set_state(ATestStates.cost)
    await message.answer("Стоимость попытки в кадрах (0 — бесплатно):")


@admin_training.message(ATestStates.cost)
async def create_cost(message: Message, state: FSMContext):
    if not await admin_only(message, state):
        return
    try:
        cost = parse_amount(message.text)
    except ValueError as e:
        await message.answer(f"⚠️ {e}")
        return
    await state.update_data(cost=cost)
    await state.set_state(ATestStates.count)
    await message.answer(f"Сколько вопросов? (1–{MAX_QUESTIONS})")


@admin_training.message(ATestStates.count)
async def create_count(message: Message, state: FSMContext):
    if not await admin_only(message, state):
        return
    try:
        total = int((message.text or "").strip())
    except ValueError:
        total = 0
    if not 1 <= total <= MAX_QUESTIONS:
        await message.answer(f"Нужно число от 1 до {MAX_QUESTIONS}:")
        return
    await state.update_data(mode="create", q_total=total, questions=[])
    await ask_question_text(message, state)


# ---------- Вопрос: текст → 4 варианта → правильный (общее для create / edit_q / add_q) ----------

@admin_training.message(ATestStates.q_text)
async def got_q_text(message: Message, state: FSMContext):
    if not await admin_only(message, state):
        return
    text = (message.text or "").strip()
    if len(text) < 2:
        await message.answer("Текст вопроса — минимум 2 символа. Введите ещё раз:")
        return
    await state.update_data(cur_text=text)
    await state.set_state(ATestStates.q_options)
    await message.answer("Отправьте 4 варианта ответа одним сообщением — каждый с новой строки:")


@admin_training.message(ATestStates.q_options)
async def got_q_options(message: Message, state: FSMContext):
    if not await admin_only(message, state):
        return
    try:
        options = parse_options(message.text)
    except ValueError as e:
        await message.answer(f"⚠️ {e}")
        return
    await state.update_data(cur_options=options)
    await state.set_state(ATestStates.q_correct)
    kb = InlineKeyboardBuilder()
    for n in range(1, 5):
        kb.button(text=str(n), callback_data=ACorrectCb(option=n).pack())
    kb.adjust(4)
    listing = "\n".join(f"{n}. {opt}" for n, opt in enumerate(options, start=1))
    await message.answer(f"{listing}\n\nКакой вариант правильный?", reply_markup=kb.as_markup())


@admin_training.callback_query(ATestStates.q_correct, ACorrectCb.filter())
async def got_q_correct(callback: CallbackQuery, callback_data: ACorrectCb, state: FSMContext):
    if not await admin_only(callback, state):
        return
    data = await state.get_data()
    q = {"text": data["cur_text"], "options": data["cur_options"], "correct": callback_data.option}
    await callback.message.edit_text(f"{callback.message.text}\n\nПравильный: {callback_data.option}")
    await callback.answer()

    mode = data.get("mode")
    if mode == "create":
        questions = data["questions"] + [q]
        if len(questions) < data["q_total"]:
            await state.update_data(questions=questions)
            await ask_question_text(callback.message, state)
            return
        await create_test(data["title"], data["cost"], questions)
        await state.clear()
        await callback.message.answer(f"✅ Тест «{data['title']}» создан: {len(questions)} вопросов.")
        return

    if mode == "edit_q":
        ok = await update_question(data["question_id"], q)
        result = "✅ Вопрос обновлён." if ok else "❌ Вопрос не найден."
    else:  # add_q
        ok = await add_question(data["test_id"], q)
        result = "✅ Вопрос добавлен." if ok else f"❌ Не удалось добавить (максимум {MAX_QUESTIONS})."
    test_id = data["test_id"]
    await state.clear()
    await callback.message.answer(result)
    await send_test_menu(callback.message, test_id)


# ---------- Выбор теста для изменения / удаления ----------

@admin_training.callback_query(ATestCb.filter(F.action.in_({"edit_list", "delete_list"})))
async def pick_test(callback: CallbackQuery, callback_data: ATestCb, state: FSMContext):
    if not await admin_only(callback, state):
        return
    tests = await get_tests_with_counts()
    if not tests:
        await callback.answer("Тестов пока нет.", show_alert=True)
        return
    action = "edit" if callback_data.action == "edit_list" else "delete"
    kb = InlineKeyboardBuilder()
    for test, count in tests:
        kb.button(text=f"{test.title} ({count})", callback_data=ATestCb(action=action, test_id=test.id).pack())
    kb.adjust(1)
    await callback.message.answer("Выберите тест:", reply_markup=kb.as_markup())
    await callback.answer()


@admin_training.callback_query(ATestCb.filter(F.action == "edit"))
async def edit_menu(callback: CallbackQuery, callback_data: ATestCb, state: FSMContext):
    if not await admin_only(callback, state):
        return
    await state.clear()
    await send_test_menu(callback.message, callback_data.test_id)
    await callback.answer()


# ---------- Изменение названия / стоимости ----------

@admin_training.callback_query(ATestCb.filter(F.action.in_({"title", "cost"})))
async def edit_field_start(callback: CallbackQuery, callback_data: ATestCb, state: FSMContext):
    if not await admin_only(callback, state):
        return
    await state.clear()
    await state.update_data(test_id=callback_data.test_id)
    if callback_data.action == "title":
        await state.set_state(ATestStates.new_title)
        await callback.message.answer("Введите новое название:")
    else:
        await state.set_state(ATestStates.new_cost)
        await callback.message.answer("Введите новую стоимость в кадрах (0 — бесплатно):")
    await callback.answer()


@admin_training.message(ATestStates.new_title)
async def edit_title_apply(message: Message, state: FSMContext):
    if not await admin_only(message, state):
        return
    title = (message.text or "").strip()
    if len(title) < 2:
        await message.answer("Название — минимум 2 символа. Введите ещё раз:")
        return
    test_id = (await state.get_data())["test_id"]
    await state.clear()
    ok = await update_test(test_id, title=title)
    await message.answer("✅ Название обновлено." if ok else "❌ Тест не найден.")
    if ok:
        await send_test_menu(message, test_id)


@admin_training.message(ATestStates.new_cost)
async def edit_cost_apply(message: Message, state: FSMContext):
    if not await admin_only(message, state):
        return
    try:
        cost = parse_amount(message.text)
    except ValueError as e:
        await message.answer(f"⚠️ {e}")
        return
    test_id = (await state.get_data())["test_id"]
    await state.clear()
    ok = await update_test(test_id, cost=cost)
    await message.answer("✅ Стоимость обновлена." if ok else "❌ Тест не найден.")
    if ok:
        await send_test_menu(message, test_id)


# ---------- Вопросы: изменить / добавить / удалить ----------

@admin_training.callback_query(ATestCb.filter(F.action.in_({"questions", "del_q_list"})))
async def question_list(callback: CallbackQuery, callback_data: ATestCb, state: FSMContext):
    if not await admin_only(callback, state):
        return
    questions = await get_questions(callback_data.test_id)
    if not questions:
        await callback.answer("Вопросов нет.", show_alert=True)
        return
    action = "edit" if callback_data.action == "questions" else "delete"
    kb = InlineKeyboardBuilder()
    for i, q in enumerate(questions, start=1):
        kb.button(text=f"{i}. {q.text[:40]}",
                  callback_data=AQuestionCb(action=action, question_id=q.id, test_id=callback_data.test_id).pack())
    kb.adjust(1)
    prompt = "Какой вопрос изменить?" if action == "edit" else "Какой вопрос удалить?"
    await callback.message.answer(prompt, reply_markup=kb.as_markup())
    await callback.answer()


@admin_training.callback_query(AQuestionCb.filter(F.action == "edit"))
async def question_edit_start(callback: CallbackQuery, callback_data: AQuestionCb, state: FSMContext):
    if not await admin_only(callback, state):
        return
    q = await get_question(callback_data.question_id)
    if not q:
        await callback.answer("Вопрос не найден.", show_alert=True)
        return
    await state.clear()
    await state.update_data(mode="edit_q", question_id=q.id, test_id=callback_data.test_id)
    options = "\n".join(f"{n}. {opt}" for n, opt in enumerate([q.option_1, q.option_2, q.option_3, q.option_4], start=1))
    await callback.message.answer(f"Сейчас:\n{q.text}\n\n{options}\n\nПравильный: {q.correct}")
    await callback.answer()
    await ask_question_text(callback.message, state)


@admin_training.callback_query(AQuestionCb.filter(F.action == "delete"))
async def question_delete(callback: CallbackQuery, callback_data: AQuestionCb, state: FSMContext):
    if not await admin_only(callback, state):
        return
    if not await delete_question(callback_data.question_id):
        await callback.answer("Нельзя удалить последний вопрос.", show_alert=True)
        return
    await callback.answer("🗑 Вопрос удалён")
    await send_test_menu(callback.message, callback_data.test_id)


@admin_training.callback_query(ATestCb.filter(F.action == "add_q"))
async def question_add_start(callback: CallbackQuery, callback_data: ATestCb, state: FSMContext):
    if not await admin_only(callback, state):
        return
    await state.clear()
    await state.update_data(mode="add_q", test_id=callback_data.test_id)
    await callback.answer()
    await ask_question_text(callback.message, state)


# ---------- Удаление теста ----------

@admin_training.callback_query(ATestCb.filter(F.action == "delete"))
async def delete_confirm(callback: CallbackQuery, callback_data: ATestCb, state: FSMContext):
    if not await admin_only(callback, state):
        return
    test = await get_test(callback_data.test_id)
    if not test:
        await callback.answer("Тест не найден.", show_alert=True)
        return
    kb = InlineKeyboardBuilder()
    kb.button(text="Да, удалить", callback_data=ATestCb(action="delete_yes", test_id=test.id).pack())
    kb.button(text="Отмена", callback_data=ATestCb(action="cancel").pack())
    kb.adjust(2)
    await callback.message.answer(f"Удалить тест «{test.title}» вместе с вопросами и попытками?",
                                  reply_markup=kb.as_markup())
    await callback.answer()


@admin_training.callback_query(ATestCb.filter(F.action == "delete_yes"))
async def delete_apply(callback: CallbackQuery, callback_data: ATestCb, state: FSMContext):
    if not await admin_only(callback, state):
        return
    ok = await delete_test(callback_data.test_id)
    await callback.message.edit_text("🗑 Тест удалён." if ok else "❌ Тест не найден.")
    await callback.answer()


@admin_training.callback_query(ATestCb.filter(F.action == "cancel"))
async def delete_cancel(callback: CallbackQuery, state: FSMContext):
    if not await admin_only(callback, state):
        return
    await callback.message.edit_text("Отменено.")
    await callback.answer()
