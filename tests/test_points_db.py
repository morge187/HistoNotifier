import asyncio

from database import requests as r


def run(coro):
    return asyncio.run(coro)


# ── update_user_points ──────────────────────────────────────────────────────

def test_update_user_points_happy_path(make_user):
    uid = make_user(points=5)
    assert run(r.update_user_points(uid, 2.5)) is True
    assert run(r.get_user_by_id(uid)).points == 7.5


def test_update_user_points_none_treated_as_zero(make_user):
    uid = make_user(points=None)
    assert run(r.update_user_points(uid, 3)) is True
    assert run(r.get_user_by_id(uid)).points == 3


def test_update_user_points_not_found(db):
    assert run(r.update_user_points(999, 3)) is False


# ── set_status ───────────────────────────────────────────────────────────────

def test_set_status_updates_status_and_points(make_user):
    uid = make_user(tg_id=42, status="base_user", points=5)
    run(r.set_status(42, "admin", points=2))
    stored = run(r.get_user_by_id(uid))
    assert stored.status == "admin" and stored.points == 7


def test_set_status_none_points_treated_as_zero(make_user):
    uid = make_user(tg_id=43, status="base_user", points=None)
    run(r.set_status(43, "admin", points=4))
    assert run(r.get_user_by_id(uid)).points == 4


def test_set_status_unknown_tg_id_is_noop(db):
    run(r.set_status(999, "admin"))  # не должно бросать исключение


# ── set_user_points_value ────────────────────────────────────────────────────

def test_set_user_points_value_happy_path(make_user):
    uid = make_user(points=5)
    assert run(r.set_user_points_value(uid, 12.5)) is True
    assert run(r.get_user_by_id(uid)).points == 12.5


def test_set_user_points_value_clamped_at_zero(make_user):
    uid = make_user(points=5)
    assert run(r.set_user_points_value(uid, -3)) is True
    assert run(r.get_user_by_id(uid)).points == 0


def test_set_user_points_value_not_found(db):
    assert run(r.set_user_points_value(999, 5)) is False


# ── decrease_user_points ────────────────────────────────────────────────────

def test_decrease_user_points_happy_path(make_user):
    uid = make_user(points=10)
    assert run(r.decrease_user_points(uid, 3)) is True
    assert run(r.get_user_by_id(uid)).points == 7


def test_decrease_user_points_none_treated_as_zero(make_user):
    uid = make_user(points=None)
    assert run(r.decrease_user_points(uid, 3)) is True
    assert run(r.get_user_by_id(uid)).points == 0


def test_decrease_user_points_clamped_at_zero(make_user):
    uid = make_user(points=2)
    assert run(r.decrease_user_points(uid, 5)) is True
    assert run(r.get_user_by_id(uid)).points == 0


def test_decrease_user_points_not_found(db):
    assert run(r.decrease_user_points(999, 5)) is False
