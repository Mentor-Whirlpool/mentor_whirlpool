from telegram import bot
from telebot import types
import logging

from database import Database
from students_handles import generic_start
from mentor_handles import mentor_start
from admin_handles import admin_start
from support_handles import support_start


@bot.message_handler(commands=['start'])
async def start(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    db = Database()
    if await db.check_is_support(message.from_user.id):
        logging.warn(f'chat_id: {message.from_user.id} is support')

        keyboard.add(*[types.KeyboardButton(task)
                       for task in await support_start(message)])
        await bot.send_message(message.chat.id,
                               'Ваши опции приведены в клавиатуре снизу:',
                               reply_markup=keyboard, parse_mode='Html')
        return

    if await db.check_is_mentor(message.from_user.id):
        logging.warn(f'chat_id: {message.from_user.id} is mentor')
        keyboard.add(*[types.KeyboardButton(task)
                       for task in await mentor_start(message)])
    elif await db.check_is_admin(message.from_user.id):
        logging.warn(f'chat_id: {message.from_user.id} is admin')
        keyboard.add(*[types.KeyboardButton(task)
                       for task in await admin_start(message)])
    else:
        logging.warn(f'chat_id: {message.from_user.id} is student')
        keyboard.add(*[types.KeyboardButton(task)
                       for task in await generic_start(message)])
    await bot.send_message(message.from_user.id,
                           'Ваши опции приведены в клавиатуре снизу:',
                           reply_markup=keyboard, parse_mode='Html')
