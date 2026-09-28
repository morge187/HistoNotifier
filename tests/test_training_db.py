import asyncio

import pytest

from database import training as t
from database.requests import get_user_by_id


def run(coro):
    return asyncio.run(coro)


def q(n: int, correct: int = 1) -> dict:
    return {"text": f"Вопрос {n}", "options": ["a", "b", "c", "d"], "correct": correct}


def test_create_and_read(db):
    test_id = run(t.create_test("Тест А", 2.5, [q(1, 2), q(2, 4)]))
    [(test, count)] = run(t.get_tests_with_counts())
    assert (test.id, test.title, test.cost, count) == (test_id, "Тест А", 2.5, 2)
    questions = run(t.get_questions(test_id))
    assert [t.question_to_dict(x) for x in questions] == [q(1, 2), q(2, 4)]


def test_create_validates_count(db):
    with pytest.raises(ValueError):
        run(t.create_test("x", 0, []))
    with pytest.raises(ValueError):
        run(t.create_test("x", 0, [q(i) for i in range(26)]))


def test_edit_questions(db):
    test_id = run(t.create_test("x", 0, [q(1)]))
    [first] = run(t.get_questions(test_id))

    assert run(t.delete_question(first.id)) is False  # последний вопрос не удаляется
    assert run(t.add_question(test_id, q(2, 3))) is True
    assert run(t.update_question(first.id, q(9, 4))) is True
    assert [t.question_to_dict(x) for x in run(t.get_questions(test_id))] == [q(9, 4), q(2, 3)]
    assert run(t.delete_question(first.id)) is True
    assert len(run(t.get_questions(test_id))) == 1
    assert run(t.update_test(test_id, title="Новое", cost=1)) is True
    assert (run(t.get_test(test_id)).title, run(t.get_test(test_id)).cost) == ("Новое", 1)
    assert run(t.update_test(999, title="x")) is False


def test_add_question_limit(db):
    test_id = run(t.create_test("x", 0, [q(i) for i in range(25)]))
    assert run(t.add_question(test_id, q(26))) is False


def test_attempts_and_delete(db, make_user):
    uid = make_user()
    test_id = run(t.create_test("x", 0, [q(1)]))
    assert run(t.has_passed(uid, test_id)) is False
    assert run(t.last_failed_at(uid, test_id)) is None

    assert run(t.record_attempt(uid, test_id, 0, 1, False)) is True
    assert run(t.last_failed_at(uid, test_id)) is not None
    assert run(t.record_attempt(uid, test_id, 1, 1, True)) is True
    assert run(t.has_passed(uid, test_id)) is True

    assert run(t.delete_test(test_id)) is True
    assert run(t.get_test(test_id)) is None
    assert run(t.get_questions(test_id)) == []
    assert run(t.get_test_statuses(uid)) == []
    assert run(t.record_attempt(uid, test_id, 1, 1, True)) is False
    assert run(t.delete_test(test_id)) is False


def test_charge_points(make_user):
    uid = make_user(points=5)
    assert run(t.charge_points(uid, 0)) is True
    assert run(t.charge_points(uid, 6)) is False
    assert run(t.charge_points(uid, 2.5)) is True
    assert run(get_user_by_id(uid)).points == 2.5


def test_create_test_returns_id_under_production_session(db):
    # Регрессия: create_test читал test.id после commit — при expire_on_commit=True
    # (как в проде) это ленивая подгрузка в async-сессии -> MissingGreenlet.
    from database.models import async_session as prod_session
    assert db.kw.get("expire_on_commit", True) == prod_session.kw.get("expire_on_commit", True) is True
    test_id = run(t.create_test("Регрессия", 1, [q(1)]))
    assert isinstance(test_id, int)
    assert run(t.get_test(test_id)).title == "Регрессия"
