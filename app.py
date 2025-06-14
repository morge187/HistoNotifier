import asyncio
import os
from dotenv import load_dotenv
from handlers import handlers

load_dotenv()

from aiogram import Bot, Dispatcher

bot = Bot(token=os.getenv('TOKEN'))
dp = Dispatcher()


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    for router in handlers:
        dp.include_router(router)
    await dp.start_polling(bot)
  

if __name__ == '__main__':
    print('Bot has started')
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Bot has stopped')