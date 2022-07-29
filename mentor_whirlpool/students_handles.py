from mentor_whirlpool.telegram import bot
from telebot import types
from telebot import asyncio_filters
from telebot.asyncio_handler_backends import State, StatesGroup
from mentor_whirlpool.database import Database
from asyncio import gather, create_task
from mentor_whirlpool.confirm import confirm
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
    commands = ['Добавить запрос', 'Удалить запрос', 'Мои запросы', 'Идеи',
                'Хочу стать ментором', 'Поддержка']
    return commands


async def student_help():
    return 'Привет! Я здесь для того, чтобы помочь тебе найти ментора, если тебе нужна ' \
           'помощь с твоей курсовой. Прочитай это сообщение внимательно, ведь это важно! ' \
           'Мой функционал:\n' \
           '- Кнопка «Добавить запрос» позволяет запросить ментора. При нажатии она ' \
           'вернет список направлений, по которым ведется менторство. Если подходящего ' \
           'направления там нет, обращайся в поддержку, мы поможем! Если же ты нашел ' \
           'свое направление, выбирай его и пиши свою тему. Если ты еще не определился, ' \
           'какую именно курсовую хочешь написать, то можешь отправить несколько ' \
           'запросов, однако, как только один из них примет ментор, остальные ' \
           'аннулируются.\n\n' \
           'Также эта кнопка позволит тебе добавить дополнительный запрос после ' \
           'принятия твоей курсовой ментором в том случае, если у работы несколько ' \
           'направлений.\n' \
           '- Кнопка «Удалить запрос» вернет тебе список с твоими запросами, нажав на ' \
           'которые, ты можешь их удалить. Если же ты уже работаешь с ментором, то эта ' \
           'кнопка предложить удалить твою курсовую: это нужно для завершения работы ' \
           'после окончания курсовой.\n' \
           '- Кнопка «Мои запросы» вернет список твоих текущих запросов.\n' \
           '- При нажатии на «Хочу стать ментором», сообщение отправится ' \
           'администратору, после чего с тобой свяжутся.\n' \
           '- Кнопка «Поддержка» нужна для связи со службой поддержки. Обращайся, если ' \
           'у тебя возникли вопросы по функционалу, темам, направлениям или менторам.'


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
        all_subjects = await db.get_subjects()
        # stud_accepted_subj is identical with all_subjects aside from sorting
        if not [subj for subj in all_subjects if subj not in stud_accepted_subj]:
            await bot.send_message(message.from_user.id,
                                   'Ты уже добавили все возможные направления!\n'
                                   'Если остались вопросы, обратись в поддержку')
            return
        if len(stud_accepted_subj) > 2:
            await bot.send_message(message.from_user.id,
                                   'Тебя уже обслуживает доп. ментор!\n'
                                   'Если остались вопросы, обратись в поддержку')
            return
        markup.add(*[types.InlineKeyboardButton(sub['subject'], callback_data=f'readm_{sub["id"]}')
                     for sub in await db.get_subjects()
                     if sub not in stud_accepted_subj])
        await bot.send_message(message.from_user.id,
                               "Тебя уже обслуживает ментор\n"
                               "Создаём запрос на доп. ментора!\n"
                               "Выбери направление, которая вас интересует:",
                               reply_markup=markup)
        return
    markup.add(*[types.InlineKeyboardButton(sub['subject'], callback_data=f'add_request_{sub["id"]}')
                 for sub in await db.get_subjects()
                 if sub not in stud_accepted_subj])
    logging.debug(f'chat_id: {message.from_user.id} preparing ADD_REQUEST')
    await bot.send_message(message.chat.id, "Добавить запрос:", reply_markup=markup)
    await bot.delete_message(message.chat.id, message.id)
    logging.debug(f'chat_id: {message.from_user.id} done ADD_REQUEST')


@bot.callback_query_handler(func=lambda call: call.data.startswith('readm_'))
async def readmission_request(call):
    db = Database()
    logging.debug(f'chat_id: {call.from_user.id} is in ADDITIONAL_MENTOR')

    id = await db.get_students(chat_id=call.from_user.id)
    new_subj_id = int(call.data[6:])
    new_subj = (await db.get_subjects(new_subj_id))[0]
    accepted = None
    if id:
        accepted = await db.get_accepted(student=id[0]['id'])
    # should be possible if button is clicked after student decides to nuke himself
    if not accepted:
        await bot.send_message(call.from_user.id, 'Тебя ещё не курирует ментор')
        return

    cw_id = await db.readmission_work(accepted[0]['id'], new_subj['id'])
    accept_markup = types.InlineKeyboardMarkup(row_width=1)
    accept_markup.add(types.InlineKeyboardButton('Принять', callback_data=f'mnt_work_{cw_id}'))
    mentors_to_alert = [ment for ment in await db.get_mentors()
                        if new_subj in ment['subjects']]
    logging.debug(f'chat_id: {call.from_user.id} preparing ADD_REQUEST')
    await gather(bot.answer_callback_query(call.id),
                 bot.send_message(call.from_user.id,
                                  'Ты успешно запросил доп. ментора!\n'
                                  'Если передумаешь, можно отменить '
                                  'запрос, используя "Удалить запрос"'),
                 *[bot.send_message(ment['chat_id'],
                                    f'Поступил новый запрос на доп. ментора по вашему направлению: {new_subj["subject"]} от @{call.from_user.username}]!\n'
                                    f'Тема: {accepted[0]["description"]}',
                                    reply_markup=accept_markup)
                   for ment in mentors_to_alert
                   if ment not in await db.get_mentors(student=id[0]['id'])])
    logging.debug(f'chat_id: {call.from_user.id} done ADD_REQUEST')


@bot.message_handler(state=StudentStates.add_work_flag)
async def save_request(message):
    logging.debug(f'chat_id: {message.from_user.id} is in add_work_flag')
    entered_topic = message.text
    student_dict = dict()

    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        student_dict = {'name': message.from_user.username, 'chat_id': message.chat.id, 'subjects': [data['subject']],
                        'description': entered_topic}

    db = Database()
    subject = create_task(db.get_subjects(student_dict['subjects'][0]))
    id = await db.get_students(chat_id=message.from_user.id)
    logging.debug(f'chat_id: {message.from_user.id} self {id}')

    if id:
        student_request = await db.get_course_works(student=id[0]['id'])
        course_work_names = [work['description'] for work in student_request]

        if entered_topic in course_work_names:
            logging.warn(f'chat_id: {message.from_user.id} work already exists')
            await gather(bot.delete_state(message.from_user.id, message.chat.id),
                         bot.send_message(message.chat.id, "Работа с такой темой уже добавлена!"))
            return
    logging.debug(f'chat_id: {message.from_user.id} preparing add_work_flag')
    cw_id = await db.add_course_work(student_dict)
    accept_markup = types.InlineKeyboardMarkup(row_width=1)
    accept_markup.add(types.InlineKeyboardButton('Принять', callback_data=f'mnt_work_{cw_id}'))
    subject = (await subject)[0]
    mentors_to_alert = [ment['chat_id'] for ment in await db.get_mentors()
                        if subject in ment['subjects']]
    await gather(bot.delete_state(message.from_user.id, message.chat.id),
                 bot.send_message(message.chat.id, "Работа успешно добавлена! Ожидайте ответа ментора. "
                                                   "\nЕсли вы захотите запросить дополнительного ментора, нажми кнопку "
                                                   "<b>\"Добавить запрос\"</b>", parse_mode="Html"),
                 *[bot.send_message(ment,
                                    f'Поступил новый запрос по вашему направлению: {subject["subject"]} от @{student_dict["name"]}!\n'
                                    f'Тема: {student_dict["description"]}',
                                    reply_markup=accept_markup)
                   for ment in mentors_to_alert])
    logging.debug(f'chat_id: {message.from_user.id} done add_work_flag')


@bot.message_handler(func=lambda msg: msg.text == 'Мои запросы')
async def my_requests(message):
    await bot.delete_message(message.chat.id, message.id)
    db = Database()
    logging.debug(f'chat_id: {message.from_user.id} is in MY_REQUESTS')
    if await db.check_is_mentor(message.from_user.id):
        logging.warn(f'chat_id: {message.from_user.id} is a mentor')
        return
    id = await db.get_students(chat_id=message.chat.id)
    logging.debug(f'chat_id: {message.from_user.id} info {id}')

    if not id:
        await bot.send_message(message.from_user.id, "Пока нет запросов. Скорее добавь первый!")
        return

    student_request = create_task(db.get_course_works(student=id[0]['id']))
    if await db.get_accepted(student=id[0]['id']):
        logging.debug(f'chat_id: {message.from_user.id} preparing MY_REQUESTS')
        text = f'Текущая принятая курсовая работа: <b>{id[0]["course_works"][0]["description"]}</b>\nТвои менторы: \n<b>'
        for ment in await db.get_mentors(student=id[0]['id']):
            text += f"@{ment['name']}\n"
        text += "</b>"
        await bot.send_message(message.from_user.id, text, parse_mode="Html")
        student_request = await student_request
        if student_request:
            await bot.send_message(message.from_user.id,
                                   'У тебя имеется запрос на доп. ментора по этой работе!'
                                   'Если хочешь его удалить, воспользуйся "Удалить запрос"')
        logging.debug(f'chat_id: {message.from_user.id} done MY_REQUESTS')
        return
    student_request = await student_request
    logging.debug(f'chat_id: {message.from_user.id} preparing MY_REQUESTS')
    await gather(*[bot.send_message(message.chat.id,
                                    f"<b>Работа №{course_work['id']}</b>\nНаправление: {course_work['subjects'][0]['subject']}\n"
                                    f"Тема работы: {course_work['description']}", parse_mode="Html")
                   for course_work in student_request])
    logging.debug(f'chat_id: {message.from_user.id} done MY_REQUESTS')


@bot.message_handler(func=lambda msg: msg.text == 'Удалить запрос')
async def remove_request(message):
    await bot.delete_message(message.chat.id, message.id)
    db = Database()
    logging.debug(f'chat_id: {message.from_user.id} is in REMOVE_REQUEST')
    if await db.check_is_mentor(message.from_user.id):
        logging.warn(f'chat_id: {message.from_user.id} is a mentor')
        return
    id = await db.get_students(chat_id=message.chat.id)

    if not id:
        await bot.send_message(message.from_user.id, "Пока нет запросов. Скорее добавь первый!")
        return

    student_request = create_task(db.get_course_works(student=id[0]['id']))
    markup = types.InlineKeyboardMarkup(row_width=1)
    if await db.get_accepted(student=id[0]['id']):
        student_request = await student_request
        if student_request:
            markup.add(types.InlineKeyboardButton('Запрос на доп. ментора',
                                                  callback_data=f"delete_request_{student_request[0]['id']}"))
            markup.add(types.InlineKeyboardButton(f"Курсовая работа \"{id[0]['course_works'][0]['description']}\"",
                                                  callback_data=f"delete_finale_{id[0]['id']}"))
            await bot.send_message(message.from_user.id, 'Что удалить?', reply_markup=markup)
            return

        markup.add(types.InlineKeyboardButton(f"Удалить курсовую \"{id[0]['course_works'][0]['description']}\"",
                                              callback_data=f"delete_finale_{id[0]['id']}"))

        await bot.send_message(message.from_user.id, 'Внимание! Ты собираешься удалить свою курсовую работу!\n'
                                                     'Тебя больше не будут курировать менторы',
                               reply_markup=markup)
        return
    else:
        student_request = await student_request

        for course_work in student_request:
            markup.add(
                types.InlineKeyboardButton(f'{course_work["subjects"][0]["subject"]}: {course_work["description"]}',
                                           callback_data=f"delete_request_{course_work['id']}"))

        await bot.send_message(message.chat.id, "Выбери работу, которую хочешь удалить из списка запросов: ",
                               reply_markup=markup)


@bot.message_handler(func=lambda msg: msg.text == 'Хочу стать ментором')
async def mentor_resume(message):
    await bot.delete_message(message.chat.id, message.id)
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
    db = Database()
    subject = (await db.get_subjects(call.data[12:]))[0]
    await bot.send_message(call.from_user.id, f"<b>Тема: {subject['subject']}</b>\n\n"
                                              f"Введи название работы. \n\n<b>Если не знаешь, на какую тему будешь писать работу, "
                                              f"просто напиши \"Открыт к предложениям\":</b>", parse_mode='Html')

    await bot.set_state(call.from_user.id, StudentStates.add_work_flag, call.message.chat.id)
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['subject'] = subject['id']

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
                                  "Курсовая работа успешно удалена. Но ты всегда можете начать новую!"),
                 *[bot.send_message(ment['chat_id'],
                                    f"Студент @{student[0]['name']} удалил принятую вами "
                                    f"курсовую работу \"{student[0]['course_works'][0]['description']}\"")
                   for ment in mentors],
                 bot.delete_message(call.message.chat.id, call.message.id))
    logging.debug(f'chat_id: {call.from_user.id} done delete_finale')


@bot.message_handler(func=lambda msg: msg.text == 'Идеи')
async def start_show_idea(message):
    await bot.delete_message(message.chat.id, message.id)
    db = Database()

    if await db.check_is_mentor(message.from_user.id):
        logging.warning(f'chat_id: {message.from_user.id} is a mentor')
        return

    ideas = '<b>Идеи от менторов</b>\n' \
            '- Проверка ЭП по qr коду\n' \
            '- Распределеный УЦ (Блокчейн)\n' \
            '- УЦ для экспериментов с криптомодулями\n' \
            '- Анализатор безопасности смарт-контрактов\n' \
            '- Гостовый ssl сканер\n' \
            '- Сервис для автоматического плана путешествий\n' \
            '- Сервис для составления расписания\n' \
            '- Веб-рация (вроде Discord)\n' \
            '- Конвертор между музыкальными сервисами\n'

    await bot.send_message(message.from_user.id, ideas, parse_mode='html')


bot.add_custom_filter(asyncio_filters.StateFilter(bot))
bot.add_custom_filter(asyncio_filters.IsDigitFilter())
