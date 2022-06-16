from telegram import bot
from asyncio import gather

from database import Database
import logging


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
    logging.debug(f'chat_id: {message.from_user.id} is in SUPPORT')
    db = Database()
    is_ellegible = not any(await gather(db.check_is_admin(message.from_user.id),
                                        db.check_is_support(message.from_user.id)))
    if not is_ellegible:
        logging.warn(f'chat_id: {message.from_user.id} is inellegible')
        return
    if not await db.get_support_requests(chat_id=message.chat.id):
        logging.debug(f'chat_id: {message.from_user.id} preparing SUPPORT')
        await gather(db.add_support_request({
            'chat_id': message.chat.id,
            'name': message.from_user.username,
            'issue': None,
        }),
            *[bot.send_message(chat_id, 'Пользователю нужна помощь')
              for chat_id in [rec['chat_id'] for rec in await db.get_supports()]],
            bot.send_message(message.chat.id, 'Ждите ответ поддержки'))
        logging.debug(f'chat_id: {message.from_user.id} done SUPPORT')
    else:
        logging.warn(f'chat_id: {message.from_user.id} is already seeking support')
        await bot.send_message(message.chat.id, 'Вы уже отправили запрос. Ждите ответ поддержки')
