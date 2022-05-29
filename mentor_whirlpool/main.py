#!/usr/bin/env python3

from asyncio import run
from telegram import bot
from database import Database

# here will be handles importing
import common
import students_handles
import mentor_handles
import admin_handles
import support_handles
import support_request_handler

run(bot.polling())
