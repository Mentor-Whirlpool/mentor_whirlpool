from mentor_whirlpool.telegram import bot
from telebot import types
from telebot.asyncio_handler_backends import State, StatesGroup
from mentor_whirlpool.database import Database
from mentor_whirlpool.utils import get_pretty_mention_db, get_name
from asyncio import gather, create_task
import logging as logging
import start
import course_works
import students
import subjects

class MentorStates(StatesGroup):
    add_idea = State()
    add_support = State()

