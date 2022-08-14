from mentor_whirlpool.telegram import bot
from telebot import types
from mentor_whirlpool.confirm import confirm
from telebot.asyncio_handler_backends import State, StatesGroup
from mentor_whirlpool.database import Database
from mentor_whirlpool.utils import get_pretty_mention, get_pretty_mention_db, get_name
from asyncio import gather, create_task
import logging

logging.getLogger(__name__)


class MentorStates(StatesGroup):
    add_idea = State()
    add_support = State()


async def mentor_start(message):
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
    return ['Запросы', 'Мои направления', 'Мои студенты', 'Пет-проект', 'Поддержка']


async def mentor_help():
    return 'Привет! Я здесь для того, чтобы помочь тебе поддерживать связь со ' \
           'студентами, нуждающимися в твоих советах. Прочитай это сообщение ' \
           'внимательно, ведь это важно! Мой функционал:\n\n' \
           '- Каждый раз, когда студент добавляет запрос по твоему направлению, тебе ' \
           'будет приходить сообщение.\n' \
           '- Кнопка «Запросы» вернет список «висящих» запросов от студентов.\n' \
           '- Нажимая на кнопку «Мои направления», ты можешь увидеть список направлений, по ' \
           'которым ты ведешь менторство. Там же ты можешь удалить или добавить ' \
           'направление. Если ты хочешь добавить направление, которого нет в списке ' \
           'доступных, напиши в поддержку.\n' \
           '- «Мои студенты» вернет тебе список твоих студентов с названием их работ.\n' \
           '- Кнопка «Поддержка» нужна для связи со службой поддержки. Обращайся, если ' \
           'у тебя возникли вопросы по функционалу, темам, направлениям или студентам.'


@bot.message_handler(func=lambda msg: msg.text == 'Запросы')
async def works(message):
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
async def callback_query_work(call):
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


@bot.message_handler(func=lambda msg: msg.text == 'Мои направления')
async def my_subjects(message):
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
    message_subjects = '<b>Мои направления</b>\n'

    if mentor["subjects"]:
        delete = types.InlineKeyboardButton('Удалить', callback_data='mnt_sub_to_delete')
        markup.row(add, delete)
        message_subjects += '\n'.join([subj['subject'] for subj in mentor["subjects"]])
    else:
        markup.add(add)

    logging.debug(f'chat_id: {message.from_user.id} preparing MY_SUBJECTS')
    await bot.send_message(message.chat.id, f'{message_subjects}', reply_markup=markup)
    logging.debug(f'chat_id: {message.from_user.id} done MY_SUBJECTS')


# мои темы получаешь еще кнопки с темам, тыкаешь на кнопку получаешь список курсачей по этой теме (тоже кнопками) -> жмешь на курсач и принимаешь его

@bot.callback_query_handler(func=lambda call: call.data.startswith('subject_'))
async def callback_show_course_works_by_subject(call):
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
async def callback_show_subjects_to_add(call):
    db = Database()
    answ_task = create_task(bot.answer_callback_query(call.id))
    mentor = (await db.get_mentors(chat_id=call.from_user.id))[0]

    subjects_to_add = await db.get_subjects()

    for subject in mentor["chat_id"]:
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
async def callback_add_subject(call):
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
async def callback_show_subjects_to_delete(call):
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
async def callback_del_subject(call):
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


@bot.message_handler(func=lambda msg: msg.text == 'Мои студенты')
async def my_students(message):
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


@bot.message_handler(func=lambda msg: msg.text == 'Пет-проект')
async def start_idea_by_mentor(message):
    await bot.delete_message(message.chat.id, message.id)
    db = Database()
    if not await db.check_is_mentor(message.from_user.id):
        logging.warning(f'User isn\'t a mentor [user_id: {message.from_user.id}]')
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Добавить', callback_data='mnt_add_idea'),
               types.InlineKeyboardButton('Удалить', callback_data='mnt_idea_to_del'))
    ideas = await db.get_ideas()
    logging.debug(ideas)
    await bot.send_message(message.from_user.id,
                           '\n'.join(['Уже существующие идеи:'] +
                                     [f'- {idea["description"]}' for idea in ideas]))
    await bot.send_message(message.from_user.id, 'Что сделать?', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'mnt_add_idea')
async def add_idea_by_mentor(call):
    await bot.delete_message(call.from_user.id, call.message.id)
    logging.debug(f'Delete message  [{call.data}: {call.from_user.id}]')

    await bot.answer_callback_query(call.id)

    db = Database()

    mentor = (await db.get_mentors(chat_id=call.from_user.id))[0]
    logging.debug(f'mentor: {mentor}')

    message_subjects = '__Выберете направление пет-проекта__\n'

    if not mentor["subjects"]:
        await bot.send_message(call.from_user.id, '__Сначала добавьте направления!__')
        logging.warning(f'chat_id: {call.from_user.id} doesn\'t have any subjects')
        return
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        *[types.InlineKeyboardButton(sub['subject'], callback_data=f'mnt_sub_for_idea_{sub["id"]}')
          for sub in mentor["subjects"]])

    logging.debug(f'chat_id: {call.from_user.id} preparing MY_SUBJECTS')
    await bot.send_message(call.from_user.id, f'{message_subjects}', reply_markup=markup)
    logging.debug(f'chat_id: {call.from_user.id} done MY_SUBJECTS')


@bot.callback_query_handler(func=lambda call: call.data.startswith('mnt_sub_for_idea_'))
async def callback_add_idea(call):
    db = Database()
    subject = (await db.get_subjects(id_field=call.data[17:]))[0]
    logging.debug(f'chat_id: {call.from_user.id} preparing add_idea')
    await bot.set_state(call.from_user.id, MentorStates.add_idea, call.message.chat.id)
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['subject'] = subject['id']
    await gather(bot.send_message(call.from_user.id, f'Тема: __{subject["subject"]}__\n\n'
                                                     f'Введи название работы.\n'),
                 bot.delete_message(call.from_user.id, call.message.id))
    logging.debug(f'chat_id: {call.from_user.id} done add_idea')


@bot.message_handler(state=MentorStates.add_idea)
async def save_idea(message):
    logging.debug(f'chat_id: {message.from_user.id} is in add_work_flag')
    # idea = dict() вроде можно убрать эту строчку

    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        idea={'name': get_name(message.from_user)',
              'chat_id': message.chat.id,
              'subjects': [data['subject']],
              'description': message.text}

    db = Database()
    # subject = create_task(db.get_subjects(idea['subjects'][0])) вроде нигде не используется
    id = await db.get_mentors(chat_id=message.from_user.id)
    logging.debug(f'chat_id: {message.from_user.id} self {id}')

    if id:
        ideas = await db.get_ideas(mentor=id[0]['id'])
        # ideas_names = [work['description'] for work in ideas] вроде нигде не используется

        if idea['description'] in ideas:
            logging.warning(f'chat_id: {message.from_user.id} idea already exists')
            await gather(bot.delete_state(message.from_user.id, message.chat.id),
                         bot.send_message(message.chat.id, "Пет-проект с такой темой уже добавлен!"))
            return
    logging.debug(f'chat_id: {message.from_user.id} preparing add_work_flag')
    await gather(db.add_idea(idea),
                 bot.delete_message(message.from_user.id, message.id),
                 bot.delete_state(message.from_user.id, message.chat.id),
                 bot.send_message(message.chat.id, f"Пет-проект __{message.text}__ успешно добавлен!"))
    logging.debug(f'chat_id: {message.from_user.id} done add_idea')


@bot.callback_query_handler(func=lambda call: call.data == 'mnt_idea_to_del')
async def callback_del_idea_by_mentor(call):
    db = Database()
    myself = await db.get_mentors(chat_id=call.from_user.id)
    mentor_ideas = await db.get_ideas(mentor=myself[0]['id'])

    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(*[types.InlineKeyboardButton(idea['description'], callback_data='mnt_idea_del_' + str(idea['id']))
                 for idea in mentor_ideas])

    logging.debug(f'chat_id: {call.from_user.id} preparing mnt_idea_to_del')
    await gather(bot.answer_callback_query(call.id),
                 bot.delete_message(call.from_user.id, call.message.id),
                 bot.send_message(call.from_user.id,
                                  '__Удалить пет-проект__',
                                  reply_markup=markup))
    logging.debug(f'chat_id: {call.from_user.id} done mnt_idea_to_del')


@bot.callback_query_handler(func=lambda call: call.data.startswith('mnt_idea_del_'))
async def callback_del_idea(call):
    db = Database()
    idea = (await db.get_ideas(call.data[13:]))[0]

    logging.debug(f'chat_id: {call.from_user.id} preparing mnt_idea_del_')
    await gather(db.remove_idea(idea['id']),
                 bot.send_message(call.from_user.id,
                                  f'Идея __{idea["description"]}__ успешно удалена'),
                 bot.delete_message(call.from_user.id, call.message.id),
                 bot.answer_callback_query(call.id))
    logging.debug(f'chat_id: {call.from_user.id} done mnt_idea_del_')
