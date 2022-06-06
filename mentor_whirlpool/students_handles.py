from telegram import bot
from telebot import types
from database import Database
from asyncio import create_task
from confirm import confirm

import pandas as pd
import test_database

add_own_subject_flag = False
add_work_flag = False

subject = ""
topic = ""


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
    commands = ['Добавить запрос', 'Удалить запрос', 'Мои запросы', 'Хочу стать ментором']
    return commands


@bot.message_handler(func=lambda msg: msg.text == 'Добавить запрос')
async def add_request(message):
    db = Database()

    markup = types.InlineKeyboardMarkup(row_width=1)
    subjects_ = await db.get_subjects()
    for sub in subjects_:
        markup.add(types.InlineKeyboardButton(sub, callback_data=f"add_request_{sub}"))
    markup.add(types.InlineKeyboardButton("Добавить свою тему", callback_data=f"own_request"))
    await bot.send_message(message.chat.id, f"Добавить запрос:", reply_markup=markup)


@bot.message_handler(func=lambda m: add_own_subject_flag is True)
async def add_own_subject(message):
    global add_own_subject_flag
    global add_work_flag
    global subject

    subject = message.text
    add_own_subject_flag = False
    add_work_flag = True

    await bot.send_message(message.chat.id, "Введите название работы:")


@bot.message_handler(func=lambda m: add_work_flag is True)
async def save_request(message):
    global subject
    global add_work_flag

    entered_topic = message.text
    student_dict = {'name': message.from_user.username, 'chat_id': message.chat.id, 'subjects': [subject],
                    'description': entered_topic}

    db = Database()
    await db.add_course_work(student_dict)

    add_work_flag = False
    await bot.send_message(message.chat.id, "Работа успешно добавлена! Ожидайте ответа ментора.")


@bot.message_handler(func=lambda msg: msg.text == 'Мои запросы')
async def my_requests(message):
    db = Database()
    id = await db.get_students(chat_id=message.chat.id)

    if not id:
        await bot.send_message(message.chat.id, f"Пока у вас нет запросов. Скорее добавьте первый!")
        await add_request(message)
    else:
        student_request = await db.get_course_works(student=id[0]['id'])
        if not student_request:
            await bot.send_message(message.chat.id, f"Пока у вас нет запросов.")
            await add_request(message)
        else:
            for course_work in student_request:
                await bot.send_message(message.chat.id,
                                       f"*Работа №{course_work['id']}*\nПредмет: {course_work['subjects'][0]}\n"
                                       f"Тема работы: {course_work['description']}",
                                       parse_mode='Markdown')


@bot.message_handler(func=lambda msg: msg.text == 'Удалить запрос')
async def remove_request(message):
    db = Database()
    id = await db.get_students(chat_id=message.chat.id)

    student_request = await db.get_course_works(student=id[0]['id'])

    markup = types.InlineKeyboardMarkup(row_width=1)
    for course_work in student_request:
        markup.add(
            types.InlineKeyboardButton(course_work['description'],
                                       callback_data=f"delete_request_{course_work['id']}"))

    await bot.send_message(message.chat.id, "Выберите работу, которую хотите удалить из списка запросов: ",
                           reply_markup=markup)


@bot.message_handler(func=lambda msg: msg.text == 'Хочу стать ментором')
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
    db = Database()
    admins = await db.get_admins()

    for admin in admins:
        admin_chat_id = admin['chat_id']
        await bot.send_message(admin_chat_id, f"Пользователь @{message.from_user.username} хочет стать ментором.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("add_request_"))
async def select_subject_callback(call):
    await bot.send_message(call.from_user.id, "Введите название работы:")
    global add_work_flag
    global subject

    add_work_flag = True
    subject = call.data[12:]
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("own_request"))
async def add_own_subject_callback(call):
    global add_own_subject_flag

    await bot.answer_callback_query(call.id)
    await bot.send_message(call.from_user.id, "Введите название предмета:")
    add_own_subject_flag = True


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_request_"))
async def delete_topic_callback(call):
    id_ = call.data[15:]
    db = Database()

    await db.remove_course_work(id_)
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.from_user.id, "Работа успешно удалена!")
