from celery import Celery
from . import celery_config


def create_celery() -> Celery:
    celery_app = Celery(
        "leadgen-backend",
        broker=celery_config.broker_url,
        backend=celery_config.result_backend,
    )
    celery_app.conf.update(
        task_serializer=celery_config.task_serializer,
        result_serializer=celery_config.result_serializer,
        accept_content=celery_config.accept_content,
        timezone=celery_config.timezone,
        enable_utc=celery_config.enable_utc,
    )
    return celery_app
