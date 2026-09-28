import asyncio
import importlib
from types import SimpleNamespace

import pytest
from aiogram.dispatcher.event.bases import SkipHandler

# handlers/__init__ экспортирует роутер start, затеняя одноимённый модуль.
st = importlib.import_module("handlers.start")


class FakeMessage:
    def __init__(self, text, tg_id=500):
        self.text = text
        self.from_user = SimpleNamespace(id=tg_id)
        self.answers = []

    async def answer(self, text, reply_markup=None, **kwargs):
        self.answers.append((text, reply_markup))


class FakeState:
    def __init__(self):
        self.cleared = False
        self.state = None

    async def clear(self):
        self.cleared = True

    async def set_state(self, state):
        self.state = state


@pytest.mark.parametrize("text", ["Личный кабинет", "Матч-штрафы", "Обучение", "/menu", "/cabinet"])
def test_nick_input_skips_menu_buttons_and_commands(db, text):
    state = FakeState()
    message = FakeMessage(text)
    with pytest.raises(SkipHandler):
        asyncio.run(st.set_name_to_user(message, state))
    assert state.cleared and message.answers == []


def test_start_for_onboarded_user_sends_menu(make_user):
    make_user(tg_id=500, name="Youra", onboarded=True)
    message = FakeMessage("/start")
    state = FakeState()
    asyncio.run(st.start_command(message, state))
    assert message.answers == [("Меню", st.userboard)]
    assert state.state is None


def test_start_for_not_onboarded_user_resends_welcome(make_user):
    make_user(tg_id=500, name="Youra", onboarded=False)
    message = FakeMessage("/start")
    asyncio.run(st.start_command(message, FakeState()))
    assert message.answers == [(st.WELCOME_TEXT, st.onboard_kb)]
