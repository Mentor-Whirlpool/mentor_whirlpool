from telegram import bot
from telebot import types
from database import Database
from asyncio import create_task
from confirm import confirm


async def admin_start(message):
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


@bot.message_handler(func=lambda msg: msg.text == 'Добавить ментора')
async def add_mentor(message):
    """
    If from_user.id is in admins, parse the message to get new admin chat_id
    and add it with db.add_admin(). Otherwise, report an error to the sender.
    Should ask for confirmation

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    raise NotImplementedError


@bot.message_handler(func=lambda msg: msg.text == 'Удалить ментора')
async def delete_mentor(message):
    """
    If from_user.id is in admins, parse the message to get admin chat_id
    and remove it with db.remove_admin(). If the message is empty, remove
    sender

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    raise NotImplementedError


@bot.message_handler(func=lambda msg: msg.text == 'Список менторов')
async def list_mentors(message):
    """
    If from_user.id is in admins, print an InlineMarkupKeyboard of mentors.
    Clicking these buttons should trigger a mentor deletion with a confirmation

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    raise NotImplementedError
