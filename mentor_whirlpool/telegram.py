from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage
from os import environ

bot = AsyncTeleBot(environ['TELEGRAM_BOT_TOKEN'], state_storage=StateMemoryStorage(), parse_mode='Markdown')
