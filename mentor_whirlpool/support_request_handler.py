from telegram import bot
from asyncio import create_task

from database import Database


@bot.message_handler(func=lambda msg: msg.text == 'Поддержка')
async def request_support(message):
    """
    Send a notice to all supports
    Add new record to support_requests table with db.add_support_request(chat_id, name)

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    db = Database()
    if await db.get_students(chat_id=message.chat.id) or await db.get_mentors(chat_id=message.chat.id):
        if not await db.get_support_requests(chat_id=message.chat.id):
            create_task(db.add_support_request({
                'chat_id': message.chat.id,
                'name': message.from_user.username,
                'issue': None,
            }))
            for chat_id in [rec['chat_id'] for rec in await db.get_supports()]:
                await bot.send_message(chat_id, 'Пользователю нужна помощь')
            await bot.send_message(message.chat.id, 'Ждите ответ поддержки')
        else:
            await bot.send_message(message.chat.id, 'Вы уже отправили запрос. Ждите ответ поддержки')
