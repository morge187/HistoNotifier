from sqlalchemy import select, update, delete, desc
from sqlalchemy.orm import joinedload
from datetime import datetime

from database.models import User, UserEvent, Event, async_session, Reward, UserReward, Tank # Импорты модели User и асинхронной сессии

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
        if user: # Проверка существования пользователя
            user.status = status # Изменение статуса пользователя
            user.points = (user.points if user.points else 0) + points
            await session.commit()


async def save_event(data: dict):
    async with async_session() as session:
        # Убираем проверку по id, так как он всегда -1 при создании
        event = Event(
            name=data['name'], 
            photo_id=data['image_file_id'], 
            cost=data['points'],
            discription=data['description'],
            time=data['datetime']
        )
        session.add(event)
        await session.commit()
        return event  # Возвращаем созданное событие
    

async def get_events(dateTime):
    async with async_session() as session:
        events = await session.scalar(select(Event).where(Event.time >= dateTime))

        return events

# ... существующие функции ...

async def get_future_events():
    async with async_session() as session:
        # Используем scalars для получения списка, а не одного значения
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
            .offset(index - 1)  # -1 т.к. нумерация с 1
            .limit(1)
        )
        return events.first()

async def add_user_to_event(user_id: int, event_id: int):
    async with async_session() as session:
        # Проверяем, не записан ли уже пользователь
        existing = await session.scalar(
            select(UserEvent)
            .where(UserEvent.user_id == user_id, UserEvent.event_id == event_id)
        )
        if existing:
            return False  # Уже записан
        
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
        
        # Обновляем только переданные поля
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
           
            # 2. Удаляем связи пользователей с этим ивентом (если есть таблица UserEvent)
            try:
                await session.execute(
                    delete(UserEvent).where(UserEvent.event_id == event_id)
                )
            except Exception as e:
                pass
            
            # 3. Удаляем сам ивент
            await session.execute(
                delete(Event).where(Event.id == event_id)
            )
            
            # 4. Коммитим изменения
            await session.commit()
            
            return True
            
        except Exception as e:
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
        #except Exception as e:
        #    await session.rollback()
        #    return False

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
        except Exception as e:
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
        except Exception as e:
            await session.rollback()
            return False

async def assign_reward_to_user(user_id: int, reward_id: int) -> bool:
    async with async_session() as session:
        try:
            # Проверяем, не получил ли пользователь уже эту награду
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
            # Удаляем все связи пользователей с наградами
            await session.execute(delete(UserReward))
            
            # Активируем все награды
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

async def create_tank(name: str, nation: str, discript: str, photo_id: str) -> bool:
    async with async_session() as session:
        try:
            tank = Tank(
                name=name,
                nation=nation,
                discript=discript,
                photo_id=photo_id
            )
            session.add(tank)
            await session.commit()
            return True
        except Exception as e:
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
                if hasattr(tank, key):
                    setattr(tank, key, value)
            
            await session.commit()
            return True
        except Exception as e:
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
        except Exception as e:
            await session.rollback()
            return False

async def get_all_nations():
    async with async_session() as session:
        result = await session.execute(
            select(Tank.nation).distinct().order_by(Tank.nation)
        )
        return [row[0] for row in result.all()]