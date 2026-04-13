# Short-form AI Pipeline API

롱폼 영상을 업로드하면 STT → 하이라이트 추출 → 편집/TTS/음악 매칭까지 이어지는 숏폼 자동 생성 파이프라인의 MVP 백엔드입니다.

## 주요 기능
- `POST /api/v1/jobs`: 영상 업로드 + 옵션으로 Job 생성
- `GET /api/v1/jobs/{job_id}/status`: 파이프라인 단계별 진행률 조회
- `GET /api/v1/jobs/{job_id}/clips`: 최종 클립 메타데이터 조회
- Celery Task 엔트리포인트(`tasks.py`) 제공
- 내부 모듈 스키마(`TranscriptDocument`, `HighlightResult`, `TTS`, `MusicMatcher`)를 Pydantic으로 명시

## 실행
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

## 테스트
```bash
python -m pytest -q
```

## Celery 사용 (선택)
기본값은 FastAPI `BackgroundTasks`로 동작합니다.

```bash
# 1) Redis 실행
# 2) Celery 워커 실행
python -m celery -A tasks.celery_app worker -l info

# 3) API 실행 전 환경변수 설정
export USE_CELERY=1
python -m uvicorn app.main:app --reload
```

## 문제 해결
- `ModuleNotFoundError`가 나면 현재 쉘의 파이썬/uvicorn이 같은 venv를 가리키는지 확인하세요.
- 특히 `uvicorn app.main:app` 대신 `python -m uvicorn app.main:app --reload`를 권장합니다.
- Celery가 설치되지 않았거나 비활성이어도 API는 정상 기동되도록 fallback 처리되어 있습니다.
