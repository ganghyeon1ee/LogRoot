from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from .contracts import HighlightClip, MusicRecommendation, SubtitleCue, TranscriptSegment, WordTimestamp


class WhisperXTranscriber:
    def __init__(self, model_name: str = "medium", language: str = "ko", batch_size: int = 16, compute_type: str = "float16"):
        self.model_name = model_name
        self.language = language
        self.batch_size = batch_size
        self.compute_type = compute_type

    def transcribe(self, video_path: str) -> list[TranscriptSegment]:
        try:
            import torch
            import whisperx
        except ImportError as exc:
            raise RuntimeError("WhisperXTranscriber requires `whisperx` and `torch`.") from exc

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = whisperx.load_model(self.model_name, device, compute_type=self.compute_type, language=self.language)
        audio = whisperx.load_audio(video_path)
        raw = model.transcribe(audio, batch_size=self.batch_size)

        align_model, metadata = whisperx.load_align_model(language_code=raw.get("language", self.language), device=device)
        aligned = whisperx.align(raw["segments"], align_model, metadata, audio, device, return_char_alignments=False)

        parsed: list[TranscriptSegment] = []
        for seg in aligned["segments"]:
            words = [
                WordTimestamp(word=w.get("word", ""), start_sec=float(w.get("start", 0)), end_sec=float(w.get("end", 0)))
                for w in seg.get("words", [])
            ]
            parsed.append(
                TranscriptSegment(
                    start_sec=float(seg.get("start", 0)),
                    end_sec=float(seg.get("end", 0)),
                    text=seg.get("text", "").strip(),
                    speaker=seg.get("speaker"),
                    words=words,
                )
            )
        return parsed


class GroqHighlighter:
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model = model

    def extract_highlights(self, segments: list[TranscriptSegment], max_clips: int, max_duration: int) -> list[HighlightClip]:
        try:
            from groq import Groq
        except ImportError as exc:
            raise RuntimeError("GroqHighlighter requires `groq` package.") from exc

        transcript = "\n".join(f"[{int(s.start_sec//60):02d}:{int(s.start_sec%60):02d}] {s.text}" for s in segments[:4000])
        prompt = f"""다음 전사에서 {max_clips}개 하이라이트를 JSON으로 추출해줘.
각 클립은 {max_duration}초 이하.
반드시 {{\"highlights\": [...]}} JSON만 출력.
전사:\n{transcript}"""

        client = Groq(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1400,
        )
        raw = response.choices[0].message.content
        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            raise ValueError(f"Invalid highlight response: {raw[:200]}")
        data = json.loads(match.group())

        highlights: list[HighlightClip] = []
        for idx, item in enumerate(data.get("highlights", [])[:max_clips], start=1):
            highlights.append(
                HighlightClip(
                    rank=int(item.get("rank", idx)),
                    start_sec=float(item["start_sec"]),
                    end_sec=float(item["end_sec"]),
                    title=str(item.get("title", f"clip_{idx}")),
                    reason=str(item.get("reason", "핵심 구간")),
                    hook=str(item.get("hook", "")),
                    platform_tags=list(item.get("platform_tags", [])),
                )
            )
        return highlights


class RuleBasedHighlighter:
    """테스트/로컬 개발용 경량 하이라이터."""

    def extract_highlights(self, segments: list[TranscriptSegment], max_clips: int, max_duration: int) -> list[HighlightClip]:
        highlights: list[HighlightClip] = []
        for idx, seg in enumerate(segments[:max_clips], start=1):
            end_sec = min(seg.end_sec, seg.start_sec + max_duration)
            highlights.append(
                HighlightClip(
                    rank=idx,
                    start_sec=seg.start_sec,
                    end_sec=end_sec,
                    title=f"핵심구간 {idx}",
                    reason="초기 프로토타입 기본 규칙 추출",
                    hook=seg.text[:50],
                    platform_tags=["#shorts", "#ai"],
                )
            )
        return highlights


class SegmentSubtitleGenerator:
    def generate(self, segments: list[TranscriptSegment], highlight: HighlightClip) -> list[SubtitleCue]:
        cues: list[SubtitleCue] = []
        idx = 1
        for seg in segments:
            if seg.end_sec < highlight.start_sec or seg.start_sec > highlight.end_sec:
                continue
            cues.append(
                SubtitleCue(
                    index=idx,
                    start_sec=max(0, seg.start_sec - highlight.start_sec),
                    end_sec=max(0, seg.end_sec - highlight.start_sec),
                    text=seg.text,
                )
            )
            idx += 1
        return cues


class XTTSVoiceSynthesizer:
    def __init__(self, model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2"):
        self.model_name = model_name

    def synthesize(self, text: str, output_path: str, speaker_wav: str | None = None, language: str = "ko") -> str:
        try:
            import torch
            from TTS.api import TTS
        except ImportError as exc:
            raise RuntimeError("XTTSVoiceSynthesizer requires `TTS` and `torch`.") from exc

        device = "cuda" if torch.cuda.is_available() else "cpu"
        tts = TTS(self.model_name).to(device)
        kwargs = {"text": text, "language": language, "file_path": output_path}
        if speaker_wav:
            kwargs["speaker_wav"] = speaker_wav
        tts.tts_to_file(**kwargs)
        return output_path


class NoopMusicRecommender:
    def recommend(self, highlight: HighlightClip, top_k: int = 1) -> list[MusicRecommendation]:
        del highlight
        del top_k
        return []


class FFmpegClipRenderer:
    def __init__(self, vertical: bool = True):
        self.vertical = vertical

    def render(
        self,
        video_path: str,
        highlight: HighlightClip,
        subtitle_cues: list[SubtitleCue],
        output_path: str,
        voiceover_path: str | None = None,
        background_music_uri: str | None = None,
    ) -> str:
        out_dir = Path(output_path).parent
        out_dir.mkdir(parents=True, exist_ok=True)

        srt_path = out_dir / f"subtitle_{highlight.rank:02d}.srt"
        self._write_srt(subtitle_cues, str(srt_path))

        vf = [f"subtitles={srt_path}"]
        if self.vertical:
            vf.insert(0, "scale=iw*min(1920/iw\\,1080/ih):ih*min(1920/iw\\,1080/ih),crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920")

        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            str(highlight.start_sec),
            "-i",
            video_path,
            "-t",
            str(max(0.1, highlight.end_sec - highlight.start_sec)),
        ]

        if voiceover_path:
            cmd += ["-i", voiceover_path]

        if background_music_uri:
            # s3:// URI 는 런타임에서 로컬 다운로드 후 경로로 넣어야 함.
            pass

        cmd += ["-vf", ",".join(vf), "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac", output_path]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg render failed: {result.stderr[-500:]}")

        return output_path

    @staticmethod
    def _write_srt(cues: list[SubtitleCue], path: str) -> None:
        def fmt(sec: float) -> str:
            h = int(sec // 3600)
            m = int((sec % 3600) // 60)
            s = int(sec % 60)
            ms = int((sec % 1) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

        lines: list[str] = []
        for c in cues:
            lines.extend([str(c.index), f"{fmt(c.start_sec)} --> {fmt(c.end_sec)}", c.text, ""])

        Path(path).write_text("\n".join(lines), encoding="utf-8")
