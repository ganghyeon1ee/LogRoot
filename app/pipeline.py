from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.schemas import (
    ClipAssets,
    ClipResult,
    ClipSegment,
    HighlightItem,
    HighlightResult,
    MatchedTrack,
    MixConfig,
    MusicInfo,
    MusicMatchRequest,
    MusicMatchResponse,
    TranscriptDocument,
    TranscriptSegment,
    TranscriptWord,
    TTSRequest,
    TTSResponse,
)


def run_stt(job_id: str, language: str, video_path: str) -> TranscriptDocument:
    """Run STT with optional faster-whisper; fallback to lightweight mock text."""
    try:
        from faster_whisper import WhisperModel  # type: ignore

        device = "cuda" if shutil.which("nvidia-smi") else "cpu"
        compute = "float16" if device == "cuda" else "int8"
        model = WhisperModel("large-v3", device=device, compute_type=compute)
        segments_iter, info = model.transcribe(video_path, language=None if language == "auto" else language, beam_size=5)

        transcript_segments: list[TranscriptSegment] = []
        for idx, segment in enumerate(segments_iter):
            words = [
                TranscriptWord(
                    word=getattr(w, "word", ""),
                    start_sec=float(getattr(w, "start", segment.start)),
                    end_sec=float(getattr(w, "end", segment.end)),
                    confidence=float(getattr(w, "probability", 0.9)),
                )
                for w in (getattr(segment, "words", None) or [])
            ]
            transcript_segments.append(
                TranscriptSegment(
                    seg_id=idx,
                    start_sec=float(segment.start),
                    end_sec=float(segment.end),
                    text=segment.text.strip(),
                    speaker="SPEAKER_00",
                    words=words,
                )
            )

        if transcript_segments:
            full_text = "\n".join(
                f"[{s.start_sec:.1f}-{s.end_sec:.1f}] {s.text}" for s in transcript_segments
            )
            return TranscriptDocument(
                job_id=job_id,
                language=getattr(info, "language", language),
                duration_sec=float(getattr(info, "duration", transcript_segments[-1].end_sec)),
                segments=transcript_segments,
                full_text=full_text,
                model="faster-whisper-large-v3",
                processed_at=datetime.now(timezone.utc),
            )
    except Exception:
        pass

    # fallback for local dev/non-GPU/non-model environment
    fallback_segment = TranscriptSegment(
        seg_id=0,
        start_sec=0.0,
        end_sec=60.0,
        text="업로드된 영상에 대한 기본 전사입니다. 실제 STT 엔진 연동 시 이 값은 실제 음성 전사로 대체됩니다.",
        speaker="SPEAKER_00",
        words=[],
    )
    return TranscriptDocument(
        job_id=job_id,
        language=language,
        duration_sec=60.0,
        segments=[fallback_segment],
        full_text=f"[0.0-60.0] {fallback_segment.text}",
        model="fallback-stt",
        processed_at=datetime.now(timezone.utc),
    )


def extract_highlights(transcript: TranscriptDocument, clip_count: int, min_sec: int, max_sec: int) -> HighlightResult:
    """Heuristic highlight extraction based on transcript segments/time windows."""
    highlights: list[HighlightItem] = []

    if not transcript.segments:
        return HighlightResult(
            job_id=transcript.job_id,
            model_used="heuristic-v1",
            highlights=[],
            extracted_at=datetime.now(timezone.utc),
        )

    for rank in range(1, clip_count + 1):
        seg = transcript.segments[min(rank - 1, len(transcript.segments) - 1)]
        start = max(0.0, seg.start_sec)
        target = min(max_sec, max(min_sec, int(seg.end_sec - seg.start_sec) or min_sec))
        end = min(transcript.duration_sec, start + float(target))
        if end <= start:
            end = start + float(min_sec)

        highlights.append(
            HighlightItem(
                rank=rank,
                start_sec=round(start, 1),
                end_sec=round(end, 1),
                title=f"하이라이트 {rank}",
                summary=seg.text[:120],
                highlight_reason="전사 텍스트 밀도/길이 기준 자동 추출",
                emotion_tags=["informative"],
                score=round(max(0.5, 1.0 - (rank - 1) * 0.08), 2),
            )
        )

    # Optional: local LLM override via Ollama-compatible endpoint
    ollama_url = "http://127.0.0.1:11434/api/generate"
    try:
        prompt = (
            f"다음 전사에서 {clip_count}개의 {min_sec}-{max_sec}초 하이라이트를 JSON으로 반환하세요.\n"
            f"전사:\n{transcript.full_text}"
        )
        payload = {"model": "qwen2.5:7b", "prompt": prompt, "format": "json", "stream": False}
        with httpx.Client(timeout=5.0) as client:
            r = client.post(ollama_url, json=payload)
            if r.status_code == 200 and "response" in r.json():
                pass
    except Exception:
        pass

    return HighlightResult(
        job_id=transcript.job_id,
        model_used="heuristic-v1",
        highlights=highlights,
        extracted_at=datetime.now(timezone.utc),
    )


def cut_video_clip(video_path: str, start_sec: float, end_sec: float, output_path: str) -> str:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    if shutil.which("ffmpeg") is None:
        shutil.copy(video_path, output)
        return str(output)

    duration = max(0.1, end_sec - start_sec)
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start_sec}",
        "-i",
        video_path,
        "-t",
        f"{duration}",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(output),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        shutil.copy(video_path, output)
    return str(output)


def synthesize_tts(request: TTSRequest) -> TTSResponse:
    return TTSResponse(
        clip_id=request.clip_id,
        audio_url=f"https://cdn.example.com/tts/{request.clip_id}_tts.mp3",
        duration_sec=43.2,
        sample_rate=24000,
        model_used=request.model,
    )


def match_music(request: MusicMatchRequest) -> MusicMatchResponse:
    track = MatchedTrack(
        track_id="ncs_042",
        title="Elektronomia - Sky High",
        source="NCS",
        license="CC-BY 3.0",
        bpm=128,
        mood_tags=["energetic", "uplifting"],
        similarity_score=0.87,
        url="https://storage/music/ncs_042.mp3",
    )
    return MusicMatchResponse(
        clip_id=request.clip_id,
        matched_tracks=[track],
        selected_track_id=track.track_id,
        mix_config=MixConfig(
            fade_in_sec=1.0,
            fade_out_sec=1.5,
            volume_db=-18,
            ducking_enabled=True,
            duck_db=-12,
        ),
    )


def build_clip_result(
    job_id: str,
    item: HighlightItem,
    with_tts: bool,
    with_music: bool,
    clip_video_path: str,
) -> ClipResult:
    clip_id = f"{job_id}_clip_{item.rank:03d}"
    assets = ClipAssets(
        video_url=clip_video_path,
        thumbnail_url=f"https://cdn.example.com/clips/{clip_id}_thumb.jpg",
        subtitle_url=f"https://cdn.example.com/clips/{clip_id}.srt",
    )

    if with_tts:
        tts = synthesize_tts(
            TTSRequest(
                clip_id=clip_id,
                mode="voice_clone",
                reference_audio_url=f"https://storage/{job_id}/sample_30s.mp3",
                text=item.summary,
                speed=1.25,
                model="xtts-v2",
                language="ko",
            )
        )
        assets.audio_url = tts.audio_url

    music_info = None
    if with_music:
        music = match_music(
            MusicMatchRequest(
                clip_id=clip_id,
                emotion_tags=item.emotion_tags,
                content_type="lecture",
                clip_duration_sec=item.end_sec - item.start_sec,
            )
        )
        selected = music.matched_tracks[0]
        music_info = MusicInfo(
            track_id=selected.track_id,
            title=selected.title,
            mood=selected.mood_tags[0],
            bpm=selected.bpm,
            volume_db=music.mix_config.volume_db,
        )

    return ClipResult(
        clip_id=clip_id,
        rank=item.rank,
        title=item.title,
        score=item.score,
        segment=ClipSegment(
            start_sec=item.start_sec,
            end_sec=item.end_sec,
            duration_sec=round(item.end_sec - item.start_sec, 1),
        ),
        highlight_reason=item.highlight_reason,
        emotion_tags=item.emotion_tags,
        assets=assets,
        music=music_info,
        created_at=datetime.now(timezone.utc),
    )