FROM python:latest
MAINTAINER bas@toonk.nl

RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get install -y build-essential
COPY requirements.txt /
RUN pip install -r requirements.txt
RUN pip install --pre --upgrade kubernetes

COPY mysocketd.py /

ENTRYPOINT ["/mysocketd.py"]

