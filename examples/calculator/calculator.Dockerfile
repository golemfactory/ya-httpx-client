FROM python:3.8-slim

WORKDIR /golem/work
VOLUME /golem/work

#   This is necessary only as long as we install yagna-requests from git
RUN apt-get update && \
    apt-get install -y git

#   This is *required* in every image that is supposed to work with yagna-requests
RUN pip install git+https://github.com/golemfactory/yagna-requests.git@johny-b/poc-APPS-122

#   And this is calculator-related code (this part will be different in other examples). 
RUN pip install Flask==2.0.1 gunicorn==20.1.0
COPY examples/calculator/calculator_server.py /golem/run/calculator_server.py
