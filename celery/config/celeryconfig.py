from celery import Celery

app = Celery('tasks')

app.conf.update(
    broker_url='amqp://userf:userd@rabbitmq:5672',
    backend='redis://redis:6379',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    singleton_backend_url='redis://redis:6379/0'
    # timezone='Africa/Casablanca',
)
