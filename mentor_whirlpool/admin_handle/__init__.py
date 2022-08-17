from mentor_whirlpool.telegram import bot
from telebot import asyncio_filters
import start
import edit_subject
import mentors
import support

bot.add_custom_filter(asyncio_filters.StateFilter(bot))
