"""Test that fine_payment_router is first in handlers list to prevent payment loss."""
from handlers import handlers
from handlers.fine_payment import fine_payment_router


def test_fine_payment_router_is_first():
    """fine_payment_router must be first to intercept successful_payment before FSM handlers."""
    assert handlers[0] is fine_payment_router, (
        "fine_payment_router must be first in handlers list to prevent Telegram payment "
        "updates from being swallowed by state-filtered FSM handlers"
    )
