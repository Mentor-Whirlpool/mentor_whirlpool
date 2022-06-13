from mentor_whirlpool.telegram import bot
from telebot import types
from asyncio import create_task
import logging

from mentor_whirlpool.database import Database
from mentor_whirlpool.students_handles import generic_start, student_help
from mentor_whirlpool.mentor_handles import mentor_start, mentor_help
from mentor_whirlpool.admin_handles import admin_start, admin_help
from mentor_whirlpool.support_handles import support_start


@bot.message_handler(commands=['start'])
async def start(message):
    help_task = create_task(help(message))
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
    await help_task


@bot.message_handler(commands=['help'])
async def help(message):
    db = Database()
    if await db.check_is_mentor(message.from_user.id):
        logging.warn(f'chat_id: {message.from_user.id} is mentor and requested help')
        await bot.send_message(message.from_user.id,
                               await mentor_help(), parse_mode='html')
    elif await db.check_is_admin(message.from_user.id):
        logging.warn(f'chat_id: {message.from_user.id} is admin and requested help')
        await bot.send_message(message.from_user.id,
                               await admin_help(), parse_mode='html')
    elif await db.check_is_support(message.from_user.id):
        logging.warn(f'chat_id: {message.from_user.id} is support and requested help')
        await bot.send_message(message.from_user.id,
                               'Ого, гуру нужна помощь? Набираем 911!')
    else:
        logging.warn(f'chat_id: {message.from_user.id} is student and requested help')
        await bot.send_message(message.from_user.id,
                               await student_help, parse_mode='html')
