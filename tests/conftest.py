import asyncio
import importlib

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from database.models import Base, User

# Модули, у которых подменяем async_session на временную БД.
# Модуль, которого ещё нет (создаётся в поздних задачах), пропускается.
DB_MODULES = ("database.requests", "database.fines", "database.training")


@pytest.fixture
def db(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}", poolclass=NullPool)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init())
    for name in DB_MODULES:
        try:
            module = importlib.import_module(name)
        except ModuleNotFoundError:
            continue
        monkeypatch.setattr(module, "async_session", session_maker)
    yield session_maker
    asyncio.run(engine.dispose())


@pytest.fixture
def make_user(db):
    def _make(name="A", tg_id=1, status="base_user", points=0.0, **extra) -> int:
        async def go():
            async with db() as session:
                user = User(name=name, tg_id=tg_id, status=status, points=points, **extra)
                session.add(user)
                await session.commit()
                return user.id
        return asyncio.run(go())
    return _make
