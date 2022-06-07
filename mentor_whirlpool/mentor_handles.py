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
    return ['Запросы', 'Мои темы', 'Мои студенты', 'Поддержка']


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
    db = Database()
    my_subjects_ = (await db.get_mentors(chat_id=message.from_user.id))[0]['subjects']
    if my_subjects_:
        course_works = await db.get_course_works(subjects=my_subjects_)
        markup = types.InlineKeyboardMarkup()

        for work in course_works:
            markup.add(
                types.InlineKeyboardButton(
                    f'@{(await db.get_students(work["student"]))[0]["name"]}\n{work["description"]}',
                    callback_data='work_' + str(work['id'])))

        await bot.send_message(message.chat.id, '*Доступные курсовые работы*', reply_markup=markup,
                               parse_mode='markdown')
    else:
        await bot.send_message(message.chat.id, '*Сначала добавьте темы*', parse_mode='markdown')


@bot.callback_query_handler(func=lambda call: call.data.startswith('work_'))
async def callback_query_work(call):
    db = Database()
    my_id = (await db.get_mentors(chat_id=call.from_user.id))[0]['id']
    course_work_info = (await db.get_course_works(int(call.data[5:])))[0]

    await db.accept_work(my_id, call.data[5:])
    for work in (await db.get_students(student=course_work_info["student"]))[0]['course_works']:
        await db.remove_course_work(work['id'])
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.from_user.id,
                           f'Вы взялись за *{course_work_info["description"]}*\nНапишите @{(await db.get_students(student=course_work_info["student"]))[0]["name"]}',
                           )


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
    my_subjects_ = (await db.get_mentors(chat_id=message.from_user.id))[0]['subjects']

    markup = types.InlineKeyboardMarkup(row_width=3)
    add = types.InlineKeyboardButton('Добавить', callback_data='sub_to_add')
    message_subjects = '*Мои темы*\n'
    if my_subjects_:
        delete = types.InlineKeyboardButton('Удалить', callback_data='sub_to_delete')
        markup.row(add, delete)
        message_subjects += '\n'.join(my_subjects_)

    else:
        markup.add(add)

    await bot.send_message(message.chat.id, f'{message_subjects}', reply_markup=markup,
                           parse_mode='markdown')


# мои темы получаешь еще кнопки с темам, тыкаешь на кнопку получаешь список курсачей по этой теме (тоже кнопками) -> жмешь на курсач и принимаешь его

# @bot.callback_query_handler(func=lambda call: call.data.startswith('subject_'))
# async def callback_show_course_works_by_subject(call):
#     db = Database()
#     markup = types.InlineKeyboardMarkup(row_width=3)
#     markup.add(
#         *[types.InlineKeyboardButton(f'{work["student"]} {work["description"]}',
#                                      callback_data='work_' + str(work['id'])) for work in
#           await db.get_course_works([call.data[8:]])])  # добавление курсачей будет в callback_query_work
#     await bot.answer_callback_query(call.id)
#     await bot.send_message(call.from_user.id, f'Курсовые работы по теме *{call.data[8:]}*', reply_markup=markup,
#                            parse_mode='markdown')


@bot.callback_query_handler(func=lambda call: call.data == 'sub_to_add')
async def callback_show_subjects_to_add(call):
    db = Database()
    my_subjects_ = (await db.get_mentors(chat_id=call.from_user.id))[0]['subjects']

    if not my_subjects_:
        my_subjects_ = []

    subjects_to_add = await db.get_subjects()

    for subject in my_subjects_:
        if subject in my_subjects_:
            subjects_to_add.remove(subject)

    if subjects_to_add:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            *[types.InlineKeyboardButton(subject, callback_data='sub_add_' + subject) for subject in subjects_to_add])
        await bot.send_message(call.from_user.id, '*Все темы*', reply_markup=markup, parse_mode='markdown')
    else:
        await bot.send_message(call.from_user.id, '*Вы добавили все доступные темы*', parse_mode='markdown')
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('sub_add_'))
async def callback_add_subject(call):
    db = Database()
    my_id = (await db.get_mentors(chat_id=call.from_user.id))[0]['id']

    if not (await db.get_mentors(chat_id=call.from_user.id))[0]['subjects'] or call.data[8:] not in \
            (await db.get_mentors(chat_id=call.from_user.id))[0]['subjects']:
        await db.add_mentor_subjects(my_id, [call.data[8:]])
        await bot.send_message(call.from_user.id, f'Тема *{call.data[8:]}* успешно добавлена', parse_mode='markdown')
    else:
        await bot.send_message(call.from_user.id, f'Тема *{call.data[8:]}* уже была добавлена', parse_mode='markdown')
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == 'sub_to_delete')
async def callback_show_subjects_to_delete(call):
    db = Database()
    my_subjects_ = (await db.get_mentors(chat_id=call.from_user.id))[0]['subjects']

    markup = types.InlineKeyboardMarkup()
    markup.add(
        *[types.InlineKeyboardButton(subject, callback_data='sub_delete_' + subject) for subject in my_subjects_])
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.from_user.id, '*Удалить тему*', reply_markup=markup, parse_mode='markdown')


@bot.callback_query_handler(func=lambda call: call.data.startswith('sub_delete_'))
async def callback_add_subject(call):
    db = Database()
    my_id = (await db.get_mentors(chat_id=call.from_user.id))[0]['id']

    await db.remove_mentor_subject(my_id, call.data[11:])
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.from_user.id, f'Тема *{call.data[11:]}* успешно удалена', parse_mode='markdown')


@bot.message_handler(func=lambda msg: msg.text == 'Мои студенты')
async def my_students(message):
    db = Database()

    mentor_info = (await db.get_mentors(chat_id=message.from_user.id))[0]
    my_students_ = mentor_info['students']

    if not my_students_:
        str_my_students_ = 'У Вас нет студентов!'
    else:

        str_my_students_ = '\n'.join(
            '@' + student['name'] + ' - ' + student["course_works"][0]["description"] for student
            in my_students_)
    await bot.send_message(message.chat.id, f'Список моих студентов\n{str_my_students_}')
