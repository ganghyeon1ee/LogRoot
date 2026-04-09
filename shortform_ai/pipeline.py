from __future__ import annotations

from dataclasses import asdict

from .downloader import download_audio, sha256_file
from .schemas import MusicAsset
from .storage import SQLiteMusicRepository, S3Uploader


class MusicIngestionPipeline:
    """무료 음원 수집 -> AI 태깅 -> DB/S3 저장 파이프라인."""

    def __init__(self, tagger, repository: SQLiteMusicRepository, uploader: S3Uploader | None = None):
        self.tagger = tagger
        self.repository = repository
        self.uploader = uploader

    def process_url(self, source_url: str, title: str | None = None, top_k: int = 5) -> MusicAsset:
        local_path = download_audio(source_url)
        sha256 = sha256_file(local_path)

        tags = self.tagger.tag_audio(local_path, top_k=top_k)
        extra: dict[str, object] = {}
        if self.uploader:
            extra["s3_uri"] = self.uploader.upload_file(local_path, sha256)

        asset = MusicAsset(
            source_url=source_url,
            local_path=local_path,
            sha256=sha256,
            title=title or source_url.rsplit("/", 1)[-1],
            tags=tags,
            extra=extra,
        )

        self.repository.upsert(asset)
        return asset

    @staticmethod
    def to_api_payload(asset: MusicAsset) -> dict:
        payload = asdict(asset)
        payload["created_at"] = asset.created_at.isoformat()
        return payload
