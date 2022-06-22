from telegram import bot
from telebot import types
from telebot import asyncio_filters
from telebot.asyncio_handler_backends import State, StatesGroup
from database import Database
from asyncio import gather, create_task
from confirm import confirm
import random
import logging


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
    commands = ['Добавить запрос', 'Удалить запрос', 'Мои запросы',
                'Хочу стать ментором', 'Поддержка']
    return commands


@bot.message_handler(func=lambda msg: msg.text == 'Добавить запрос')
async def add_request(message):
    db = Database()
    logging.debug(f'chat_id: {message.from_user.id} is in ADD_REQUEST')
    if await db.check_is_mentor(message.from_user.id):
        logging.warn(f'chat_id: {message.from_user.id} is a mentor')
        return

    id = await db.get_students(chat_id=message.chat.id)

    stud_accepted_subj = []
    if id:
        stud_accepted = await db.get_accepted(student=id[0]['id'])
        for work in stud_accepted:
            stud_accepted_subj += work['subjects']
    markup = types.InlineKeyboardMarkup(row_width=1)
    if id and stud_accepted_subj:
        if set(await db.get_subjects()) == set(stud_accepted_subj):
            await bot.send_message(message.from_user.id,
                                   'Вы уже добавили все возможные темы!\n'
                                   'Если у вас остались вопросы, обратитесь в поддержку')
            return
        if len(stud_accepted_subj) > 2:
            await bot.send_message(message.from_user.id,
                                   'Вас уже обслуживает доп. ментор!\n'
                                   'Если у вас остались вопросы, обратитесь в поддержку')
            return
        markup.add(*[types.InlineKeyboardButton(sub, callback_data=f'readm_{sub}')
                     for sub in await db.get_subjects()
                     if sub not in stud_accepted_subj])
        await bot.send_message(message.from_user.id,
                               "Вас уже обслуживает ментор\n"
                               "Создаём запрос на доп. ментора!\n"
                               "Выберите тему, которая вас интересует:",
                               reply_markup=markup)
        return
    markup.add(*[types.InlineKeyboardButton(sub, callback_data=f'add_request_{sub}')
                 for sub in await db.get_subjects()
                 if sub not in stud_accepted_subj])
    logging.debug(f'chat_id: {message.from_user.id} preparing ADD_REQUEST')
    await bot.send_message(message.chat.id, "Добавить запрос:", reply_markup=markup)
    logging.debug(f'chat_id: {message.from_user.id} done ADD_REQUEST')


@bot.callback_query_handler(func=lambda call: call.data.startswith('readm_'))
async def readmission_request(call):
    db = Database()
    logging.debug(f'chat_id: {call.from_user.id} is in ADDITIONAL_MENTOR')

    id = await db.get_students(chat_id=call.from_user.id)
    accepted = None
    if id:
        accepted = await db.get_accepted(student=id[0]['id'])
    # should be possible if button is clicked after student decides to nuke himself
    if not accepted:
        await bot.send_message(call.from_user.id, 'Вас ещё не курирует ментор')
        return

    cw_id = await db.readmission_work(accepted[0]['id'], call.data[6:])
    accept_markup = types.InlineKeyboardMarkup(row_width=1)
    accept_markup.add(types.InlineKeyboardButton('Принять', callback_data=f'mnt_work_{cw_id}'))
    mentors_to_alert = [ment['chat_id'] for ment in await db.get_mentors()
                        if call.data[6:] in ment['subjects']]
    logging.debug(f'chat_id: {call.from_user.id} preparing ADD_REQUEST')
    await gather(bot.answer_callback_query(call.id),
                 bot.send_message(call.from_user.id,
                                  'Вы успешно запросили доп. ментора!\n'
                                  'Если вы передумаете, вы можете отменить '
                                  'запрос, используя "Удалить запрос"'),
                 *[bot.send_message(ment, 'Поступил новый запрос на доп. ментора по вашей теме!',
                                    reply_markup=accept_markup)
                   for ment in mentors_to_alert])
    logging.debug(f'chat_id: {call.from_user.id} done ADD_REQUEST')


@bot.message_handler(state=StudentStates.add_own_subject_flag)
async def add_own_subject(message):
    db = Database()
    logging.debug(f'chat_id: {message.from_user.id} is in add_own_subject_flag')
    subjects = await db.get_subjects()

    if message.text in subjects:
        logging.debug(f'chat_id: {message.from_user.id} preparing add_own_subject_flag')
        await gather(bot.delete_state(message.from_user.id, message.chat.id),
                     bot.send_message(message.chat.id, "Предмет с таким названием уже существует!"))
        logging.debug(f'chat_id: {message.from_user.id} done add_own_subject_flag')
    else:
        async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['subject'] = message.text

        db = Database()
        subjects = await db.get_subjects()

        logging.debug(f'chat_id: {message.from_user.id} preparing add_own_subject_flag')
        await gather(bot.set_state(message.from_user.id, StudentStates.add_work_flag, message.chat.id),
                     bot.send_message(message.chat.id, "Введите название работы:"))
        logging.debug(f'chat_id: {message.from_user.id} done add_own_subject_flag')


@bot.message_handler(state=StudentStates.add_work_flag)
async def save_request(message):
    logging.debug(f'chat_id: {message.from_user.id} is in add_work_flag')
    entered_topic = message.text
    student_dict = dict()

    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        student_dict = {'name': message.from_user.username, 'chat_id': message.chat.id, 'subjects': [data['subject']],
                        'description': entered_topic}

    db = Database()
    id = await db.get_students(chat_id=message.chat.id)
    logging.debug(f'chat_id: {message.from_user.id} self {id}')

    if id:
        student_request = await db.get_course_works(student=id[0]['id'])
        course_work_names = [work['description'] for work in student_request]

        if entered_topic in course_work_names:
            logging.warn(f'chat_id: {message.from_user.id} work already exists')
            await gather(bot.delete_state(message.from_user.id, message.chat.id),
                         bot.send_message(message.chat.id, "Работа с таким именем уже добавлена!"))
            return
    logging.debug(f'chat_id: {message.from_user.id} preparing add_work_flag')
    cw_id = await db.add_course_work(student_dict)
    accept_markup = types.InlineKeyboardMarkup(row_width=1)
    accept_markup.add(types.InlineKeyboardButton('Принять', callback_data=f'mnt_work_{cw_id}'))
    mentors_to_alert = [ment['chat_id'] for ment in await db.get_mentors()
                        if student_dict['subjects'][0] in ment['subjects']]
    await gather(bot.delete_state(message.from_user.id, message.chat.id),
                 bot.send_message(message.chat.id, "Работа успешно добавлена! Ожидайте ответа ментора. "
                                                   "<br><br>Если вы захотите запросить дополнительного ментора, нажмите кнопку "
                                                   "<b>\"Запросить доп. ментора\"</b>", parse_mode="Html"),
                 *[bot.send_message(ment, 'Поступил новый запрос на доп. ментора по вашей теме!',
                                    reply_markup=accept_markup)
                   for ment in mentors_to_alert])
    logging.debug(f'chat_id: {message.from_user.id} done add_work_flag')


@bot.message_handler(func=lambda msg: msg.text == 'Мои запросы')
async def my_requests(message):
    db = Database()
    logging.debug(f'chat_id: {message.from_user.id} is in MY_REQUESTS')
    if await db.check_is_mentor(message.from_user.id):
        logging.warn(f'chat_id: {message.from_user.id} is a mentor')
        return
    id = await db.get_students(chat_id=message.chat.id)
    logging.debug(f'chat_id: {message.from_user.id} info {id}')

    if not id:
        await bot.send_message(message.from_user.id, "Пока у вас нет запросов. Скорее добавьте первый!")
        return

    student_request = create_task(db.get_course_works(student=id[0]['id']))
    if await db.get_accepted(student=id[0]['id']):
        logging.debug(f'chat_id: {message.from_user.id} preparing MY_REQUESTS')
        text = f'Текущая принятая курсовая работа: <b>{id[0]["course_works"][0]["description"]}</b><br>Твои менторы: <br><b>'
        for ment in await db.get_mentors(student=id[0]['id']):
            text += f"@{ment['name']}<br>"
        text += "</b>"
        await bot.send_message(message.from_user.id, text, parse_mode="Html")
        student_request = await student_request
        if student_request:
            await bot.send_message(message.from_user.id,
                                   'У вас имеется запрос на доп. ментора по этой работе!'
                                   'Если хотите его удалить, воспользуйтесь "Удалить запрос"')
        logging.debug(f'chat_id: {message.from_user.id} done MY_REQUESTS')
        return
    student_request = await student_request
    logging.debug(f'chat_id: {message.from_user.id} preparing MY_REQUESTS')
    await gather(*[bot.send_message(message.chat.id,
                                    f"<b>Работа №{course_work['id']}</b>\nПредмет: {course_work['subjects'][0]}\n"
                                    f"Тема работы: {course_work['description']}", parse_mode="Html")
                   for course_work in student_request])
    logging.debug(f'chat_id: {message.from_user.id} done MY_REQUESTS')


@bot.message_handler(func=lambda msg: msg.text == 'Удалить запрос')
async def remove_request(message):
    db = Database()
    logging.debug(f'chat_id: {message.from_user.id} is in REMOVE_REQUEST')
    if await db.check_is_mentor(message.from_user.id):
        logging.warn(f'chat_id: {message.from_user.id} is a mentor')
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
    logging.debug(f'chat_id: {message.from_user.id} is in BECOME_MENTOR_REQUEST')
    if await db.check_is_mentor(message.from_user.id):
        logging.warn(f'chat_id: {message.from_user.id} is a mentor')
        return
    admins = await db.get_admins()

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton('Одобрить', callback_data='add_mentor_via_admin_' + str(message.from_user.id)))

    admin_chat_id = random.choice(admins)['chat_id']
    logging.debug(f'chat_id: {message.from_user.id} preparing BECOME_MENTOR_REQUEST')
    await gather(bot.send_message(admin_chat_id, f"Пользователь @{message.from_user.username} хочет стать ментором.",
                                  reply_markup=markup),
                 bot.send_message(message.chat.id, "Ваша заявка на рассмотрении. Ожидайте ответа от администратора!\n"))
    logging.debug(f'chat_id: {message.from_user.id} done BECOME_MENTOR_REQUEST')


@bot.callback_query_handler(func=lambda call: call.data.startswith("add_request_"))
async def select_subject_callback(call):
    logging.debug(f'chat_id: {call.from_user.id} is in add_request')
    await bot.send_message(call.from_user.id, f"<b>Тема: {call.data[12:]}</b>\n\n"
                                              f"Введите название работы. \n\n<b>Если вы не знаете, на какую тему будете писать работу, "
                                              f"просто напишите \"Я не знаю\":</b>", parse_mode='Html')

    await bot.set_state(call.from_user.id, StudentStates.add_work_flag, call.message.chat.id)
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['subject'] = call.data[12:]

    await bot.answer_callback_query(call.id)


# @bot.callback_query_handler(func=lambda call: call.data.startswith("own_request"))
# async def add_own_subject_callback(call):
#     logging.debug(f'chat_id: {call.from_user.id} is in own_request')
#     await bot.set_state(call.from_user.id, StudentStates.add_own_subject_flag, call.message.chat.id)
#
#     await gather(bot.answer_callback_query(call.id),
#                  bot.send_message(call.from_user.id, "Введите название предмета:"))


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_request_"))
async def delete_topic_callback(call):
    logging.debug(f'chat_id: {call.from_user.id} is in delete_request')
    id_ = call.data[15:]
    db = Database()

    logging.debug(f'chat_id: {call.from_user.id} preparing delete_request')
    await gather(db.remove_course_work(id_), bot.answer_callback_query(call.id),
                 bot.send_message(call.from_user.id, "Работа успешно удалена!"),
                 bot.delete_message(call.message.chat.id, call.message.id))
    logging.debug(f'chat_id: {call.from_user.id} done delete_request')


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_finale"))
async def delete_finale(call):
    logging.debug(f'chat_id: {call.from_user.id} is in delete_finale')
    id_ = call.data[14:]

    db = Database()
    student = await db.get_students(id_)
    mentors = await db.get_mentors(student=id_)

    logging.debug(f'chat_id: {call.from_user.id} preparing delete_finale')
    await gather(db.remove_student(id_), bot.answer_callback_query(call.id),
                 bot.send_message(call.from_user.id,
                                  "Ваша курсовая работа успешно удалена. Но вы всегда можете начать новую!"),
                 *[bot.send_message(ment['chat_id'],
                                    f"Студент @{student[0]['name']} удалил принятую вами "
                                    f"курсовую работу \"{student[0]['course_works'][0]['description']}\"")
                   for ment in mentors],
                 bot.delete_message(call.message.chat.id, call.message.id))
    logging.debug(f'chat_id: {call.from_user.id} done delete_finale')


bot.add_custom_filter(asyncio_filters.StateFilter(bot))
bot.add_custom_filter(asyncio_filters.IsDigitFilter())
