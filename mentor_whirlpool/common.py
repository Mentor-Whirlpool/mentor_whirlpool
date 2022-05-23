from telegram import bot
from telebot import types
from database import db
from asyncio import create_task
from generic_handles import generic_start
from mentor_handles import mentor_start
from admin_handles import admin_start


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
    bot.send_message(message.chat.id,
                     'Ваши опции приведены в клавиатуре снизу:',
                     reply_markup=keyboard, parse_mode='Html')


async def confirm(message, callback_yes, callback_no=None):
    """
    Should ask for user confirmation. If user replies with yes, call the
    callback. Otherwise, if callback_no is not None, call it

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    callback_yes : function
    callback_no : function or None
    """
    raise NotImplementedError
