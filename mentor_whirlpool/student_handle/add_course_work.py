from __init__ import bot, Database, logging, types, gather, get_pretty_mention_db, get_name, get_pretty_mention, \
    StudentStates, create_task


@bot.message_handler(func=lambda msg: msg.text == 'Добавить запрос')
async def add_request(message: types.Message) -> None:
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
async def readmission_request(call: types.CallbackQuery) -> None:
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
                                    f'Поступил новый запрос на доп. ментора по вашему направлению: {new_subj["subject"]} от '
                                    f'{get_pretty_mention(call.from_user)}'
                                    f'Тема: {accepted[0]["description"]}',
                                    reply_markup=accept_markup)
                   for ment in mentors_to_alert
                   if ment not in await db.get_mentors(student=id[0]['id'])])
    logging.debug(f'chat_id: {call.from_user.id} done ADD_REQUEST')


@bot.message_handler(state=StudentStates.add_work_flag)
async def save_request(message: types.Message) -> None:
    logging.debug(f'chat_id: {message.from_user.id} is in add_work_flag')
    entered_topic = message.text
    student_dict = dict()

    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        student_dict = {'name': get_name(message.from_user),
                        'chat_id': message.chat.id,
                        'subjects': [data['subject']],
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
                                                   "__\"Добавить запрос\"__"),
                 *[bot.send_message(ment,
                                    f'Поступил новый запрос по вашему направлению: {subject["subject"]} от '
                                    f'{get_pretty_mention_db(student_dict)}!\n'
                                    f'Тема: {student_dict["description"]}',
                                    reply_markup=accept_markup)
                   for ment in mentors_to_alert])
    logging.debug(f'chat_id: {message.from_user.id} done add_work_flag')


@bot.callback_query_handler(func=lambda call: call.data.startswith("add_request_"))
async def select_subject_callback(call: types.CallbackQuery) -> None:
    logging.debug(f'chat_id: {call.from_user.id} is in add_request')
    db = Database()
    subject = (await db.get_subjects(call.data[12:]))[0]
    await bot.send_message(call.from_user.id, f"__Тема: {subject['subject']}__\n\n"
                                              f"Введи название работы. \n\n"
                                              f"__Если не знаешь, на какую тему будешь писать работу, "
                                              f"просто напиши \"Открыт к предложениям\":__")

    await bot.set_state(call.from_user.id, StudentStates.add_work_flag, call.message.chat.id)
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['subject'] = subject['id']

    await bot.answer_callback_query(call.id)
