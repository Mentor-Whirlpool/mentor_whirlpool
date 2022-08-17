from mentor_whirlpool.telegram import bot
from telebot import asyncio_filters
import ideas
import add_course_work
import delete_course_work
import read_course_works
import start
import wanna_be_mentor

bot.add_custom_filter(asyncio_filters.StateFilter(bot))
bot.add_custom_filter(asyncio_filters.IsDigitFilter())
