import asyncio
import os
from dotenv import load_dotenv
from handlers import handlers

load_dotenv()

from aiogram import Bot, Dispatcher
from database.models import async_main

async def main():
    bot = Bot(token=os.getenv('TOKEN'))
    dp = Dispatcher()
    await bot.delete_webhook(drop_pending_updates=True)
    for router in handlers:
        dp.include_router(router)
    dp.startup.register(startup) 
    await dp.start_polling(bot)

async def startup(dispatcher: Dispatcher): # !!!
    await async_main()
  
if __name__ == '__main__':
    print('Bot has started')
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Bot has stopped')