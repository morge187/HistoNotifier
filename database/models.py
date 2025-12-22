from sqlalchemy import BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from datetime import datetime

engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3',
                             echo=True)

async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=True) 
    tg_id = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(nullable=True)
    points: Mapped[int] = mapped_column(nullable=True, default=0)


class UserEvent(Base):
    __tablename__ = 'userevents'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    event_id: Mapped[int] = mapped_column(ForeignKey('events.id'))


class Tank(Base):
    __tablename__ = 'tanks'
    id: Mapped[int] = mapped_column(primary_key=True)
    discript: Mapped[str] = mapped_column() 
    photo_id = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column()
    nation: Mapped[str] = mapped_column()


class Event(Base):
    __tablename__ = 'events'
    id: Mapped[int] = mapped_column(primary_key=True)
    discription: Mapped[str] = mapped_column() 
    photo_id = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(nullable=True)
    time = mapped_column(DateTime)
    cost: Mapped[int] = mapped_column(nullable=True)


class Reward(Base):
    __tablename__ = 'rewards'  # Изменили на 'rewards' вместо 'rewardings'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=True)
    gift_link: Mapped[str] = mapped_column(nullable=False)
    price: Mapped[int] = mapped_column(nullable=False)
    image_file_id = mapped_column(BigInteger, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class UserReward(Base):
    __tablename__ = 'userrewards'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    reward_id: Mapped[int] = mapped_column(ForeignKey('rewards.id'))  # Исправлено: rewards вместо rewardings
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)