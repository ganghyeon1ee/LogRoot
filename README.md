# Short-form AI Pipeline (MVP)

롱폼 영상을 업로드하면 STT → 하이라이트 추출 → 클립 패키징까지 자동으로 처리하는 FastAPI + Celery 기반 MVP입니다.

## 포함 기능

- `POST /api/v1/jobs`: 업로드 + 옵션 입력으로 Job 생성
- `GET /api/v1/jobs/{job_id}/status`: 단계별 진행률 조회
- `GET /api/v1/jobs/{job_id}/clips`: 완료된 클립 목록 조회
- 내부 스키마:
  - TranscriptDocument
  - HighlightResult
  - TTS Request/Response
  - Music Matcher Request/Response

## 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Celery 워커(선택):

```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

> Redis/Celery가 없으면 API 서버가 동기 파이프라인으로 자동 폴백합니다.

## 샘플 요청

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/jobs" \
  -F 'file=@sample.mp4' \
  -F 'options={"clip_count":3,"clip_duration_range":{"min_sec":30,"max_sec":60},"content_type":"lecture","language":"ko","tts_enabled":true,"tts_mode":"voice_clone","tts_speed":1.25,"subtitle_style":"dynamic","music_enabled":true,"music_mood":"auto"}'
```
