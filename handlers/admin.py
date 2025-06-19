import os
from aiogram import Router
from aiogram.filters import Filter, Command
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()

admin = Router()

ADMIN_ID = int(os.getenv("ADMIN", "0")) # Получаем ID пользователя и преобразуем его в строку, дабы избежать ошибок, если ID не будет, вернется 0

class Admin(Filter): # Кастомный фильтр, название класса "Admin", можете называть по-своему
    def __init__(self): # Конструктор инициализирует фильтр, сохраняя ID администратора
        self.admin_id = ADMIN_ID # Поле для дальнейшего использования

    async def __call__(self, message: Message): # По правилам ООП, создается автоматически. Сравнивает ID пользователя (message.from_user.id) с (self.admin_id)
        return message.from_user.id == self.admin_id

@admin.message(Admin(), Command('apanel')) # Соответственно, устанавливаем наш фильтр для проверки
async def apanel(message: Message):
    await message.answer('Это панель администратора')