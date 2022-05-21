from telebot.async_telebot import AsyncTeleBot
from os import environ

bot = AsyncTeleBot(environ['TELEGRAM_BOT_TOKEN'], parse_mode=None)
