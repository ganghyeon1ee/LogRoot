from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile

from app.schemas import ClipsResponse, JobOptions, JobResponse, JobStatusResponse
from app.storage import store
from app.tasks import enqueue_pipeline

app = FastAPI(title="Short-form AI Pipeline API", version="1.0.0")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/api/v1/jobs", response_model=JobResponse, status_code=202)
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    options: str = Form(...),
) -> JobResponse:
    try:
        parsed = json.loads(options)
        if "music_ mood" in parsed and "music_mood" not in parsed:
            parsed["music_mood"] = parsed.pop("music_ mood")
        job_options = JobOptions.model_validate(parsed)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid options JSON: {exc}") from exc

    job_id = f"job_{uuid.uuid4().hex[:8]}"
    file_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    file_path.write_bytes(await file.read())

    record = store.create_job(job_id, job_options, str(file_path))
    enqueue_pipeline(background_tasks, job_id)

    return JobResponse(
        job_id=job_id,
        status=record.status,
        created_at=record.created_at,
        estimated_duration_sec=180,
        webhook_url=job_options.webhook_url,
        _links={
            "self": f"/api/v1/jobs/{job_id}",
            "status": f"/api/v1/jobs/{job_id}/status",
            "clips": f"/api/v1/jobs/{job_id}/clips",
        },
    )


@app.get("/api/v1/jobs/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(job_id: str) -> JobStatusResponse:
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(job_id=job_id, status=job.status, progress=job.progress, error=job.error)


@app.get("/api/v1/jobs/{job_id}/clips", response_model=ClipsResponse)
def get_clips(job_id: str) -> ClipsResponse:
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "done":
        raise HTTPException(status_code=409, detail="Job is not completed yet")
    return ClipsResponse(job_id=job_id, clips=job.clips)

