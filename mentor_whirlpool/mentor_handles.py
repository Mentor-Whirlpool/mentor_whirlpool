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
    return ['Запросы', 'Мои темы', 'Мои студенты']


@bot.message_handler(func=lambda msg: msg.text == 'Запросы')
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
    # description - название курсовой, запросы спмсок кнопок
    db = Database()
    my_subjects_ = []
    for mentor in await db.get_mentors():
        if mentor['chat_id'] == message.from_user.id:
            my_subjects_ = mentor['subjects']
            break
    course_works = await db.get_course_works(my_subjects_)
    # course_works = [{
    #     'id': 'id1',
    #     'name': 'name1',
    #     'chat_id': 'id1',
    #     'description': 'd1'
    # }, {
    #     'id': 'id2',
    #     'name': 'name2',
    #     'chat_id': 'id2',
    #     'description': 'd2'
    # }, {
    #     'id': 'id3',
    #     'name': 'name3',
    #     'chat_id': 'id3',
    #     'description': 'd3'
    # }, {
    #     'id': 'id4',
    #     'name': 'name4',
    #     'chat_id': 'id4',
    #     'description': 'd4'
    # }, ]

    markup = types.InlineKeyboardMarkup()
    for work in course_works:
        markup.add(
            types.InlineKeyboardButton(f'{work["chat_id"]}\n{work["description"]}', callback_data='work_' + work['id']))

    await bot.send_message(message.chat.id, '*Доступные курсовые работы*', reply_markup=markup, parse_mode='markdown')


@bot.callback_query_handler(func=lambda call: call.data.startswith('work_'))
async def callback_query_work(call):
    await bot.answer_callback_query(call.id)

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


@bot.message_handler(func=lambda msg: msg.text == 'Темы')
async def subjects(message):
    """
    Should send a list of inline buttons from db.get_subjects() and a finish button

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
    Should send a list of inline buttons from db.get_subjects() with a from_user.id
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
    # my_subjects_ = ['sub1', 'sub2', 'sub3', 'sub4']
    my_subjects_ = []
    for mentor in await db.get_mentors():
        if mentor['chat_id'] == message.from_user.id:
            my_subjects_ = mentor['subjects']
            break

    markup = types.InlineKeyboardMarkup(row_width=3)
    add = types.InlineKeyboardButton('Добавить', callback_data='sub_to_add')

    if my_subjects_ is not None:
        delete = types.InlineKeyboardButton('Удалить', callback_data='sub_delete')
        markup.row(add, delete)
        markup.add(
            *[types.InlineKeyboardButton(subject, callback_data='subject_' + subject) for subject in my_subjects_])
    else:
        markup.add(add)

    await bot.send_message(message.chat.id, f'*Мои темы*', reply_markup=markup,
                           parse_mode='markdown')


# мои темы получаешь еще кнопки с темам, тыкаешь на кнопку получаешь список курсачей по этой теме (тоже кнопками) -> жмешь на курсач и принимаешь его


@bot.callback_query_handler(func=lambda call: call.data.startswith('subject_'))
async def callback_show_course_works_by_subject(call):
    db = Database()
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(*[types.InlineKeyboardButton(work, callback_data='work_' + work) for work in
                 await db.get_course_works([call.data[8:]])])  # добавление курсачей будет в callback_query_work
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.from_user.id, f'Курсовые работы по теме *{call.data[8:]}*', reply_markup=markup,
                           parse_mode='markdown')


@bot.callback_query_handler(func=lambda call: call.data == 'sub_to_add')
async def callback_show_subjects_to_add(call):
    db = Database()
    my_subjects_ = []

    for mentor in await db.get_mentors():
        if mentor['chat_id'] == call.from_user.id:
            my_subjects_ = mentor['subjects']
            break

    subjects_to_add = await db.get_subjects()

    for subject in subjects_to_add:
        if subject in my_subjects_:
            subjects_to_add.remove(subject)

    # subjects_to_add = ['sub1', 'sub2', 'sub3', 'sub4']
    markup = types.InlineKeyboardMarkup()
    markup.add(
        *[types.InlineKeyboardButton(subject, callback_data='sub_add_' + subject) for subject in subjects_to_add])
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.from_user.id, '*Все темы*', reply_markup=markup, parse_mode='markdown')


@bot.callback_query_handler(func=lambda call: call.data.startswith('sub_add_'))
async def callback_add_subject(call):
    await bot.answer_callback_query(call.id)


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


@bot.message_handler(func=lambda msg: msg.text == 'Мои студенты')
async def my_students(message):
    db = Database()
    # my_students_ = ['st1','st2','st3']
    my_students_ = []
    for mentor in await db.get_mentors():
        if mentor['chat_id'] == message.from_user.id:
            my_students_ = mentor['students']
            break
    str_my_students_ = '\n'.join(my_students_)
    await bot.send_message(message.chat.id, f'*Список моих студентов*\n{str_my_students_}', parse_mode='markdown')
