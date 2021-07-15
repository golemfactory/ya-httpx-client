FROM python:3.8-slim

WORKDIR /golem/work
VOLUME  /golem/work

#   Install yagna-requests. This could be done also with
#   RUN pip install git+https://github.com/golemfactory/yagna-requests.git#egg=yagna-requests[provider]
#   but this way is much more convenient during the development.
COPY yagna_requests yagna_requests
COPY setup.py       setup.py
COPY README.md      README.md
RUN pip install .[provider]
RUN rm -r *

#   And this is calculator-related code (this part will be different in other examples). 
RUN pip install Flask==2.0.1 gunicorn==20.1.0
COPY examples/calculator/calculator_server.py /golem/run/calculator_server.py
