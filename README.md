### Build image
```
docker build -t bot:latest .
```

### Run containers
```
MOTION_ROOT=/data/motion

docker run -d --restart=unless-stopped -e TOKEN=$(cat token) -v ${MOTION_ROOT}:/data/motion:rw -v /var/run/docker.sock:/var/run/docker.sock:rw bot:latest

docker run -d --restart=unless-stopped --privileged -v ${MOTION_ROOT}:/data/motion:rw motion:latest
docker run -d --restart=unless-stopped --privileged -v /data/motion:/data/motion:rw -v /etc/motion/motion.conf:/etc/motion/motion.conf jwater7/motion:latest
```
