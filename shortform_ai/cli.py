from __future__ import annotations

import argparse
import json
import os

from .music_tagging import ClapMusicMoodTagger
from .pipeline import MusicIngestionPipeline
from .providers import (
    FFmpegClipRenderer,
    NoopMusicRecommender,
    RuleBasedHighlighter,
    SegmentSubtitleGenerator,
    WhisperXTranscriber,
    XTTSVoiceSynthesizer,
)
from .shortform_pipeline import ShortformGenerationPipeline
from .storage import S3Uploader, SQLiteMusicRepository


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Shortform AI pipelines")
    sub = p.add_subparsers(dest="command", required=True)

    music = sub.add_parser("ingest-music", help="Download free music and auto-tag mood")
    music.add_argument("url", help="Direct downloadable audio URL")
    music.add_argument("--title", default=None)
    music.add_argument("--top-k", type=int, default=5)
    music.add_argument("--db-path", default="music_assets.db")
    music.add_argument("--s3-bucket", default=None)
    music.add_argument("--s3-prefix", default="music")

    shortform = sub.add_parser("make-shortform", help="Generate shortform clips from longform video")
    shortform.add_argument("video_path")
    shortform.add_argument("--output-dir", default="outputs")
    shortform.add_argument("--num-highlights", type=int, default=3)
    shortform.add_argument("--max-clip-duration", type=int, default=60)
    shortform.add_argument("--speaker-reference-wav", default=None)
    shortform.add_argument("--disable-tts", action="store_true")
    shortform.add_argument("--whisperx-model", default="medium")

    return p


def run_music_ingestion(args: argparse.Namespace) -> dict:
    tagger = ClapMusicMoodTagger()
    repo = SQLiteMusicRepository(db_path=args.db_path)
    uploader = S3Uploader(bucket=args.s3_bucket, prefix=args.s3_prefix) if args.s3_bucket else None

    pipeline = MusicIngestionPipeline(tagger=tagger, repository=repo, uploader=uploader)
    asset = pipeline.process_url(source_url=args.url, title=args.title, top_k=args.top_k)
    return MusicIngestionPipeline.to_api_payload(asset)


def run_shortform(args: argparse.Namespace) -> dict:
    if not os.path.exists(args.video_path):
        raise FileNotFoundError(f"Cannot find video: {args.video_path}")

    transcriber = WhisperXTranscriber(model_name=args.whisperx_model)
    highlighter = RuleBasedHighlighter()  # 운영 환경에서는 LLM 하이라이터(Groq 등)로 교체
    subtitle_generator = SegmentSubtitleGenerator()
    renderer = FFmpegClipRenderer(vertical=True)
    voice_synthesizer = None if args.disable_tts else XTTSVoiceSynthesizer()

    pipeline = ShortformGenerationPipeline(
        transcriber=transcriber,
        highlighter=highlighter,
        subtitle_generator=subtitle_generator,
        renderer=renderer,
        voice_synthesizer=voice_synthesizer,
        music_recommender=NoopMusicRecommender(),
    )

    result = pipeline.run(
        video_path=args.video_path,
        output_dir=args.output_dir,
        num_highlights=args.num_highlights,
        max_clip_duration=args.max_clip_duration,
        speaker_reference_wav=args.speaker_reference_wav,
    )

    return ShortformGenerationPipeline.to_api_payload(result)


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "ingest-music":
        payload = run_music_ingestion(args)
    elif args.command == "make-shortform":
        payload = run_shortform(args)
    else:
        raise ValueError(f"Unsupported command: {args.command}")

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
