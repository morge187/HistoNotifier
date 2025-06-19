from sqlalchemy import select, update, delete, desc

from database.models import User, async_session # Импорты модели User и асинхронной сессии

async def set_user(tg_id): # Асинхронная функция для работы с пользователем
    async with async_session() as session: # Открываем асинхронную сессию
        user = await session.scalar(select(User).where(User.tg_id == tg_id)) # Запомните, что scalar может быть и scalars в мн. числе
        
        if not user: # Если пользователя с таким tg_id нет в базе данных
            session.add(User(tg_id=tg_id)) # Создаём нового пользователя
            await session.commit() # Сохраняем изменения в базе данных

        return user
    
    
async def set_status(tg_id, status): # Поскольку мы изменяем статус конкретного юзера по его tg_id, то этот параметр обязателен.
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user: # Проверка существования пользователя
            user.status = status # Изменение статуса пользователя
            await session.commit()