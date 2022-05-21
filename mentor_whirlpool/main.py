#!/usr/bin/env python3

from asyncio import run

from telegram import bot
# here will be handles importing
import generic_handles
import mentor_handles

run(bot.polling())
