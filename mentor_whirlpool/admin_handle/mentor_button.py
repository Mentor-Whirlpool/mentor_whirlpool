from mentor_whirlpool.telegram import bot
from telebot import types
from mentor_whirlpool.database import Database
from asyncio import create_task, gather
import logging


@bot.message_handler(func=lambda msg: msg.text == 'Менторы')
async def list_mentors(message):
    """
    If from_user.id is in admins, print an InlineMarkupKeyboard of mentors.
    Clicking these buttons should trigger a mentor deletion with a confirmation

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    db = Database()
    if not await db.check_is_admin(message.from_user.id):
        logging.warning(f'MENTORS: chat_id: {message.from_user.id} is not an admin')
        return

    logging.debug(f'chat_id: {message.from_user.id} in MENTORS')
    mentors = await db.get_mentors()
    tasks = []
    for mentor in mentors:

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Выбрать', callback_data=f'admin_choose_mentor_{str(mentor["chat_id"])}'))

        if not mentor['subjects']:
            tasks.append(
                bot.send_message(message.from_user.id, f'<b>@{mentor["name"]}</b>\nНет выбранных направлений',
                                 reply_markup=markup,
                                 parse_mode='html'))
            continue

        subjects_count_dict = dict.fromkeys([subj['subject'] for subj in mentor['subjects']], 0)

        for student in mentor['students']:
            for subject in [subj['subject'] for subj in student['course_works'][0]['subjects']]:

                if subject in subjects_count_dict:
                    subjects_count_dict[subject] += 1
                else:
                    continue

        message_subjects = '\n'.join(f'{k} - {v}' for k, v in subjects_count_dict.items())

        tasks.append(
            bot.send_message(message.from_user.id, f'<b>@{mentor["name"]}</b>\n{message_subjects}', reply_markup=markup,
                             parse_mode='html'))

    logging.debug(f'chat_id: {message.from_user.id} preparing MENTORS')
    await gather(*tasks, bot.delete_message(message.chat.id, message.id))
    logging.debug(f'chat_id: {message.from_user.id} sent MENTORS')
