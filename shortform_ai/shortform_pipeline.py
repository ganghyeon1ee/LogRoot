from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Protocol

from .contracts import (
    HighlightClip,
    MusicRecommendation,
    RenderedClip,
    ShortformJobResult,
    SubtitleCue,
    TranscriptSegment,
)


class Transcriber(Protocol):
    def transcribe(self, video_path: str) -> list[TranscriptSegment]: ...


class Highlighter(Protocol):
    def extract_highlights(self, segments: list[TranscriptSegment], max_clips: int, max_duration: int) -> list[HighlightClip]: ...


class SubtitleGenerator(Protocol):
    def generate(self, segments: list[TranscriptSegment], highlight: HighlightClip) -> list[SubtitleCue]: ...


class VoiceSynthesizer(Protocol):
    def synthesize(self, text: str, output_path: str, speaker_wav: str | None = None, language: str = "ko") -> str: ...


class MusicRecommender(Protocol):
    def recommend(self, highlight: HighlightClip, top_k: int = 1) -> list[MusicRecommendation]: ...


class ClipRenderer(Protocol):
    def render(
        self,
        video_path: str,
        highlight: HighlightClip,
        subtitle_cues: list[SubtitleCue],
        output_path: str,
        voiceover_path: str | None = None,
        background_music_uri: str | None = None,
    ) -> str: ...


class ShortformGenerationPipeline:
    """롱폼 입력으로 숏폼 클립을 자동 생성하는 오케스트레이터."""

    def __init__(
        self,
        transcriber: Transcriber,
        highlighter: Highlighter,
        subtitle_generator: SubtitleGenerator,
        renderer: ClipRenderer,
        voice_synthesizer: VoiceSynthesizer | None = None,
        music_recommender: MusicRecommender | None = None,
    ):
        self.transcriber = transcriber
        self.highlighter = highlighter
        self.subtitle_generator = subtitle_generator
        self.renderer = renderer
        self.voice_synthesizer = voice_synthesizer
        self.music_recommender = music_recommender

    def run(
        self,
        video_path: str,
        output_dir: str,
        num_highlights: int = 3,
        max_clip_duration: int = 60,
        speaker_reference_wav: str | None = None,
    ) -> ShortformJobResult:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        segments = self.transcriber.transcribe(video_path)
        highlights = self.highlighter.extract_highlights(
            segments=segments,
            max_clips=num_highlights,
            max_duration=max_clip_duration,
        )

        rendered_clips: list[RenderedClip] = []

        for highlight in highlights:
            subtitle_cues = self.subtitle_generator.generate(segments, highlight)

            voiceover_path = None
            if self.voice_synthesizer:
                voiceover_text = f"{highlight.title}. {highlight.hook}"
                voiceover_path = str(Path(output_dir) / f"voiceover_{highlight.rank:02d}.wav")
                voiceover_path = self.voice_synthesizer.synthesize(
                    text=voiceover_text,
                    output_path=voiceover_path,
                    speaker_wav=speaker_reference_wav,
                )

            background_music_track_id = None
            background_music_uri = None
            if self.music_recommender:
                recommendations = self.music_recommender.recommend(highlight, top_k=1)
                if recommendations:
                    background_music_track_id = recommendations[0].track_id
                    background_music_uri = recommendations[0].s3_uri

            clip_path = str(Path(output_dir) / f"highlight_{highlight.rank:02d}.mp4")
            clip_path = self.renderer.render(
                video_path=video_path,
                highlight=highlight,
                subtitle_cues=subtitle_cues,
                output_path=clip_path,
                voiceover_path=voiceover_path,
                background_music_uri=background_music_uri,
            )

            rendered_clips.append(
                RenderedClip(
                    highlight=highlight,
                    video_path=clip_path,
                    subtitle_path=str(Path(output_dir) / f"subtitle_{highlight.rank:02d}.srt"),
                    voiceover_path=voiceover_path,
                    background_music_track_id=background_music_track_id,
                )
            )

        return ShortformJobResult(
            source_video_path=video_path,
            transcript_segments=segments,
            highlights=highlights,
            rendered_clips=rendered_clips,
        )

    @staticmethod
    def to_api_payload(result: ShortformJobResult) -> dict:
        payload = asdict(result)
        payload["created_at"] = result.created_at.isoformat()
        return payload
