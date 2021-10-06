FROM python:3.8-slim

WORKDIR /golem/work
VOLUME  /golem/work

#   Install ya-httpx-client.
#   This is only required for the non-VPN comunication.
RUN apt-get update && apt-get install -y git
RUN pip install git+https://github.com/golemfactory/ya-httpx-client.git#egg=ya-httpx-client[provider]

#   Install example dependencies & copy code
RUN pip install Flask==2.0.1 gunicorn==20.1.0
COPY echo_server.py /golem/run/echo_server.py
