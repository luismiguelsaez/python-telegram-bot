import logging
import os
import requests
import json
import sqlite3
import psutil
import subprocess
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters

def main():

    telegram_token = os.environ['TOKEN']

    updater = Updater(token=telegram_token)
    dispatcher = updater.dispatcher

    #Declare handlers
    start_handler = CommandHandler('start', start)
    whoami_handler = CommandHandler('whoami', whoami)
    updates_handler = CommandHandler('updates', updates)
    motion_start_handler = CommandHandler('motionstart', motionStart)
    motion_stop_handler = CommandHandler('motionstop', motionStop)
    echo_handler = MessageHandler(Filters.text, echo)
    unknown_handler = MessageHandler(Filters.command, unknown)

    #Start handlers
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(whoami_handler)
    dispatcher.add_handler(updates_handler)
    dispatcher.add_handler(motion_start_handler)
    dispatcher.add_handler(motion_stop_handler)
    dispatcher.add_handler(echo_handler)
    dispatcher.add_handler(unknown_handler)

    updater.start_polling()

def motionStart(bot, update):
    running = 0
    startCmd = "motion -b"

    for proc in psutil.process_iter():
      if proc.name() == "motion":
        running = 1
        pid = proc.pid

    if running != 1:
      print("Motion not running, starting") 
      proc = subprocess.Popen(startCmd, stdout=subprocess.PIPE, shell=True)
      (out, err) = proc.communicate()
      proc_status = proc.wait()
      print("Command exit code: " + str(proc_status))
      if proc_status == 0:
        bot.send_message(chat_id=update.message.chat_id, text="Motion started successfully") 
      else:
        bot.send_message(chat_id=update.message.chat_id, text="Motion start error for command [" + startCmd + "] Error: " + err)
    else:
      print("Motion already running with pid: " + str(pid))
      bot.send_message(chat_id=update.message.chat_id, text="Motion already running with pid: " + str(pid))

def motionStop(bot, update):
    running = 0
    stopCmd = "killall motion"

    for proc in psutil.process_iter():
      if proc.name() == "motion":
        running = 1
        pid = proc.pid

    if running == 1:
      proc = subprocess.Popen(stopCmd, stdout=subprocess.PIPE, shell=True)
      (out, err) = proc.communicate()
      proc_status = proc.wait()
      print("Command exit code: " + str(proc_status))
      if proc_status == 0:
        bot.send_message(chat_id=update.message.chat_id, text="Motion stopped successfully. Killed process with pid: " + str(pid))
      else:
        bot.send_message(chat_id=update.message.chat_id, text="Motion stop error for command [" + stopCmd + "] Error: " + err)
    else:
      print("Motion is not running")
      bot.send_message(chat_id=update.message.chat_id, text="Motion is not running")

def loggingSetup():

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

def updates(bot, update):
    count = 0

    bot.send_message(chat_id=update.message.chat_id, text="Looking for new updates ...")

    conn = sqlite3.connect('/data/motion/db/motion.sqlite')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM security WHERE event_ack = 0')
    unack_events = cursor.fetchall()

    for event in unack_events:
      if event[3] == 8:
        count += 1
        bot.send_message(chat_id=update.message.chat_id, text=event)
        print("Found event with TS [" + str(event[5]) + "]") 
        bot.send_video(chat_id=update.message.chat_id, video=open(event[1], 'rb'), supports_streaming=True)
        print("Updating event [" + str(event[5]) + "]")
        update_query = "UPDATE security SET event_ack = 1 WHERE event_time_stamp == '" + str(event[5]) + "';"
        print("Executing query [" + update_query + "]")
        cursor.execute(update_query)

    if count == 0:
      bot.send_message(chat_id=update.message.chat_id, text="No updates found")

    cursor.close()
    conn.commit()
    conn.close()

def whoami(bot, update):
    r = requests.get('http://ifconfig.co/json')

    if r.status_code == 200:
        data = r.json()
        bot.send_message(chat_id=update.message.chat_id, text=data['city'] + "(" + data['country'] + ") " + data['ip'])
    else:
        bot.send_message(chat_id=update.message.chat_id, text="ifconfig.co returned bad HTTP_CODE :(")

def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.")

def echo(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=update.message.text)

def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="I'm a bot, please talk to me!")


if __name__ == "__main__":
    main()
