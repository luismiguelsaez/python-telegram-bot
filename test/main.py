from telegram import Bot, Update
from telegram.error import Forbidden, NetworkError
from os import getenv, path, remove, system
import logging
import asyncio
import contextlib
from typing import NoReturn
import sqlite3

async def manage_motion(op: str = 'start') -> None:
    logging.info(f"Executing motion-daemon operation {op}")

    command = f"sudo systemctl {op} motion-daemon"
    command_res = system(command)

    return command_res

async def get_updates(bot: Bot, update_id: int)->int:
    updates = await bot.get_updates(offset=update_id, timeout=10, allowed_updates=Update.ALL_TYPES)
    for update in updates:
        logger.info("Processing update %s", update.update_id)
        next_update_id = update.update_id + 1
        if update.message and update.message.text:
            logger.info(f"Processing message {update.message.text}")
            await update.message.reply_text(f"Processing message {update.message.text}")
            if update.message.text == '/start':
                return_code = await manage_motion('start')
            elif update.message.text == '/stop':
                return_code = await manage_motion('stop')
            await update.message.reply_text(f"Processed message {update.message.text} with return code {return_code}")
        return next_update_id
    return update_id

async def scan_database(bot: Bot, update_id: int)->int:
    sqlite_conn = sqlite3.connect('/data/motion/db/motion.sqlite')
    sqlite_cursor = sqlite_conn.cursor()
    sqlite_cursor.execute('SELECT * FROM security WHERE event_end = 1 AND event_ack = 0')
    rows = sqlite_cursor.fetchall()
    if len(rows) > 0:
        await bot.send_message(chat_id='15060431', text=f'Got {len(rows)} rows from database')
    for row in rows:
        if path.exists(row[1]):
            await bot.send_message(chat_id='15060431', text=f'Sending video {row[1]}')
            await bot.send_video(chat_id='15060431',video=open(row[1], 'rb'),filename=row[1], supports_streaming=True)
        else:
            await bot.send_message(chat_id='15060431', text=f'Video file not found: {row[1]}')
        update_query = f'UPDATE security SET event_ack = 1 WHERE filename LIKE "{row[1]}"'
        remove(row[1])
        sqlite_cursor.execute(update_query)
    sqlite_conn.commit()
    sqlite_conn.close()

async def loop_main(bot: Bot, update_id: int)->None:

    while True:
        logger.info("Awaiting updates ...")
        try:
            update_id = await get_updates(bot, update_id)
        except NetworkError:
            logger.error("Network error has occurred. Sleeping for 1 second.")
            await asyncio.sleep(1)
        except Forbidden:
            logger.error("Forbiden error has occurred.")
            update_id += 1

        logger.info("Looking for database updates ...")
        await scan_database(bot, update_id)

        await asyncio.sleep(1)


telegram_token = getenv('TOKEN', None)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.INFO)
logger = logging.getLogger(__name__)

async def main() -> NoReturn:
    async with Bot(telegram_token) as bot:
        # Get last update_id and start from there
        try:
            update_id = (await bot.get_updates())[0].update_id
        except IndexError:
            update_id = None

        logger.info("Bot listening ...")

        await loop_main(bot, update_id)


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):  # Ignore exception when Ctrl-C is pressed
        asyncio.run(main())
