from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
import os
import requests
from time import sleep
import sqlite3
import threading
import datetime
import logging


def loopWatcher(update: Update, context: CallbackContext) -> None:
    messagingLogger.info("Starting database watcher")
    motionBot.sendMessage(chat_id=update.effective_user.id,text="Watcher started by user id: {}".format(update.effective_user.id))

    con = sqlite3.connect('/data/motion/db/motion.sqlite')
    cur = con.cursor()

    counter = 1
    while True:
        if counter % 20 == 0:
            logger.debug("Loop iteration {}".format(str(counter)))
        cur.execute('SELECT * FROM security WHERE event_end = 1 AND event_ack = 0')
        rows = cur.fetchall()

        if len(rows) > 0:
            messagingLogger.debug("Found {} events".format(str(len(rows)))) 
            print("Found {} events".format(str(len(rows)))) 
            for row in rows:
                if os.path.exists(row[1]):
                    messagingLogger.info("Watcher: sending video {}".format(row[1]))
                    motionBot.sendVideo(chat_id=update.effective_user.id,video=open(row[1], 'rb'),filename=row[1], supports_streaming=True)
                else:
                    motionBot.sendMessage(chat_id=update.effective_user.id,text="Video file not found: {}".format(row[1]))
                update_query = 'UPDATE security SET event_ack = 1 WHERE filename LIKE "{}"'.format(row[1])
                cur.execute(update_query)


            con.commit()

        sleep(5)

        if exitLoopWatcher.is_set():
            con.close()
            messagingLogger.info("Exiting loop watcher")
            break

def startWatcher(update: Update, context: CallbackContext) -> None:
    t1 = threading.Thread(target=loopWatcher, args=(update, context)).start() 

def stopWatcher(update: Update, context: CallbackContext) -> None:
    exitLoopWatcher.set()

def getStillImage(update: Update, context: CallbackContext) -> None:
    now = datetime.datetime.now()
    nowStr = now.strftime('%Y%m%d%H%M%S')
    command = "raspistill -o /tmp/{}.jpg".format(nowStr)
    res = os.system(command)

    if res != 0:
        update.message.reply_text("Command returned error: {}".format(str(res)))
    else:
        update.message.reply_photo(open("/tmp/{}.jpg".format(nowStr), 'rb'))

def getClip(update: Update, context: CallbackContext) -> None:
    now = datetime.datetime.now()
    nowStr = now.strftime('%Y%m%d%H%M%S')
    if len(context.args) > 0:
        print("Creating video with custom duration: {} sec".format(context.args[0]))
        duration = int(context.args[0])
    else:
        duration = 5
    print("Executing raspivid: {}ms".format(str(duration * 1000)))
    command = "raspivid -w 400 -h 300 -fps 15 -t {} -o /tmp/{}.h264".format(str(duration * 1000), nowStr)
    res = os.system(command)

    if res != 0:
        update.message.reply_text("Command returned error: {}".format(str(res)))
    else:
        transCmd = "MP4Box -fps 30 -add /tmp/{}.h264 /tmp/{}.mp4".format(nowStr, nowStr)
        resTrans = os.system(transCmd)
        if resTrans != 0:
            update.message.reply_text("Transcode command returned error: {}".format(str(resTrans)))
        else:
            update.message.reply_video(video=open("/tmp/{}.mp4".format(nowStr), 'rb'), duration=duration,supports_streaming=True)

def getDatabaseUpdates(update: Update, context: CallbackContext) -> None:
    con = sqlite3.connect('/data/motion/db/motion.sqlite')
    cur = con.cursor()
    cur.execute('SELECT * FROM security')
    rows = cur.fetchall()
    for row in rows: 
        update.message.reply_video(open(row[1], 'rb'))

def opsMotion(update: Update, context: CallbackContext) -> None:
    logging.info("Executing motion-daemon operation".format())
    if len(context.args) > 0:
        op = context.args[0]
    else:
        op = "start"

    command = "sudo systemctl {} motion-daemon".format(op)
    res = os.system(command)

    if res != 0:
        update.message.reply_text("Command returned error: {}".format(str(res)))
        messagingLogger.error("Command returned error: {}".format(str(res)))
    else:
        update.message.reply_text("Command executed: {}".format(op))

def getIfcfg(update: Update, context: CallbackContext) -> None:
    response = requests.get(url="http://ifconfig.co/ip")
    update.message.reply_text(response.text)

def hello(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Hello {} {}".format(update.effective_user.id, update.effective_user.first_name))


if 'TOKEN' not in os.environ:
    print("Error: TOKEN variable not found in environment")
    exit(1)
else:
    telegramToken = os.environ['TOKEN']

# Set bot default logger options
logFormat = "%(levelname)s %(asctime)s - %(message)s"

logging.basicConfig(
        filename='/tmp/py-bot-telegram.log', 
        encoding='utf-8',
        format=logFormat,
        level=logging.DEBUG
)

# Set messages logger options
messagingLogger = logging.getLogger(__name__)
mfh = logging.FileHandler('/tmp/py-bot-messaging.log')
mfmt = logging.Formatter('%(levelname)s %(asctime)s - %(message)s')
mfh.setFormatter(mfmt)
messagingLogger.addHandler(mfh)
messagingLogger.setLevel(logging.DEBUG)


exitLoopWatcher = threading.Event()

motionBot = Bot(token=telegramToken)
updater = Updater(bot=motionBot)
updater.dispatcher.add_handler(CommandHandler('hello', hello))
updater.dispatcher.add_handler(CommandHandler('ip', getIfcfg))
updater.dispatcher.add_handler(CommandHandler('db', getDatabaseUpdates))
updater.dispatcher.add_handler(CommandHandler('start', startWatcher))
updater.dispatcher.add_handler(CommandHandler('stop', stopWatcher))
updater.dispatcher.add_handler(CommandHandler('img', getStillImage))
updater.dispatcher.add_handler(CommandHandler('video', getClip))
updater.dispatcher.add_handler(CommandHandler('motion', opsMotion))

messagingLogger.info("Starting Telegram bot")

updater.start_polling()
updater.idle()
