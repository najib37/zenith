FROM python:3.11-alpine
RUN apk update --no-cache 
RUN apk add ffmpeg
COPY requirements.txt /home/celery/requirements.txt
RUN pip install -r /home/celery/requirements.txt
