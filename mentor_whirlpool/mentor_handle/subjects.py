from mentor_whirlpool.telegram import bot
from telebot import types
from mentor_whirlpool.database import Database
from asyncio import gather, create_task
import logging

@bot.message_handler(func=lambda msg: msg.text == 'Мои направления')
async def my_subjects(message: types.Message) -> None:
    """
    Should send a list of inline buttons from db.get_subjects() with a from_user.id
    argument and a finish button

    Buttons with subjects can be clicked to narrow the list
    Clicking on a finish button should produce a list of course works with
    selected subject. Those buttons should behave the same way they behave in
    works handle

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    await bot.delete_message(message.chat.id, message.id)

    db = Database()
    logging.debug(f'chat_id: {message.from_user.id} in MY_SUBJECTS')
    if not await db.check_is_mentor(message.from_user.id):
        logging.warn(f'chat_id: {message.from_user.id} is not a mentor')
        return
    mentor = (await db.get_mentors(chat_id=message.from_user.id))[0]
    logging.debug(f'mentor: {mentor}')

    markup = types.InlineKeyboardMarkup(row_width=3)
    add = types.InlineKeyboardButton('Добавить', callback_data='mnt_sub_to_add')
    message_subjects = '__Мои направления__\n'

    if mentor["subjects"]:
        delete = types.InlineKeyboardButton('Удалить', callback_data='mnt_sub_to_delete')
        markup.row(add, delete)
        message_subjects += '\n'.join([subj['subject'] for subj in mentor["subjects"]])
    else:
        markup.add(add)

    logging.debug(f'chat_id: {message.from_user.id} preparing MY_SUBJECTS')
    await bot.send_message(message.chat.id, f'{message_subjects}', reply_markup=markup)
    logging.debug(f'chat_id: {message.from_user.id} done MY_SUBJECTS')


@bot.callback_query_handler(func=lambda call: call.data.startswith('subject_'))
async def callback_show_course_works_by_subject(call: types.CallbackQuery) -> None:
    db = Database()
    subject = await db.get_subjects(id_field=call.data[8:])
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        *[types.InlineKeyboardButton(f'{(await db.get_students(work["student"]))[0]["name"]} - {work["description"]}',
                                     callback_data=f'work_{work["id"]}') for work in
          await db.get_course_works(subjects=[subject['id']])])  # добавление курсачей будет в callback_query_work
    await gather(bot.answer_callback_query(call.id),
                 bot.delete_message(call.from_user.id, call.message.id),
                 bot.send_message(call.from_user.id, f'Курсовые работы по направлению __{subject["subject"]}__',
                                  reply_markup=markup))


@bot.callback_query_handler(func=lambda call: call.data == 'mnt_sub_to_add')
async def callback_show_subjects_to_add(call: types.CallbackQuery) -> None:
    db = Database()
    answ_task = create_task(bot.answer_callback_query(call.id))
    mentor = (await db.get_mentors(chat_id=call.from_user.id))[0]

    subjects_to_add = await db.get_subjects()

    for subject in mentor["subjects"]:
        subjects_to_add.remove(subject)

    if subjects_to_add:
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            *[types.InlineKeyboardButton(subject['subject'], callback_data=f'mnt_sub_add_{subject["id"]}')
              for subject in subjects_to_add])
        await bot.send_message(call.from_user.id, '__Все направления__',
                               reply_markup=markup)
    else:
        await bot.send_message(call.from_user.id, '__Вы добавили все доступные направления__')
    await bot.delete_message(call.from_user.id, call.message.id)
    await answ_task


@bot.callback_query_handler(func=lambda call: call.data.startswith('mnt_sub_add_'))
async def callback_add_subject(call: types.CallbackQuery) -> None:
    db = Database()
    answ_task = create_task(bot.answer_callback_query(call.id))
    myself = (await db.get_mentors(chat_id=call.from_user.id))[0]
    logging.debug(f'chat_id: {call.from_user.id} info {myself}')

    if not myself['subjects'] or call.data[12:] not in [my_subj['id'] for my_subj in myself['subjects']]:
        logging.debug(f'chat_id: {call.from_user.id} adding subject {call.data[12:]}')
        await gather(db.add_mentor_subjects(myself['id'], [call.data[12:]]),
                     bot.send_message(call.from_user.id,
                                      f'Направление __{(await db.get_subjects(int(call.data[12:])))[0]["subject"]}__ успешно добавлено'))
    else:
        logging.warn(f'chat_id: {call.from_user.id} adding added subject {call.data[12:]}')
        await bot.send_message(call.from_user.id,
                               f'Направление __{call.data[12:]}__ уже была добавлено')
    await bot.delete_message(call.from_user.id, call.message.id)
    await answ_task


@bot.callback_query_handler(func=lambda call: call.data == 'mnt_sub_to_delete')
async def callback_show_subjects_to_delete(call: types.CallbackQuery) -> None:
    db = Database()
    my_subjects_ = (await db.get_mentors(chat_id=call.from_user.id))[0]['subjects']
    logging.debug(f'chat_id: {call.from_user.id} subjects {my_subjects_}')

    markup = types.InlineKeyboardMarkup()
    markup.add(
        *[types.InlineKeyboardButton(subject['subject'], callback_data=f'mnt_sub_delete_{subject["id"]}')
          for subject in my_subjects_])
    logging.debug(f'chat_id: {call.from_user.id} preparing mnt_sub_to_delete')
    await gather(bot.answer_callback_query(call.id),
                 bot.delete_message(call.from_user.id, call.message.id),
                 bot.send_message(call.from_user.id,
                                  '__Удалить направление__',
                                  reply_markup=markup))
    logging.debug(f'chat_id: {call.from_user.id} done mnt_sub_to_delete')


@bot.callback_query_handler(func=lambda call: call.data.startswith('mnt_sub_delete_'))
async def callback_del_subject(call: types.CallbackQuery) -> None:
    db = Database()
    my_id = (await db.get_mentors(chat_id=call.from_user.id))[0]['id']
    subject = (await db.get_subjects(call.data[15:]))[0]

    logging.debug(f'chat_id: {call.from_user.id} preparing mnt_sub_delete')
    await gather(db.remove_mentor_subjects(my_id, [subject['id']]),
                 bot.send_message(call.from_user.id,
                                  f'Направление __{subject["subject"]}__ успешно удалено'),
                 bot.delete_message(call.from_user.id, call.message.id),
                 bot.answer_callback_query(call.id))
    logging.debug(f'chat_id: {call.from_user.id} done mnt_sub_delete')
