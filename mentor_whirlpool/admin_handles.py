from telegram import bot
from telebot import types
from database import db
from asyncio import create_task


async def admin_start(message):
    raise NotImplementedError


@bot.message_handler(func=lambda msg: msg.text == 'Добавить ментора')
async def add_mentor(message):
    raise NotImplementedError


@bot.message_handler(func=lambda msg: msg.text == 'Удалить ментора')
async def delete_mentor(message):
    raise NotImplementedError


@bot.message_handler(func=lambda msg: msg.text == 'Список менторов')
async def list_mentors(message):
    raise NotImplementedError
