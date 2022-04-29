from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
import os
import requests
from time import sleep
import sqlite3
import threading
import datetime


def loopWatcher(update: Update, context: CallbackContext) -> None:
    while True:
        con = sqlite3.connect('/data/motion/db/motion.sqlite')
        cur = con.cursor()
        cur.execute('SELECT * FROM security WHERE event_end = 1 AND event_ack = 0')
        rows = cur.fetchall()
        for row in rows: 
            update.message.reply_video(open(row[1], 'rb'))
            update_query = 'UPDATE security SET event_ack = 1 WHERE filename LIKE "{}"'.format(row[1])
            cur.execute(update_query)

        con.commit()
        con.close()

        sleep(5)

        if exitLoopWatcher.is_set():
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
        update.message.repli_text("Command returned error: {}".format(str(res)))
    else:
        update.message.reply_photo(open("/tmp/{}.jpg".format(nowStr), 'rb'))

def getClip(update: Update, context: CallbackContext) -> None:
    now = datetime.datetime.now()
    nowStr = now.strftime('%Y%m%d%H%M%S')
    command = "raspivid -w 400 -h 300 -fps 15 -t 2000 -o /tmp/{}.h264".format(nowStr)
    res = os.system(command)

    if res != 0:
        update.message.repli_text("Command returned error: {}".format(str(res)))
    else:
        update.message.reply_video(open("/tmp/{}.h264".format(nowStr), 'rb'))

def getDatabaseUpdates(update: Update, context: CallbackContext) -> None:
    con = sqlite3.connect('/data/motion/db/motion.sqlite')
    cur = con.cursor()
    cur.execute('SELECT * FROM security')
    rows = cur.fetchall()
    for row in rows: 
        update.message.reply_video(open(row[1], 'rb'))

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

exitLoopWatcher = threading.Event()

updater = Updater(telegramToken)
updater.dispatcher.add_handler(CommandHandler('hello', hello))
updater.dispatcher.add_handler(CommandHandler('ip', getIfcfg))
updater.dispatcher.add_handler(CommandHandler('db', getDatabaseUpdates))
updater.dispatcher.add_handler(CommandHandler('start', startWatcher))
updater.dispatcher.add_handler(CommandHandler('stop', stopWatcher))
updater.dispatcher.add_handler(CommandHandler('img', getStillImage))
updater.dispatcher.add_handler(CommandHandler('video', getClip))

updater.start_polling()
updater.idle()
