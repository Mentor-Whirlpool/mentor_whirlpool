from __init__ import types, Database, bot, logging, gather, AdminStates, generic_start, get_pretty_mention_db, \
    support_start


@bot.message_handler(func=lambda msg: msg.text == 'Редактировать поддержку')
async def edit_subjects(message: types.Message) -> None:
    """
    Prints a list of all suppoerts as inline buttons and a button
    for addition of support

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
    markup.add(*[types.InlineKeyboardButton(f'Удалить: {supp["name"]}', callback_data=f'adm_rem_supp_{supp["id"]}')
                 for supp in await db.get_supports()])
    markup.add(types.InlineKeyboardButton('Добавить саппорта',
                                          callback_data='adm_add_supp'))
    await bot.send_message(message.from_user.id, 'Что сделать?', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_rem_supp_'))
async def callback_delete_subject(call: types.CallbackQuery) -> None:
    db = Database()
    supp_id = int(call.data[13:])
    supp = (await db.get_supports(supp_id))[0]
    logging.debug(f'chat_id: {call.from_user.id} preparing adm_rem_supp')
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*[types.KeyboardButton(task)
                 for task in await generic_start(None)])
    await gather(
        db.remove_support(supp_id),
        bot.send_message(supp['chat_id'], f'Вы больше не часть поддержки!', reply_markup=markup),
        bot.send_message(call.from_user.id,
                         f'Саппорт {get_pretty_mention_db(supp)} удалён'),
        bot.delete_message(call.from_user.id, call.message.id),
        bot.answer_callback_query(call.id))
    logging.debug(f'chat_id: {call.from_user.id} done adm_rem_supp')


@bot.callback_query_handler(func=lambda call: call.data == 'adm_add_supp')
async def callback_add_support(call: types.CallbackQuery) -> None:
    await gather(bot.set_state(call.from_user.id, AdminStates.add_support),
                 bot.answer_callback_query(call.id),
                 bot.send_message(call.from_user.id,
                                  'Введите chat_id нового саппорта\nПолучить chat_id возможно у @RawDataBot'))


@bot.message_handler(state=AdminStates.add_support)
async def add_support_chat_id_handler(message: types.Message) -> None:
    db = Database()
    supp_chat_id = message.text
    try:
        supp = await bot.get_chat(supp_chat_id)
    except:
        await gather(bot.send_message(message.from_user.id,
                                      'Пользователь не найден!\n'
                                      'Убедитесь что вы ввели chat_id верно, и пользователь начал взаимодействие с ботом'),
                     bot.delete_state(message.from_user.id))
        return
    supp_dict = {
        'chat_id': supp_chat_id,
        'name': supp.username,
    }
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*[types.KeyboardButton(task)
                 for task in await support_start(None)])
    await gather(db.add_support(supp_dict),
                 bot.delete_state(message.from_user.id),
                 bot.send_message(message.from_user.id, 'Саппорт успешно добавлен'),
                 bot.send_message(supp_chat_id, 'Теперь вы член группы поддержки!', reply_markup=markup))
    stud = await db.get_students(chat_id=supp_chat_id)
    if stud:
        await db.remove_student(stud[0]['id'])
