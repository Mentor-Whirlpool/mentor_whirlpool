from telegram import bot
from telebot import types
from database import Database
from asyncio import create_task


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
