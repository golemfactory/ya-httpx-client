FROM python:3.8-slim

WORKDIR /golem/work
VOLUME  /golem/work

#   Install ya-httpx-client. This could be done also with
#   RUN pip install git+https://github.com/golemfactory/ya-httpx-client.git#egg=ya-httpx-client[provider]
#   but this way is much more convenient during the development.
COPY ya_httpx_client ya_httpx_client
COPY setup.py       setup.py
COPY README.md      README.md
RUN pip install .[provider]
RUN rm -r *

#   And this is calculator-related code (this part will be different in other examples). 
RUN pip install Flask==2.0.1 gunicorn==20.1.0
COPY examples/calculator/calculator_server.py /golem/run/calculator_server.py
