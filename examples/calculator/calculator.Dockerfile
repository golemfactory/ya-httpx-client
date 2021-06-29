FROM python:3.8-slim

RUN pip install Flask==2.0.1 gunicorn==20.1.0

VOLUME /golem/work
WORKDIR /golem/work
