from sqlalchemy import select, update, delete, desc
from sqlalchemy.orm import joinedload
from sqlalchemy import and_, func
from datetime import datetime

from database.models import User, UserEvent, Event, async_session, Reward, UserReward, Tank, YearTank # Импорты модели User и асинхронной сессии

async def get_user(tg_id):
    async with async_session() as session: # Открываем асинхронную сессию
        user = await session.scalar(select(User).where(User.tg_id == tg_id)) # Запомните, что scalar может быть и scalars в мн. числе
    
    return user

async def set_name_user(tg_id, name):
    async with async_session() as session: # Открываем асинхронную сессию
        user = await session.scalar(select(User).where(User.tg_id == tg_id)) # Запомните, что scalar может быть и scalars в мн. числе
        
        user.name = name
        await session.commit() # Сохраняем изменения в базе данных

        return user

async def set_user(tg_id): # Асинхронная функция для работы с пользователем
    async with async_session() as session: # Открываем асинхронную сессию
        user = await session.scalar(select(User).where(User.tg_id == tg_id)) # Запомните, что scalar может быть и scalars в мн. числе
        
        if not user: # Если пользователя с таким tg_id нет в базе данных
            session.add(User(tg_id=tg_id)) # Создаём нового пользователя
            await session.commit() # Сохраняем изменения в базе данных

        return user
    
    
async def set_status(tg_id, status, points=0): # Поскольку мы изменяем статус конкретного юзера по его tg_id, то этот параметр обязателен.
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user:
            user.status = status 
            user.points = (user.points if user.points else 0) + points
            await session.commit()


async def save_event(data: dict):
    async with async_session() as session:
        event = Event(
            name=data['name'], 
            photo_id=data['image_file_id'], 
            cost=data['points'],
            discription=data['description'],
            time=data['datetime']
        )
        session.add(event)
        await session.commit()
        return event
    

async def get_events():
    async with async_session() as session:
        events = await session.scalars(
            select(Event)
            .order_by(Event.time)
        )
        return events.all()
    
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Event


async def create_event(session: AsyncSession, name: str, time, cost: int, discription: str, photo_id: int):
    event = Event(
        name=name,
        time=time,
        cost=cost,
        discription=discription,
        photo_id=photo_id,
    )
    session.add(event)
    await session.commit()
    return event


async def get_future_events():
    async with async_session() as session:
        events = await session.scalars(
            select(Event)
            .where(Event.time >= datetime.now())
            .order_by(Event.time)
        )
        return events.all()

async def get_event_by_id(event_id: int):
    async with async_session() as session:
        event = await session.scalar(
            select(Event)
            .where(Event.id == event_id)
        )
        return event

async def get_event_by_index(index: int):
    async with async_session() as session:
        events = await session.scalars(
            select(Event)
            .where(Event.time >= datetime.now())
            .order_by(Event.time)
            .offset(index - 1)
            .limit(1)
        )
        return events.first()

async def add_user_to_event(user_id: int, event_id: int):
    async with async_session() as session:
        existing = await session.scalar(
            select(UserEvent)
            .where(UserEvent.user_id == user_id, UserEvent.event_id == event_id)
        )
        if existing:
            return False
        
        session.add(UserEvent(user_id=user_id, event_id=event_id))
        await session.commit()
        return True

async def get_event_participants(event_id: int):
    async with async_session() as session:
        participants = await session.scalars(
            select(User)
            .join(UserEvent, User.id == UserEvent.user_id)
            .where(UserEvent.event_id == event_id)
            .order_by(User.id)
        )
        return participants.all()

async def update_user_points(user_id: int, points: int):
    async with async_session() as session:
        user = await session.scalar(
            select(User)
            .where(User.id == user_id)
        )
        if user:
            user.points = (user.points or 0) + points
            await session.commit()
            return True
        return False


async def get_all_events():
    async with async_session() as session:
        events = await session.scalars(
            select(Event)
            .order_by(Event.time.desc())
        )
        return events.all()
    

async def update_event(event_id: int, update_data: dict):
    async with async_session() as session:
        event = await session.scalar(
            select(Event)
            .where(Event.id == event_id)
        )
        if not event:
            return False
        
        if 'name' in update_data:
            event.name = update_data['name']
        if 'description' in update_data:
            event.discription = update_data['description']
        if 'datetime' in update_data:
            event.time = update_data['datetime']
        if 'points' in update_data:
            event.cost = update_data['points']
        if 'image_file_id' in update_data:
            event.photo_id = update_data['image_file_id']
        
        await session.commit()
        return True
    
async def get_all_users():
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.status != "admin")
        )
        users = result.scalars().all()
        return users
    
async def get_last_event_id():
    async with async_session() as session:
        result = await session.execute(
            select(Event.id)
            .order_by(desc(Event.id))
            .limit(1)
        )
        
        return result.scalar_one_or_none()
    
async def delete_event_by_id(event_id: int) -> bool:
    async with async_session() as session:
        try:
            event_result = await session.execute(
                select(Event).where(Event.id == event_id)
            )
            event = event_result.scalar_one_or_none()
            
            if not event:
                return False
           
            try:
                await session.execute(
                    delete(UserEvent).where(UserEvent.event_id == event_id)
                )
            except Exception as e:
                pass
            
            await session.execute(
                delete(Event).where(Event.id == event_id)
            )

            await session.commit()
            
            return True
            
        except Exception:
            await session.rollback()
            return False

async def create_reward(name: str, description: str, gift_link: str, price: int, image_file_id: str) -> bool:
    async with async_session() as session:
        #try:
            reward = Reward(
                name=name,
                description=description,
                gift_link=gift_link,
                price=price,
                image_file_id=image_file_id,
                is_active=True
            )
            session.add(reward)
            await session.commit()
            return True

async def get_all_rewards(active_only: bool = False):
    async with async_session() as session:
        query = select(Reward)
        if active_only:
            query = query.where(Reward.is_active == True)
        query = query.order_by(Reward.price, Reward.id)
        
        result = await session.execute(query)
        return result.scalars().all()

async def get_reward_by_id(reward_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(Reward).where(Reward.id == reward_id)
        )
        return result.scalar_one_or_none()

async def get_rewards_by_price(price: int):
    async with async_session() as session:
        result = await session.execute(
            select(Reward)
            .where(Reward.price == price, Reward.is_active == True)
            .order_by(Reward.id)
        )
        return result.scalars().all()

async def update_reward(reward_id: int, **kwargs):
    async with async_session() as session:
        try:
            result = await session.execute(
                select(Reward).where(Reward.id == reward_id)
            )
            reward = result.scalar_one_or_none()
            
            if not reward:
                return False
            
            for key, value in kwargs.items():
                if hasattr(reward, key):
                    setattr(reward, key, value)
            
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            return False

async def delete_reward(reward_id: int) -> bool:
    async with async_session() as session:
        try:
            await session.execute(
                delete(Reward).where(Reward.id == reward_id)
            )
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            return False

async def assign_reward_to_user(user_id: int, reward_id: int) -> bool:
    async with async_session() as session:
        try:
            existing = await session.execute(
                select(UserReward)
                .where(UserReward.user_id == user_id, UserReward.reward_id == reward_id)
            )
            if existing.scalar_one_or_none():
                return False
            
            user_reward = UserReward(user_id=user_id, reward_id=reward_id)
            session.add(user_reward)
            await session.commit()
            return True
        except Exception as e:
            await session.rollback()
            return False

async def get_user_rewards(user_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(Reward)
            .join(UserReward, Reward.id == UserReward.reward_id)
            .where(UserReward.user_id == user_id)
            .order_by(UserReward.created_at.desc())
        )
        return result.scalars().all()

async def is_admin(user_id: int) -> bool:
    user = await get_user(user_id)
    return user and user.status == 'admin'

async def reset_rewards():
    async with async_session() as session:
        try:
            await session.execute(delete(UserReward))
            
            await session.execute(
                update(Reward).values(is_active=True)
            )
            
            await session.commit()
            return True, "✅ Все награды сброшены и активированы!"
            
        except Exception as e:
            await session.rollback()
            return False, f"❌ Ошибка при сбросе наград: {str(e)}"
        
async def get_enactive_rewards():
    async with async_session() as session:
        result = await session.execute(
            select(Reward)
            .where(Reward.is_active == False)
            .order_by(Reward.price, Reward.id)
        )
        return result.scalars().all()
    
async def get_reward_statistic():
    async with async_session() as session:
        total_rewards_result = await session.execute(select(Reward))
        total_rewards = total_rewards_result.scalars().all()
        
        active_rewards_result = await session.execute(
            select(Reward).where(Reward.is_active == True)
        )
        active_rewards = active_rewards_result.scalars().all()
        
        # Получаем статистику по пользователям
        user_rewards_result = await session.execute(
            select(UserReward)
        )
        user_rewards = user_rewards_result.scalars().all()
        
        # Получаем уникальных пользователей с наградами
        unique_users_result = await session.execute(
            select(UserReward.user_id).distinct()
        )
        unique_users = unique_users_result.scalars().all()

        return (total_rewards, active_rewards, user_rewards, unique_users)

async def get_all_tanks():
    async with async_session() as session:
        result = await session.execute(
            select(Tank).order_by(Tank.nation, Tank.name)
        )
        return result.scalars().all()

async def get_tanks_by_nation(nation: str):
    async with async_session() as session:
        result = await session.execute(
            select(Tank)
            .where(Tank.nation == nation)
            .order_by(Tank.name)
        )
        return result.scalars().all()

async def get_tank_by_id(tank_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(Tank).where(Tank.id == tank_id)
        )
        return result.scalar_one_or_none()

async def create_tank(name: str, nation: str, discript: str, photo_id: str, tank_type: str, years: list) -> bool:
    async with async_session() as session:
        try:
            tank = Tank(
                name=name,
                nation=nation,
                discript=discript,
                photo_id=photo_id,
                tank_type=tank_type,
            )
            session.add(tank)
            await session.flush()
            
            for year in years:
                year_tank = YearTank(tank_id=tank.id, year=year)
                session.add(year_tank)
            
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            return False

async def update_tank(tank_id: int, **kwargs) -> bool:
    async with async_session() as session:
        try:
            result = await session.execute(
                select(Tank).where(Tank.id == tank_id)
            )
            tank = result.scalar_one_or_none()
            
            if not tank:
                return False
            
            for key, value in kwargs.items():
                if hasattr(tank, key) and key != 'years':  # Годы обрабатываем отдельно
                    setattr(tank, key, value)
            
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            return False
        
async def update_tank_years(tank_id: int, years: list) -> bool:
    async with async_session() as session:
        try:
            await session.execute(
                delete(YearTank).where(YearTank.tank_id == tank_id)
            )
            
            for year in years:
                year_tank = YearTank(tank_id=tank_id, year=year)
                session.add(year_tank)
            
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            return False

async def delete_tank(tank_id: int) -> bool:
    async with async_session() as session:
        try:
            await session.execute(
                delete(Tank).where(Tank.id == tank_id)
            )
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            return False
        
async def delete_tank_years(tank_id: int) -> bool:
    async with async_session() as session:
        try:
            await session.execute(
                delete(YearTank).where(YearTank.tank_id == tank_id)
            )
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            return False
        
async def get_tank_years(tank_id: int) -> list:
    async with async_session() as session:
        result = await session.execute(
            select(YearTank.year)
            .where(YearTank.tank_id == tank_id)
            .order_by(YearTank.year)
        )
        return [row[0] for row in result.all()]

async def get_all_nations():
    async with async_session() as session:
        result = await session.execute(
            select(Tank.nation).distinct().order_by(Tank.nation)
        )
        return [row[0] for row in result.all()]
    
async def get_all_years():
    async with async_session() as session:
        result = await session.execute(
            select(YearTank.year)
            .distinct()
            .order_by(YearTank.year.desc())
        )
        return [row[0] for row in result.all()]

async def get_tanks_by_year(year: int):
    async with async_session() as session:
        result = await session.execute(
            select(Tank)
            .join(YearTank, Tank.id == YearTank.tank_id)
            .where(YearTank.year == year)
            .order_by(Tank.name)
        )
        return result.scalars().all()

async def get_tanks_by_year_and_type(year: int, tank_type: str):
    async with async_session() as session:
        result = await session.execute(
            select(Tank)
            .join(YearTank, Tank.id == YearTank.tank_id)
            .where(YearTank.year == year, Tank.tank_type == tank_type)
            .order_by(Tank.name)
        )
        return result.scalars().all()

async def get_tank_types_by_year(year: int):
    async with async_session() as session:
        result = await session.execute(
            select(Tank.tank_type)
            .join(YearTank, Tank.id == YearTank.tank_id)
            .where(YearTank.year == year, Tank.tank_type.isnot(None))
            .distinct()
            .order_by(Tank.tank_type)
        )
        return [row[0] for row in result.all() if row[0]]

async def get_tank_with_years(tank_id: int):
    async with async_session() as session:
        tank_result = await session.execute(
            select(Tank).where(Tank.id == tank_id)
        )
        tank = tank_result.scalar_one_or_none()
        
        if not tank:
            return None
        
        years_result = await session.execute(
            select(YearTank.year)
            .where(YearTank.tank_id == tank_id)
            .order_by(YearTank.year)
        )
        years = [row[0] for row in years_result.all()]
        
        return tank, years
    
async def get_users_with_fines():
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(
                and_(
                    User.name.isnot(None),
                    User.fine.isnot(None),
                    func.length(func.trim(User.fine)) > 0
                )
            )
            .order_by(User.name)
        )
        return result.scalars().all()

async def get_users_with_fines():
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(
                and_(
                    User.name.isnot(None),
                    User.fine.isnot(None),
                    func.length(func.trim(User.fine)) > 0
                )
            )
            .order_by(User.name)
        )
        return result.scalars().all()

async def get_users_with_fines_by_event(event_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .join(UserEvent, User.id == UserEvent.user_id)
            .where(
                and_(
                    UserEvent.event_id == event_id,
                    User.name.isnot(None),
                    User.fine.isnot(None),
                    func.length(func.trim(User.fine)) > 0
                )
            )
            .order_by(User.name)
        )
        return result.scalars().all()

async def get_user_by_name(name: str):
    async with async_session() as session:
        return await session.scalar(
            select(User).where(func.lower(User.name) == func.lower(name))
        )

async def get_all_users_ordered():
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.status != "admin")
            .order_by(User.name)
        )
        return result.scalars().all()

async def set_user_fine(user_id: int, fine_text: str):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.id == user_id))
        if not user:
            return False
        user.fine = fine_text
        await session.commit()
        return True

async def clear_user_fine(user_id: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.id == user_id))
        if not user:
            return False
        user.fine = None
        await session.commit()
        return True

async def set_user_points_value(user_id: int, value: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.id == user_id))
        if not user:
            return False
        user.points = max(0, int(value))
        await session.commit()
        return True

async def decrease_user_points(user_id: int, delta: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.id == user_id))
        if not user:
            return False
        current = user.points or 0
        user.points = max(0, current - int(delta))
        await session.commit()
        return True

async def reset_user_points(user_id: int):
    return await set_user_points_value(user_id, 0)

async def check_name_exists(name: str, exclude_user_id: int = None):
    async with async_session() as session:
        query = select(User).where(func.lower(User.name) == func.lower(name))
        if exclude_user_id:
            query = query.where(User.id != exclude_user_id)
        return await session.scalar(query) is not None