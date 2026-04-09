from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CreateShortformJobRequest:
    video_path: str
    output_dir: str
    num_highlights: int = 3
    max_clip_duration: int = 60
    speaker_reference_wav: str | None = None


@dataclass(slots=True)
class CreateMusicIngestionRequest:
    source_url: str
    title: str | None = None
    top_k: int = 5
