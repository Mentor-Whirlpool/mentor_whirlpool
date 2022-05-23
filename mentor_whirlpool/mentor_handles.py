from telegram import bot
from telebot import types
from confirm import confirm


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

    markup = types.ReplyKeyboardMarkup(row_width=2)
    btn_course_works = types.KeyboardButton('Курсовые')
    btn_subjects = types.KeyboardButton('Темы')
    btn_my_subjects = types.KeyboardButton('Мои темы')
    btn_add_subtr_subject = types.KeyboardButton('Установить темы')

    markup.add(btn_course_works, btn_subjects, btn_my_subjects, btn_add_subtr_subject)
    await bot.send_message(message.chat.id, 'Что делать?', reply_markup=markup)
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
    course_works = ['course1', 'course2', 'course3',
                    'course4']  # test without db.get_course_works()
    markup = types.ReplyKeyboardMarkup(row_width=3)
    markup.add(*[types.KeyboardButton(x) for x in course_works])
    await bot.send_message(message.chat.id, 'Курсовые', reply_markup=markup)
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
    course_works = ['theme1', 'theme2', 'theme3',
                    'theme4']  # test without db.subjects()
    markup = types.ReplyKeyboardMarkup(row_width=3)
    markup.add(*[types.KeyboardButton(x) for x in course_works])
    await bot.send_message(message.chat.id, 'Темы', reply_markup=markup)
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
    course_works = ['my_theme1', 'my_theme2', 'my_theme3',
                    'my_theme4']  # test without db.subjects()
    markup = types.ReplyKeyboardMarkup(row_width=3)
    markup.add(*[types.KeyboardButton(x) for x in course_works])
    await bot.send_message(message.chat.id, 'Мои темы', reply_markup=markup)
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
