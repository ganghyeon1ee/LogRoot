from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import JobOptions, JobProgress, JobRecord, JobStatus, PipelineStep, StepStatus

PIPELINE_NAMES = [
    "stt",
    "highlight_extraction",
    "video_edit",
    "tts",
    "subtitle",
    "music",
    "packaging",
]


class InMemoryJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}

    def create_job(self, job_id: str, options: JobOptions, file_path: str) -> JobRecord:
        steps = [PipelineStep(name=name, status=StepStatus.pending, pct=0) for name in PIPELINE_NAMES]
        progress = JobProgress(current_step="queued", steps=steps, overall_pct=0)
        record = JobRecord(
            job_id=job_id,
            created_at=datetime.now(timezone.utc),
            status=JobStatus.queued,
            options=options,
            file_path=file_path,
            progress=progress,
        )
        self._jobs[job_id] = record
        return record

    def get_job(self, job_id: str) -> JobRecord | None:
        return self._jobs.get(job_id)

    def update_step(self, job_id: str, step_name: str, status: StepStatus, pct: int) -> None:
        job = self._jobs[job_id]
        for step in job.progress.steps:
            if step.name == step_name:
                step.status = status
                step.pct = pct
                break

        job.progress.current_step = step_name
        total = sum(step.pct for step in job.progress.steps)
        job.progress.overall_pct = round(total / len(job.progress.steps))
        if status == StepStatus.processing:
            job.status = JobStatus.processing

    def mark_done(self, job_id: str) -> None:
        job = self._jobs[job_id]
        for step in job.progress.steps:
            if step.status != StepStatus.done:
                step.status = StepStatus.done
                step.pct = 100
        job.progress.current_step = "packaging"
        job.progress.overall_pct = 100
        job.status = JobStatus.done

    def mark_failed(self, job_id: str, error: str) -> None:
        job = self._jobs[job_id]
        job.status = JobStatus.failed
        job.error = error


store = InMemoryJobStore()
