FROM python:3.7.2-alpine

RUN sed -i -e 's/v[[:digit:]]\.[[:digit:]]/edge/g' /etc/apk/repositories \
    && echo http://dl-cdn.alpinelinux.org/alpine/edge/testing >> /etc/apk/repositories

RUN apk update && apk upgrade && apk add motion && apk add --virtual build-deps openssl-dev musl-dev libffi-dev gcc

COPY requirements.txt .

RUN pip install -r requirements.txt --upgrade

RUN apk del build-deps

RUN mkdir /app
WORKDIR /app
COPY code/ /app

ENTRYPOINT ["python","/app/run.py"]
