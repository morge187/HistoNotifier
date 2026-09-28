"""Обучение: тесты, вопросы, попытки."""
from sqlalchemy import delete, func, select, update

from database.models import TrainingAttempt, TrainingQuestion, TrainingTest, User, async_session

MAX_QUESTIONS = 25


async def get_test_statuses(user_id: int) -> list:
    """[(test_id, title, passed)] по всем тестам."""
    async with async_session() as session:
        tests = (await session.execute(
            select(TrainingTest.id, TrainingTest.title).order_by(TrainingTest.id)
        )).all()
        passed = set((await session.scalars(
            select(TrainingAttempt.test_id)
            .where(TrainingAttempt.user_id == user_id, TrainingAttempt.passed.is_(True))
        )).all())
    return [(test_id, title, test_id in passed) for test_id, title in tests]


def question_to_dict(q) -> dict:
    return {"text": q.text, "options": [q.option_1, q.option_2, q.option_3, q.option_4], "correct": q.correct}


def _question_columns(q: dict) -> dict:
    o = q["options"]
    return {"text": q["text"], "option_1": o[0], "option_2": o[1], "option_3": o[2],
            "option_4": o[3], "correct": int(q["correct"])}


async def create_test(title: str, cost: float, questions: list) -> int:
    if not 1 <= len(questions) <= MAX_QUESTIONS:
        raise ValueError(f"В тесте должно быть от 1 до {MAX_QUESTIONS} вопросов")
    async with async_session() as session:
        test = TrainingTest(title=title, cost=round(float(cost), 2))
        session.add(test)
        await session.flush()
        test_id = test.id  # до commit: после него объект истекает
        for position, q in enumerate(questions, start=1):
            session.add(TrainingQuestion(test_id=test_id, position=position, **_question_columns(q)))
        await session.commit()
        return test_id


async def get_tests_with_counts() -> list:
    async with async_session() as session:
        rows = await session.execute(
            select(TrainingTest, func.count(TrainingQuestion.id))
            .outerjoin(TrainingQuestion, TrainingQuestion.test_id == TrainingTest.id)
            .group_by(TrainingTest.id)
            .order_by(TrainingTest.id)
        )
        return [(test, count) for test, count in rows.all()]


async def get_test(test_id: int):
    async with async_session() as session:
        return await session.get(TrainingTest, test_id)


async def get_questions(test_id: int) -> list:
    async with async_session() as session:
        result = await session.scalars(
            select(TrainingQuestion)
            .where(TrainingQuestion.test_id == test_id)
            .order_by(TrainingQuestion.position, TrainingQuestion.id)
        )
        return list(result.all())


async def get_question(question_id: int):
    async with async_session() as session:
        return await session.get(TrainingQuestion, question_id)


async def update_test(test_id: int, **fields) -> bool:
    async with async_session() as session:
        test = await session.get(TrainingTest, test_id)
        if not test:
            return False
        for name, value in fields.items():
            setattr(test, name, value)
        await session.commit()
        return True


async def update_question(question_id: int, q: dict) -> bool:
    async with async_session() as session:
        question = await session.get(TrainingQuestion, question_id)
        if not question:
            return False
        for name, value in _question_columns(q).items():
            setattr(question, name, value)
        await session.commit()
        return True


async def _count_questions(session, test_id: int) -> int:
    return await session.scalar(
        select(func.count(TrainingQuestion.id)).where(TrainingQuestion.test_id == test_id)
    )


async def add_question(test_id: int, q: dict) -> bool:
    async with async_session() as session:
        if not await session.get(TrainingTest, test_id):
            return False
        if await _count_questions(session, test_id) >= MAX_QUESTIONS:
            return False
        last = await session.scalar(
            select(func.max(TrainingQuestion.position)).where(TrainingQuestion.test_id == test_id)
        )
        session.add(TrainingQuestion(test_id=test_id, position=(last or 0) + 1, **_question_columns(q)))
        await session.commit()
        return True


async def delete_question(question_id: int) -> bool:
    async with async_session() as session:
        question = await session.get(TrainingQuestion, question_id)
        if not question or await _count_questions(session, question.test_id) <= 1:
            return False
        await session.delete(question)
        await session.commit()
        return True


async def delete_test(test_id: int) -> bool:
    # SQLite без PRAGMA foreign_keys не выполняет ON DELETE CASCADE — удаляем явно
    async with async_session() as session:
        test = await session.get(TrainingTest, test_id)
        if not test:
            return False
        await session.execute(delete(TrainingAttempt).where(TrainingAttempt.test_id == test_id))
        await session.execute(delete(TrainingQuestion).where(TrainingQuestion.test_id == test_id))
        await session.delete(test)
        await session.commit()
        return True


async def has_passed(user_id: int, test_id: int) -> bool:
    async with async_session() as session:
        found = await session.scalar(
            select(TrainingAttempt.id)
            .where(TrainingAttempt.user_id == user_id, TrainingAttempt.test_id == test_id,
                   TrainingAttempt.passed.is_(True))
            .limit(1)
        )
        return found is not None


async def last_failed_at(user_id: int, test_id: int):
    async with async_session() as session:
        return await session.scalar(
            select(TrainingAttempt.created_at)
            .where(TrainingAttempt.user_id == user_id, TrainingAttempt.test_id == test_id,
                   TrainingAttempt.passed.is_(False))
            .order_by(TrainingAttempt.created_at.desc())
            .limit(1)
        )


async def charge_points(user_id: int, cost: float) -> bool:
    """Атомарно списывает кадры, если их хватает."""
    if not cost:
        return True
    async with async_session() as session:
        result = await session.execute(
            update(User)
            .where(User.id == user_id, User.points >= cost)
            .values(points=func.round(User.points - cost, 2))
        )
        await session.commit()
        return result.rowcount == 1


async def record_attempt(user_id: int, test_id: int, correct: int, total: int, passed: bool) -> bool:
    async with async_session() as session:
        if not await session.get(TrainingTest, test_id):
            return False
        session.add(TrainingAttempt(user_id=user_id, test_id=test_id,
                                    correct_count=correct, total=total, passed=passed))
        await session.commit()
        return True
