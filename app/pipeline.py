from __future__ import annotations

from datetime import datetime

from .schemas import (
    Clip,
    ClipAssets,
    ClipMusic,
    ClipSegment,
    HighlightItem,
    HighlightResult,
    JobStatus,
    StoredJob,
    TranscriptDocument,
    TranscriptSegment,
)


def update_step(job: StoredJob, step_name: str, status: str, pct: int) -> None:
    job.progress.current_step = step_name
    for step in job.progress.steps:
        if step.name == step_name:
            step.status = status
            step.pct = pct
    job.progress.overall_pct = int(sum(s.pct for s in job.progress.steps) / len(job.progress.steps))


def run_stt(job: StoredJob) -> TranscriptDocument:
    update_step(job, "stt", "processing", 30)
    seg = TranscriptSegment(
        seg_id=0,
        start_sec=0.0,
        end_sec=50.0,
        text="안녕하세요, 오늘은 AI가 바꿀 직업의 미래에 대해 이야기해보겠습니다.",
        speaker="SPEAKER_00",
        words=[],
    )
    update_step(job, "stt", "done", 100)
    return TranscriptDocument(
        job_id=job.job_id,
        language=job.options.language.value,
        duration_sec=1800.0,
        segments=[seg],
        full_text=f"[{seg.start_sec:.1f}-{seg.end_sec:.1f}] {seg.text}",
        model="faster-whisper-large-v3",
        processed_at=datetime.utcnow(),
    )


def extract_highlights(job: StoredJob, transcript: TranscriptDocument) -> HighlightResult:
    update_step(job, "highlight_extraction", "processing", 60)
    min_sec = job.options.clip_duration_range.min_sec
    highlights = []
    start = 300.0
    for rank in range(1, job.options.clip_count + 1):
        highlights.append(
            HighlightItem(
                rank=rank,
                start_sec=start + (rank * 15),
                end_sec=start + (rank * 15) + min_sec,
                title=f"하이라이트 {rank}",
                summary="스토리 완결성이 높고 숏폼 전환에 적합한 구간",
                highlight_reason="기승전결이 명확하고 흥미 유발 포인트가 있음",
                emotion_tags=["informative", "surprising"],
                score=max(0.7, 0.95 - (rank * 0.05)),
            )
        )
    update_step(job, "highlight_extraction", "done", 100)
    return HighlightResult(
        job_id=job.job_id,
        model_used="llama3-70b-instruct",
        highlights=highlights,
        extracted_at=datetime.utcnow(),
    )


def build_clips(job: StoredJob, highlights: HighlightResult) -> list[Clip]:
    update_step(job, "video_edit", "processing", 40)
    clips: list[Clip] = []
    for h in highlights.highlights:
        clip_id = f"clip_{h.rank:03d}"
        duration_sec = round(h.end_sec - h.start_sec, 1)
        music = (
            ClipMusic(
                track_id="ncs_042",
                title="Elektronomia - Sky High",
                mood="energetic",
                bpm=128,
                volume_db=-18,
            )
            if job.options.music_enabled
            else None
        )
        assets = ClipAssets(
            video_url=f"https://cdn.example.com/clips/{job.job_id}/{clip_id}.mp4",
            thumbnail_url=f"https://cdn.example.com/clips/{job.job_id}/{clip_id}_thumb.jpg",
            subtitle_url=f"https://cdn.example.com/clips/{job.job_id}/{clip_id}.srt"
            if job.options.subtitle_style.value != "disabled"
            else None,
            audio_url=f"https://cdn.example.com/tts/{job.job_id}/{clip_id}_tts.mp3"
            if job.options.tts_enabled
            else None,
        )
        clips.append(
            Clip(
                clip_id=clip_id,
                rank=h.rank,
                title=h.title,
                score=h.score,
                segment=ClipSegment(start_sec=h.start_sec, end_sec=h.end_sec, duration_sec=duration_sec),
                highlight_reason=h.highlight_reason,
                emotion_tags=h.emotion_tags,
                assets=assets,
                music=music,
                created_at=datetime.utcnow(),
            )
        )

    update_step(job, "video_edit", "done", 100)
    update_step(job, "tts", "done", 100 if job.options.tts_enabled else 0)
    update_step(job, "subtitle", "done", 100 if job.options.subtitle_style.value != "disabled" else 0)
    update_step(job, "music", "done", 100 if job.options.music_enabled else 0)
    update_step(job, "packaging", "done", 100)
    return clips


def run_pipeline(job: StoredJob) -> StoredJob:
    try:
        job.status = JobStatus.processing
        transcript = run_stt(job)
        highlights = extract_highlights(job, transcript)
        job.clips = build_clips(job, highlights)
        job.status = JobStatus.done
        job.progress.overall_pct = 100
        return job
    except Exception as exc:
        job.status = JobStatus.failed
        job.error = str(exc)
        return job
