import asyncio
import importlib
from types import SimpleNamespace

from aiogram.exceptions import TelegramBadRequest

# handlers/__init__ экспортирует роутер admin_create, затеняя одноимённый модуль.
ac = importlib.import_module("handlers.admin_create")


class FakeMessage:
    def __init__(self, text, delete_exc=None):
        self.text = text
        self.from_user = SimpleNamespace(id=7)
        self.delete_exc = delete_exc
        self.deleted = False
        self.answers = []

    async def delete(self):
        self.deleted = True
        if self.delete_exc:
            raise self.delete_exc

    async def answer(self, text, **kwargs):
        self.answers.append(text)


class FakeState:
    def __init__(self):
        self.cleared = False
        self.data = {}

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def clear(self):
        self.cleared = True


def _run(monkeypatch, password, message):
    promoted = []

    async def fake_set_status(tg_id, status, points=0):
        promoted.append((tg_id, status))

    monkeypatch.setattr(ac, "PASSWORD", password)
    monkeypatch.setattr(ac, "set_status", fake_set_status)
    state = FakeState()
    asyncio.run(ac.is_correcr(message, state))
    assert state.cleared and state.data == {}  # пароль в FSM не сохраняется
    return promoted


def test_sticker_without_configured_password_is_rejected(monkeypatch):
    message = FakeMessage(text=None)
    assert _run(monkeypatch, None, message) == []
    assert message.answers == ["Неверный пароль"]


def test_sticker_is_rejected_even_with_password(monkeypatch):
    assert _run(monkeypatch, "secret", FakeMessage(text=None)) == []


def test_correct_password_promotes_and_deletes_message(monkeypatch):
    message = FakeMessage(text="secret")
    assert _run(monkeypatch, "secret", message) == [(7, "admin")]
    assert message.deleted and message.answers == ["Всё верно"]


def test_delete_failure_is_ignored(monkeypatch):
    exc = TelegramBadRequest(method=None, message="Bad Request: message can't be deleted")
    message = FakeMessage(text="wrong", delete_exc=exc)
    assert _run(monkeypatch, "secret", message) == []
    assert message.answers == ["Неверный пароль"]
