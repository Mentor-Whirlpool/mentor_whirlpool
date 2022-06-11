from telegram import bot
from telebot import types
import json
from asyncio import create_task, gather

from database import Database
import support_request_handler


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
    db = Database()
    if not await db.check_is_support(chat_id=message.chat.id):
        await bot.send_message(message.chat.id, 'Вы не являетесь членом группы поддержки!',
                               parse_mode='Html')
        return
    requests = await db.get_support_requests()
    if not requests:
        await bot.send_message(message.chat.id, 'Актуальных запросов нет')
        return
    requests_list = types.InlineKeyboardMarkup()
    for sup in requests:
        requests_list.add(
            types.InlineKeyboardButton(text=f'Пользователь {sup["name"]}',
                                       callback_data='cbd_{"c_i": "%s", "un": "%s"}' % (
                                           sup['chat_id'], sup['name']))
        )
    await bot.send_message(message.chat.id, 'Запросы поддержки:',
                           reply_markup=requests_list, parse_mode='Html')


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
    db = Database()
    if not await db.check_is_support(chat_id=call.from_user.id):
        await bot.send_message(call.from_user.id, 'Вы не являетесь членом группы поддержки!',
                               parse_mode='Html')
        return
    callback_data = json.loads(call.data[call.data.index('_') + 1:])
    chat_id = callback_data['c_i']
    username = callback_data['un']

    curr_request = await db.get_support_requests(chat_id=chat_id)
    if not curr_request:
        await gather(bot.send_message(call.from_user.id,
                                      f'Запрос пользователя @{username} больше не актуален'),
                     bot.answer_callback_query(call.id))
        return
    curr_request = curr_request[0]
    new_keyboard = types.InlineKeyboardMarkup()
    new_keyboard.add(types.InlineKeyboardButton(text=f'Помочь пользователю {username}', url=f't.me/{username}'))
    await gather(db.remove_support_request(curr_request['id']),
                 bot.send_message(chat_id, f'Член поддержки @{call.from_user.username} скоро окажет вам помощь'),
                 bot.edit_message_reply_markup(call.from_user.id, call.message.id, reply_markup=new_keyboard),
                 answ_task)
