from mentor_whirlpool.telegram import bot
from telebot import types
from telebot import asyncio_filters
from telebot.asyncio_handler_backends import State, StatesGroup
from mentor_whirlpool.database import Database
from asyncio import gather, create_task
# from mentor_whirlpool.confirm import confirm
from mentor_whirlpool.utils import get_pretty_mention, get_pretty_mention_db, get_name
import random
import logging
import ideas
import add_course_work
import delete_course_work
import read_course_works
import start
import wanna_be_mentor


class StudentStates(StatesGroup):
    add_work_flag = State()
    add_own_subject_flag = State()
    subject = State()
    topic = State()


bot.add_custom_filter(asyncio_filters.StateFilter(bot))
bot.add_custom_filter(asyncio_filters.IsDigitFilter())
