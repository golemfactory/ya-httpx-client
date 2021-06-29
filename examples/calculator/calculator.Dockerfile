FROM python:3.8-slim

#   NOTE: this is *required* in every image that is supposed to work with yagna-requests
RUN pip  install git+https://github.com/golemfactory/yagna-requests.git@johny-b/poc-APPS-122

#   And this is just because our example server is using Flask and running on gunicorn
RUN pip install Flask==2.0.1 gunicorn==20.1.0

VOLUME /golem/work
WORKDIR /golem/work
