from __future__ import annotations

import os

from fastapi import BackgroundTasks

from app.main_pipeline import process_video_pipeline

try:
    from celery import Celery
except ImportError:  # pragma: no cover
    Celery = None

celery_app = None
if Celery is not None:
    celery_app = Celery(
        "video_tasks",
        broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    )


if celery_app is not None:

    @celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
    def process_video_pipeline_task(self, job_id: str):
        try:
            process_video_pipeline(job_id)
            return {"job_id": job_id, "status": "done"}
        except Exception as exc:  # pragma: no cover
            raise self.retry(exc=exc)


def enqueue_pipeline(background_tasks: BackgroundTasks, job_id: str) -> str:
    use_celery = os.getenv("USE_CELERY", "0") == "1"
    if use_celery and celery_app is not None:
        process_video_pipeline_task.delay(job_id)
        return "celery"

    background_tasks.add_task(process_video_pipeline, job_id)
    return "background"
