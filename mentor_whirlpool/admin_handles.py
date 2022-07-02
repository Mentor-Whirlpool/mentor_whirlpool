from mentor_whirlpool.telegram import bot
from telebot import types, asyncio_filters
from telebot.asyncio_handler_backends import State, StatesGroup
from mentor_whirlpool.database import Database
from re import fullmatch
from asyncio import create_task, gather
from mentor_whirlpool.confirm import confirm
from mentor_whirlpool.mentor_handles import mentor_start
from mentor_whirlpool.students_handles import generic_start
from mentor_whirlpool.support_handles import support_start
import logging


class AdminStates(StatesGroup):
    add_subject = State()
    add_support = State()


async def admin_start(message):
    """
    Should provide a starting point with a ReplyMarkupKeyboard
    It should contain all the following handles

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class

    Returns
    -------
    iterable
        Iterable with all handles texts
    """
    return ['Менторы', 'Запросы (админ)', 'Редактировать поддержку', 'Редактировать направления']


async def admin_help():
    return 'Привет! Ты и сам знаешь, зачем я здесь. Мой функционал:\n\n' \
           '- «Менторы» — возвращает список менторов с количеством студентов по каждой ' \
           'из их тем. При выборе конкретного ментора можно редактировать его темы, ' \
           'студентов, а также удалить этого ментора.\n' \
           '- «Запросы» — показывает висящие запросы от студентов.\n' \
           '- «Редактировать направления» — позволяет добавлять и удалять направления.\n'


@bot.callback_query_handler(func=lambda call: call.data.startswith('add_mentor_via_admin_'))
async def callback_add_mentor(call):
    db = Database()
    new_mentor_info = await bot.get_chat(call.data[21:])
    student_info = await db.get_students(chat_id=call.data[21:])
    logging.info(f'chat_id: {call.data[21:]} is now a mentor')
    mentor_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mentor_markup.add(*[types.KeyboardButton(task)
                        for task in await mentor_start(None)])
    if await db.check_is_support(call.from_user.id):
        mentor_markup.add(*[types.KeyboardButton(task)
                            for task in await support_start(None)])
    await gather(db.add_mentor({'name': new_mentor_info.username, 'chat_id': call.data[21:], 'subjects': None}),
                 bot.send_message(call.data[21:], 'Теперь Вы ментор!', reply_markup=mentor_markup),
                 bot.send_message(call.from_user.id, f'@{new_mentor_info.username} стал ментором'),
                 bot.answer_callback_query(call.id),
                 bot.delete_message(call.from_user.id, call.message.id))
    if student_info:
        await db.remove_student(student_info[0]['id'])


@bot.callback_query_handler(func=lambda call: call.data == 'adm_add_subj')
async def add_subject_admin(call):
    """
    If from_user.id is in admins, ask him to write name of new subject

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    logging.debug(f'chat_id: {call.from_user.id} preparing add_subject')
    await gather(bot.set_state(call.from_user.id, AdminStates.add_subject),
                 bot.send_message(call.from_user.id, "Введите название направления:"),
                 bot.delete_message(call.from_user.id, call.message.id))
    logging.debug(f'chat_id: {call.from_user.id} done add_subject')


@bot.message_handler(func=lambda msg: msg.text == 'Редактировать направления')
async def edit_subjects(message):
    """
    Prints a list of all subjects as inline buttons with subjects and a button
    for addition of subject

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    db = Database()
    if not await db.check_is_admin(message.from_user.id):
        logging.warn(f'MENTORS: chat_id: {message.from_user.id} is not an admin')
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(*[types.InlineKeyboardButton(f'Удалить: {subj}', callback_data=f'adm_rem_subj_{subj}')
                 for subj in await db.get_subjects()])
    markup.add(types.InlineKeyboardButton('Добавить направление',
                                          callback_data='adm_add_subj'))
    await bot.send_message(message.from_user.id, 'Что сделать?', reply_markup=markup)
    await bot.delete_message(message.chat.id, message.id)


@bot.message_handler(state=AdminStates.add_subject)
async def save_subject(message):
    logging.debug(f'chat_id: {message.from_user.id} is in add_subject')

    db = Database()
    if message.text in await db.get_subjects():
        await gather(bot.delete_state(message.from_user.id),
                     bot.send_message(message.from_user.id, "Предмет уже добавлен."))
        logging.warn(f'chat_id: {message.from_user.id} subject already added')
        return
    await gather(db.add_subject(message.text),
                 bot.delete_state(message.from_user.id),
                 bot.send_message(message.from_user.id, "Предмет успешно добавлен."))
    logging.debug(f'chat_id: {message.from_user.id} subject has been added')


@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_rem_subj_'))
async def remove_subject(call):
    logging.debug(f'chat_id: {call.from_user.id} is in remove_subject')

    db = Database()
    await gather(db.remove_subject(call.data[13:]),
                 bot.send_message(call.from_user.id, "Предмет успешно удалён."),
                 bot.delete_message(call.from_user.id, call.message.id))
    logging.debug(f'chat_id: {call.from_user.id} subject has been removed')


@bot.message_handler(func=lambda msg: msg.text == 'Запросы (админ)')
async def course_work(message):
    db = Database()
    if not await db.check_is_admin(message.from_user.id):
        logging.warn(f'MENTORS: chat_id: {message.from_user.id} is not an admin')
        return

    course_works = await db.get_course_works()
    messages = []
    if course_works:
        for work in course_works:
            messages.append(f'@{(await db.get_students(work["student"]))[0]["name"]}\n{work["description"]}')
        message_course_works = '\n--------\n'.join(messages)
        await bot.send_message(message.from_user.id, message_course_works)
    else:
        await bot.send_message(message.from_user.id, 'Нет запросов курсовых работ')
    await bot.delete_message(message.chat.id, message.id)


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
        logging.warn(f'MENTORS: chat_id: {message.from_user.id} is not an admin')
        return

    logging.debug(f'chat_id: {message.from_user.id} in MENTORS')
    mentors = await db.get_mentors()
    tasks = []
    for mentor in mentors:

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Выбрать', callback_data='admin_choose_mentor_' + str(mentor['chat_id'])))

        if not mentor['subjects']:
            tasks.append(
                bot.send_message(message.from_user.id, f'<b>@{mentor["name"]}</b>\nНет выбранных направлений',
                                 reply_markup=markup,
                                 parse_mode='html'))
            continue

        subjects_count_dict = dict.fromkeys(mentor['subjects'], 0)

        for student in mentor['students']:
            for subject in student['course_works'][0]['subjects']:

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


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_choose_mentor_'))
async def callback_mentors_info(call):
    db = Database()
    mentor_info = (await db.get_mentors(chat_id=int(call.data[20:])))[0]
    logging.debug(f'chat_id: {call.from_user.id} chosen mentor {mentor_info}')
    message_subjects = 'Нет выбранных направлений'
    message_students = 'Нет студентов'
    if mentor_info['subjects']:
        message_subjects = '\n'.join(mentor_info['subjects'])
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
    message = f'@{mentor_info["name"]}\n----Направления----\n{message_subjects}\n----Студенты----\n{message_students}'
    logging.debug(f'chat_id: {call.from_user.id} preparing admin_choose_mentor')
    await bot.send_message(call.from_user.id, message, reply_markup=markup)
    await bot.delete_message(call.from_user.id, call.message.id)
    logging.debug(f'chat_id: {call.from_user.id} sent admin_choose_mentor')


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_delete_mentor_'))
async def delete_mentor(call):
    db = Database()
    mentor_info = (await db.get_mentors(chat_id=int(call.data[20:])))[0]
    logging.debug(f'chat_id: {call.from_user.id} chosen mentor {mentor_info}')
    logging.debug(f'chat_id: {call.from_user.id} preparing admin_delete_mentor')
    student_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    student_markup.add(*[types.KeyboardButton(task)
                         for task in await generic_start(None)])
    if await db.check_is_support(call.from_user.id):
        student_markup.add(*[types.KeyboardButton(task)
                             for task in await support_start(None)])
    await gather(
        db.remove_mentor(id_field=mentor_info['id']),
        bot.send_message(call.from_user.id, f'Ментор @{mentor_info["name"]} был удален'),
        bot.send_message(mentor_info['chat_id'], 'Вы больше не являетесь ментором', reply_markup=student_markup),
        bot.delete_message(call.from_user.id, call.message.id),
        bot.answer_callback_query(call.id)
    )
    logging.debug(f'chat_id: {call.from_user.id} done admin_delete_mentor')


# students
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_edit_students_'))
async def edit_students(call):
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
async def callback_add_student_subject_choice(call):
    db = Database()
    mentor_subjects = (await db.get_mentors(chat_id=call.data[33:]))[0]['subjects']

    markup = types.InlineKeyboardMarkup()
    markup.add(*[types.InlineKeyboardButton(subject,
                                            callback_data='admin_add_student_with_subject_' + subject + '_' + call.data[
                                                                                                              33:])
                 for subject in mentor_subjects])

    logging.debug(f'chat_id: {call.from_user.id} preparing admin_add_student_subject_choice')
    await bot.send_message(call.from_user.id, 'Выберете направление курсовой чтобы добавить студента',
                           reply_markup=markup)
    await bot.answer_callback_query(call.id)
    await bot.delete_message(call.from_user.id, call.message.id)
    logging.debug(f'chat_id: {call.from_user.id} done admin_add_student_subject_choice')


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_add_student_with_subject_'))
async def callback_add_student(call):
    subject, mentor_chat_id = call.data[31:].split('_')

    force = types.ForceReply(selective=False)
    logging.debug(f'chat_id: {call.from_user.id} preparing admin_add_student_with_subject')
    await gather(bot.delete_message(call.from_user.id, call.message.id),
                 bot.send_message(call.from_user.id,
                                  'Добавлять студента СТРОГО в формате <pre>@student;course_work_name</pre>',
                                  parse_mode='html'),
                 bot.send_message(call.from_user.id, f'Добавить студента для {mentor_chat_id} {subject}',
                                  reply_markup=force),
                 bot.answer_callback_query(call.id))
    logging.debug(f'chat_id: {call.from_user.id} done admin_add_student_with_subject')


@bot.message_handler(func=lambda message: message.reply_to_message and message.reply_to_message.text.startswith(
    'Добавить студента для '))
async def callback_user_add_subject(message):
    db = Database()
    mentor_chat_id, subject = message.reply_to_message.text[22:].split()
    logging.debug(f'chat_id: {message.from_user.id} getting mentor with chat_id {mentor_chat_id}')
    mentor_id = (await db.get_mentors(chat_id=mentor_chat_id))[0]['id']
    logging.debug(f'chat_id: {message.from_user.id} got mentor with id {mentor_id}')
    student_name, course_work_name = message.text.strip()[1:].split(';')

    student_chat_id = None
    for student in await db.get_students():
        if student['name'] == student_name:
            student_chat_id = student['chat_id']
            break

    if not student_chat_id:
        await bot.send_message(message.from_user.id, f'Студент {student_name} НЕ НАЙДЕН')
        return

    logging.debug(f'chat_id: {message.from_user.id} preparing ADD_STUDENT_FOR')
    await gather(
        db.accept_work(mentor_id, await db.add_course_work(
            {'name': student_name, 'chat_id': student_chat_id, 'subjects': [subject],
             'description': course_work_name})),
        bot.send_message(message.from_user.id,
                         f'Студент {student_name} добавлен к ментору {(await db.get_mentors(chat_id=mentor_chat_id))[0]["name"]}'),
        bot.send_message(mentor_chat_id, f'Студент @{student_name} привязан к Вам админом'),
        bot.send_message(student_chat_id,
                         f'@{(await db.get_mentors(chat_id=mentor_chat_id))[0]["name"]} привязан к Вам админом')
    )
    logging.debug(f'chat_id: {message.from_user.id} done ADD_STUDENT_FOR')


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_delete_student_info_'))
async def callback_delete_student_info(call):
    db = Database()
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        *[types.InlineKeyboardButton(f'{student["name"]}',
                                     callback_data=f'admin_delete_stud_{call.data[26:]}_{str(student["course_works"][0]["id"])}_{student["id"]}')
          for student in (await db.get_mentors(chat_id=int(call.data[26:])))[0]['students']])
    logging.debug(f'chat_id: {call.from_user.id} preparing admin_delete_student_info')
    await gather(bot.delete_message(call.from_user.id, call.message.id),
                 bot.answer_callback_query(call.id),
                 bot.send_message(call.from_user.id, 'Выберите какого студента удалить', reply_markup=markup))
    logging.debug(f'chat_id: {call.from_user.id} done admin_delete_student_info')


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_delete_stud_'))
async def callback_delete_student(call):
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
        bot.send_message(mentor_chat_id, f'Студент @{student_info["name"]} удален'),
        bot.send_message(student_info['chat_id'],
                         f'@{(await db.get_mentors(chat_id=mentor_chat_id))[0]["name"]} больше не Ваш ментор'),
        bot.answer_callback_query(call.id),
        bot.send_message(call.from_user.id, 'Студент удален'),
        bot.delete_message(call.from_user.id, call.message.id)
    )
    logging.debug(f'chat_id: {call.from_user.id} done admin_delete_stud')


# subjects
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_edit_subjects_'))
async def callback_edit_subjects(call):
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
async def callback_delete_subject_info(call):
    db = Database()
    mentor_subjects = (await db.get_mentors(chat_id=call.data[26:]))[0]['subjects']

    markup = types.InlineKeyboardMarkup()
    markup.add(
        *[types.InlineKeyboardButton(subject, callback_data='admin_delete_subject_' + subject + '_' + call.data[26:])
          for
          subject in mentor_subjects])
    logging.debug(f'chat_id: {call.from_user.id} preparing admin_delete_subject_info')
    await gather(bot.delete_message(call.from_user.id, call.message.id),
                 bot.answer_callback_query(call.id),
                 bot.send_message(call.from_user.id,
                                  f'Удалить тему у ментора @{(await db.get_mentors(chat_id=call.data[26:]))[0]["name"]}',
                                  reply_markup=markup))
    logging.debug(f'chat_id: {call.from_user.id} done admin_delete_subject_info')


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_delete_subject_'))
async def callback_delete_subject(call):
    db = Database()
    subject, mentor_chat_id = call.data[21:].split('_')
    logging.debug(f'chat_id: {call.from_user.id} getting mentor with chat_id {mentor_chat_id}')
    mentor_id = (await db.get_mentors(chat_id=mentor_chat_id))[0]['id']
    logging.debug(f'chat_id: {call.from_user.id} got mentor with id {mentor_id}')

    logging.debug(f'chat_id: {call.from_user.id} preparing admin_delete_subject')
    await gather(
        db.remove_mentor_subjects(mentor_id, [subject]),
        bot.send_message(mentor_chat_id, f'Тема {subject} успешно удалена админом'),
        bot.send_message(call.from_user.id,
                         f'Тема {subject} успешно удалена у @{(await db.get_mentors(chat_id=mentor_chat_id))[0]["name"]}',
                         ),
        bot.answer_callback_query(call.id),
        bot.delete_message(call.from_user.id, call.message.id))
    logging.debug(f'chat_id: {call.from_user.id} done admin_delete_subject')


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_add_subject_'))
async def callback_add_subject_info(call):
    mentor_chat_id = call.data[18:]

    force = types.ForceReply(selective=False)
    logging.debug(f'chat_id: {call.from_user.id} preparing admin_add_subject')
    await gather(bot.delete_message(call.from_user.id, call.message.id),
                 bot.send_message(call.from_user.id,
                                  'Добавлять тему/темы СТРОГО в формате <pre>тема1;тема2;тема3</pre>',
                                  parse_mode='html'),
                 bot.send_message(call.from_user.id, f'Добавить тему для {mentor_chat_id}', reply_markup=force),
                 bot.answer_callback_query(call.id))
    logging.debug(f'chat_id: {call.from_user.id} done admin_add_subject')


@bot.message_handler(
    func=lambda message: message.reply_to_message and message.reply_to_message.text.startswith('Добавить тему для '))
async def callback_user_add_subject(message):
    db = Database()

    mentor_chat_id = message.reply_to_message.text[18:]
    logging.debug(f'chat_id: {message.from_user.id} getting mentor with chat_id {mentor_chat_id}')
    mentor_id = (await db.get_mentors(chat_id=mentor_chat_id))[0]['id']
    logging.debug(f'chat_id: {message.from_user.id} got mentor with id {mentor_id}')
    subjects_to_add = message.text.strip().split(';')
    for subject in subjects_to_add:

        await db.add_subject(subject)
        mentor_subjects = (await db.get_mentors(chat_id=mentor_chat_id))[0]['subjects']
        if mentor_subjects and subject in mentor_subjects:
            await bot.send_message(message.from_user.id, f'Тема <b>{subject}</b> уже была добавлена', parse_mode='html')
            return

        add_mentor_sub_task = create_task(db.add_mentor_subjects(mentor_id, [subject]))
        logging.debug(f'chat_id: {message.from_user.id} preparing ADD SUBJECT FOR')
        await bot.send_message(message.from_user.id, f'Тема <b>{subject}</b> успешно добавлена', parse_mode='html')
        await add_mentor_sub_task
        logging.debug(f'chat_id: {message.from_user.id} done ADD SUBJECT FOR')


@bot.message_handler(func=lambda msg: msg.text == 'Редактировать поддержку')
async def edit_subjects(message):
    """
    Prints a list of all suppoerts as inline buttons and a button
    for addition of support

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    db = Database()
    if not await db.check_is_admin(message.from_user.id):
        logging.warn(f'MENTORS: chat_id: {message.from_user.id} is not an admin')
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(*[types.InlineKeyboardButton(f'Удалить: {supp["name"]}', callback_data=f'adm_rem_supp_{supp["id"]}')
                 for supp in await db.get_supports()])
    markup.add(types.InlineKeyboardButton('Добавить саппорта',
                                          callback_data='adm_add_supp'))
    await bot.send_message(message.from_user.id, 'Что сделать?', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_rem_supp_'))
async def callback_delete_subject(call):
    db = Database()
    supp_id = int(call.data[13:])
    supp = await db.get_supports(supp_id)
    logging.debug(f'chat_id: {call.from_user.id} preparing adm_rem_supp')
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*[types.KeyboardButton(task)
                 for task in await generic_start(None)])
    await gather(
        db.remove_support(supp_id),
        bot.send_message(supp[0]['chat_id'], f'Вы больше не часть поддержки!', reply_markup=markup),
        bot.send_message(call.from_user.id,
                         f'Саппорт {supp[0]["name"]} удалён'),
        bot.answer_callback_query(call.id))
    logging.debug(f'chat_id: {call.from_user.id} done adm_rem_supp')


@bot.callback_query_handler(func=lambda call: call.data == 'adm_add_supp')
async def callback_add_support(call):
    await gather(bot.set_state(call.from_user.id, AdminStates.add_support),
                 bot.answer_callback_query(call.id),
                 bot.send_message(call.from_user.id,
                                  'Введите chat_id нового саппорта\nПолучить chat_id возможно у @RawDataBot'))


@bot.message_handler(state=AdminStates.add_support)
async def add_support_chat_id_handler(message):
    db = Database()
    supp_chat_id = message.text
    try:
        supp = await bot.get_chat(supp_chat_id)
    except:
        await gather(bot.send_message(message.from_user.id,
                                      'Пользователь не найден!\n'
                                      'Убедитесь что вы ввели chat_id верно, и пользователь начал взаимодействие с ботом'),
                     bot.delete_state(message.from_user.id))
        return
    supp_dict = {
        'chat_id': supp_chat_id,
        'name': supp.username,
    }
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*[types.KeyboardButton(task)
                 for task in await support_start(None)])
    await gather(db.add_support(supp_dict),
                 bot.delete_state(message.from_user.id),
                 bot.send_message(message.from_user.id, 'Саппорт успешно добавлен'),
                 bot.send_message(supp_chat_id, 'Теперь вы член группы поддержки!', reply_markup=markup))
    stud = await db.get_students(chat_id=supp_chat_id)
    if stud:
        await db.remove_student(stud[0]['id'])

bot.add_custom_filter(asyncio_filters.StateFilter(bot))
