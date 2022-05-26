from telegram import bot
from telebot import types
from confirm import confirm
from database.necessities import Database


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

    return ['Курсовые', 'Темы', 'Мои темы', 'Установить темы']
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
    db = Database()
    course_works = [work['name'] for work in await db.get_course_works()]
    # course_works = [work['name'] for work in[{
    #     'name': 'w1',
    #     'description': 'd1'
    # }, {
    #     'name': 'w2',
    #     'description': 'd2'
    # }, {
    #     'name': 'w3',
    #     'description': 'd3'
    # }, {
    #     'name': 'w4',
    #     'description': 'd4'
    # }, ]]
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(*[types.InlineKeyboardButton(x, callback_data=x) for x in course_works])
    await bot.send_message(message.chat.id, 'Курсовые', reply_markup=markup)
    raise NotImplementedError


@bot.callback_query_handler(func=lambda call: True)
async def callback_query_work(call):
    db = Database()
    description = ''
    # course_works = [{
    #     'name': 'w1',
    #     'description': 'd1'
    # }, {
    #     'name': 'w2',
    #     'description': 'd2'
    # }, {
    #     'name': 'w3',
    #     'description': 'd3'
    # }, {
    #     'name': 'w4',
    #     'description': 'd4'
    # }, ]
    for work in await db.get_course_works():
    # for work in course_works:
        if work['name'] == call.data:
            description = work['description']
            break

    await bot.answer_callback_query(call.id, description, show_alert=True)


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
    db = Database()
    subjects_ = await db.get_subjects()
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(*[types.InlineKeyboardButton(x, callback_data=x) for x in subjects_])
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
    db = Database()
    my_subjects_ = []
    for mentor in await db.get_mentors():
        if mentor['chat_id'] == message.from_user.id:
            my_subjects_ = mentor['subjects']

    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(*[types.InlineKeyboardButton(x, callback_data=x) for x in my_subjects_])
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
