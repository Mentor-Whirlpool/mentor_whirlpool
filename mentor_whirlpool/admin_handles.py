from telegram import bot
from telebot import types
from database import Database
from asyncio import create_task
from confirm import confirm


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
    return ['Менторы', 'Запросы']


@bot.message_handler(func=lambda msg: msg.text == 'Запросы')
async def course_work(message):
    db = Database()
    course_works = await db.get_course_works()
    messages = []
    for work in course_works:
        messages.append(f'{work["student"]}\n{work["description"]}')
    message_course_works = '--------\n'.join(messages)
    await bot.send_message(message.chat.id, message_course_works)


@bot.message_handler(func=lambda msg: msg.text == 'Добавить ментора')
async def add_mentor(message):
    """
    If from_user.id is in admins, parse the message to get new admin chat_id
    and add it with db.add_admin(). Otherwise, report an error to the sender.
    Should ask for confirmation

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    raise NotImplementedError


@bot.message_handler(func=lambda msg: msg.text == 'Удалить ментора')
async def delete_mentor(message):
    """
    If from_user.id is in admins, parse the message to get admin chat_id
    and remove it with db.remove_admin(). If the message is empty, remove
    sender

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    raise NotImplementedError


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
    mentors = await db.get_mentors()
    for mentor in mentors:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Выбрать', callback_data='choose_mentor_' + str(mentor['id'])))
        message_subjects = '\n'.join(mentor['subjects'])
        await bot.send_message(message.chat.id, f'*@{mentor["name"]}*\n{message_subjects}', reply_markup=markup,
                               parse_mode='markdown')


@bot.callback_query_handler(func=lambda call: call.data.startswith('choose_mentor_'))
async def callback_mentors_info(call):
    db = Database()
    mentors = await db.get_mentors()

    mentor_info = {}
    for mentor in mentors:
        if mentor['id'] == int(call.data[14:]):
            mentor_info = mentor
            break

    message_subjects = '\n'.join(mentor_info['subjects'])
    message_students = '\n'.join(student['name'] for student in mentor_info['students'])
    markup = types.InlineKeyboardMarkup()
    edit_subjects = types.InlineKeyboardButton('Изменить тему', callback_data='edit_subjects')
    edit_students = types.InlineKeyboardButton('Изменить студентов', callback_data='edit_students')
    markup.add(edit_students, edit_subjects)
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.from_user.id,
                           f'*@{mentor_info["name"]}*\n{message_subjects}\nStudents\n{message_students}',
                           reply_markup=markup, parse_mode='markdown')
