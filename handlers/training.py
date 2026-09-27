"""Раздел «Обучение»: список тестов и прохождение."""
from datetime import datetime

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.requests import get_user
from database.training import (
    charge_points, get_questions, get_test, get_test_statuses, get_tests_with_counts,
    has_passed, last_failed_at, question_to_dict, record_attempt,
)
from utils import fmt_cost, fmt_duration, is_quiz_passed, start_decision

training_router = Router()

TRAINING_BUTTON = "Обучение"


class TrainCb(CallbackData, prefix="train"):
    action: str  # open | start
    test_id: int


class TrainAnswerCb(CallbackData, prefix="train_ans"):
    test_id: int
    index: int
    option: int


class TrainStates(StatesGroup):
    in_test = State()


def question_text(data: dict) -> str:
    i = data["tt_i"]
    q = data["tt_q"][i]
    options = "\n".join(f"{n}. {opt}" for n, opt in enumerate(q["options"], start=1))
    return f"❓ Вопрос {i + 1}/{len(data['tt_q'])}\n\n{q['text']}\n\n{options}"


async def send_question(message: Message, data: dict):
    kb = InlineKeyboardBuilder()
    for n in range(1, 5):
        kb.button(
            text=str(n),
            callback_data=TrainAnswerCb(test_id=data["tt_id"], index=data["tt_i"], option=n).pack(),
        )
    kb.adjust(4)
    await message.answer(question_text(data), reply_markup=kb.as_markup())


@training_router.message(F.text == TRAINING_BUTTON)
@training_router.message(Command("training"))
async def training_list(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    if not user or not user.name:
        await message.answer("Сначала зарегистрируйтесь с помощью /start")
        return

    tests = await get_tests_with_counts()
    if not tests:
        await message.answer("📚 Тестов пока нет.")
        return

    passed = {test_id: ok for test_id, _, ok in await get_test_statuses(user.id)}
    lines = ["📚 Обучение", ""]
    kb = InlineKeyboardBuilder()
    for i, (test, count) in enumerate(tests, start=1):
        mark = "🟢" if passed.get(test.id) else "🔴"
        lines.append(f"{i}. {test.title} — {count} вопросов — {fmt_cost(test.cost)} {mark}")
        kb.button(text=f"{i}. {test.title}", callback_data=TrainCb(action="open", test_id=test.id).pack())
    kb.adjust(1)
    await message.answer("\n".join(lines), reply_markup=kb.as_markup())


@training_router.callback_query(TrainCb.filter(F.action == "open"))
async def training_open(callback: CallbackQuery, callback_data: TrainCb):
    test = await get_test(callback_data.test_id)
    if not test:
        await callback.answer("Тест не найден.", show_alert=True)
        return
    count = len(await get_questions(test.id))
    kb = InlineKeyboardBuilder()
    kb.button(text="▶️ Начать", callback_data=TrainCb(action="start", test_id=test.id).pack())
    await callback.message.answer(
        f"📘 {test.title}\n\n"
        f"Вопросов: {count}\n"
        f"Стоимость попытки: {fmt_cost(test.cost)}\n"
        f"Для прохождения нужно 80% верных ответов.",
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@training_router.callback_query(TrainCb.filter(F.action == "start"))
async def training_start(callback: CallbackQuery, callback_data: TrainCb, state: FSMContext):
    # Лочим состояние ДО любых DB-обращений, чтобы повторный тап (или тап во
    # время уже идущего теста) не мог списать кадры второй раз.
    if await state.get_state() == TrainStates.in_test.state:
        await callback.answer("Сначала закончи текущий тест (или напиши «отмена»)", show_alert=True)
        return
    await state.set_state(TrainStates.in_test)

    # Всё до успешного старта теста — под защитой: если что-то из этого
    # (транзиентная ошибка БД и т.п.) выбросит исключение, лок обязательно
    # снимается, иначе пользователь застрянет с ложным «тест уже идёт».
    try:
        user = await get_user(callback.from_user.id)
        test = await get_test(callback_data.test_id)
        questions = await get_questions(callback_data.test_id) if test else []
        if not user or not test or not questions:
            await state.clear()
            await callback.answer("Тест не найден.", show_alert=True)
            return

        decision, left = start_decision(
            await has_passed(user.id, test.id),
            await last_failed_at(user.id, test.id),
            user.points, test.cost, datetime.now(),
        )
        if decision == "passed":
            await state.clear()
            await callback.answer("✅ Тест уже пройден", show_alert=True)
            return
        if decision == "cooldown":
            await state.clear()
            await callback.answer(f"Попробуй через {fmt_duration(left)}", show_alert=True)
            return
        if decision == "no_points" or not await charge_points(user.id, test.cost):
            await state.clear()
            await callback.answer("Недостаточно кадров", show_alert=True)
            return

        data = {
            "tt_id": test.id,
            "tt_title": test.title,
            "tt_q": [question_to_dict(q) for q in questions],
            "tt_i": 0,
            "tt_ok": 0,
        }
        await state.set_data(data)
    except BaseException:
        await state.clear()
        raise

    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await send_question(callback.message, data)


@training_router.callback_query(TrainAnswerCb.filter())
async def training_answer(callback: CallbackQuery, callback_data: TrainAnswerCb, state: FSMContext):
    if await state.get_state() != TrainStates.in_test.state:
        await callback.answer("Тест прерван. Начни заново через «Обучение».", show_alert=True)
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
        return

    data = await state.get_data()
    if callback_data.test_id != data["tt_id"] or callback_data.index != data["tt_i"]:
        await callback.answer("Кнопка устарела.", show_alert=True)
        return

    q = data["tt_q"][data["tt_i"]]
    data["tt_ok"] += int(callback_data.option == q["correct"])
    data["tt_i"] += 1
    await state.update_data(tt_i=data["tt_i"], tt_ok=data["tt_ok"])
    await callback.answer()
    try:
        await callback.message.edit_text(f"{callback.message.text}\n\nТвой ответ: {callback_data.option}")
    except TelegramBadRequest:
        pass

    total = len(data["tt_q"])
    if data["tt_i"] < total:
        await send_question(callback.message, data)
        return

    await state.clear()
    correct = data["tt_ok"]
    passed = is_quiz_passed(correct, total)
    user = await get_user(callback.from_user.id)
    if user:
        await record_attempt(user.id, data["tt_id"], correct, total, passed)
    if passed:
        await callback.message.answer(f"✅ Тест «{data['tt_title']}» пройден! {correct} из {total} верно.")
    else:
        await callback.message.answer(f"{total - correct} ошибок из {total}. Попробуй ещё раз через 24 ч.")
