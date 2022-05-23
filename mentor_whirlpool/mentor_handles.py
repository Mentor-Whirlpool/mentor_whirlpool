from telegram import bot
from telebot import types
from common import confirm
# from gettext import translation

# strings = translation('mentor', localedir='locales', languages=['RU']).gettext


async def mentor_start(message):
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


@bot.message_handler(func=lambda msg: msg.text == 'Курсовые')
async def works(message):
    """
    Should send a list of inline buttons from db.get_course_works()

    Clicking on a button should produce a description of selected course work
    and a prompt to accept a work to lead. This prompt should ask for
    confirmation

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    raise NotImplementedError


@bot.message_handler(func=lambda msg: msg.text == 'Темы')
async def subjects(message):
    """
    Should send a list of inline buttons from db.subjects() and a finish button

    Buttons with subjects can be clicked to narrow the list
    Clicking on a finish button should produce a list of course works with
    selected subject. Those buttons should behave the same way they behave in
    works handle

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    raise NotImplementedError


@bot.message_handler(func=lambda msg: msg.text == 'Мои темы')
async def my_subjects(message):
    """
    Should send a list of inline buttons from db.subjects() with a from_user.id
    argument and a finish button

    Buttons with subjects can be clicked to narrow the list
    Clicking on a finish button should produce a list of course works with
    selected subject. Those buttons should behave the same way they behave in
    works handle

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    raise NotImplementedError


@bot.message_handler(func=lambda msg: msg.text == 'Установить темы')
async def set_subjects(message):
    """
    Should ask for addition/subtraction of subjects. Subsequent messages
    should be treated accordingly. If in addition mode, an unknown subject is
    received, add it. If in subtraction mode, an unknown subject is received,
    reply with a warning and do nothing

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    raise NotImplementedError
