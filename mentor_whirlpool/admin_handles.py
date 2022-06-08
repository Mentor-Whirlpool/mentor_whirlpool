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
        messages.append(f'@{(await db.get_students(work["student"]))[0]["name"]}\n{work["description"]}')
    message_course_works = '\n--------\n'.join(messages)
    await bot.send_message(message.chat.id, message_course_works)


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
                        continue

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
    markup.add(
        *[types.InlineKeyboardButton(f'{student["name"]}',
                                     callback_data=f'delete_stud_{call.data[20:]}_{str(student["course_works"][0]["id"])}_{student["id"]}')
          for student in (await db.get_mentors(chat_id=int(call.data[20:])))[0]['students']])
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.from_user.id, 'Выберите какого студента удалить', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_stud_'))
async def callback_delete_student(call):
    db = Database()
    mentor_id, work_id, student_id = call.data[12:].split('_')
    student_info = (await db.get_students(student=student_id))[0]
    await bot.send_message(mentor_id, f'Студент @{student_info["name"]} удален')
    await bot.send_message(student_info['chat_id'],
                           f'@{(await db.get_mentors(chat_id=mentor_id))[0]["name"]} больше не Ваш ментор')
    mentor_id = (await db.get_mentors(chat_id=mentor_id))[0]['id']

    await db.reject_work(mentor_id, work_id)
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.from_user.id, 'Студент удален')


# subjects
@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_subjects_'))
async def callback_edit_subjects(call):
    markup = types.InlineKeyboardMarkup()
    add = types.InlineKeyboardButton('Добавить тему', callback_data='add_subject_' + call.data[14:])
    delete = types.InlineKeyboardButton('Удалить тему', callback_data='delete_subject_info_' + call.data[14:])
    markup.add(add, delete)
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.from_user.id, 'Что сделать с темами?', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_subject_info_'))
async def callback_delete_subject_info(call):
    db = Database()
    mentor_subjects = (await db.get_mentors(chat_id=call.data[20:]))[0]['subjects']

    markup = types.InlineKeyboardMarkup()
    markup.add(
        *[types.InlineKeyboardButton(subject, callback_data='delete_subject_' + subject + '_' + call.data[20:]) for
          subject in mentor_subjects])
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.from_user.id,
                           f'Удалить тему у ментора @{(await db.get_mentors(chat_id=call.data[20:]))[0]["name"]}',
                           reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_subject_'))
async def callback_delete_subject(call):
    db = Database()
    subject, mentor_chat_id = call.data[15:].split('_')
    mentor_id = (await db.get_mentors(chat_id=mentor_chat_id))[0]['id']

    await db.remove_mentor_subject(mentor_id, subject)
    await bot.send_message(mentor_chat_id, f'Тема {subject} успешно удалена админом')
    await bot.send_message(call.from_user.id,
                           f'Тема {subject} успешно удалена у @{(await db.get_mentors(chat_id=mentor_chat_id))[0]["name"]}',
                           )
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('add_subject_'))
async def callback_add_subject_info(call):
    db = Database()
    mentor_chat_id = call.data[12:]

    force = types.ForceReply(selective=False)
    await bot.send_message(call.from_user.id, 'Добавлять тему/темы строго в формате \'тема1;тема2;тема3')
    await bot.send_message(call.from_user.id, f'Добавить тему для {mentor_chat_id}', reply_markup=force)
    await bot.answer_callback_query(call.id)


@bot.message_handler(
    func=lambda message: message.reply_to_message and message.reply_to_message.text.startswith('Добавить тему для '))
async def callback_user_add_subject(message):
    db = Database()
    mentor_chat_id = message.reply_to_message.text[18:]
    mentor_id = (await db.get_mentors(chat_id=mentor_chat_id))[0]['id']
    subjects_to_add = message.text.split(';')
    for subject in subjects_to_add:

        await db.add_subject(subject)

        if not (await db.get_mentors(chat_id=mentor_chat_id))[0]['subjects'] or subject not in \
                (await db.get_mentors(chat_id=mentor_chat_id))[0]['subjects']:
            await db.add_mentor_subjects(mentor_id, [subject])
            await bot.send_message(message.chat.id, f'Тема *{subject}* успешно добавлена', parse_mode='markdown')
        else:
            await bot.send_message(message.from_user.id, f'Тема *{subject}* уже была добавлена', parse_mode='markdown')
