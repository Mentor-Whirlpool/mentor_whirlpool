from mentor_whirlpool.telegram import bot
from telebot import types, asyncio_filters
from telebot.asyncio_handler_backends import State, StatesGroup
from mentor_whirlpool.database import Database
from asyncio import create_task, gather
from mentor_whirlpool.mentor_handles import mentor_start
from mentor_whirlpool.students_handles import generic_start
from mentor_whirlpool.support_handles import support_start
from mentor_whirlpool.utils import get_name, get_pretty_mention, get_pretty_mention_db
import logging as logging
import start
import edit_subject
import mentors
import support


class AdminStates(StatesGroup):
    add_subject = State()
    add_support = State()


bot.add_custom_filter(asyncio_filters.StateFilter(bot))
