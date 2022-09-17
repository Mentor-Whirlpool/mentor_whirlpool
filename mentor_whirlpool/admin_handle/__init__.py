from mentor_whirlpool.telegram import bot
from telebot import asyncio_filters
import mentor_whirlpool.admin_handle.start
import mentor_whirlpool.admin_handle.edit_subject
import mentor_whirlpool.admin_handle.mentors
import mentor_whirlpool.admin_handle.support
import mentor_whirlpool.admin_handle.requests

bot.add_custom_filter(asyncio_filters.StateFilter(bot))
