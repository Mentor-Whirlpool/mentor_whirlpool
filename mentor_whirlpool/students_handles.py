from telegram import bot
from telebot import types
from database import Database
from asyncio import create_task
from confirm import confirm

import pandas as pd
import test_database


async def generic_start(message):
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
    raise NotImplementedError


@bot.message_handler(func=lambda msg: msg.text == 'Добавить запрос')
async def add_request(message):
    """
    Adds a course work with db.add_course_work() with confirmation
    If there is a mentor that has selected subjects in their preferences
    send them a notice of a new course work

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """

    with open("/home/keyow/PycharmProjects/mentor_whirlpool/mentor_whirlpool/test_database/test_db.csv",
              newline='') as csvfile:
        df = pd.read_csv(csvfile)
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            *[types.InlineKeyboardButton(df.iloc[i, 0], callback_data=f"add_request_{i}") for i in
              range(len(df))])
    await bot.send_message(message.chat.id, "Доступные работы:", reply_markup=markup)
    raise NotImplementedError


@bot.message_handler(func=lambda msg: msg.text == 'Мои запросы')
async def my_requests(message):
    with open("/home/keyow/PycharmProjects/mentor_whirlpool/mentor_whirlpool/test_database/test_db.csv",
              newline='') as csvfile:
        df = pd.read_csv(csvfile)
        counter = 0
        markup = types.InlineKeyboardMarkup(row_width=1)
        for i in range(len(df)):
            if df.iloc[i, 1] == '+':
                markup.add(types.InlineKeyboardButton(df.iloc[i, 0], callback_data=f"my_request_{i}"))
                counter += 1
    if counter == 0:
        await bot.send_message(message.chat.id, "На данный момент у вас нет запросов")
        return
    await bot.send_message(message.chat.id, f"Мои запросы (всего {counter}):", reply_markup=markup)
    raise NotImplementedError


@bot.message_handler(func=lambda msg: msg.text == 'Удалить запрос')
async def remove_request(message):
    """
    Removes a course work with db.remove_course_work() with confirmation

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    with open("/home/keyow/PycharmProjects/mentor_whirlpool/mentor_whirlpool/test_database/test_db.csv",
              newline='') as csvfile:
        df = pd.read_csv(csvfile)
        markup = types.InlineKeyboardMarkup(row_width=1)
        counter = 0
        for i in range(len(df)):
            if df.iloc[i, 1] == '+':
                markup.add(types.InlineKeyboardButton(df.iloc[i, 0], callback_data=f"delete_request_{i}"))
                counter += 1
    if counter == 0:
        await bot.send_message(message.chat.id, "На данный момент у вас нет запросов")
        return
    await bot.send_message(message.chat.id, f"Мои запросы (всего {counter}):", reply_markup=markup)
    raise NotImplementedError


@bot.message_handler(func=lambda msg: msg.text == 'Хочу быть ментором')
async def mentor_resume(message):
    """
    Send a notice to random admin with contact details of requester
    Send a requester contact details of an admin
    Should request a confirmation

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    raise NotImplementedError


@bot.callback_query_handler(func=lambda call: call.data.startswith("add_request_"))
async def add_subject_callback(call):
    path = "/home/keyow/PycharmProjects/mentor_whirlpool/mentor_whirlpool/test_database/test_db.csv"
    df = pd.read_csv(path)
    subject_index = int(call.data.split('_')[-1])

    for i in range(len(df)):
        if df.iloc[subject_index, 1] == '+':
            await bot.send_message(call.from_user.id, 'Эта работа уже добавлена!')
            return
    df.iloc[subject_index, 1] = '+'

    df.to_csv(path, index=False)
    await bot.send_message(call.from_user.id, 'Работа успешно добавлена!')


@bot.callback_query_handler(func=lambda call: call.data.startswith("my_request_"))
async def topic_description_callback(call):
    path = "/home/keyow/PycharmProjects/mentor_whirlpool/mentor_whirlpool/test_database/test_db.csv"
    df = pd.read_csv(path)

    subject_index = int(call.data.split('_')[-1])
    for i in range(len(df)):
        if df.iloc[subject_index, 1] == '+':
            await bot.send_message(call.from_user.id, f'### {df.iloc[subject_index, 0]} ###\n'
                                                      f'{df.iloc[subject_index, 2]}')
            return


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_request_"))
async def delete_topic_callback(call):
    path = "/home/keyow/PycharmProjects/mentor_whirlpool/mentor_whirlpool/test_database/test_db.csv"
    df = pd.read_csv(path)

    subject_index = int(call.data.split('_')[-1])
    df.iloc[subject_index, 1] = ''

    df.to_csv(path, index=False)
    await bot.send_message(call.from_user.id, 'Работа успешно удалена!')

