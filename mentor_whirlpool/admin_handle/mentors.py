from mentor_whirlpool.telegram import bot
from telebot import types
from mentor_whirlpool.database import Database
from asyncio import gather
from mentor_whirlpool.support_handles import support_start
from mentor_whirlpool.utils import get_name, get_pretty_mention_db, get_pretty_mention
from mentor_whirlpool.student_handle import start
from mentor_whirlpool.mentor_handle.start import mentor_start
import logging


@bot.message_handler(func=lambda msg: msg.text == 'Менторы')
async def list_mentors(message: types.Message) -> None:
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
        logging.warn(f'MENTORS: chat_id: {message.from_user.id} is not an admin')
        return

    logging.debug(f'chat_id: {message.from_user.id} in MENTORS')
    mentors = await db.get_mentors()
    tasks = []
    for mentor in mentors:

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Выбрать', callback_data=f'admin_choose_mentor_{mentor["chat_id"]}'))

        if not mentor['subjects']:
            tasks.append(
                bot.send_message(message.from_user.id, f'__{get_pretty_mention_db(mentor)}__\nНет выбранных направлений',
                                 reply_markup=markup))
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
            bot.send_message(message.from_user.id, f'__{get_pretty_mention_db(mentor)}__\n'
                                                   f'{message_subjects}',
                             reply_markup=markup))

    logging.debug(f'chat_id: {message.from_user.id} preparing MENTORS')
    await gather(*tasks, bot.delete_message(message.chat.id, message.id))
    logging.debug(f'chat_id: {message.from_user.id} sent MENTORS')


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_choose_mentor_'))
async def callback_mentors_info(call: types.CallbackQuery) -> None:
    db = Database()
    mentor_info = (await db.get_mentors(chat_id=int(call.data[20:])))[0]
    logging.debug(f'chat_id: {call.from_user.id} chosen mentor {mentor_info}')
    message_subjects = 'Нет выбранных направлений'
    message_students = 'Нет студентов'
    if mentor_info['subjects']:
        message_subjects = '\n'.join([subj['subject'] for subj in mentor_info['subjects']])
    if mentor_info['students']:
        message_students = '\n'.join(student['name'] for student in mentor_info['students'])
    markup = types.InlineKeyboardMarkup()
    edit_subjects = types.InlineKeyboardButton('Изменить направления',
                                               callback_data='admin_edit_subjects_' + call.data[20:])
    edit_students = types.InlineKeyboardButton('Изменить студентов',
                                               callback_data='admin_edit_students_' + call.data[20:])
    delete_mentor = types.InlineKeyboardButton('Удалить ментора', callback_data='admin_delete_mentor_' + call.data[20:])
    markup.add(edit_students, edit_subjects, delete_mentor)
    await bot.answer_callback_query(call.id)
    message = f'{get_pretty_mention_db(mentor_info)}\n----Направления----\n{message_subjects}\n----Студенты----\n{message_students}'
    logging.debug(f'chat_id: {call.from_user.id} preparing admin_choose_mentor')
    await bot.send_message(call.from_user.id, message, reply_markup=markup)
    await bot.delete_message(call.from_user.id, call.message.id)
    logging.debug(f'chat_id: {call.from_user.id} sent admin_choose_mentor')


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_delete_mentor_'))
async def delete_mentor(call: types.CallbackQuery) -> None:
    db = Database()
    mentor_info = (await db.get_mentors(chat_id=int(call.data[20:])))[0]
    logging.debug(f'chat_id: {call.from_user.id} chosen mentor {mentor_info}')
    logging.debug(f'chat_id: {call.from_user.id} preparing admin_delete_mentor')
    student_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    student_markup.add(*[types.KeyboardButton(task)
                         for task in await start.generic_start()])
    if await db.check_is_support(call.from_user.id):
        student_markup.add(*[types.KeyboardButton(task)
                             for task in await support_start()])
    await gather(
        db.remove_mentor(id_field=mentor_info['id']),
        bot.send_message(call.from_user.id, f'Ментор {get_pretty_mention_db(mentor_info)} был удален'),
        bot.send_message(mentor_info['chat_id'], 'Вы больше не являетесь ментором', reply_markup=student_markup),
        bot.delete_message(call.from_user.id, call.message.id),
        bot.answer_callback_query(call.id)
    )
    logging.debug(f'chat_id: {call.from_user.id} done admin_delete_mentor')


# students
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_edit_students_'))
async def edit_students(call: types.CallbackQuery) -> None:
    markup = types.InlineKeyboardMarkup()
    add = types.InlineKeyboardButton('Добавить студента',
                                     callback_data='admin_add_student_subject_choice_' + call.data[20:])
    delete = types.InlineKeyboardButton('Удалить студента', callback_data='admin_delete_student_info_' + call.data[20:])
    markup.add(add, delete)
    await bot.answer_callback_query(call.id)
    logging.debug(f'chat_id: {call.from_user.id} preparing admin_edit_students')
    await bot.send_message(call.from_user.id, 'Что сделать со студентами?', reply_markup=markup)
    await bot.delete_message(call.from_user.id, call.message.id)
    logging.debug(f'chat_id: {call.from_user.id} done admin_edit_students')


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_add_student_subject_choice_'))
async def callback_add_student_subject_choice(call: types.CallbackQuery) -> None:
    db = Database()
    mentor_subjects = (await db.get_mentors(chat_id=call.data[33:]))[0]['subjects']

    markup = types.InlineKeyboardMarkup()
    markup.add(*[types.InlineKeyboardButton(subject['subject'],
                                            callback_data=f'admin_add_student_with_subject_' \
                                                          f'{subject["id"]}_{call.data[33:]}')
                 for subject in mentor_subjects])

    logging.debug(f'chat_id: {call.from_user.id} preparing admin_add_student_subject_choice')
    await bot.send_message(call.from_user.id, 'Выберете направление курсовой чтобы добавить студента',
                           reply_markup=markup)
    await bot.answer_callback_query(call.id)
    await bot.delete_message(call.from_user.id, call.message.id)
    logging.debug(f'chat_id: {call.from_user.id} done admin_add_student_subject_choice')


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_add_student_with_subject_'))
async def callback_add_student(call: types.CallbackQuery) -> None:
    db = Database()
    subject, mentor_chat_id = call.data[31:].split('_')
    subject = await db.get_subjects(int(subject))

    force = types.ForceReply(selective=False)
    logging.debug(f'chat_id: {call.from_user.id} preparing admin_add_student_with_subject')
    await gather(bot.delete_message(call.from_user.id, call.message.id),
                 bot.send_message(call.from_user.id,
                                  'Добавлять студента СТРОГО в формате `@student;course_work_name`'),
                 bot.send_message(call.from_user.id,
                                  f'Добавить студента для tg://user?id={mentor_chat_id} {subject[0]["subject"]}',
                                  reply_markup=force),
                 bot.answer_callback_query(call.id))
    logging.debug(f'chat_id: {call.from_user.id} done admin_add_student_with_subject')


@bot.message_handler(func=lambda message: message.reply_to_message and message.reply_to_message.text.startswith(
    'Добавить студента для '))
async def callback_user_add_subject(message: types.Message) -> None:
    db = Database()
    mentor_chat_id, subject_name = message.reply_to_message.text[55:].split()
    subject = None
    for subj in await db.get_subjects():
        if subject_name == subj['subject']:
            subject = subj
            break
    if subject is None:
        await bot.send_message(message.from_user.id, f'Направление {subject_name} НЕ НАЙДЕНО')
        return
    logging.debug(f'chat_id: {message.from_user.id} getting mentor with chat_id {mentor_chat_id}')
    mentor = (await db.get_mentors(chat_id=mentor_chat_id))[0]
    logging.debug(f'chat_id: {message.from_user.id} got mentor {mentor}')
    student_name, course_work_name = message.text.strip()[1:].split(';')

    student = None
    for stud in await db.get_students():
        if stud['name'] == student_name:
            student = stud
            break

    if not student:
        await bot.send_message(message.from_user.id, f'Студент {student_name} НЕ НАЙДЕН')
        return

    logging.debug(f'chat_id: {message.from_user.id} preparing ADD_STUDENT_FOR')
    await gather(
        db.accept_work(mentor["id"], await db.add_course_work(
            {'name': student["name"],
             'chat_id': student["chat_id"],
             'subjects': [subject['id']],
             'description': course_work_name})),
        bot.send_message(message.from_user.id,
                         f'Студент {get_pretty_mention_db(student)} ' \
                         f'добавлен к ментору {get_pretty_mention_db(mentor)}'),
        bot.send_message(mentor["chat_id"], f'Студент {get_pretty_mention_db(student)} привязан к Вам админом'),
        bot.send_message(student["chat_id"],
                         f'Ментор {get_pretty_mention_db(mentor)} привязан к Вам админом')
    )
    logging.debug(f'chat_id: {message.from_user.id} done ADD_STUDENT_FOR')


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_delete_student_info_'))
async def callback_delete_student_info(call: types.CallbackQuery) -> None:
    db = Database()
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        *[types.InlineKeyboardButton(f'{student["name"]}',
                                     callback_data=f'admin_delete_stud_' \
                                                   f'{call.data[26:]}_{student["course_works"][0]["id"]}_{student["id"]}')
          for student in (await db.get_mentors(chat_id=int(call.data[26:])))[0]['students']])
    logging.debug(f'chat_id: {call.from_user.id} preparing admin_delete_student_info')
    await gather(bot.delete_message(call.from_user.id, call.message.id),
                 bot.answer_callback_query(call.id),
                 bot.send_message(call.from_user.id, 'Выберите какого студента удалить', reply_markup=markup))
    logging.debug(f'chat_id: {call.from_user.id} done admin_delete_student_info')


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_delete_stud_'))
async def callback_delete_student(call: types.CallbackQuery) -> None:
    db = Database()
    mentor_chat_id, work_id, student_id = call.data[18:].split('_')
    logging.debug(
        f'chat_id: {call.from_user.id} getting mentor with chat_id {mentor_chat_id}, student with chat_id {student_id}')
    student_info = (await db.get_students(id_field=student_id))[0]
    logging.debug(f'chat_id: {call.from_user.id} got student {student_info}')
    mentor_id = (await db.get_mentors(chat_id=mentor_chat_id))[0]['id']
    logging.debug(f'chat_id: {call.from_user.id} got mentor with id {mentor_id}')

    logging.debug(f'chat_id: {call.from_user.id} preparing admin_delete_stud')
    await gather(
        db.reject_student(mentor_id, student_id),
        bot.send_message(mentor_chat_id, f'Студент {get_pretty_mention_db(student_info)} удален'),
        bot.send_message(student_info['chat_id'],
                         f'{get_pretty_mention_db((await db.get_mentors(chat_id=mentor_chat_id))[0])} больше не Ваш ментор'),
        bot.answer_callback_query(call.id),
        bot.send_message(call.from_user.id, 'Студент удален'),
        bot.delete_message(call.from_user.id, call.message.id)
    )
    logging.debug(f'chat_id: {call.from_user.id} done admin_delete_stud')


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_edit_subjects_'))
async def callback_edit_subjects(call: types.CallbackQuery) -> None:
    markup = types.InlineKeyboardMarkup()
    add = types.InlineKeyboardButton('Добавить тему', callback_data='admin_add_subject_' + call.data[20:])
    delete = types.InlineKeyboardButton('Удалить тему', callback_data='admin_delete_subject_info_' + call.data[20:])
    markup.add(add, delete)
    logging.debug(f'chat_id: {call.from_user.id} preparing admin_edit_subjects')
    await gather(bot.delete_message(call.from_user.id, call.message.id),
                 bot.answer_callback_query(call.id),
                 bot.send_message(call.from_user.id, 'Что сделать с темами?', reply_markup=markup))
    logging.debug(f'chat_id: {call.from_user.id} done admin_edit_subjects')


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_delete_subject_info_'))
async def callback_delete_subject_info(call: types.CallbackQuery) -> None:
    db = Database()
    mentor = (await db.get_mentors(chat_id=call.data[26:]))[0]

    markup = types.InlineKeyboardMarkup()
    markup.add(
        *[types.InlineKeyboardButton(subject['subject'], callback_data=f'admin_delete_subject_' \
                                                                       f'{subject["id"]}_{call.data[26:]}')
          for subject in mentor["subjects"]])
    logging.debug(f'chat_id: {call.from_user.id} preparing admin_delete_subject_info')
    await gather(bot.delete_message(call.from_user.id, call.message.id),
                 bot.answer_callback_query(call.id),
                 bot.send_message(call.from_user.id,
                                  f'Удалить тему у ментора {get_pretty_mention_db(mentor)}',
                                  reply_markup=markup))
    logging.debug(f'chat_id: {call.from_user.id} done admin_delete_subject_info')


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_delete_subject_'))
async def callback_delete_subject(call: types.CallbackQuery) -> None:
    db = Database()
    subject_id, mentor_chat_id = call.data[21:].split('_')
    subject = (await db.get_subjects(subject_id))[0]
    logging.debug(f'chat_id {call.from_user.id} got subject {subject}')
    if subject is None:
        await bot.send_message(call.from_user.id, f'Направление НЕ НАЙДЕНО')
        return
    logging.debug(f'chat_id: {call.from_user.id} getting mentor with chat_id {mentor_chat_id}')
    mentor = (await db.get_mentors(chat_id=mentor_chat_id))[0]
    logging.debug(f'chat_id: {call.from_user.id} got mentor {mentor}')

    logging.debug(f'chat_id: {call.from_user.id} preparing admin_delete_subject')
    await gather(
        db.remove_mentor_subjects(mentor['id'], [subject['id']]),
        bot.send_message(mentor_chat_id, f'Тема {subject["subject"]} успешно удалена админом'),
        bot.send_message(call.from_user.id,
                         f'Тема {subject["subject"]} успешно удалена у {get_pretty_mention_db(mentor)}'),
        bot.answer_callback_query(call.id),
        bot.delete_message(call.from_user.id, call.message.id))
    logging.debug(f'chat_id: {call.from_user.id} done admin_delete_subject')


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_add_subject_'))
async def callback_add_subject_info(call: types.CallbackQuery) -> None:
    mentor_chat_id = call.data[18:]

    force = types.ForceReply(selective=False)
    logging.debug(f'chat_id: {call.from_user.id} preparing admin_add_subject')
    await gather(bot.delete_message(call.from_user.id, call.message.id),
                 bot.send_message(call.from_user.id,
                                  'Добавлять тему/темы СТРОГО в формате `тема1;тема2;тема3`'),
                 bot.send_message(call.from_user.id, f'Добавить тему для {mentor_chat_id}', reply_markup=force),
                 bot.answer_callback_query(call.id))
    logging.debug(f'chat_id: {call.from_user.id} done admin_add_subject')


@bot.message_handler(
    func=lambda message: message.reply_to_message and message.reply_to_message.text.startswith('Добавить тему для '))
async def callback_user_add_subject(message: types.Message) -> None:
    db = Database()

    mentor_chat_id = message.reply_to_message.text[18:]
    logging.debug(f'chat_id: {message.from_user.id} getting mentor with chat_id {mentor_chat_id}')
    mentor = (await db.get_mentors(chat_id=mentor_chat_id))[0]
    logging.debug(f'chat_id: {message.from_user.id} got mentor {mentor}')
    subjects_to_add = message.text.strip().split(';')
    for subject in subjects_to_add:

        await db.add_subject(subject)
        has_subject = False
        for subj in mentor['subjects']:
            if subj['subject'] == subject:
                has_subject = True
                break

        if has_subject:
            await bot.send_message(message.from_user.id, f'Тема __{subject}__ уже была добавлена')
            return

        logging.debug(f'chat_id: {message.from_user.id} preparing ADD SUBJECT FOR')
        await gather(bot.send_message(message.from_user.id, f'Тема __{subject}__ успешно добавлена'),
                     db.add_mentor_subjects(mentor['id'], [await db.add_subject(subject)]))
        logging.debug(f'chat_id: {message.from_user.id} done ADD SUBJECT FOR')

@bot.callback_query_handler(func=lambda call: call.data.startswith('add_mentor_via_admin_'))
async def callback_add_mentor(call):
    db = Database()
    new_mentor_info = await bot.get_chat(call.data[21:])
    student_info = await db.get_students(chat_id=call.data[21:])
    logging.info(f'chat_id: {call.data[21:]} is now a mentor')
    mentor_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mentor_markup.add(*[types.KeyboardButton(task)
                        for task in await mentor_start()])
    if await db.check_is_support(call.from_user.id):
        mentor_markup.add(*[types.KeyboardButton(task)
                            for task in await support_start()])
    await gather(db.add_mentor({'name': get_name(new_mentor_info),
                                'chat_id': call.data[21:],
                                'subjects': None}),
                 bot.send_message(call.data[21:], 'Теперь Вы ментор!', reply_markup=mentor_markup),
                 bot.send_message(call.from_user.id, f'@{new_mentor_info.username} стал ментором'),
                 bot.answer_callback_query(call.id),
                 bot.delete_message(call.from_user.id, call.message.id))
    if student_info:
        await db.remove_student(student_info[0]['id'])

