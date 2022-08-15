from __init__ import bot, Database, logging, types, gather, get_pretty_mention_db, create_task


@bot.message_handler(func=lambda msg: msg.text == 'Удалить запрос')
async def remove_request(message: types.Message) -> None:
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


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_request_"))
async def delete_topic_callback(call: types.CallbackQuery) -> None:
    logging.debug(f'chat_id: {call.from_user.id} is in delete_request')
    id_ = call.data[15:]
    db = Database()

    logging.debug(f'chat_id: {call.from_user.id} preparing delete_request')
    await gather(db.remove_course_work(id_), bot.answer_callback_query(call.id),
                 bot.send_message(call.from_user.id, "Работа успешно удалена!"),
                 bot.delete_message(call.message.chat.id, call.message.id))
    logging.debug(f'chat_id: {call.from_user.id} done delete_request')


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_finale"))
async def delete_finale(call: types.CallbackQuery) -> None:
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
                                    f"Студент {get_pretty_mention_db(student[0])} удалил принятую вами "
                                    f"курсовую работу \"{student[0]['course_works'][0]['description']}\"")
                   for ment in mentors],
                 bot.delete_message(call.message.chat.id, call.message.id))
    logging.debug(f'chat_id: {call.from_user.id} done delete_finale')
