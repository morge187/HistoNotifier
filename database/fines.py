"""Матч-штрафы: выдача, снятие, оплата. Записи не удаляются — это история."""
from datetime import datetime

from sqlalchemy import func, select, update

from database.models import Fine, User, UserEvent, async_session


async def add_fine(user_id: int, description: str, cost: float):
    async with async_session() as session:
        if not await session.get(User, user_id):
            return None
        fine = Fine(user_id=user_id, description=description, cost=round(float(cost), 2))
        session.add(fine)
        await session.commit()
        await session.refresh(fine)
        return fine


async def get_fine(fine_id: int):
    async with async_session() as session:
        return await session.get(Fine, fine_id)


async def get_active_fines(user_id: int) -> list:
    async with async_session() as session:
        result = await session.scalars(
            select(Fine)
            .where(Fine.user_id == user_id, Fine.status == "active")
            .order_by(Fine.created_at, Fine.id)
        )
        return list(result.all())


async def get_users_with_active_fines(event_id: int = None) -> list:
    """[(User, [Fine, ...]), ...] — только игроки с ником и активными штрафами."""
    stmt = (
        select(User, Fine)
        .join(Fine, Fine.user_id == User.id)
        .where(Fine.status == "active", User.name.isnot(None))
        .order_by(User.name, Fine.created_at, Fine.id)
    )
    if event_id is not None:
        participants = select(UserEvent.user_id).where(UserEvent.event_id == event_id)
        stmt = stmt.where(User.id.in_(participants))

    async with async_session() as session:
        rows = (await session.execute(stmt)).all()

    grouped = {}
    for user, fine in rows:
        grouped.setdefault(user.id, (user, []))[1].append(fine)
    return list(grouped.values())


async def remove_fine(fine_id: int, admin_tg_id: int) -> bool:
    async with async_session() as session:
        result = await session.execute(
            update(Fine)
            .where(Fine.id == fine_id, Fine.status == "active")
            .values(status="removed", closed_at=datetime.now(), closed_by=admin_tg_id)
        )
        await session.commit()
        return result.rowcount == 1


async def pay_fine_with_cadrs(fine_id: int, user_id: int) -> str:
    """'ok' | 'not_found' | 'not_active' | 'free' | 'no_points'."""
    async with async_session() as session:
        fine = await session.get(Fine, fine_id)
        if not fine or fine.user_id != user_id:
            return "not_found"
        if fine.status != "active":
            return "not_active"
        if not fine.cost:
            return "free"

        # Условный UPDATE защищает от двойного нажатия: второй запрос не найдёт active
        fine_result = await session.execute(
            update(Fine)
            .where(Fine.id == fine_id, Fine.status == "active")
            .values(status="paid", paid_with="cadrs", closed_at=datetime.now())
        )
        if fine_result.rowcount != 1:
            await session.rollback()
            return "not_active"

        # Условный UPDATE списывает баллы атомарно в той же транзакции:
        # защищает от гонки двух одновременных оплат разных штрафов одним юзером.
        points_result = await session.execute(
            update(User)
            .where(User.id == user_id, User.points >= fine.cost)
            .values(points=func.round(User.points - fine.cost, 2))
        )
        if points_result.rowcount != 1:
            await session.rollback()
            return "no_points"

        await session.commit()
        return "ok"


async def mark_fine_paid_stars(fine_id: int, stars: int, charge_id: str) -> bool:
    async with async_session() as session:
        result = await session.execute(
            update(Fine)
            .where(Fine.id == fine_id, Fine.status == "active")
            .values(status="paid", paid_with="stars", stars_amount=stars,
                    charge_id=charge_id, closed_at=datetime.now())
        )
        await session.commit()
        return result.rowcount == 1
