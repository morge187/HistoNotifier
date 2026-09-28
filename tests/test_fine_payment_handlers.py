import asyncio
import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest

from database import fines as f
from handlers.common import safe_answer
from utils import fine_payload

fp = importlib.import_module("handlers.fine_payment")


def run(coro):
    return asyncio.run(coro)


def make_payment_message(fine_id, user_id, charge_id="ch_1", stars=10, tg_id=1):
    return SimpleNamespace(
        successful_payment=SimpleNamespace(
            invoice_payload=fine_payload(fine_id, user_id),
            total_amount=stars,
            telegram_payment_charge_id=charge_id,
        ),
        from_user=SimpleNamespace(id=tg_id),
        answer=AsyncMock(),
        bot=SimpleNamespace(send_message=AsyncMock()),
    )


def test_successful_payment_redelivery_is_success(make_user):
    """Final review #7: повторная доставка того же платежа — не «вернём звёзды»."""
    make_user(name="adm", tg_id=99, status="admin")
    uid = make_user(tg_id=1)
    fine = run(f.add_fine(uid, "x", 2))

    first = make_payment_message(fine.id, uid)
    run(fp.successful_payment(first))
    again = make_payment_message(fine.id, uid)
    run(fp.successful_payment(again))

    for message in (first, again):
        message.answer.assert_called_once_with("✅ Штраф оплачен: 10 ⭐. Спасибо!")
        message.bot.send_message.assert_not_called()


def test_successful_payment_for_closed_fine_alerts_admins(make_user):
    make_user(name="adm", tg_id=99, status="admin")
    uid = make_user(tg_id=1)
    fine = run(f.add_fine(uid, "x", 2))
    run(f.mark_fine_paid_stars(fine.id, 10, "ch_other"))

    message = make_payment_message(fine.id, uid, charge_id="ch_new")
    run(fp.successful_payment(message))

    assert "Администратор вернёт звёзды" in message.answer.call_args.args[0]
    assert message.bot.send_message.call_args.args[0] == 99


def test_safe_answer_swallows_bad_request():
    callback = SimpleNamespace(answer=AsyncMock(side_effect=TelegramBadRequest(method=None, message="query is too old")))
    run(safe_answer(callback, "ok", show_alert=True))
    callback.answer.assert_called_once_with("ok", show_alert=True)


def test_safe_answer_reraises_other_errors():
    callback = SimpleNamespace(answer=AsyncMock(side_effect=RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        run(safe_answer(callback))
