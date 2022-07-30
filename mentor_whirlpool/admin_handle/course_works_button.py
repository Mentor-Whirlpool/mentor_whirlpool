from mentor_whirlpool.telegram import bot
from mentor_whirlpool.database import Database
import logging


@bot.message_handler(func=lambda msg: msg.text == 'Запросы (админ)')
async def course_work(message):
    db = Database()
    if not await db.check_is_admin(message.from_user.id):
        logging.warning(f'MENTORS: chat_id: {message.from_user.id} is not an admin')
        return

    course_works = await db.get_course_works()
    if course_works:
        messages = [f'@{(await db.get_students(work["student"]))[0]["name"]}\n' \
                    f'{work["description"]}'
                    for work in course_works]
        message_course_works = '\n--------\n'.join(messages)
        await bot.send_message(message.from_user.id, message_course_works)
    else:
        await bot.send_message(message.from_user.id, 'Нет запросов курсовых работ')
    await bot.delete_message(message.chat.id, message.id)
