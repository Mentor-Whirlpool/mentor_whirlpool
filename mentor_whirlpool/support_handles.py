from mentor_whirlpool.telegram import bot
from telebot import types
from asyncio import create_task, gather
import logging

from mentor_whirlpool.database import Database
import mentor_whirlpool.support_request_handler


async def support_start(message):
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
    return ['Актуальные запросы']


@bot.message_handler(func=lambda msg: msg.text == 'Актуальные запросы')
async def check_requests(message):
    """
    Display support requests with db.get_support_requests() as buttons

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    logging.debug(f'chat_id: {message.from_user.id} is in SUPPORT_REQUESTS')
    db = Database()
    if not await db.check_is_support(chat_id=message.chat.id):
        logging.warn(f'chat_id: {message.from_user.id} is not a support')
        return
    requests = await db.get_support_requests()
    if not requests:
        await bot.send_message(message.chat.id, 'Актуальных запросов нет')
        return
    requests_list = types.InlineKeyboardMarkup()
    for sup in requests:
        requests_list.add(
            types.InlineKeyboardButton(text=f'Пользователь {sup["name"]}',
                                       callback_data=f'cbd_{sup["chat_id"]}')
        )
    logging.debug(f'chat_id: {message.from_user.id} preparing SUPPORT_REQUESTS')
    await bot.send_message(message.chat.id, 'Запросы поддержки:',
                           reply_markup=requests_list, parse_mode='Html')
    logging.debug(f'chat_id: {message.from_user.id} done SUPPORT_REQUESTS')


@bot.callback_query_handler(lambda call: call.data.startswith('cbd_'))
async def callback_answer_support_request(call):
    """
    Handles click on support request button
    If request still actual, buttons changes with single one - redirect to chat with user, who required support
    Send message to request`s author

    Parameters
    ----------
    call : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    answ_task = create_task(bot.answer_callback_query(call.id))
    logging.debug(f'chat_id: {call.from_user.id} is in cbd support')
    db = Database()
    if not await db.check_is_support(chat_id=call.from_user.id):
        logging.warn(f'chat_id: {call.from_user.id} is not a support')
        return

    chat_id = call.data[call.data.index('_') + 1:]

    mentor = await db.get_mentors(chat_id=chat_id)
    if mentor:
        username = mentor[0]['name']
    else:
        student = await db.get_students(chat_id=chat_id)
        if student:
            username = student[0]['name']

    curr_request = await db.get_support_requests(chat_id=chat_id)
    if not curr_request:
        logging.warn(f'chat_id: {call.from_user.id} expired request')
        await gather(bot.send_message(call.from_user.id,
                                      f'Запрос пользователя @{username} больше не актуален'),
                     answ_task)
        return
    curr_request = curr_request[0]
    new_keyboard = types.InlineKeyboardMarkup()
    new_keyboard.add(types.InlineKeyboardButton(text=f'Помочь пользователю {username}', url=f't.me/{username}'))
    logging.debug(f'chat_id: {call.from_user.id} preparing cbd support')
    await gather(db.remove_support_request(curr_request['id']),
                 bot.send_message(chat_id, f'Член поддержки @{call.from_user.username} скоро окажет вам помощь'),
                 bot.edit_message_reply_markup(call.from_user.id, call.message.id, reply_markup=new_keyboard),
                 answ_task)
    logging.debug(f'chat_id: {call.from_user.id} done cbd support')
