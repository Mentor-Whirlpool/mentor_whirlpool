from mentor_whirlpool.telegram import bot
from telebot import types
from mentor_whirlpool.database import Database
from mentor_whirlpool.utils import get_pretty_mention_db
from asyncio import gather
import logging


@bot.message_handler(func=lambda msg: msg.text == 'Запросы')
async def works(message: types.Message) -> None:
    """
    Should send a list of inline buttons from db.get_course_works()

    Clicking on a button should produce a description of selected course work
    and a prompt to accept a work to lead. This prompt should ask for
    confirmation

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    await bot.delete_message(message.chat.id, message.id)

    db = Database()
    logging.debug(f'chat_id: {message.from_user.id} in REQUESTS')
    if not await db.check_is_mentor(message.from_user.id):
        logging.warn(f'chat_id: {message.from_user.id} is not a mentor')
        return
    mentor = (await db.get_mentors(chat_id=message.from_user.id))[0]
    if not mentor["subjects"]:
        await bot.send_message(message.chat.id, '__Сначала добавьте направления!__')
        return
    course_works = await db.get_course_works(subjects=[subj['id'] for subj in mentor["subjects"]])
    logging.debug(f'available course works for specified subjects: {course_works}')
    logging.debug(f'served students: {mentor["students"]}')

    for stud in mentor["students"]:
        for work in stud['course_works']:
            try:
                course_works.remove(work)
                logging.debug(f'removed work from list: {work}')
            except ValueError:
                continue
    logging.debug('finished removing works')

    markup = types.InlineKeyboardMarkup(row_width=1)

    for work in course_works:
        stud = (await db.get_students(work["student"]))[0]
        line = f'{stud["name"]} - {work["subjects"][0]["subject"]} - {work["description"]}'
        if await db.get_accepted(student=work['student']):
            line += ' (доп. запрос)'
        markup.add(
            types.InlineKeyboardButton(line, callback_data=f'mnt_work_{work["id"]}'))

    logging.debug(f'chat_id: {message.from_user.id} preparing COURSE_WORKS')
    await bot.send_message(message.chat.id, '__Доступные курсовые работы__',
                           reply_markup=markup)
    logging.debug(f'chat_id: {message.from_user.id} done COURSE_WORKS')


@bot.callback_query_handler(func=lambda call: call.data.startswith('mnt_work_'))
async def callback_query_work(call: types.CallbackQuery) -> None:
    db = Database()
    mentor_info = (await db.get_mentors(chat_id=call.from_user.id))[0]
    course_work_info = {}
    try:
        course_work_info = (await db.get_course_works(int(call.data[9:])))[0]
    except IndexError:
        await gather(bot.answer_callback_query(call.id),
                     bot.send_message(call.from_user.id, 'Запрос уже не действителен!'),
                     bot.delete_message(call.from_user.id, call.message.id))
        return

    stud = (await db.get_students(id_field=course_work_info["student"]))[0]
    logging.debug(f'chat_id: {call.from_user.id} preparing mnt_work')
    await gather(db.accept_work(mentor_info['id'], call.data[9:]),
                 bot.answer_callback_query(call.id),
                 bot.delete_message(call.from_user.id, call.message.id),
                 bot.send_message(call.from_user.id,
                                  f'Вы взялись за __{course_work_info["description"]}__\n'
                                  f'Напишите {get_pretty_mention_db(stud)}'),
                 bot.send_message(stud["chat_id"],
                                  f'Ментор {get_pretty_mention_db(mentor_info)} принял Ваш запрос __{course_work_info["description"]}__\n'
                                  'Если вам будет необходимо запросить дополнительного ментора, воспользуйтесь "Добавить запрос"'))
    logging.debug(f'chat_id: {call.from_user.id} done mnt_work')
