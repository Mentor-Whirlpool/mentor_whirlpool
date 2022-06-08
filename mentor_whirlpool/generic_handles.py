from telegram import bot
from telebot import types
from asyncio import create_task

from database import Database
from confirm import confirm


async def generic_start(message):
    """
    Should provide a starting point with a ReplyMarkupKeyboard
    It should contain all the following handles

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class

    Returns
    -------
    iterable
        Iterable with all handles texts
    """
    return ['Добавить работу', 'Удалить работу', 'Редактировать работу', 'Хочу быть ментором', 'Поддержка']


@bot.message_handler(func=lambda msg: msg.text == 'Добавить работу')
async def add_work(message):
    """
    Adds a course work with db.add_course_work() with confirmation
    If there is a mentor that has selected subjects in their preferences
    send them a notice of a new course work

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    raise NotImplementedError


@bot.message_handler(func=lambda msg: msg.text == 'Удалить работу')
async def remove_work(message):
    """
    Removes a course work with db.remove_course_work() with confirmation

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    raise NotImplementedError


@bot.message_handler(func=lambda msg: msg.text == 'Редактировать работу')
async def edit_work(message):
    """
    Edits a course work with db.modify_course_work()
    If there is a mentor that has selected subjects in their preferences
    send them a notice of a new course work. Should contain a cancel button

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    raise NotImplementedError


@bot.message_handler(func=lambda msg: msg.text == 'Хочу быть ментором')
async def mentor_resume(message):
    """
    Send a notice to random admin with contact details of requester
    Send a requester contact details of an admin
    Should request a confirmation

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    raise NotImplementedError


@bot.message_handler(func=lambda msg: msg.text == 'Поддержка')
async def request_support(message):
    """
    Send a notice to all supports
    Add new record to support_requests table with db.add_support_request(chat_id, name)

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    db = Database()
    await db.add_support_request(message.chat.id, message.from_user.username)
    for chat_id in await db.get_supports():
        await bot.send_message(chat_id, 'Пользователю нужна помощь')
    await bot.send_message(message.chat.id, 'Ждите ответ поддержки')
