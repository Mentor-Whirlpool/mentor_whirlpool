from telegram import bot
from telebot import types
from confirm import confirm
from database import Database
from asyncio import gather, create_task

# from gettext import translation

from confirm import confirm
from database import Database


# strings = translation('mentor', localedir='locales', languages=['RU']).gettext


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
    return ['Запросы', 'Мои темы', 'Мои студенты', 'Поддержка']


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
    db = Database()
    if not await db.check_is_mentor(message.from_user.id):
        await bot.send_message(message.chat.id, '<b>Вы не ментор</b>', parse_mode='html')
        return
    my_subjects_ = (await db.get_mentors(chat_id=message.from_user.id))[0]['subjects']
    if not my_subjects_:
        await bot.send_message(message.chat.id, '<b>Сначала добавьте темы</b>', parse_mode='html')
        return
    course_works = await db.get_course_works(subjects=my_subjects_)
    students = (await db.get_mentors(chat_id=message.from_user.id))[0]['students']

    for stud in students:
        for work in stud['course_works']:
            try:
                course_works.remove(work)
            except ValueError:
                continue

    markup = types.InlineKeyboardMarkup()

    for work in course_works:
        if await db.get_accepted(id_feild=work['id']):
            markup.add(
                types.InlineKeyboardButton(
                    f'@{(await db.get_students(work["student"]))[0]["name"]} - {work["description"]} (доп. запрос)',
                    callback_data='mnt_work_' + str(work['id'])))
            continue
        markup.add(
            types.InlineKeyboardButton(
                f'@{(await db.get_students(work["student"]))[0]["name"]} - {work["description"]}',
                callback_data='mnt_work_' + str(work['id'])))

    await bot.send_message(message.chat.id, '<b>Доступные курсовые работы</b>',
                           reply_markup=markup, parse_mode='html')


@bot.callback_query_handler(func=lambda call: call.data.startswith('mnt_work_'))
async def callback_query_work(call):
    db = Database()
    mentor_info = (await db.get_mentors(chat_id=call.from_user.id))[0]
    course_work_info = (await db.get_course_works(int(call.data[9:])))[0]

    await gather(db.accept_work(mentor_info['id'], call.data[9:]),
                 bot.answer_callback_query(call.id),
                 bot.send_message(call.from_user.id,
                                  f'Вы взялись за <b>{course_work_info["description"]}</b>\n'
                                  f'Напишите @{(await db.get_students(id_field=course_work_info["student"]))[0]["name"]}',
                                  parse_mode='html'),
                 bot.send_message((await db.get_students(id_field=course_work_info["student"]))[0]["chat_id"],
                                  f'Ментор @{mentor_info["name"]} принял Ваш запрос <b>{course_work_info["description"]}</b>',
                                  parse_mode='html'))


@bot.message_handler(func=lambda msg: msg.text == 'Мои темы')
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
    db = Database()
    if not await db.check_is_mentor(message.from_user.id):
        await bot.send_message(message.chat.id, '<b>Вы не ментор</b>', parse_mode='html')
        return
    my_subjects_ = (await db.get_mentors(chat_id=message.from_user.id))[0]['subjects']

    markup = types.InlineKeyboardMarkup(row_width=3)
    add = types.InlineKeyboardButton('Добавить', callback_data='mnt_sub_to_add')
    message_subjects = '<b>Мои темы</b>\n'

    if my_subjects_:
        delete = types.InlineKeyboardButton('Удалить', callback_data='mnt_sub_to_delete')
        markup.row(add, delete)
        message_subjects += '\n'.join(my_subjects_)
    else:
        markup.add(add)

    await bot.send_message(message.chat.id, f'{message_subjects}', reply_markup=markup, parse_mode='html')


# мои темы получаешь еще кнопки с темам, тыкаешь на кнопку получаешь список курсачей по этой теме (тоже кнопками) -> жмешь на курсач и принимаешь его

# @bot.callback_query_handler(func=lambda call: call.data.startswith('subject_'))
# async def callback_show_course_works_by_subject(call):
#     db = Database()
#     markup = types.InlineKeyboardMarkup(row_width=3)
#     markup.add(
#         *[types.InlineKeyboardButton(f'{work["student"]} {work["description"]}',
#                                      callback_data='work_' + str(work['id'])) for work in
#           await db.get_course_works([call.data[8:]])])  # добавление курсачей будет в callback_query_work
#     await bot.answer_callback_query(call.id)
#     await bot.send_message(call.from_user.id, f'Курсовые работы по теме *{call.data[8:]}*', reply_markup=markup,
#                            parse_mode='html')


@bot.callback_query_handler(func=lambda call: call.data == 'mnt_sub_to_add')
async def callback_show_subjects_to_add(call):
    db = Database()
    answ_task = create_task(bot.answer_callback_query(call.id))
    my_subjects_ = (await db.get_mentors(chat_id=call.from_user.id))[0]['subjects']

    subjects_to_add = await db.get_subjects()

    for subject in my_subjects_:
        subjects_to_add.remove(subject)

    if subjects_to_add:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            *[types.InlineKeyboardButton(subject, callback_data='mnt_sub_add_' + subject)
              for subject in subjects_to_add])
        await bot.send_message(call.from_user.id, '<b>Все темы</b>',
                               reply_markup=markup, parse_mode='html')
    else:
        await bot.send_message(call.from_user.id, '<b>Вы добавили все доступные темы</b>',
                               parse_mode='html')
    await answ_task


@bot.callback_query_handler(func=lambda call: call.data.startswith('mnt_sub_add_'))
async def callback_add_subject(call):
    db = Database()
    answ_task = create_task(bot.answer_callback_query(call.id))
    myself = (await db.get_mentors(chat_id=call.from_user.id))[0]

    if not myself['subjects'] or call.data[12:] not in myself['subjects']:
        await gather(db.add_mentor_subjects(myself['id'], [call.data[12:]]),
                     bot.send_message(call.from_user.id,
                                      f'Тема <b>{call.data[12:]}</b> успешно добавлена',
                                      parse_mode='html'))
    else:
        await bot.send_message(call.from_user.id,
                               f'Тема <b>{call.data[12:]}</b> уже была добавлена',
                               parse_mode='html')
    await answ_task


@bot.callback_query_handler(func=lambda call: call.data == 'mnt_sub_to_delete')
async def callback_show_subjects_to_delete(call):
    db = Database()
    my_subjects_ = (await db.get_mentors(chat_id=call.from_user.id))[0]['subjects']

    markup = types.InlineKeyboardMarkup()
    markup.add(
        *[types.InlineKeyboardButton(subject, callback_data='mnt_sub_delete_' + subject)
          for subject in my_subjects_])
    await gather(bot.answer_callback_query(call.id),
                 bot.send_message(call.from_user.id,
                                  '<b>Удалить тему</b>',
                                  reply_markup=markup,
                                  parse_mode='html'))


@bot.callback_query_handler(func=lambda call: call.data.startswith('mnt_sub_delete_'))
async def callback_del_subject(call):
    db = Database()
    my_id = (await db.get_mentors(chat_id=call.from_user.id))[0]['id']

    await gather(db.remove_mentor_subjects(my_id, [call.data[15:]]),
                 bot.send_message(call.from_user.id,
                                  f'Тема <b>{call.data[15:]}</b> успешно удалена',
                                  parse_mode='html'),
                 bot.delete_message(call.from_user.id, call.message.id),
                 bot.answer_callback_query(call.id))


@bot.message_handler(func=lambda msg: msg.text == 'Мои студенты')
async def my_students(message):
    db = Database()
    if not await db.check_is_mentor(message.from_user.id):
        await bot.send_message(message.chat.id, '<b>Вы не ментор</b>', parse_mode='html')
        return

    mentor_info = (await db.get_mentors(chat_id=message.from_user.id))[0]
    my_students_ = mentor_info['students']

    if not my_students_:
        str_my_students_ = 'У Вас нет студентов!'
    else:
        str_my_students_ = '\n'.join(
            '@' + student['name'] + ' - ' + student["course_works"][0]["description"]
            for student in my_students_)
    await bot.send_message(message.chat.id,
                           f'Список моих студентов\n{str_my_students_}')
