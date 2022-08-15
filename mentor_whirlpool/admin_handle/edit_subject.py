from __init__ import types, Database, bot, logging, gather, AdminStates


@bot.message_handler(func=lambda msg: msg.text == 'Редактировать направления')
async def edit_subjects(message: types.Message) -> None:
    """
    Prints a list of all subjects as inline buttons with subjects and a button
    for addition of subject

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    db = Database()
    if not await db.check_is_admin(message.from_user.id):
        logging.warn(f'MENTORS: chat_id: {message.from_user.id} is not an admin')
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(*[types.InlineKeyboardButton(f'Удалить: {subj}', callback_data=f'adm_rem_subj_{subj["id"]}')
                 for subj in await db.get_subjects()])
    markup.add(types.InlineKeyboardButton('Добавить направление',
                                          callback_data='adm_add_subj'))
    await bot.send_message(message.from_user.id, 'Что сделать?', reply_markup=markup)
    await bot.delete_message(message.chat.id, message.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_rem_subj_'))
async def remove_subject(call: types.CallbackQuery) -> None:
    logging.debug(f'chat_id: {call.from_user.id} is in remove_subject')

    db = Database()
    await gather(db.remove_subject(call.data[13:]),
                 bot.send_message(call.from_user.id, "Предмет успешно удалён."),
                 bot.delete_message(call.from_user.id, call.message.id))
    logging.debug(f'chat_id: {call.from_user.id} subject has been removed')


@bot.callback_query_handler(func=lambda call: call.data == 'adm_add_subj')
async def add_subject_admin(call: types.CallbackQuery) -> None:
    """
    If from_user.id is in admins, ask him to write name of new subject

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class
    """
    logging.debug(f'chat_id: {call.from_user.id} preparing add_subject')
    await gather(bot.set_state(call.from_user.id, AdminStates.add_subject),
                 bot.send_message(call.from_user.id, "Введите название направления:"),
                 bot.delete_message(call.from_user.id, call.message.id))
    logging.debug(f'chat_id: {call.from_user.id} done add_subject')


@bot.message_handler(state=AdminStates.add_subject)
async def save_subject(message: types.Message) -> None:
    logging.debug(f'chat_id: {message.from_user.id} is in add_subject')

    db = Database()
    if message.text in [subj['subject'] for subj in await db.get_subjects()]:
        await gather(bot.delete_state(message.from_user.id),
                     bot.send_message(message.from_user.id, "Предмет уже добавлен."))
        logging.warn(f'chat_id: {message.from_user.id} subject already added')
        return
    await gather(db.add_subject(message.text),
                 bot.delete_state(message.from_user.id),
                 bot.send_message(message.from_user.id, "Предмет успешно добавлен."))
    logging.debug(f'chat_id: {message.from_user.id} subject has been added')
