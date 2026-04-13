from __future__ import annotations

from datetime import datetime, timezone

from app.pipeline import build_clip_result, extract_highlights, run_stt
from app.schemas import StepStatus
from app.storage import store


def process_video_pipeline(job_id: str) -> None:
    job = store.get_job(job_id)
    if not job:
        return

    try:
        store.update_step(job_id, "stt", StepStatus.processing, 30)
        transcript = run_stt(job_id, job.options.language.value)
        job.raw["transcript"] = transcript.model_dump(mode="json")
        store.update_step(job_id, "stt", StepStatus.done, 100)

        store.update_step(job_id, "highlight_extraction", StepStatus.processing, 60)
        highlights = extract_highlights(transcript, clip_count=job.options.clip_count)
        job.raw["highlights"] = highlights.model_dump(mode="json")
        store.update_step(job_id, "highlight_extraction", StepStatus.done, 100)

        store.update_step(job_id, "video_edit", StepStatus.done, 100)
        store.update_step(job_id, "tts", StepStatus.done, 100)
        store.update_step(job_id, "subtitle", StepStatus.done, 100)
        store.update_step(job_id, "music", StepStatus.done, 100)

        store.update_step(job_id, "packaging", StepStatus.processing, 80)
        clips = [
            build_clip_result(job_id, h, with_tts=job.options.tts_enabled, with_music=job.options.music_enabled)
            for h in highlights.highlights
        ]
        job.clips = clips
        store.update_step(job_id, "packaging", StepStatus.done, 100)

        store.mark_done(job_id)
        job.raw["completed_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        store.mark_failed(job_id, str(exc))
