from __future__ import annotations

from datetime import datetime, timezone

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


def run_stt(job_id: str, language: str) -> TranscriptDocument:
    segments = [
        TranscriptSegment(
            seg_id=0,
            start_sec=0.0,
            end_sec=4.8,
            text="안녕하세요, 오늘은 AI가 바꿀 직업의 미래에 대해 이야기합니다.",
            speaker="SPEAKER_00",
            words=[
                TranscriptWord(word="안녕하세요", start_sec=0.0, end_sec=0.7, confidence=0.98),
                TranscriptWord(word="오늘은", start_sec=0.8, end_sec=1.2, confidence=0.97),
            ],
        )
    ]
    full_text = "\n".join(f"[{s.start_sec:.1f}-{s.end_sec:.1f}] {s.text}" for s in segments)
    return TranscriptDocument(
        job_id=job_id,
        language=language,
        duration_sec=1823.5,
        segments=segments,
        full_text=full_text,
        model="faster-whisper-large-v3",
        processed_at=datetime.now(timezone.utc),
    )


def extract_highlights(transcript: TranscriptDocument, clip_count: int) -> HighlightResult:
    highlights = []
    base = [
        (1, 312.4, 367.1, "AI가 바꿀 미래 직업들", "기승전결이 명확하고 핵심 주장이 완결됨", ["surprising", "informative"], 0.94),
        (2, 820.0, 871.5, "인간만이 할 수 있는 것", "반론 구조가 좋아 몰입도가 높음", ["inspiring", "calm"], 0.88),
        (3, 1205.2, 1258.9, "관객 Q&A 반전 포인트", "웃음 포인트 + 결론이 선명함", ["funny", "energetic"], 0.85),
    ]
    for rank, start, end, title, reason, tags, score in base[:clip_count]:
        highlights.append(
            HighlightItem(
                rank=rank,
                start_sec=start,
                end_sec=end,
                title=title,
                summary=f"{title}에 대한 핵심 요약",
                highlight_reason=reason,
                emotion_tags=tags,
                score=score,
            )
        )
    return HighlightResult(
        job_id=transcript.job_id,
        model_used="llama3-70b-instruct",
        highlights=highlights,
        extracted_at=datetime.now(timezone.utc),
    )


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


def build_clip_result(job_id: str, item: HighlightItem, with_tts: bool, with_music: bool) -> ClipResult:
    clip_id = f"{job_id}_clip_{item.rank:03d}"
    assets = ClipAssets(
        video_url=f"https://cdn.example.com/clips/{clip_id}.mp4",
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
