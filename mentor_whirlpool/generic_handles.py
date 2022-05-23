from telegram import bot
from telebot import types
from database import db
from asyncio import create_task
from common import confirm


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
    raise NotImplementedError


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
