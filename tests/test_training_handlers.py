"""Тесты обработчиков «Обучение»: защита от повторного списания и устаревших кнопок."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

import handlers.training as tr
from database import training as t
from database.requests import get_user_by_id


def run(coro):
    return asyncio.run(coro)


def q(n: int, correct: int = 1) -> dict:
    return {"text": f"Вопрос {n}", "options": ["a", "b", "c", "d"], "correct": correct}


def make_state(tg_id: int) -> FSMContext:
    return FSMContext(storage=MemoryStorage(), key=StorageKey(bot_id=1, chat_id=tg_id, user_id=tg_id))


def make_callback(tg_id: int):
    """Лёгкая замена aiogram CallbackQuery: только атрибуты, которые использует хэндлер."""
    message = SimpleNamespace(
        text="вопрос",
        answer=AsyncMock(),
        edit_reply_markup=AsyncMock(),
        edit_text=AsyncMock(),
    )
    return SimpleNamespace(
        from_user=SimpleNamespace(id=tg_id),
        message=message,
        answer=AsyncMock(),
    )


def test_double_tap_start_charges_once(db, make_user):
    """Findings #1: повторный тап «Начать» (в т.ч. во время идущего теста) не списывает кадры дважды."""
    tg_id = 111
    uid = make_user(tg_id=tg_id, points=5)
    test_id = run(t.create_test("Тест", 2, [q(1)]))
    state = make_state(tg_id)
    cb_data = tr.TrainCb(action="start", test_id=test_id)

    callback1 = make_callback(tg_id)
    run(tr.training_start(callback1, cb_data, state))
    assert run(get_user_by_id(uid)).points == 3  # списано ровно раз
    assert run(state.get_state()) == tr.TrainStates.in_test.state
    callback1.answer.assert_called_once_with()

    # Повторный тап («▶️ Начать» снова, или дубль-клик) во время уже идущего теста.
    callback2 = make_callback(tg_id)
    run(tr.training_start(callback2, cb_data, state))
    assert run(get_user_by_id(uid)).points == 3  # НЕ списано повторно
    callback2.answer.assert_called_once()
    _, kwargs = callback2.answer.call_args
    assert kwargs.get("show_alert") is True
    # Тест не сброшен повторным тапом — прогресс всё ещё на первом вопросе.
    assert run(state.get_data())["tt_i"] == 0


def test_start_clears_lock_on_early_return(db, make_user):
    """Ранние выходы (недостаточно кадров и т.п.) снимают лок, иначе пользователь застрянет."""
    tg_id = 112
    make_user(tg_id=tg_id, points=0)
    test_id = run(t.create_test("Тест", 5, [q(1)]))
    state = make_state(tg_id)
    cb_data = tr.TrainCb(action="start", test_id=test_id)

    callback = make_callback(tg_id)
    run(tr.training_start(callback, cb_data, state))
    callback.answer.assert_called_once_with("Недостаточно кадров", show_alert=True)
    # Лок снят — следующая попытка не блокируется фразой "Сначала закончи текущий тест".
    assert run(state.get_state()) is None


def test_start_clears_lock_on_unexpected_exception(db, make_user, monkeypatch):
    """Round 2: транзиентная ошибка (напр. БД) между локом и стартом теста не должна
    оставлять пользователя навечно застрявшим в TrainStates.in_test."""
    tg_id = 113
    make_user(tg_id=tg_id, points=5)
    test_id = run(t.create_test("Тест", 0, [q(1)]))
    state = make_state(tg_id)
    cb_data = tr.TrainCb(action="start", test_id=test_id)
    callback = make_callback(tg_id)

    async def boom(_tg_id):
        raise RuntimeError("db down")

    monkeypatch.setattr(tr, "get_user", boom)

    with pytest.raises(RuntimeError):
        run(tr.training_start(callback, cb_data, state))

    # Исключение пробросилось наружу, но лок снят — следующий тап не увидит
    # ложное "Сначала закончи текущий тест".
    assert run(state.get_state()) is None


def test_stale_answer_button_alerts(db, make_user):
    """Findings #3: устаревшая кнопка (index/test_id не совпадают) → короткий alert, не silent answer."""
    tg_id = 222
    make_user(tg_id=tg_id, points=5)
    test_id = run(t.create_test("Тест", 0, [q(1), q(2)]))
    other_test_id = run(t.create_test("Другой тест", 0, [q(1)]))
    state = make_state(tg_id)

    start_cb = make_callback(tg_id)
    run(tr.training_start(start_cb, tr.TrainCb(action="start", test_id=test_id), state))
    start_cb.message.answer.assert_called_once()  # первый вопрос отправлен

    # Кнопка от другого теста — test_id не совпадает.
    stale_test_cb = make_callback(tg_id)
    run(tr.training_answer(stale_test_cb, tr.TrainAnswerCb(test_id=other_test_id, index=0, option=1), state))
    stale_test_cb.answer.assert_called_once_with("Кнопка устарела.", show_alert=True)
    assert run(state.get_data())["tt_i"] == 0  # прогресс не изменился

    # Кнопка с верным test_id, но устаревшим index (например, от предыдущего вопроса).
    stale_index_cb = make_callback(tg_id)
    run(tr.training_answer(stale_index_cb, tr.TrainAnswerCb(test_id=test_id, index=5, option=1), state))
    stale_index_cb.answer.assert_called_once_with("Кнопка устарела.", show_alert=True)
    assert run(state.get_data())["tt_i"] == 0


def test_edit_text_failure_does_not_block_progress(db, make_user):
    """Findings #2: TelegramBadRequest в edit_text не должен оставлять callback без ответа."""
    tg_id = 333
    make_user(tg_id=tg_id, points=0)
    test_id = run(t.create_test("Тест", 0, [q(1), q(2)]))
    state = make_state(tg_id)

    start_cb = make_callback(tg_id)
    run(tr.training_start(start_cb, tr.TrainCb(action="start", test_id=test_id), state))

    ans_cb = make_callback(tg_id)
    ans_cb.message.edit_text = AsyncMock(side_effect=TelegramBadRequest(method=None, message="MESSAGE_TOO_LONG"))
    run(tr.training_answer(ans_cb, tr.TrainAnswerCb(test_id=test_id, index=0, option=1), state))

    ans_cb.answer.assert_called_once_with()  # callback отвечен несмотря на исключение
    ans_cb.message.answer.assert_called_once()  # следующий вопрос всё же отправлен
    assert run(state.get_data())["tt_i"] == 1


TOO_OLD = TelegramBadRequest(method=None, message="Bad Request: query is too old and response timeout expired")


def test_start_sends_question_when_callback_answer_fails(db, make_user):
    """Final review #6: кадры списаны, а callback.answer() упал («query is too old») —
    вопрос всё равно должен уйти, иначе оплаченная попытка потеряна."""
    tg_id = 444
    uid = make_user(tg_id=tg_id, points=5)
    test_id = run(t.create_test("Тест", 2, [q(1)]))
    state = make_state(tg_id)

    callback = make_callback(tg_id)
    callback.answer = AsyncMock(side_effect=TOO_OLD)
    run(tr.training_start(callback, tr.TrainCb(action="start", test_id=test_id), state))

    assert run(get_user_by_id(uid)).points == 3
    callback.message.answer.assert_called_once()  # первый вопрос отправлен
    assert run(state.get_state()) == tr.TrainStates.in_test.state


def test_answer_sends_next_question_when_callback_answer_fails(db, make_user):
    tg_id = 445
    make_user(tg_id=tg_id, points=0)
    test_id = run(t.create_test("Тест", 0, [q(1), q(2)]))
    state = make_state(tg_id)
    run(tr.training_start(make_callback(tg_id), tr.TrainCb(action="start", test_id=test_id), state))

    ans_cb = make_callback(tg_id)
    ans_cb.answer = AsyncMock(side_effect=TOO_OLD)
    run(tr.training_answer(ans_cb, tr.TrainAnswerCb(test_id=test_id, index=0, option=1), state))

    ans_cb.message.answer.assert_called_once()  # следующий вопрос отправлен
    assert run(state.get_data())["tt_i"] == 1
