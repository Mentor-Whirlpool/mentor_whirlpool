from telegram import bot
from telebot import types
from database import Database
from asyncio import create_task
from generic_handles import generic_start
from mentor_handles import mentor_start
from admin_handles import admin_start


@bot.message_handler(commands=['start'])
async def start(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    db = Database()
    if message.chat.id in await db.get_mentors():
        keyboard.add(*[types.KeyboardButton(task)
                       for task in await mentor_start(message)])
    else:
        keyboard.add(*[types.KeyboardButton(task)
                       for task in await generic_start(message)])
    if message.chat.id in await db.get_admins():
        keyboard.add(*[types.KeyboardButton(task)
                       for task in await admin_start(message)])
    bot.send_message(message.chat.id,
                     'Ваши опции приведены в клавиатуре снизу:',
                     reply_markup=keyboard, parse_mode='Html')
