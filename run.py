import logging
import threading
import sqlite3
import os
import time
from PIL import Image
from shell import process
from configuration import file
from telegram import Bot
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters )


def main():

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    try:
        telegram_token = os.environ['TOKEN']
        telegram_user_id = os.environ['USERID']
    except os as err:
        print("Error reading environment variables: {0}".format(err))
        exit(1)

    bot_instance = Bot(token=telegram_token)
    updater = Updater(bot=bot_instance)
    dispatcher = updater.dispatcher

    # Declare handlers
    start_handler = CommandHandler('start', start)
    updates_handler = CommandHandler('updates', updates)
    motion_start_handler = CommandHandler('motionstart', motion_start)
    motion_stop_handler = CommandHandler('motionstop', motion_stop)
    motion_take_video_handler = CommandHandler('motiontakevideo', motion_take_video)
    unknown_handler = MessageHandler(Filters.command, unknown)

    # Start handlers
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(updates_handler)
    dispatcher.add_handler(motion_start_handler)
    dispatcher.add_handler(motion_stop_handler)
    dispatcher.add_handler(motion_take_video_handler)
    dispatcher.add_handler(unknown_handler)

    th_update = threading.Thread(target=check_update_loop,args=(bot_instance,telegram_user_id))
    th_update.start()

    updater.start_polling()


def check_update_loop(bot, user_id):

    while True:

        motion_data_dir = file.get_param_from_file('config/main.cfg', 'Motion', 'data_directory')
        motion_db_dir = file.get_param_from_file('config/main.cfg', 'Motion', 'db_directory')
        motion_db_file = file.get_param_from_file('config/main.cfg', 'Motion', 'db_file')
        motion_db_path = motion_db_dir + "/" + motion_db_file
        motion_db_update_check_interval = file.get_param_from_file('config/main.cfg', 'Motion', 'db_update_check_interval')

        try:
            conn = sqlite3.connect(motion_db_path)
        except sqlite3.OperationalError as err:
            print("Error opening database [" + motion_db_path + "]: {0}".format(err))
            exit(0)

        cursor = conn.cursor()
        cursor.execute('SELECT * FROM security WHERE event_ack = 0 and event_end = 1')
        unack_events = cursor.fetchall()

        for event in unack_events:
            if event[3] == 8:
                print("Found event [" + str(event) + "]")

                event_thumb_orig = motion_data_dir + "/" + str(event[5]) + ".jpg"
                event_thumb_dest = "/tmp/" + str(event[5]) + "-thumb.jpg"
                event_thumb = Image.open(event_thumb_orig)
                size = 90,90
                event_thumb.thumbnail(size)
                event_thumb.save(event_thumb_dest,"JPEG")

                #bot.send_message(chat_id=user_id, text="New event found with time: " + str(event[4]))
                bot.send_video(
                    chat_id=user_id, 
                    video=open(event[1], 'rb'), 
                    caption=str(event[4]),
                    thumb=open(event_thumb_dest, 'rb'), 
                    supports_streaming=True)

                update_query = "UPDATE security SET event_ack = 1 WHERE event_time_stamp == '" + str(event[5]) + "';"
                cursor.execute(update_query)

        cursor.close()
        conn.commit()
        conn.close()

        time.sleep(int(motion_db_update_check_interval))


def updates(bot, update):

    count = 0

    bot.send_message(chat_id=update.message.chat_id, text="Looking for new updates ...")

    motion_db_dir = file.get_param_from_file('config/main.cfg', 'Motion', 'db_directory')
    motion_db_file = file.get_param_from_file('config/main.cfg', 'Motion', 'db_file')
    motion_db_path = motion_db_dir + "/" + motion_db_file

    try:
        conn = sqlite3.connect(motion_db_path)
    except sqlite3.OperationalError as err:
        print("Error opening database [" + motion_db_path + "]: {0} ".format(err))
        exit(0)

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


def motion_take_video(bot, update):

    motion_process_name = file.get_param_from_file('config/main.cfg', 'Motion', 'exec_bin')

    motion_status = process.check_running(motion_process_name)

    if motion_status <= 0:
        print("Motion not currently running")
        bot.send_message(
            chat_id=update.message.chat_id,
            text="Motion not currently running"
        )
    else:
        take_video_status = process.run("killall -s SIGUSR1 " + motion_process_name)

        if take_status > 0:
            print("Error with command: " + str(take_video_status))
            bot.send_message(
                chat_id=update.message.chat_id,
                text="Error with command: " + str(take_video_status)
            )
        else:
            print("Command sent successfully")
            bot.send_message(
                chat_id=update.message.chat_id,
                text="Command sent successfully"
            )


def motion_stop(bot, update):

    motion_process_name = file.get_param_from_file('config/main.cfg', 'Motion', 'exec_bin')

    motion_status = process.check_running(motion_process_name)

    if motion_status <= 0:
        print("Motion not currently running")
        bot.send_message(
            chat_id=update.message.chat_id,
            text="Motion not currently running"
        )
    else:
        stop_status = process.run("killall " + motion_process_name)

        if stop_status > 0:
            print("Error stopping motion process: " + str(stop_status))
            bot.send_message(
                chat_id=update.message.chat_id,
                text="Error stopping motion process: " + str(stop_status)
            )
        else:
            print("Motion stopped successfully")
            bot.send_message(
                chat_id=update.message.chat_id,
                text="Motion stopped successfully"
            )


def motion_start(bot, update):

    motion_process_name = file.get_param_from_file('config/main.cfg', 'Motion', 'exec_bin')

    motion_status = process.check_running(motion_process_name)

    if motion_status > 0:
        print("Motion already running with pid: " + str(motion_status))
        bot.send_message(
            chat_id=update.message.chat_id,
            text="Motion already running with pid: " + str(motion_status)
        )
    else:
        process_status = process.run(motion_process_name)

        if process_status > 0:
            print("Error starting motion process: " + str(process_status))
            bot.send_message(
                chat_id=update.message.chat_id,
                text="Error starting motion process: " + str(process_status)
            )
        else:
            print("Motion started successfully")
            bot.send_message(
                chat_id=update.message.chat_id,
                text="Motion started successfully"
            )


def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command")


def echo(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=update.message.text)


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Hi, I am motion bot. Please, talk to me!")


if __name__ == "__main__":
    main()
