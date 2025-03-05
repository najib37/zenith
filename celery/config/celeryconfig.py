
from celery import Celery

app = Celery('tasks')


app.conf.update(
    broker_url='amqp://userf:userd@localhost:5672',
    result_backend='rpc://',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)
