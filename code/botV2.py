from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
import os
import requests
from time import sleep

def getIfcfg(update: Update, context: CallbackContext) -> None:
    response = requests.get(url="http://ifconfig.co/ip")
    update.message.reply_text(response.text)

def hello(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Hello {} {}".format(update.effective_user.id, update.effective_user.first_name))

def startLoop(update: Update, context: CallbackContext) -> None:
    while True:
        update.message.reply_text("Loop message")
        sleep(1)

if 'TOKEN' not in os.environ:
    print("Error: TOKEN variable not found in environment")
    exit(1)
else:
    telegramToken = os.environ['TOKEN']

updater = Updater(telegramToken)
updater.dispatcher.add_handler(CommandHandler('hello', hello))
updater.dispatcher.add_handler(CommandHandler('ip', getIfcfg))
updater.dispatcher.add_handler(CommandHandler('loop', startLoop))

updater.start_polling()
updater.idle()
