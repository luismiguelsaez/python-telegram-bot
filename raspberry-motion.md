
# Install packages

- https://motion-project.github.io/motion_download.html

```bash
curl -sL https://raw.githubusercontent.com/Motion-Project/motion-packaging/master/builddeb.sh | /bin/bash
```

```bash
sudo apt-get install  git autoconf automake libtool libavcodec-dev libavdevice-dev libavformat-dev libswscale-dev libjpeg-dev libpq-dev libsqlite3-dev debhelper dh-autoreconf libwebp-dev libmicrohttpd-dev gettext libmariadb-dev-compat python3-pip sqlite3 gpac
```

```bash
curl -sL https://github.com/Motion-Project/motion/releases/download/release-4.4.0/pi_buster_motion_4.4.0-1_armhf.deb -o pi_buster_motion_4.4.0-1_armhf.deb
dpkg -i pi_buster_motion_4.4.0-1_armhf.deb
```

# Disable LEDs

```bash
echo 1 >/sys/class/leds/led0/brightness #Turn on
echo 0 >/sys/class/leds/led0/brightness #Turn off
```

- Edit `/boot/config.txt` file

```ini
# Turn off PWR LED
dtparam=pwr_led_trigger=none
dtparam=pwr_led_activelow=off
 
# Turn off ACT LED
dtparam=act_led_trigger=none
dtparam=act_led_activelow=off
 
# Turn off Ethernet ACT LED
dtparam=eth_led0=4
 
# Turn off Ethernet LNK LED
dtparam=eth_led1=4

# Turn off Camera module LED
disable_camera_led=1
```

# SQLite setup

```bash
sudo mkdir -p /data/motion/db
sudo chown -R pi. /data/motion
cat sqlite/create_schema.sql | sqlite3 /data/motion/db/motion.sqlite
python code/run.py
```

/etc/motion/motion.conf
```bash
sql_log_movie on
sql_query insert into security (camera, filename, frame, file_type, time_stamp, event_time_stamp, event_end, event_ack) values('%t', '%f', '%q', '%n', '%Y-%m-%d %T', '%C', 0, 0)
sql_query_stop update security set event_end = 1 where event_time_stamp='%C'
database_type sqlite3
database_dbname /data/motion/db/motion.sqlite
```


# Clone repo

```bash
git clone https://github.com/h4rdL1nk/python-telegram-bot


