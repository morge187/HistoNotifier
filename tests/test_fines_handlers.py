import asyncio

import pytest
from aiogram.exceptions import TelegramBadRequest

from handlers.fines import safe_edit


def run(coro):
    return asyncio.run(coro)


class FakeMessage:
    """Двойник aiogram.types.Message — только edit_text, как использует safe_edit."""

    def __init__(self, raise_exc=None):
        self.raise_exc = raise_exc
        self.calls = []

    async def edit_text(self, text, reply_markup=None):
        self.calls.append((text, reply_markup))
        if self.raise_exc:
            raise self.raise_exc


def test_safe_edit_swallows_message_not_modified():
    """Повторный тап по кнопке — та же карточка, Telegram ругается, но пользователь не должен увидеть ошибку."""
    exc = TelegramBadRequest(
        method=None,
        message="Bad Request: message is not modified: specified new message content "
                "and reply markup are exactly the same as a current content and reply markup of the message",
    )
    message = FakeMessage(raise_exc=exc)

    run(safe_edit(message, "текст", "kb"))  # не должно поднять исключение

    assert message.calls == [("текст", "kb")]


def test_safe_edit_reraises_other_bad_request():
    """Любая другая ошибка Telegram не должна прятаться."""
    exc = TelegramBadRequest(method=None, message="Bad Request: chat not found")
    message = FakeMessage(raise_exc=exc)

    with pytest.raises(TelegramBadRequest):
        run(safe_edit(message, "текст"))


def test_safe_edit_reraises_other_exception_types():
    """Не TelegramBadRequest — тоже наружу."""
    message = FakeMessage(raise_exc=RuntimeError("boom"))

    with pytest.raises(RuntimeError):
        run(safe_edit(message, "текст"))


def test_safe_edit_calls_edit_text_when_no_error():
    message = FakeMessage()

    run(safe_edit(message, "привет", "kb"))

    assert message.calls == [("привет", "kb")]
