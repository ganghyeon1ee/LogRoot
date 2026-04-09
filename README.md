# shortform-ai-music-pipeline

롱폼(강연/예능/브이로그) → 숏폼 자동 생성 서비스를 위한 **AI 파이프라인 백엔드 골격**입니다.

## 구현 범위

### A. 숏폼 생성 파이프라인
1. WhisperX 기반 STT + 단어 타임스탬프
2. 하이라이트(30~60초) 추출
3. 자막 생성
4. AI 음성 합성(XTTS v2)
5. 클립 렌더링(ffmpeg)

### B. 음원 태깅 파이프라인
1. 무료 음원 다운로드
2. LAION-CLAP 분위기 태깅
3. SQLite 저장
4. 선택적 S3 업로드

---

## 디렉터리 구조

- `shortform_ai/contracts.py`: 파이프라인 공통 데이터 계약 (FE/BE 연동용)
- `shortform_ai/shortform_pipeline.py`: 숏폼 생성 오케스트레이터
- `shortform_ai/providers.py`: WhisperX/Groq/XTTS/ffmpeg 등 Provider 구현체
- `shortform_ai/music_tagging.py`: CLAP 기반 분위기 태깅
- `shortform_ai/pipeline.py`: 음원 다운로드+태깅+저장 오케스트레이터
- `shortform_ai/storage.py`: SQLite/S3 저장소
- `shortform_ai/cli.py`: CLI 실행 진입점

---

## 실행 예시

### 1) 음원 수집 + 태깅
```bash
python -m shortform_ai.cli ingest-music "https://example.com/sample.mp3" --title "sample"
```

### 2) 숏폼 생성
```bash
python -m shortform_ai.cli make-shortform /path/to/video.mp4 --output-dir outputs --num-highlights 3
```

> 기본 하이라이터는 `RuleBasedHighlighter` 입니다. 운영에서는 `GroqHighlighter` 같은 LLM 구현체로 교체하세요.

---

## FE/BE 연동 포인트

- `ShortformGenerationPipeline.to_api_payload()`
- `MusicIngestionPipeline.to_api_payload()`

두 함수 결과를 API 응답/이벤트 payload로 바로 전달 가능하도록 dataclass 기반 JSON 구조로 맞췄습니다.

---

## 운영 체크리스트

- API 키 하드코딩 금지 (환경변수 사용)
- 저작권/라이선스 검증 로직 추가
- 큐 기반 비동기 처리(Celery/SQS/Kafka)
- ffmpeg/WhisperX/TTS 실패 재시도 및 DLQ 추가
- S3 업로드 전 중복/품질 필터링

---

## 의존성

- 필수(기본 테스트): Python 3.10+
- 선택(기능별):
  - STT: `whisperx`, `torch`
  - 하이라이트 LLM: `groq` 또는 `transformers`
  - TTS: `TTS`, `torch`
  - 음악 태깅: `laion_clap`, `torch`
  - 렌더링: 시스템 `ffmpeg`
  - 저장소: `boto3` (S3 사용 시)
