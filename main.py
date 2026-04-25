import logging

from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config import API_TOKEN
from db import init_db
from middlewares import MainMiddleware
from handlers import register_all_handlers
from utils.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)

async def on_startup(dp):
    logger.info("Démarrage du bot ADONAÏ MONEY…")
    await init_db()
    dp.middleware.setup(MainMiddleware(dp.bot))
    register_all_handlers(dp)
    logger.info("Bot prêt. En écoute…")

if __name__ == "__main__":
    bot = Bot(token=API_TOKEN, parse_mode="HTML")
    dp = Dispatcher(bot, storage=MemoryStorage())
    
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
