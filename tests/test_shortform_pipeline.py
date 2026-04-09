from shortform_ai.contracts import HighlightClip, SubtitleCue, TranscriptSegment
from shortform_ai.shortform_pipeline import ShortformGenerationPipeline


class FakeTranscriber:
    def transcribe(self, video_path: str):
        assert video_path.endswith(".mp4")
        return [
            TranscriptSegment(start_sec=0, end_sec=12, text="오프닝입니다"),
            TranscriptSegment(start_sec=12, end_sec=40, text="핵심 주장입니다"),
        ]


class FakeHighlighter:
    def extract_highlights(self, segments, max_clips: int, max_duration: int):
        del segments
        del max_duration
        return [
            HighlightClip(
                rank=1,
                start_sec=0,
                end_sec=30,
                title="클립1",
                reason="테스트",
                hook="핵심 훅",
                platform_tags=["#shorts"],
            )
        ][:max_clips]


class FakeSubtitleGenerator:
    def generate(self, segments, highlight):
        del segments
        return [SubtitleCue(index=1, start_sec=0, end_sec=2, text=highlight.hook)]


class FakeRenderer:
    def render(self, video_path, highlight, subtitle_cues, output_path, voiceover_path=None, background_music_uri=None):
        del video_path
        del highlight
        del subtitle_cues
        del voiceover_path
        del background_music_uri
        return output_path


class FakeVoice:
    def synthesize(self, text, output_path, speaker_wav=None, language="ko"):
        del text
        del speaker_wav
        del language
        return output_path


class FakeMusic:
    def recommend(self, highlight, top_k=1):
        del highlight
        del top_k
        return []


def test_shortform_pipeline_payload(tmp_path):
    pipeline = ShortformGenerationPipeline(
        transcriber=FakeTranscriber(),
        highlighter=FakeHighlighter(),
        subtitle_generator=FakeSubtitleGenerator(),
        renderer=FakeRenderer(),
        voice_synthesizer=FakeVoice(),
        music_recommender=FakeMusic(),
    )

    result = pipeline.run(video_path="sample.mp4", output_dir=str(tmp_path))
    payload = ShortformGenerationPipeline.to_api_payload(result)

    assert payload["source_video_path"] == "sample.mp4"
    assert len(payload["highlights"]) == 1
    assert payload["rendered_clips"][0]["video_path"].endswith("highlight_01.mp4")
