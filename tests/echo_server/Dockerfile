FROM python:3.8-slim

WORKDIR /golem/work
VOLUME /golem/work

#   This is necessary only as long as we install yagna-requests from git
RUN apt-get update && \
    apt-get install -y git
RUN pip install git+https://github.com/golemfactory/yagna-requests.git@johny-b/poc-APPS-122

#   Install dependencies & code
RUN pip install Flask==2.0.1 gunicorn==20.1.0
COPY echo_server.py /golem/run/echo_server.py
