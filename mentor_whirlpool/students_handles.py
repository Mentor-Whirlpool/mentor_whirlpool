from telegram import bot
from telebot import types
from telebot import asyncio_filters
from telebot.asyncio_handler_backends import State, StatesGroup
from database import Database
from asyncio import gather
from confirm import confirm
import random


class StudentStates(StatesGroup):
    add_work_flag = State()
    add_own_subject_flag = State()
    subject = State()
    topic = State()


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


@bot.message_handler(state=StudentStates.add_own_subject_flag)
async def add_own_subject(message):
    db = Database()
    subjects = await db.get_subjects()

    if message.text in subjects:
        await gather(bot.delete_state(message.from_user.id, message.chat.id),
                     bot.send_message(message.chat.id, "Предмет с таким названием уже существует!"))
    else:
        async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['subject'] = message.text

        db = Database()
        subjects = await db.get_subjects()

        await gather(bot.set_state(message.from_user.id, StudentStates.add_work_flag, message.chat.id),
                     bot.send_message(message.chat.id, "Введите название работы:"))


@bot.message_handler(state=StudentStates.add_work_flag)
async def save_request(message):
    entered_topic = message.text
    student_dict = dict()

    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        student_dict = {'name': message.from_user.username, 'chat_id': message.chat.id, 'subjects': [data['subject']],
                        'description': entered_topic}

    db = Database()
    id = await db.get_students(chat_id=message.chat.id)
    student_request = await db.get_course_works(student=id[0]['id'])
    course_work_names = [work['description'] for work in student_request]

    if entered_topic in course_work_names:
        await gather(bot.delete_state(message.from_user.id, message.chat.id),
                     bot.send_message(message.chat.id, "Работа с таким именем уже добавлена!"))
    else:
        await gather(db.add_course_work(student_dict), bot.delete_state(message.from_user.id, message.chat.id),
                     bot.send_message(message.chat.id, "Работа успешно добавлена! Ожидайте ответа ментора."))


@bot.message_handler(func=lambda msg: msg.text == 'Мои запросы')
async def my_requests(message):
    db = Database()
    id = await db.get_students(chat_id=message.chat.id)

    if not id:
        await bot.send_message(message.chat.id, f"Пока у вас нет запросов. Скорее добавьте первый!")
        return
    student_request = await db.get_course_works(student=id[0]['id'])
    for course_work in student_request:
        await bot.send_message(message.chat.id,
                               f"*Работа №{course_work['id']}*\nПредмет: {course_work['subjects'][0]}\n"
                               f"Тема работы: {course_work['description']}", parse_mode="Markdown")


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
    db = Database()
    admins = await db.get_admins()

    admin_chat_id = random.choice(admins)['chat_id']
    await gather(bot.send_message(admin_chat_id, f"Пользователь @{message.from_user.username} хочет стать ментором."),
                 bot.send_message(message.chat.id, "Ваша заявка на рассмотрении. Ожидайте ответа от администратора!"))


@bot.callback_query_handler(func=lambda call: call.data.startswith("add_request_"))
async def select_subject_callback(call):
    await bot.send_message(call.from_user.id, "Введите название работы:")

    await bot.set_state(call.from_user.id, StudentStates.add_work_flag, call.message.chat.id)
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['subject'] = call.data[12:]
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("own_request"))
async def add_own_subject_callback(call):
    await bot.set_state(call.from_user.id, StudentStates.add_own_subject_flag, call.message.chat.id)

    await gather(bot.answer_callback_query(call.id),
                 bot.send_message(call.from_user.id, "Введите название предмета:"))


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_request_"))
async def delete_topic_callback(call):
    id_ = call.data[15:]
    db = Database()

    await gather(db.remove_course_work(id_), bot.answer_callback_query(call.id),
                 bot.send_message(call.from_user.id, "Работа успешно удалена!"))


bot.add_custom_filter(asyncio_filters.StateFilter(bot))
bot.add_custom_filter(asyncio_filters.IsDigitFilter())
