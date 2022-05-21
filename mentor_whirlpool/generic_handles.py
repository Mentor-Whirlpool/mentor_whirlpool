from telegram import bot
from telebot import types
from database import db
from mentor_handles import mentor_start
from admin_handles import admin_start
from asyncio import create_task

async def generic_start(message):
    raise NotImplementedError

@bot.message_handler(commands=['start'])
async def start(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if message.chat.id in await db.get_mentors():
        keyboard.add(*[types.KeyboardButton(task)
                       for task in await mentor_start(message)])
    else:
        keyboard.add(*[types.KeyboardButton(task)
                       for task in await generic_start(message)])
    if message.chat.id in await db.get_admins():
        keyboard.add(*[types.KeyboardButton(task)
                       for task in await admin_start(message)])


@bot.message_handler(func=lambda msg: msg.text == 'Добавить работу')
async def add_work(message):
    raise NotImplementedError


@bot.message_handler(func=lambda msg: msg.text == 'Удалить работу')
async def remove_work(message):
    raise NotImplementedError


@bot.message_handler(func=lambda msg: msg.text == 'Редактировать работу')
async def edit_work(message):
    raise NotImplementedError
