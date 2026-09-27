import asyncio

from database import fines as f
from database.models import UserEvent


def run(coro):
    return asyncio.run(coro)


def test_add_and_list_active(make_user):
    uid = make_user(points=10)
    fine = run(f.add_fine(uid, "Опоздал", 3))
    assert fine.id and fine.status == "active" and fine.cost == 3
    assert [x.id for x in run(f.get_active_fines(uid))] == [fine.id]


def test_add_fine_unknown_user(db):
    assert run(f.add_fine(999, "x", 1)) is None


def test_remove_keeps_history(make_user):
    uid = make_user()
    fine = run(f.add_fine(uid, "x", 1))
    assert run(f.remove_fine(fine.id, admin_tg_id=555)) is True
    assert run(f.remove_fine(fine.id, admin_tg_id=555)) is False
    stored = run(f.get_fine(fine.id))
    assert stored.status == "removed" and stored.closed_by == 555 and stored.closed_at
    assert run(f.get_active_fines(uid)) == []


def test_pay_with_cadrs(make_user):
    uid = make_user(points=10)
    fine = run(f.add_fine(uid, "x", 3))
    assert run(f.pay_fine_with_cadrs(fine.id, uid)) == "ok"
    stored = run(f.get_fine(fine.id))
    assert stored.status == "paid" and stored.paid_with == "cadrs"
    from database.requests import get_user_by_id
    assert run(get_user_by_id(uid)).points == 7
    assert run(f.pay_fine_with_cadrs(fine.id, uid)) == "not_active"


def test_pay_with_cadrs_errors(make_user):
    poor = make_user(name="P", tg_id=2, points=1)
    other = make_user(name="O", tg_id=3, points=100)
    costly = run(f.add_fine(poor, "x", 3))
    free = run(f.add_fine(poor, "legacy", 0))
    assert run(f.pay_fine_with_cadrs(costly.id, poor)) == "no_points"
    assert run(f.pay_fine_with_cadrs(free.id, poor)) == "free"
    assert run(f.pay_fine_with_cadrs(costly.id, other)) == "not_found"
    assert run(f.pay_fine_with_cadrs(9999, poor)) == "not_found"
    assert run(f.get_fine(costly.id)).status == "active"


def test_pay_with_cadrs_debit_is_conditional_on_current_balance(make_user):
    """Списание баллов — условный UPDATE в той же транзакции, что и статус штрафа:
    вторая оплата не может списать баллы, которых уже не осталось после первой."""
    uid = make_user(points=5)
    first = run(f.add_fine(uid, "a", 3))
    second = run(f.add_fine(uid, "b", 3))
    assert run(f.pay_fine_with_cadrs(first.id, uid)) == "ok"
    assert run(f.pay_fine_with_cadrs(second.id, uid)) == "no_points"
    from database.requests import get_user_by_id
    assert run(get_user_by_id(uid)).points == 2
    assert run(f.get_fine(second.id)).status == "active"


def test_mark_paid_stars_once(make_user):
    uid = make_user()
    fine = run(f.add_fine(uid, "x", 2))
    assert run(f.mark_fine_paid_stars(fine.id, 10, "ch_1")) is True
    assert run(f.mark_fine_paid_stars(fine.id, 10, "ch_2")) is False
    stored = run(f.get_fine(fine.id))
    assert (stored.status, stored.paid_with, stored.stars_amount, stored.charge_id) == ("paid", "stars", 10, "ch_1")


def test_users_with_active_fines_grouped_and_by_event(db, make_user):
    a = make_user(name="Бета", tg_id=1)
    b = make_user(name="Альфа", tg_id=2)
    make_user(name="Чистый", tg_id=3)
    run(f.add_fine(a, "a1", 1))
    run(f.add_fine(a, "a2", 1))
    removed = run(f.add_fine(b, "b1", 1))
    run(f.add_fine(b, "b2", 1))
    run(f.remove_fine(removed.id, 1))

    rows = run(f.get_users_with_active_fines())
    assert [(u.name, [x.description for x in fs]) for u, fs in rows] == [("Альфа", ["b2"]), ("Бета", ["a1", "a2"])]

    async def join_event():
        async with db() as session:
            session.add_all([UserEvent(user_id=a, event_id=7), UserEvent(user_id=a, event_id=7)])
            await session.commit()
    run(join_event())
    rows = run(f.get_users_with_active_fines(event_id=7))
    assert [(u.name, len(fs)) for u, fs in rows] == [("Бета", 2)]
