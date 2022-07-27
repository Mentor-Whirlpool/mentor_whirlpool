#!/usr/bin/env python3

from asyncio import run
from mentor_whirlpool.telegram import bot
from mentor_whirlpool.database import Database
import logging

# here will be handles importing
import mentor_whirlpool.common
import mentor_whirlpool.confirm
import mentor_whirlpool.students_handles
import mentor_whirlpool.mentor_handles
import mentor_whirlpool.admin_handles
import mentor_whirlpool.support_handles
import mentor_whirlpool.support_request_handler

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - %(module)s - %(levelname)s - %(funcName)s: %(lineno)d - %(message)s",
                    datefmt='%H:%M:%S', )


async def main():
    db = Database()
    await db.initdb()
    await bot.infinity_polling()


run(main())
