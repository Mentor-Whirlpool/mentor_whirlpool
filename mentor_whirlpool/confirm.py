from telegram import bot
from telebot import types
from database import Database
from asyncio import create_task


async def confirm(message, callback_data_yes, callback_data_no=None):
    """
    Should ask for user confirmation. If user replies with yes, call the
    callback. Otherwise, if callback_no is not None, call it

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    callback_yes : function
    callback_no : function or None
    """
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Да', callback_data=callback_data_yes))
    if callback_data_no is None:
        callback_data_no = 'cancel_confirm'
    markup.add(types.InlineKeyboardButton('Нет', callback_data=callback_data_no))
    await bot.send_message(message.from_user.id, 'Вы уверены?', reply_markup=markup, parse_mode='Html')


@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_'))
async def confirm_callback(call):
    await bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Да', callback_data=call.data[8:]))
    markup.add(types.InlineKeyboardButton('Нет', callback_data='cancel_confirm'))
    await bot.send_message(call.from_user.id, 'Вы уверены?', reply_markup=markup, parse_mode='Html')


@bot.callback_query_handler(func=lambda call: call.data == 'cancel_confirm')
async def confirm_cancel(call):
    await bot.answer_callback_query(call.id)
    await bot.delete_message(call.from_user.id, call.message.id)
