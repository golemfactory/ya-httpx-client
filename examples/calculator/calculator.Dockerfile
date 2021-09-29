FROM python:3.8-slim

WORKDIR /golem/work
VOLUME  /golem/work

#   Install ya-httpx-client.
#   This is only required for the non-VPN comunication.
RUN apt-get update && apt-get install -y git
RUN pip install git+https://github.com/golemfactory/ya-httpx-client.git#egg=ya-httpx-client[provider]

#   And this is calculator-related code (this part will differ in other examples). 
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY calculator_server.py /golem/run/calculator_server.py
