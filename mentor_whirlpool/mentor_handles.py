from telegram import bot
from telebot import types
from gettext import translation

#strings = translation('mentor', localedir='locales', languages=['RU']).gettext

async def mentor_start(message):
    raise NotImplementedError


@bot.message_handler(func=lambda msg: msg.text == 'Курсовые')
async def works(message):
    raise NotImplementedError


@bot.message_handler(func=lambda msg: msg.text == 'Темы')
async def subjects(message):
    raise NotImplementedError
