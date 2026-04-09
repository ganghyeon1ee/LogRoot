from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .schemas import MusicAsset


class SQLiteMusicRepository:
    """음원 메타데이터 저장소.

    FE/BE 서비스 연동 시에는 동일 스키마를 ORM 모델로 이관할 수 있다.
    """

    def __init__(self, db_path: str = "music_assets.db"):
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS music_assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_url TEXT NOT NULL,
                    local_path TEXT NOT NULL,
                    sha256 TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    extra_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def upsert(self, asset: MusicAsset) -> int:
        tags_json = json.dumps([{"label": t.label, "score": t.score} for t in asset.tags], ensure_ascii=False)
        extra_json = json.dumps(asset.extra, ensure_ascii=False)

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO music_assets (source_url, local_path, sha256, title, tags_json, extra_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(sha256) DO UPDATE SET
                    source_url=excluded.source_url,
                    local_path=excluded.local_path,
                    title=excluded.title,
                    tags_json=excluded.tags_json,
                    extra_json=excluded.extra_json
                """,
                (
                    asset.source_url,
                    asset.local_path,
                    asset.sha256,
                    asset.title,
                    tags_json,
                    extra_json,
                    asset.created_at.isoformat(),
                ),
            )
            return cursor.lastrowid


class S3Uploader:
    def __init__(self, bucket: str, prefix: str = "music"):
        self.bucket = bucket
        self.prefix = prefix.strip("/")

        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("S3Uploader requires `boto3`.") from exc

        self._client = boto3.client("s3")

    def upload_file(self, local_path: str, sha256: str) -> str:
        ext = Path(local_path).suffix
        key = f"{self.prefix}/{sha256}{ext}"
        self._client.upload_file(local_path, self.bucket, key)
        return f"s3://{self.bucket}/{key}"
