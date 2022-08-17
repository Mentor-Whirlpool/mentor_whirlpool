from mentor_whirlpool.telegram import bot
from telebot import types
from telebot.asyncio_handler_backends import State, StatesGroup
from mentor_whirlpool.database import Database
from mentor_whirlpool.utils import get_name
from asyncio import gather
import logging


class MentorStates(StatesGroup):
    add_idea = State()
    add_support = State()


@bot.message_handler(func=lambda msg: msg.text == 'Пет-проект')
async def start_idea_by_mentor(message: types.Message) -> None:
    await bot.delete_message(message.chat.id, message.id)
    db = Database()
    if not await db.check_is_mentor(message.from_user.id):
        logging.warning(f'User isn\'t a mentor [user_id: {message.from_user.id}]')
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Добавить', callback_data='mnt_add_idea'),
               types.InlineKeyboardButton('Удалить', callback_data='mnt_idea_to_del'))
    ideas = await db.get_ideas()
    logging.debug(ideas)
    await bot.send_message(message.from_user.id,
                           '\n'.join(['Уже существующие идеи:'] +
                                     [f'- {idea["description"]}' for idea in ideas]))
    await bot.send_message(message.from_user.id, 'Что сделать?', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'mnt_add_idea')
async def add_idea_by_mentor(call: types.CallbackQuery) -> None:
    await bot.delete_message(call.from_user.id, call.message.id)
    logging.debug(f'Delete message  [{call.data}: {call.from_user.id}]')

    await bot.answer_callback_query(call.id)

    db = Database()

    mentor = (await db.get_mentors(chat_id=call.from_user.id))[0]
    logging.debug(f'mentor: {mentor}')

    message_subjects = '__Выберете направление пет-проекта__\n'

    if not mentor["subjects"]:
        await bot.send_message(call.from_user.id, '__Сначала добавьте направления!__')
        logging.warning(f'chat_id: {call.from_user.id} doesn\'t have any subjects')
        return
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        *[types.InlineKeyboardButton(sub['subject'], callback_data=f'mnt_sub_for_idea_{sub["id"]}')
          for sub in mentor["subjects"]])

    logging.debug(f'chat_id: {call.from_user.id} preparing MY_SUBJECTS')
    await bot.send_message(call.from_user.id, f'{message_subjects}', reply_markup=markup)
    logging.debug(f'chat_id: {call.from_user.id} done MY_SUBJECTS')


@bot.callback_query_handler(func=lambda call: call.data.startswith('mnt_sub_for_idea_'))
async def callback_add_idea(call: types.CallbackQuery) -> None:
    db = Database()
    subject = (await db.get_subjects(id_field=call.data[17:]))[0]
    logging.debug(f'chat_id: {call.from_user.id} preparing add_idea')
    await bot.set_state(call.from_user.id, MentorStates.add_idea, call.message.chat.id)
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['subject'] = subject['id']
    await gather(bot.send_message(call.from_user.id, f'Тема: __{subject["subject"]}__\n\n'
                                                     f'Введи название работы.\n'),
                 bot.delete_message(call.from_user.id, call.message.id))
    logging.debug(f'chat_id: {call.from_user.id} done add_idea')


@bot.message_handler(state=MentorStates.add_idea)
async def save_idea(message: types.Message) -> None:
    logging.debug(f'chat_id: {message.from_user.id} is in add_work_flag')
    # idea = dict() вроде можно убрать эту строчку

    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        idea = {'name': get_name(message.from_user),
                'chat_id': message.chat.id,
                'subjects': [data['subject']],
                'description': message.text}

    db = Database()
    # subject = create_task(db.get_subjects(idea['subjects'][0])) вроде нигде не используется
    id = await db.get_mentors(chat_id=message.from_user.id)
    logging.debug(f'chat_id: {message.from_user.id} self {id}')

    if id:
        ideas = await db.get_ideas(mentor=id[0]['id'])
        # ideas_names = [work['description'] for work in ideas] вроде нигде не используется

        if idea['description'] in ideas:
            logging.warning(f'chat_id: {message.from_user.id} idea already exists')
            await gather(bot.delete_state(message.from_user.id, message.chat.id),
                         bot.send_message(message.chat.id, "Пет-проект с такой темой уже добавлен!"))
            return
    logging.debug(f'chat_id: {message.from_user.id} preparing add_work_flag')
    await gather(db.add_idea(idea),
                 bot.delete_message(message.from_user.id, message.id),
                 bot.delete_state(message.from_user.id, message.chat.id),
                 bot.send_message(message.chat.id, f"Пет-проект __{message.text}__ успешно добавлен!"))
    logging.debug(f'chat_id: {message.from_user.id} done add_idea')


@bot.callback_query_handler(func=lambda call: call.data == 'mnt_idea_to_del')
async def callback_del_idea_by_mentor(call: types.CallbackQuery) -> None:
    db = Database()
    myself = await db.get_mentors(chat_id=call.from_user.id)
    mentor_ideas = await db.get_ideas(mentor=myself[0]['id'])

    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(*[types.InlineKeyboardButton(idea['description'], callback_data='mnt_idea_del_' + str(idea['id']))
                 for idea in mentor_ideas])

    logging.debug(f'chat_id: {call.from_user.id} preparing mnt_idea_to_del')
    await gather(bot.answer_callback_query(call.id),
                 bot.delete_message(call.from_user.id, call.message.id),
                 bot.send_message(call.from_user.id,
                                  '__Удалить пет-проект__',
                                  reply_markup=markup))
    logging.debug(f'chat_id: {call.from_user.id} done mnt_idea_to_del')


@bot.callback_query_handler(func=lambda call: call.data.startswith('mnt_idea_del_'))
async def callback_del_idea(call: types.CallbackQuery) -> None:
    db = Database()
    idea = (await db.get_ideas(call.data[13:]))[0]

    logging.debug(f'chat_id: {call.from_user.id} preparing mnt_idea_del_')
    await gather(db.remove_idea(idea['id']),
                 bot.send_message(call.from_user.id,
                                  f'Идея __{idea["description"]}__ успешно удалена'),
                 bot.delete_message(call.from_user.id, call.message.id),
                 bot.answer_callback_query(call.id))
    logging.debug(f'chat_id: {call.from_user.id} done mnt_idea_del_')
