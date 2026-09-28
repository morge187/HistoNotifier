"""Админские callback'и заново проверяют is_admin: callback_data можно подделать."""
import asyncio
import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

events = importlib.import_module("handlers.events")
reward = importlib.import_module("handlers.reward")
admin_battles = importlib.import_module("handlers.admin_battles")

CASES = [
    (events, "accept_all_participants", "accept_all:1", ("get_event_by_id",)),
    (events, "accept_by_numbers", "accept_nums:1", ("get_event_by_id",)),
    (events, "confirm_event_deletion", "confirm_delete:1", ("delete_event_by_id",)),
    (reward, "confirm_reward_deletion", "confirm_delete_reward_1", ("delete_reward",)),
    (admin_battles, "confirm_delete_battle", "del_battle_yes_1", ("delete_battle",)),
]


@pytest.mark.parametrize("module, handler, data, guarded", CASES, ids=[c[1] for c in CASES])
def test_non_admin_is_refused(db, make_user, monkeypatch, module, handler, data, guarded):
    make_user(tg_id=10, status="base_user")
    for name in guarded:
        monkeypatch.setattr(module, name, AsyncMock(side_effect=AssertionError(f"{name} called")))
    callback = SimpleNamespace(
        data=data, from_user=SimpleNamespace(id=10), answer=AsyncMock(),
        message=SimpleNamespace(answer=AsyncMock(), edit_text=AsyncMock()),
    )
    fn = getattr(module, handler)
    args = (callback, SimpleNamespace()) if fn.__code__.co_argcount == 2 else (callback,)

    asyncio.run(fn(*args))

    callback.answer.assert_called_once_with("Доступно только администратору.", show_alert=True)
    callback.message.answer.assert_not_called()
