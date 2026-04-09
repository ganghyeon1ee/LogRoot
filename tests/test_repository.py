from shortform_ai.schemas import MusicAsset, TagScore
from shortform_ai.storage import SQLiteMusicRepository


def test_sqlite_repository_upsert(tmp_path):
    db_path = tmp_path / "test.db"
    repo = SQLiteMusicRepository(str(db_path))

    asset = MusicAsset(
        source_url="https://example.com/a.mp3",
        local_path="downloads/a.mp3",
        sha256="abc123",
        title="a",
        tags=[TagScore(label="calm music", score=0.8)],
    )

    row_id = repo.upsert(asset)
    assert isinstance(row_id, int)

    # 동일 sha256 upsert 확인
    asset.tags = [TagScore(label="energetic music", score=0.9)]
    repo.upsert(asset)
