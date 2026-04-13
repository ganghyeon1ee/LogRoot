from __future__ import annotations

from celery import Celery

from .pipeline import run_pipeline
from .store import store

celery_app = Celery(
    "shortform_tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)


@celery_app.task(name="process_video_pipeline", max_retries=3, default_retry_delay=30)
def process_video_pipeline(job_id: str) -> dict:
    job = store.get(job_id)
    if not job:
        return {"job_id": job_id, "status": "failed", "error": "job_not_found"}

    updated = run_pipeline(job)
    store.save(updated)
    return {"job_id": job_id, "status": updated.status.value}
