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
    return ['Менторы', 'Запросы (админ)']


@bot.message_handler(func=lambda msg: msg.text == 'Запросы (админ)')
async def course_work(message):
    db = Database()
    course_works = await db.get_course_works()
    messages = []
    for work in course_works:
        messages.append(f'{work["student"]}\n{work["description"]}')
    message_course_works = '--------\n'.join(messages)
    await bot.send_message(message.chat.id, message_course_works)


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


@bot.message_handler(func=lambda msg: msg.text == 'Менторы')
async def list_mentors(message):
    """
    If from_user.id is in admins, print an InlineMarkupKeyboard of mentors.
    Clicking these buttons should trigger a mentor deletion with a confirmation

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    db = Database()
    mentors = await db.get_mentors()

    for mentor in mentors:

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Выбрать', callback_data='choose_mentor_' + str(mentor['chat_id'])))

        if mentor['subjects']:
            subjects_count_dict = dict.fromkeys(mentor['subjects'], 0)

            for student in mentor['students']:

                for subject in student['course_works'][0]['subjects']:
                    if subject in subjects_count_dict:
                        subjects_count_dict[subject] += 1
                    else:
                        subjects_count_dict[subject] = 1

            message_subjects = '\n'.join(f'{k} - {v}' for k, v in subjects_count_dict.items())
        else:
            message_subjects = 'Нет выбранных тем'

        await bot.send_message(message.chat.id, f'*@{mentor["name"]}*\n{message_subjects}', reply_markup=markup,
                               parse_mode='markdown')


@bot.callback_query_handler(func=lambda call: call.data.startswith('choose_mentor_'))
async def callback_mentors_info(call):
    db = Database()
    mentor_info = (await db.get_mentors(chat_id=int(call.data[14:])))[0]
    # mentor_info = {}
    # for mentor in mentors:
    #     if mentor['id'] == int(call.data[14:]):
    #         mentor_info = mentor
    #         break
    message_subjects = 'Нет выбранных тем'
    message_students = 'Нет студентов'
    if mentor_info['subjects']:
        message_subjects = '\n'.join(mentor_info['subjects'])
    if mentor_info['students']:
        message_students = '\n'.join(student['name'] for student in mentor_info['students'])
    markup = types.InlineKeyboardMarkup()
    edit_subjects = types.InlineKeyboardButton('Изменить тему', callback_data='edit_subjects_' + call.data[14:])
    edit_students = types.InlineKeyboardButton('Изменить студентов', callback_data='edit_students_' + call.data[14:])
    markup.add(edit_students, edit_subjects)
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.from_user.id,
                           f'@{mentor_info["name"]}\n----Темы----\n{message_subjects}\n----Студенты----\n{message_students}',
                           reply_markup=markup)


# students
@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_students_'))
async def edit_students(call):
    markup = types.InlineKeyboardMarkup()
    add = types.InlineKeyboardButton('Добавить студента', callback_data='add_student_' + call.data[14:])
    delete = types.InlineKeyboardButton('Удалить студента', callback_data='delete_student_info_' + call.data[14:])
    markup.add(add, delete)
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.from_user.id, 'Что сделать со студентами?', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('add_student_'))
async def callback_add_student(call):
    db = Database()
    await bot.answer_callback_query(call.id)


# для ввода от пользователя
#     force = types.ForceReply(selective=False)
#     print('fff')
#     await bot.send_message(message.chat.id, 'test', reply_markup=force)
#
#
# @bot.message_handler(func=lambda message: message.reply_to_message and message.reply_to_message.text.startswith('test'))
# async def answ(message):
#     print(message.text)


@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_student_info_'))
async def callback_delete_student_info(call):
    db = Database()
    markup = types.InlineKeyboardMarkup(row_width=3)
    test = (await db.get_mentors(chat_id=int(call.data[20:])))[0]['students']
    markup.add(
        *[types.InlineKeyboardButton(f'{student["name"]}',
                                     callback_data=f'delete_stud_{call.data[20:]}_{str(student["course_works"][0]["id"])}')
          for student in (await db.get_mentors(chat_id=int(call.data[20:])))[0]['students']])
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.from_user.id, 'Выберите какого студента удалить', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_stud_'))
async def callback_delete_student(call):
    db = Database()
    mentor_id, work_id = call.data[12:].split('_')
    mentor_id = (await db.get_mentors(chat_id=mentor_id))[0]['id']
    # await bot.send_message((await db.get_mentors(id=mentor_id))[0]['chat_id'], f'Студент {}')
    await db.reject_work(mentor_id, work_id)
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.from_user.id, 'Студент удален')


# subjects
@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_subjects_'))
async def callback_edit_subjects(call):
    pass
