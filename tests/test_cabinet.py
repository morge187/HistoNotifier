import asyncio

from database import training as t
from database.models import TrainingAttempt, TrainingTest
from utils import render_cabinet


def test_render_cabinet_full():
    text = render_cabinet(
        "Youra", 42,
        rewards=[("Камуфляж №1", True), ("Камуфляж №2", False)],
        tests=[("Тест А", True), ("Тест Б", False)],
        fines=[("Оскорбление", 3), ("Старый штраф", 0)],
    )
    assert "👤 Ник: Youra" in text
    assert "🎞 Кадры: 42" in text
    assert " • Камуфляж №1 — выдан ✅" in text
    assert " • Камуфляж №2 — не выдан ❌" in text
    assert " • Тест А — пройден 🟢" in text
    assert " • Тест Б — не пройден 🔴" in text
    assert " 1. Оскорбление — 3 кадров" in text
    assert " 2. Старый штраф" in text and "Старый штраф —" not in text


def test_render_cabinet_empty():
    text = render_cabinet("Youra", 0, rewards=[], tests=[], fines=[])
    assert "🎁 Награды: нет" in text
    assert "📚 Тесты: нет тестов" in text
    assert "⚠️ Штрафы: нет" in text


def test_get_test_statuses(db, make_user):
    uid = make_user()

    async def seed():
        async with db() as session:
            a, b = TrainingTest(title="А", cost=0), TrainingTest(title="Б", cost=0)
            session.add_all([a, b])
            await session.flush()
            session.add_all([
                TrainingAttempt(user_id=uid, test_id=a.id, correct_count=1, total=5, passed=False),
                TrainingAttempt(user_id=uid, test_id=a.id, correct_count=5, total=5, passed=True),
                TrainingAttempt(user_id=uid, test_id=b.id, correct_count=0, total=5, passed=False),
            ])
            await session.commit()
            return a.id, b.id

    a_id, b_id = asyncio.run(seed())
    assert asyncio.run(t.get_test_statuses(uid)) == [(a_id, "А", True), (b_id, "Б", False)]
