import logging
import threading
import sqlite3
import os
import glob
import time
import datetime
import requests
import json
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
    run_command_handler = CommandHandler('runcmd', run_command)
    updates_handler = CommandHandler('updates', updates)
    info_handler = CommandHandler('info', info)
    motion_start_handler = CommandHandler('motionstart', motion_start)
    motion_stop_handler = CommandHandler('motionstop', motion_stop)
    camera_take_snap_handler = CommandHandler('camerasnap', camera_take_snap)
    camera_take_video_handler = CommandHandler('cameravideo', camera_take_video)
    unknown_handler = MessageHandler(Filters.command, unknown)

    # Start handlers
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(run_command_handler)
    dispatcher.add_handler(updates_handler)
    dispatcher.add_handler(info_handler)
    dispatcher.add_handler(motion_start_handler)
    dispatcher.add_handler(motion_stop_handler)
    dispatcher.add_handler(camera_take_snap_handler)
    dispatcher.add_handler(camera_take_video_handler)
    dispatcher.add_handler(unknown_handler)

    th_update = threading.Thread(target=check_update_loop,args=(bot_instance,telegram_user_id))
    th_update.start()

    updater.start_polling()


def info(bot, update):

    valid_http_codes = [200]

    try:
        ip_request = requests.get("https://ifconfig.co/json")
    except Exception as err:
        bot.send_message(
            chat_id=update.message.chat_id,
            text="Error getting ifconfig info: " + str(err)
        )
        pass

    if ip_request.status_code in valid_http_codes:
        ip_request_json = json.loads(ip_request.text)
        bot.send_message(
            chat_id=update.message.chat_id,
            text="My IP is " + ip_request_json['ip'] + ", and I am in " + ip_request_json['city'] + " (" + ip_request_json['country'] + ")"
        )
    else:
        bot.send_message(
            chat_id=update.message.chat_id,
            text="Got unexpected status code: " + str(ip_request.status_code)
        )


def run_command(bot, update):

    command_status = process.run_output("tail -4 /tmp/motion.log")

    bot.send_message(
        chat_id=update.message.chat_id,
        text="Command output: " + command_status['output']
    )


def camera_take_video(bot, update):

    video_output_ts = str(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
    video_output_file = "/tmp/clip-" + video_output_ts
    video_status = process.run("raspivid -w 640 -h 480 -fps 25 -t 5000 -o " + video_output_file + ".raw")

    #p = subprocess.Popen(args=["raspivid","-w","640","-h","480","-fps","25","-t","1000","-o","-"],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    #stdout,stderr = p.communicate()
    #p2 = subprocess.Popen(args=["ffmpeg","-i","-","-an","-r","8","-y","-loglevel","quiet","-vcodec","copy",video_output_file + ".mp4"],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,stdin=subprocess.PIPE)
    #cvstdout,cvstderr = p2.communicate(stdout)

    if video_status > 0:
        print("Error taking snapshot: " + str(video_status))
        bot.send_message(
            chat_id=update.message.chat_id,
            text="Error taking snapshot: " + str(video_status)
        )
    else:
        print("Snapshot taken successfully")

        video_convert_status = process.run("ffmpeg -i " + video_output_file + ".raw -an -r 8 -y -loglevel quiet -vcodec copy " + video_output_file + ".mp4")
        
        if video_convert_status > 0:
            print("Error converting snapshot: " + str(video_convert_status))
            bot.send_message(
                chat_id=update.message.chat_id,
                text="Error converting snapshot: " + str(video_status)
            )
        else:
            bot.send_video(
                chat_id=update.message.chat_id, 
                video=open(video_output_file + ".mp4", 'rb'), 
                caption="Clip TS [" + video_output_ts + "]"
            )


def camera_take_snap(bot, update):

    snap_output_ts = str(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
    snap_output_file = "/tmp/snapshot-" + snap_output_ts + ".jpg"
    snap_status = process.run("raspistill -w 640 -h 480 -q 75 -th 640:480:50 -e jpg -o " + snap_output_file)

    if snap_status > 0:
        print("Error taking snapshot: " + str(snap_status))
        bot.send_message(
            chat_id=update.message.chat_id,
            text="Error taking snapshot: " + str(snap_status)
        )
    else:
        print("Snapshot taken successfully")

        bot.send_photo(
            chat_id=update.message.chat_id, 
            photo=open(snap_output_file, 'rb'), 
            caption="Snapshot TS [" + snap_output_ts + "]"
        )


def check_update_loop(bot, user_id):

    while True:

        motion_data_dir = file.get_param_from_file('config/main.cfg', 'Motion', 'data_directory')
        motion_db_dir = file.get_param_from_file('config/main.cfg', 'Motion', 'db_directory')
        motion_db_file = file.get_param_from_file('config/main.cfg', 'Motion', 'db_file')
        motion_db_path = motion_db_dir + "/" + motion_db_file
        motion_db_update_check_interval = file.get_param_from_file('config/main.cfg', 'Motion', 'db_update_check_interval')

        try:
            conn = sqlite3.connect(motion_db_path,isolation_level=None)
        except sqlite3.OperationalError as err:
            print("Error opening database [" + motion_db_path + "]: {0}".format(err))
            exit(0)

        cursor = conn.cursor()
        cursor.execute('SELECT * FROM security WHERE event_ack = 0 and event_end = 1')
        unack_events = cursor.fetchall()

        for event in unack_events:
            if event[3] == 8:
                print("Found event [" + str(event) + "]")

                event_thumb_orig = glob.glob(motion_data_dir + "/" + str(event[5]) + "*.jpg")

                if len(event_thumb_orig) > 0:
                  event_thumb_dest = "/tmp/" + str(event[5]) + "-thumb.jpg"
                  event_thumb = Image.open(event_thumb_orig[0])
                  size = 90,90
                  event_thumb.thumbnail(size)
                  event_thumb.save(event_thumb_dest,"JPEG")

                  bot.send_video(
                    chat_id=user_id, 
                    video=open(event[1], 'rb'), 
                    caption=str(event[4]),
                    thumb=open(event_thumb_dest, 'rb'), 
                    supports_streaming=True)

                else:
                  bot.send_video(
                    chat_id=user_id,
                    video=open(event[1], 'rb'),
                    caption=str(event[4]),
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
        stop_status = process.run("systemctl stop " + motion_process_name)

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
        process_status = process.run("systemctl start " + motion_process_name)

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
