from mentor_whirlpool.telegram import bot
from mentor_whirlpool.database import Database
from asyncio import gather
from mentor_whirlpool.utils import get_pretty_mention_db
import logging


@bot.message_handler(func=lambda msg: msg.text == 'Запросы (админ)')
async def course_work(message):
    db = Database()
    if not await db.check_is_admin(message.from_user.id):
        logging.warn(f'MENTORS: chat_id: {message.from_user.id} is not an admin')
        return

    course_works = await db.get_course_works()
    if course_works:
        async def get_message(work):
            stud = await db.get_students(work["student"])
            return f'{get_pretty_mention_db(stud[0])}\n'\
                   f'{work["description"]}'
        messages = await gather(*[get_message(work) for work in course_works])
        message_course_works = '\n--------\n'.join(messages)
        await bot.send_message(message.from_user.id, message_course_works)
    else:
        await bot.send_message(message.from_user.id, 'Нет запросов курсовых работ')
    await bot.delete_message(message.chat.id, message.id)
