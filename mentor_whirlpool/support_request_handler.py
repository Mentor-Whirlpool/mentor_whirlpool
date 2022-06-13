from mentor_whirlpool.telegram import bot
from asyncio import gather

from mentor_whirlpool.database import Database


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
    is_ellegible = not any(await gather(db.check_is_admin(message.from_user.id),
                                        db.check_is_support(message.from_user.id)))
    if not is_ellegible:
        return
    if not await db.get_support_requests(chat_id=message.chat.id):
        await gather(db.add_support_request({
            'chat_id': message.chat.id,
            'name': message.from_user.username,
            'issue': None,
        }),
            *[bot.send_message(chat_id, 'Пользователю нужна помощь')
              for chat_id in [rec['chat_id'] for rec in await db.get_supports()]],
            bot.send_message(message.chat.id, 'Ждите ответ поддержки'))
    else:
        await bot.send_message(message.chat.id, 'Вы уже отправили запрос. Ждите ответ поддержки')
