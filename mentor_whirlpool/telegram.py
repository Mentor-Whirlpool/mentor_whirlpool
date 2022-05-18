import telebot
from os import environ

bot = telebot.TeleBot(environ['TELEGRAM_BOT_TOKEN'], parse_mode=None)
