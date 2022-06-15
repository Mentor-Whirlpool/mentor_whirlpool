from telegram import bot
from telebot import types
from telebot import asyncio_filters
from telebot.asyncio_handler_backends import State, StatesGroup
from database import Database
from asyncio import gather, create_task
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
    commands = ['Добавить запрос', 'Удалить запрос', 'Мои запросы', 'Запросить доп. ментора', 'Хочу стать ментором',
                'Поддержка']
    return commands


@bot.message_handler(func=lambda msg: msg.text == 'Добавить запрос')
async def add_request(message):
    db = Database()
    if await db.check_is_mentor(message.from_user.id):
        return

    id = await db.get_students(chat_id=message.chat.id)

    if id and await db.get_accepted(student=id[0]['id']):
        await bot.send_message(message.from_user.id, "Вас уже обслуживает ментор")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    subjects_ = await db.get_subjects()
    for sub in subjects_:
        markup.add(types.InlineKeyboardButton(sub, callback_data=f"add_request_{sub}"))
    markup.add(types.InlineKeyboardButton("Добавить свою тему", callback_data="own_request"))

    await bot.send_message(message.chat.id, "Добавить запрос:", reply_markup=markup)


@bot.message_handler(func=lambda msg: msg.text == 'Запросить доп. ментора')
async def add_request(message):
    db = Database()
    if await db.check_is_mentor(message.from_user.id):
        return

    id = await db.get_students(chat_id=message.chat.id)
    accepted = None
    if id:
        accepted = await db.get_accepted(student=id[0]['id'])
    if not accepted:
        await bot.send_message(message.from_user.id, 'Вас ещё не курирует ментор')
        return
    await gather(db.readmission_work(accepted[0]['id']),
                 bot.send_message(message.from_user.id,
                                  'Вы успешно запросили доп. ментора!\n'
                                  'Если вы передумаете, вы можете отменить запрос, используя "Удалить запрос"'))


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

    if id:
        student_request = await db.get_course_works(student=id[0]['id'])
        course_work_names = [work['description'] for work in student_request]

        if entered_topic in course_work_names:
            await gather(bot.delete_state(message.from_user.id, message.chat.id),
                         bot.send_message(message.chat.id, "Работа с таким именем уже добавлена!"))
            return
    await gather(db.add_course_work(student_dict), bot.delete_state(message.from_user.id, message.chat.id),
                 bot.send_message(message.chat.id, "Работа успешно добавлена! Ожидайте ответа ментора. "
                                                   "\n\nЕсли вы захотите запросить дополнительного ментора, нажмите кнопку "
                                                   "*\"Запросить доп. ментора\"*", parse_mode="Markdown"))


@bot.message_handler(func=lambda msg: msg.text == 'Мои запросы')
async def my_requests(message):
    db = Database()
    if await db.check_is_mentor(message.from_user.id):
        return
    id = await db.get_students(chat_id=message.chat.id)

    if not id:
        await bot.send_message(message.from_user.id, "Пока у вас нет запросов. Скорее добавьте первый!")
        return

    student_request = create_task(db.get_course_works(student=id[0]['id']))
    if await db.get_accepted(student=id[0]['id']):
        mentor = await db.get_mentors(student=id[0]['id'])
        await bot.send_message(message.from_user.id,
                               f"Текущая принятая курсовая работа: *{id[0]['course_works'][0]['description']}*\n"
                               f"Твой ментор: *@{mentor[0]['name']}*", parse_mode="Markdown")
        student_request = await student_request
        if student_request:
            await bot.send_message(message.from_user.id,
                                   'У вас имеется запрос на доп. ментора по этой работе!'
                                   'Если хотите его удалить, воспользуйтесь "Удалить запрос"')
        return
    student_request = await student_request
    await gather(*[bot.send_message(message.chat.id,
                                    f"*Работа №{course_work['id']}*\nПредмет: {course_work['subjects'][0]}\n"
                                    f"Тема работы: {course_work['description']}", parse_mode="Markdown")
                   for course_work in student_request])


@bot.message_handler(func=lambda msg: msg.text == 'Удалить запрос')
async def remove_request(message):
    db = Database()
    if await db.check_is_mentor(message.from_user.id):
        return
    id = await db.get_students(chat_id=message.chat.id)

    if not id:
        await bot.send_message(message.from_user.id, "Пока у вас нет запросов. Скорее добавьте первый!")
        return

    student_request = create_task(db.get_course_works(student=id[0]['id']))
    markup = types.InlineKeyboardMarkup(row_width=1)
    if await db.get_accepted(student=id[0]['id']):
        student_request = await student_request
        if student_request:
            markup.add(types.InlineKeyboardButton('Запрос на доп. ментора', callback_data=f"delete_request_{student_request[0]['id']}"))
            markup.add(types.InlineKeyboardButton(f"Курсовая работа \"{id[0]['course_works'][0]['description']}\"",
                                                  callback_data=f"delete_finale_{id[0]['id']}"))
            await bot.send_message(message.from_user.id, 'Что вы хотите удалить?', reply_markup=markup)
            return

        markup.add(types.InlineKeyboardButton(f"Удалить курсовую \"{id[0]['course_works'][0]['description']}\"",
                                              callback_data=f"delete_finale_{id[0]['id']}"))

        await bot.send_message(message.from_user.id, 'Внимание! Вы собираетесь удалить свою курсовую работу!\n'
                                                     'Вас больше не будут курировать менторы',
                               reply_markup=markup)
        return
    else:
        student_request = await student_request

        for course_work in student_request:
            markup.add(
                types.InlineKeyboardButton(course_work['description'],
                                           callback_data=f"delete_request_{course_work['id']}"))

        await bot.send_message(message.chat.id, "Выберите работу, которую хотите удалить из списка запросов: ",
                               reply_markup=markup)


@bot.message_handler(func=lambda msg: msg.text == 'Хочу стать ментором')
async def mentor_resume(message):
    db = Database()
    if await db.check_is_mentor(message.from_user.id):
        return
    admins = await db.get_admins()

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton('Одобрить', callback_data='add_mentor_via_admin_' + str(message.from_user.id)))

    admin_chat_id = random.choice(admins)['chat_id']
    await gather(bot.send_message(admin_chat_id, f"Пользователь @{message.from_user.username} хочет стать ментором.",
                                  reply_markup=markup),
                 bot.send_message(message.chat.id, "Ваша заявка на рассмотрении. Ожидайте ответа от администратора!\n"))


@bot.callback_query_handler(func=lambda call: call.data.startswith("add_request_"))
async def select_subject_callback(call):
    await bot.send_message(call.from_user.id, f"*Тема: {call.data[12:]}*\n\n"
                                              f"Введите название работы. \n\n*Если вы не знаете, на какую тему будете писать работу, "
                                              f"просто напишите \"Я не знаю\":*", parse_mode='Markdown')

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
                 bot.send_message(call.from_user.id, "Работа успешно удалена!"),
                 bot.delete_message(call.message.chat.id, call.message.id))


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_finale"))
async def delete_finale(call):
    id_ = call.data[14:]

    db = Database()
    student = await db.get_students(id_)
    mentor = await db.get_mentors(student=id_)

    await gather(db.remove_student(id_), bot.answer_callback_query(call.id),
                 bot.send_message(call.from_user.id,
                                  "Ваша курсовая работа успешно удалена. Но вы всегда можете начать новую!"),
                 bot.send_message(mentor[0]['chat_id'],
                                  f"Студент @{student[0]['name']} удалил принятую вами "
                                  f"курсовую работу \"{student[0]['course_works'][0]['description']}\""),
                 bot.delete_message(call.message.chat.id, call.message.id))


bot.add_custom_filter(asyncio_filters.StateFilter(bot))
bot.add_custom_filter(asyncio_filters.IsDigitFilter())
