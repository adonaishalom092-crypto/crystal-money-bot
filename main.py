import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config import API_TOKEN
from db import init_db
from middlewares import MainMiddleware
from handlers import register_all_handlers
from utils.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)

async def main():
    logger.info("Démarrage du bot ADONAÏ MONEY…")
    await init_db()

    bot = Bot(token=API_TOKEN, parse_mode="HTML")
    dp = Dispatcher(bot, storage=MemoryStorage())

    dp.middleware.setup(MainMiddleware(bot))
    register_all_handlers(dp)

    logger.info("Bot prêt. En écoute…")
    from aiogram import executor
executor.start_polling(dp, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
