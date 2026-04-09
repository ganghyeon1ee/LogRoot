from __future__ import annotations

import argparse
import json

from .music_tagging import ClapMusicMoodTagger
from .pipeline import MusicIngestionPipeline
from .storage import S3Uploader, SQLiteMusicRepository


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Ingest free music and auto-tag mood.")
    p.add_argument("url", help="Direct downloadable audio URL")
    p.add_argument("--title", default=None)
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--db-path", default="music_assets.db")
    p.add_argument("--s3-bucket", default=None)
    p.add_argument("--s3-prefix", default="music")
    return p


def main() -> None:
    args = build_parser().parse_args()

    tagger = ClapMusicMoodTagger()
    repo = SQLiteMusicRepository(db_path=args.db_path)
    uploader = S3Uploader(bucket=args.s3_bucket, prefix=args.s3_prefix) if args.s3_bucket else None

    pipeline = MusicIngestionPipeline(tagger=tagger, repository=repo, uploader=uploader)
    asset = pipeline.process_url(source_url=args.url, title=args.title, top_k=args.top_k)

    print(json.dumps(MusicIngestionPipeline.to_api_payload(asset), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
