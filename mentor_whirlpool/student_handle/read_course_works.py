from __init__ import bot, Database, logging, types, gather, get_pretty_mention_db, create_task


@bot.message_handler(func=lambda msg: msg.text == 'Мои запросы')
async def my_requests(message: types.Message) -> None:
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
        text = f'Текущая принятая курсовая работа: __{id[0]["course_works"][0]["description"]}__\nТвои менторы: \n__'
        for ment in await db.get_mentors(student=id[0]['id']):
            text += f"{get_pretty_mention_db(ment)}\n"
        text += "__"
        await bot.send_message(message.from_user.id, text)
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
                                    f"__Работа №{course_work['id']}__\nНаправление: {course_work['subjects'][0]['subject']}\n"
                                    f"Тема работы: {course_work['description']}")
                   for course_work in student_request])
    logging.debug(f'chat_id: {message.from_user.id} done MY_REQUESTS')
