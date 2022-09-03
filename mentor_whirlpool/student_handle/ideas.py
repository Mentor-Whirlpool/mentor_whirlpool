from mentor_whirlpool.telegram import bot
from telebot import types
from mentor_whirlpool.database import Database
from asyncio import gather
from mentor_whirlpool.utils import get_pretty_mention, get_pretty_mention_db
import logging


@bot.message_handler(func=lambda msg: msg.text == 'Идеи')
async def start_show_idea(message: types.Message) -> None:
    await bot.delete_message(message.chat.id, message.id)
    db = Database()

    if await db.check_is_mentor(message.from_user.id):
        logging.warning(f'chat_id: {message.from_user.id} is a mentor')
        return

    id = await db.get_students(chat_id=message.chat.id)
    if id and await db.get_accepted(student=id[0]['id']):
        logging.warning(f'chat_id: {message.from_user.id} student already has work')

        await bot.send_message(message.from_user.id,
                               "Тебя уже обслуживает ментор\n")
        return

    markup = types.InlineKeyboardMarkup()
    subjects = await db.get_subjects()
    for subject in subjects:
        markup.add(
            types.InlineKeyboardButton(subject['subject'], callback_data=f'std_sub_for_idea_{subject["id"]}'))
    await bot.send_message(message.from_user.id, 'Выберите направление', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("std_sub_for_idea_"))
async def callback_list_of_ideas_for_sub(call: types.CallbackQuery) -> None:
    db = Database()
    markup = types.InlineKeyboardMarkup()
    sub_id = call.data[17:]
    ideas_str = '__Идеи от менторов__\n'
    ideas = await db.get_ideas(subjects=[sub_id])
    if not ideas:
        await bot.send_message(call.from_userid, "Пока идей от менторов нет. Придумай свой вариант!")
        return
    for idea in ideas:
        markup.add(types.InlineKeyboardButton(
            f'{idea["description"]} -  {idea["mentor"]["name"]}',
            callback_data=f'std_add_idea_{idea["id"]}'))
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.from_user.id, ideas_str, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("std_add_idea_"))
async def callback_accept_idea(call: types.CallbackQuery) -> None:
    db = Database()
    idea_id = call.data[13:]
    idea = await db.get_ideas(id_field=idea_id)
    await gather(
        bot.answer_callback_query(call.id),
        bot.send_message(call.from_user.id, 'Вы успешно взялись за идею от ментора'),
        bot.send_message((await db.get_mentors(id=idea[0]['mentor']))[0]['chat_id'],
                         f'Вашу идею принял {get_pretty_mention(call.from_user)}'),
        db.accept_idea({'name': call.from_user.username, 'chat_id': call.from_user.id}, idea_id)
    )
