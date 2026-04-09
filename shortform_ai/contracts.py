from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class WordTimestamp:
    word: str
    start_sec: float
    end_sec: float


@dataclass(slots=True)
class TranscriptSegment:
    start_sec: float
    end_sec: float
    text: str
    speaker: str | None = None
    words: list[WordTimestamp] = field(default_factory=list)


@dataclass(slots=True)
class HighlightClip:
    rank: int
    start_sec: float
    end_sec: float
    title: str
    reason: str
    hook: str
    platform_tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SubtitleCue:
    index: int
    start_sec: float
    end_sec: float
    text: str


@dataclass(slots=True)
class MusicRecommendation:
    track_id: str
    title: str
    mood_tags: list[str]
    score: float
    s3_uri: str | None = None


@dataclass(slots=True)
class RenderedClip:
    highlight: HighlightClip
    video_path: str
    subtitle_path: str | None = None
    voiceover_path: str | None = None
    background_music_track_id: str | None = None


@dataclass(slots=True)
class ShortformJobResult:
    source_video_path: str
    transcript_segments: list[TranscriptSegment]
    highlights: list[HighlightClip]
    rendered_clips: list[RenderedClip]
    created_at: datetime = field(default_factory=datetime.utcnow)
