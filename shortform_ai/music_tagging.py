from __future__ import annotations

import os
from typing import Sequence

from .schemas import TagScore


DEFAULT_LABELS = [
    "happy music",
    "sad music",
    "calm music",
    "relaxing music",
    "romantic music",
    "energetic music",
    "exciting music",
    "upbeat music",
    "dark music",
    "melancholic music",
    "dramatic music",
    "cinematic music",
    "cute music",
    "dreamy music",
    "peaceful music",
    "warm music",
    "emotional music",
    "mysterious music",
    "tense music",
    "epic music",
]


class ClapMusicMoodTagger:
    """LAION-CLAP 기반 음악 분위기 태거.

    의존성(torch, laion_clap)이 설치된 환경에서만 동작한다.
    """

    def __init__(self, labels: Sequence[str] | None = None, device: str | None = None):
        self.labels = list(labels or DEFAULT_LABELS)

        try:
            import torch
            import laion_clap
        except ImportError as exc:
            raise RuntimeError(
                "ClapMusicMoodTagger requires `torch` and `laion_clap`. "
                "Install them before running this pipeline."
            ) from exc

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self._torch = torch
        self.device = device
        self.model = laion_clap.CLAP_Module(enable_fusion=False, device=device)
        self.model.load_ckpt()

        with torch.no_grad():
            text_emb = self.model.get_text_embedding(self.labels)
            self.text_emb = self._to_tensor(text_emb).to(self.device)
            self.text_emb = torch.nn.functional.normalize(self.text_emb, dim=-1)

    def _to_tensor(self, x):
        if isinstance(x, self._torch.Tensor):
            return x
        return self._torch.tensor(x, dtype=self._torch.float32)

    def tag_audio(self, audio_path: str, top_k: int = 5) -> list[TagScore]:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Cannot find audio file: {audio_path}")

        with self._torch.no_grad():
            audio_emb = self.model.get_audio_embedding_from_filelist([audio_path], use_tensor=True)
            audio_emb = self._to_tensor(audio_emb).to(self.device)
            audio_emb = self._torch.nn.functional.normalize(audio_emb, dim=-1)

            scores = (audio_emb @ self.text_emb.T).squeeze(0)
            top_k = min(top_k, len(self.labels))
            values, indices = self._torch.topk(scores, k=top_k)

        return [
            TagScore(label=self.labels[idx], score=float(score))
            for score, idx in zip(values.tolist(), indices.tolist())
        ]
