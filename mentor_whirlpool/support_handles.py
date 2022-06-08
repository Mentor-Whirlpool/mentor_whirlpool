from telegram import bot
from telebot import types
import json

from database import Database


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
    requests = await db.get_support_requests()
    if requests:
        requests_list = types.InlineKeyboardMarkup()
        for sup in requests:
            requests_list.add(
                types.InlineKeyboardButton(text=f'Пользователь {sup["name"]}',
                                           callback_data='cbd_{"c_i": "%s", "un": "%s"}' % (
                                               sup['chat_id'], sup['name']))
            )
        await bot.send_message(message.chat.id, 'Запросы поддержки:', reply_markup=requests_list, parse_mode='markdown')
    else:
        await bot.send_message(message.chat.id, 'Актуальных запросов нет')


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

    db = Database()
    callback_data = json.loads(call.data[call.data.index('_') + 1:])
    chat_id = callback_data['c_i']
    username = callback_data['un']

    curr_request = await db.get_support_requests(chat_id=chat_id)
    if curr_request:
        curr_request = curr_request[0]
        await db.remove_support_request(curr_request['id'])
        await bot.send_message(chat_id, f'Член поддержки @{call.from_user.username} скоро окажет вам помощь')

        new_keyboard = types.InlineKeyboardMarkup()
        new_keyboard.add(types.InlineKeyboardButton(text=f'Помочь пользователю {username}', url=f't.me/{username}'))

        await bot.edit_message_reply_markup(call.from_user.id, call.message.id, reply_markup=new_keyboard)
    else:
        await bot.send_message(call.from_user.id, f'Запрос пользователя @{username} больше не актуален')
    await bot.answer_callback_query(call.id)
