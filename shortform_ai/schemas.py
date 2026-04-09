from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class TagScore:
    label: str
    score: float


@dataclass(slots=True)
class MusicAsset:
    source_url: str
    local_path: str
    sha256: str
    title: str
    tags: list[TagScore]
    extra: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
