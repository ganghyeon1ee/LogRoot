from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


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


class ClipDurationRange(BaseModel):
    min_sec: int = Field(default=30, ge=5, le=120)
    max_sec: int = Field(default=60, ge=5, le=180)


class JobOptions(BaseModel):
    clip_count: int = Field(default=3, ge=1, le=10)
    clip_duration_range: ClipDurationRange = Field(default_factory=ClipDurationRange)
    content_type: ContentType = ContentType.lecture
    language: Language = Language.ko
    tts_enabled: bool = True
    tts_mode: TTSMode = TTSMode.voice_clone
    tts_speed: float = Field(default=1.25, ge=0.8, le=1.5)
    subtitle_style: SubtitleStyle = SubtitleStyle.dynamic
    music_enabled: bool = True
    music_mood: MusicMood = MusicMood.auto
    webhook_url: str | None = None


class StepStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    failed = "failed"


class PipelineStep(BaseModel):
    name: str
    status: StepStatus
    pct: int = Field(ge=0, le=100)


class JobProgress(BaseModel):
    current_step: str
    steps: list[PipelineStep]
    overall_pct: int = Field(ge=0, le=100)


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    done = "done"
    failed = "failed"


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    estimated_duration_sec: int
    webhook_url: str | None = None
    links: dict[str, str] = Field(alias="_links")


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: JobProgress
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


class MusicInfo(BaseModel):
    track_id: str
    title: str
    mood: str
    bpm: int
    volume_db: int


class ClipResult(BaseModel):
    clip_id: str
    rank: int
    title: str
    score: float
    segment: ClipSegment
    highlight_reason: str
    emotion_tags: list[str]
    assets: ClipAssets
    music: MusicInfo | None = None
    created_at: datetime


class ClipsResponse(BaseModel):
    job_id: str
    clips: list[ClipResult]


# ===== Internal module schemas =====
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
    words: list[TranscriptWord] = Field(default_factory=list)


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
    speed: float
    model: str
    language: str


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
    mood_override: str | None = None


class MatchedTrack(BaseModel):
    track_id: str
    title: str
    source: str
    license: str
    bpm: int
    mood_tags: list[str]
    similarity_score: float
    url: str


class MixConfig(BaseModel):
    fade_in_sec: float
    fade_out_sec: float
    volume_db: int
    ducking_enabled: bool
    duck_db: int


class MusicMatchResponse(BaseModel):
    clip_id: str
    matched_tracks: list[MatchedTrack]
    selected_track_id: str
    mix_config: MixConfig


class JobRecord(BaseModel):
    job_id: str
    created_at: datetime
    status: JobStatus
    options: JobOptions
    file_path: str
    progress: JobProgress
    clips: list[ClipResult] = Field(default_factory=list)
    error: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
