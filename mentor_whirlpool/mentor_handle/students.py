from __init__ import bot, Database, logging, get_pretty_mention_db, types


@bot.message_handler(func=lambda msg: msg.text == 'Мои студенты')
async def my_students(message:types.Message)->None:
    await bot.delete_message(message.chat.id, message.id)

    db = Database()
    logging.debug(f'chat_id: {message.from_user.id} in MY_STUDENTS')
    if not await db.check_is_mentor(message.from_user.id):
        logging.warn(f'chat_id: {message.from_user.id} is not a mentor')
        return

    mentor_info = (await db.get_mentors(chat_id=message.from_user.id))[0]
    logging.debug(f'chat_id: {message.from_user.id} info {mentor_info}')
    my_students_ = mentor_info['students']

    if not my_students_:
        str_my_students_ = 'У Вас нет студентов!'
    else:
        str_my_students_ = '\n'.join(
            f'{get_pretty_mention_db(stud)} - '
            f'{stud["course_works"][0]["subjects"][0]["subject"]} - '
            f'{stud["course_works"][0]["description"]}'
            for stud in my_students_)
    logging.debug(f'chat_id: {message.from_user.id} preparing MY_STUDENTS')
    await bot.send_message(message.chat.id,
                           f'Список моих студентов\n{str_my_students_}')
    logging.debug(f'chat_id: {message.from_user.id} done MY_STUDENTS')
