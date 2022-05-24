#!/usr/bin/env python3

from asyncio import run
from telegram import bot
from database import Database

# here will be handles importing
import common
import generic_handles
import mentor_handles
import admin_handles

db = Database()
db.initdb()

run(bot.polling())
