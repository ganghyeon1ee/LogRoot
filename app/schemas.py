from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ContentType(str, Enum):
    lecture = "lecture"
    entertainment = "entertainment"
    vlog = "vlog"


class Language(str, Enum):
    ko = "ko"
    en = "en"
    ja = "ja"
    auto = "auto"


class TTSMode(str, Enum):
    voice_clone = "voice_clone"
    preset = "preset"
    disabled = "disabled"


class SubtitleStyle(str, Enum):
    dynamic = "dynamic"
    static = "static"
    disabled = "disabled"


class MusicMood(str, Enum):
    auto = "auto"
    energetic = "energetic"
    calm = "calm"
    funny = "funny"
    tense = "tense"


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    done = "done"
    failed = "failed"


class DurationRange(BaseModel):
    min_sec: int = Field(30, ge=10, le=300)
    max_sec: int = Field(60, ge=10, le=300)

    @field_validator("max_sec")
    @classmethod
    def validate_range(cls, v: int, info):
        min_sec = info.data.get("min_sec", 30)
        if v < min_sec:
            raise ValueError("max_sec must be greater than or equal to min_sec")
        return v


class JobOptions(BaseModel):
    clip_count: int = Field(3, ge=1, le=10)
    clip_duration_range: DurationRange = Field(default_factory=DurationRange)
    content_type: ContentType = ContentType.lecture
    language: Language = Language.ko
    tts_enabled: bool = True
    tts_mode: TTSMode = TTSMode.voice_clone
    tts_speed: float = Field(1.25, ge=0.75, le=1.5)
    subtitle_style: SubtitleStyle = SubtitleStyle.dynamic
    music_enabled: bool = True
    music_mood: MusicMood = MusicMood.auto
    webhook_url: HttpUrl | None = None


class JobLinks(BaseModel):
    self: str
    status: str
    clips: str


class JobAcceptedResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    estimated_duration_sec: int
    webhook_url: HttpUrl | None = None
    links: JobLinks = Field(alias="_links")


class ProgressStep(BaseModel):
    name: str
    status: str
    pct: int = Field(ge=0, le=100)


class Progress(BaseModel):
    current_step: str
    steps: list[ProgressStep]
    overall_pct: int = Field(ge=0, le=100)


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: Progress
    error: str | None = None


class ClipSegment(BaseModel):
    start_sec: float
    end_sec: float
    duration_sec: float


class ClipAssets(BaseModel):
    video_url: str
    thumbnail_url: str | None = None
    subtitle_url: str | None = None
    audio_url: str | None = None


class ClipMusic(BaseModel):
    track_id: str
    title: str
    mood: str
    bpm: int
    volume_db: int


class Clip(BaseModel):
    clip_id: str
    rank: int
    title: str
    score: float
    segment: ClipSegment
    highlight_reason: str
    emotion_tags: list[str]
    assets: ClipAssets
    music: ClipMusic | None = None
    created_at: datetime


class ClipsResponse(BaseModel):
    job_id: str
    clips: list[Clip]


class TranscriptWord(BaseModel):
    word: str
    start_sec: float
    end_sec: float
    confidence: float


class TranscriptSegment(BaseModel):
    seg_id: int
    start_sec: float
    end_sec: float
    text: str
    speaker: str | None = None
    words: list[TranscriptWord] = []


class TranscriptDocument(BaseModel):
    job_id: str
    language: str
    duration_sec: float
    segments: list[TranscriptSegment]
    full_text: str
    model: str
    processed_at: datetime


class HighlightItem(BaseModel):
    rank: int
    start_sec: float
    end_sec: float
    title: str
    summary: str
    highlight_reason: str
    emotion_tags: list[str]
    score: float


class HighlightResult(BaseModel):
    job_id: str
    model_used: str
    highlights: list[HighlightItem]
    extracted_at: datetime


class TTSRequest(BaseModel):
    clip_id: str
    mode: TTSMode
    reference_audio_url: str | None = None
    text: str
    speed: float = 1.25
    model: str = "xtts-v2"
    language: str = "ko"


class TTSResponse(BaseModel):
    clip_id: str
    audio_url: str
    duration_sec: float
    sample_rate: int
    model_used: str


class MusicMatchRequest(BaseModel):
    clip_id: str
    emotion_tags: list[str]
    content_type: ContentType
    clip_duration_sec: float
    mood_override: MusicMood | None = None


class MatchedTrack(BaseModel):
    track_id: str
    title: str
    source: str
    license: str
    bpm: int
    mood_tags: list[str]
    similarity_score: float
    url: str


class MusicMixConfig(BaseModel):
    fade_in_sec: float = 1.0
    fade_out_sec: float = 1.5
    volume_db: int = -18
    ducking_enabled: bool = True
    duck_db: int = -12


class MusicMatchResponse(BaseModel):
    clip_id: str
    matched_tracks: list[MatchedTrack]
    selected_track_id: str
    mix_config: MusicMixConfig


class StoredJob(BaseModel):
    job_id: str
    created_at: datetime
    status: JobStatus
    options: JobOptions
    progress: Progress
    clips: list[Clip] = []
    error: str | None = None
    artifacts: dict[str, Any] = {}
