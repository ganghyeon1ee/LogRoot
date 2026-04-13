from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.pipeline import build_clip_result, cut_video_clip, extract_highlights, run_stt
from app.schemas import StepStatus
from app.storage import store


CLIP_DIR = Path("uploads/clips")


def process_video_pipeline(job_id: str) -> None:
    job = store.get_job(job_id)
    if not job:
        return

    try:
        store.update_step(job_id, "stt", StepStatus.processing, 30)
        transcript = run_stt(job_id, job.options.language.value, job.file_path)
        job.raw["transcript"] = transcript.model_dump(mode="json")
        store.update_step(job_id, "stt", StepStatus.done, 100)

        store.update_step(job_id, "highlight_extraction", StepStatus.processing, 60)
        highlights = extract_highlights(
            transcript,
            clip_count=job.options.clip_count,
            min_sec=job.options.clip_duration_range.min_sec,
            max_sec=job.options.clip_duration_range.max_sec,
        )
        job.raw["highlights"] = highlights.model_dump(mode="json")
        store.update_step(job_id, "highlight_extraction", StepStatus.done, 100)

        store.update_step(job_id, "video_edit", StepStatus.processing, 50)
        clip_video_paths: dict[int, str] = {}
        for h in highlights.highlights:
            clip_path = CLIP_DIR / f"{job_id}_clip_{h.rank:03d}.mp4"
            clip_video_paths[h.rank] = cut_video_clip(job.file_path, h.start_sec, h.end_sec, str(clip_path))
        store.update_step(job_id, "video_edit", StepStatus.done, 100)

        store.update_step(job_id, "tts", StepStatus.done, 100)
        store.update_step(job_id, "subtitle", StepStatus.done, 100)
        store.update_step(job_id, "music", StepStatus.done, 100)

        store.update_step(job_id, "packaging", StepStatus.processing, 80)
        clips = [
            build_clip_result(
                job_id,
                h,
                with_tts=job.options.tts_enabled,
                with_music=job.options.music_enabled,
                clip_video_path=clip_video_paths[h.rank],
            )
            for h in highlights.highlights
        ]
        job.clips = clips
        store.update_step(job_id, "packaging", StepStatus.done, 100)

        store.mark_done(job_id)
        job.raw["completed_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        store.mark_failed(job_id, str(exc))
