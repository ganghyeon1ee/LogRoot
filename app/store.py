from __future__ import annotations

from datetime import datetime
from threading import Lock

from .schemas import JobOptions, JobStatus, Progress, ProgressStep, StoredJob


class InMemoryJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, StoredJob] = {}
        self._lock = Lock()

    def create(self, job_id: str, options: JobOptions) -> StoredJob:
        progress = Progress(
            current_step="stt",
            steps=[
                ProgressStep(name="stt", status="pending", pct=0),
                ProgressStep(name="highlight_extraction", status="pending", pct=0),
                ProgressStep(name="video_edit", status="pending", pct=0),
                ProgressStep(name="tts", status="pending", pct=0),
                ProgressStep(name="subtitle", status="pending", pct=0),
                ProgressStep(name="music", status="pending", pct=0),
                ProgressStep(name="packaging", status="pending", pct=0),
            ],
            overall_pct=0,
        )
        job = StoredJob(
            job_id=job_id,
            created_at=datetime.utcnow(),
            status=JobStatus.queued,
            options=options,
            progress=progress,
        )
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> StoredJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def save(self, job: StoredJob) -> None:
        with self._lock:
            self._jobs[job.job_id] = job


store = InMemoryJobStore()
