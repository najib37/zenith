FROM python:3.11-alpine
RUN apk add --no-cache ffmpeg
# COPY . /home/celery
COPY requirements.txt /home/celery/requirements.txt
RUN pip install -r /home/celery/requirements.txt
