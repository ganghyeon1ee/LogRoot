from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from .pipeline import run_pipeline
from .schemas import ClipsResponse, JobAcceptedResponse, JobOptions, JobStatus, JobStatusResponse
from .store import store
from .tasks import process_video_pipeline

app = FastAPI(title="Short-form AI Pipeline API", version="0.1.0")


@app.post("/api/v1/jobs", status_code=202, response_model=JobAcceptedResponse)
async def create_job(file: UploadFile = File(...), options: str = Form(...)) -> JobAcceptedResponse:
    try:
        parsed = JobOptions.model_validate(json.loads(options))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid options payload: {exc}") from exc

    job_id = f"job_{uuid.uuid4().hex[:8]}"
    target = Path("/tmp") / f"{job_id}_{file.filename}"
    content = await file.read()
    target.write_bytes(content)

    job = store.create(job_id, parsed)
    job.artifacts["source_video"] = str(target)
    store.save(job)

    # Redis/Celery가 없으면 동기 파이프라인으로 즉시 처리되도록 폴백
    try:
        process_video_pipeline.delay(job_id)
    except Exception:
        updated = run_pipeline(job)
        store.save(updated)

    return JobAcceptedResponse(
        job_id=job_id,
        status=job.status,
        created_at=job.created_at,
        estimated_duration_sec=180,
        webhook_url=parsed.webhook_url,
        links={
            "self": f"/api/v1/jobs/{job_id}",
            "status": f"/api/v1/jobs/{job_id}/status",
            "clips": f"/api/v1/jobs/{job_id}/clips",
        },
    )


@app.get("/api/v1/jobs/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(job_id: str) -> JobStatusResponse:
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return JobStatusResponse(job_id=job.job_id, status=job.status, progress=job.progress, error=job.error)


@app.get("/api/v1/jobs/{job_id}/clips", response_model=ClipsResponse)
def get_job_clips(job_id: str) -> ClipsResponse:
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != JobStatus.done:
        raise HTTPException(status_code=409, detail="job not completed yet")
    return ClipsResponse(job_id=job.job_id, clips=job.clips)
