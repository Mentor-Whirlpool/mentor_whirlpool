from mentor_whirlpool.telegram import bot
from telebot import types
from mentor_whirlpool.database import Database
from asyncio import gather
from mentor_whirlpool.utils import get_pretty_mention
import random
import logging


@bot.message_handler(func=lambda msg: msg.text == 'Хочу стать ментором')
async def mentor_resume(message):
    await bot.delete_message(message.chat.id, message.id)
    db = Database()
    logging.debug(f'chat_id: {message.from_user.id} is in BECOME_MENTOR_REQUEST')
    if await db.check_is_mentor(message.from_user.id):
        logging.warn(f'chat_id: {message.from_user.id} is a mentor')
        return
    admins = await db.get_admins()

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton('Одобрить', callback_data=f'add_mentor_via_admin_{message.from_user.id}'))

    admin_chat_id = random.choice(admins)['chat_id']
    logging.debug(f'chat_id: {message.from_user.id} preparing BECOME_MENTOR_REQUEST')
    await gather(
        bot.send_message(admin_chat_id, f"Пользователь {get_pretty_mention(message.from_user)} хочет стать ментором.",
                         reply_markup=markup),
        bot.send_message(message.chat.id, "Ваша заявка на рассмотрении. Ожидайте ответа от администратора!\n"))
    logging.debug(f'chat_id: {message.from_user.id} done BECOME_MENTOR_REQUEST')
