# Short-form AI Service — BE 전달용 API/파이프라인 명세

> 문서 목적: 프론트/백엔드/ML 간 공통 계약(Contract) 정리

---

## 1) 시스템 개요

롱폼 영상(강연/예능/브이로그)을 입력받아 아래 파이프라인으로 숏폼 클립 N개를 생성한다.

1. 영상 업로드 + Job 생성
2. STT(전사)
3. 하이라이트 추출
4. 비디오 편집
5. TTS(선택)
6. 자막 생성(선택)
7. 음악 매칭(선택)
8. 패키징 + 결과 반환

---

## 2) 공통 규칙

- Base URL: `/api/v1`
- Content-Type:
  - 파일 업로드: `multipart/form-data`
  - 일반 조회: `application/json`
- 시간 표기: ISO-8601 UTC (`2026-04-13T02:23:48.299154Z`)
- Job 상태: `queued | processing | done | failed`
- Pipeline step 상태: `pending | processing | done | failed`

---

## 3) API 명세

## 3.1 Job 생성

### `POST /api/v1/jobs`

#### Request (multipart)
- `file`: 영상 파일 (필수)
- `options`: JSON string (필수)

```json
{
  "clip_count": 3,
  "clip_duration_range": { "min_sec": 30, "max_sec": 60 },
  "content_type": "lecture",
  "language": "ko",
  "tts_enabled": true,
  "tts_mode": "voice_clone",
  "tts_speed": 1.25,
  "subtitle_style": "dynamic",
  "music_enabled": true,
  "music_mood": "auto",
  "webhook_url": null
}
```

> 하위호환: `music_ mood` 키가 들어오면 서버에서 `music_mood`로 정규화 처리.

#### Response `202 Accepted`

```json
{
  "job_id": "job_e65b744b",
  "status": "queued",
  "created_at": "2026-04-13T02:23:48.299154Z",
  "estimated_duration_sec": 180,
  "webhook_url": null,
  "_links": {
    "self": "/api/v1/jobs/job_e65b744b",
    "status": "/api/v1/jobs/job_e65b744b/status",
    "clips": "/api/v1/jobs/job_e65b744b/clips"
  }
}
```

#### Error
- `400`: options JSON 파싱/스키마 검증 실패

---

## 3.2 Job 상태 조회

### `GET /api/v1/jobs/{job_id}/status`

#### Response `200 OK`

```json
{
  "job_id": "job_e65b744b",
  "status": "processing",
  "progress": {
    "current_step": "highlight_extraction",
    "steps": [
      { "name": "stt", "status": "done", "pct": 100 },
      { "name": "highlight_extraction", "status": "processing", "pct": 60 },
      { "name": "video_edit", "status": "pending", "pct": 0 },
      { "name": "tts", "status": "pending", "pct": 0 },
      { "name": "subtitle", "status": "pending", "pct": 0 },
      { "name": "music", "status": "pending", "pct": 0 },
      { "name": "packaging", "status": "pending", "pct": 0 }
    ],
    "overall_pct": 28
  },
  "error": null
}
```

#### Error
- `404`: job_id 없음

---

## 3.3 클립 조회

### `GET /api/v1/jobs/{job_id}/clips`

#### Response `200 OK`

```json
{
  "job_id": "job_e65b744b",
  "clips": [
    {
      "clip_id": "job_e65b744b_clip_001",
      "rank": 1,
      "title": "AI가 바꿀 미래 직업들",
      "score": 0.94,
      "segment": {
        "start_sec": 312.4,
        "end_sec": 367.1,
        "duration_sec": 54.7
      },
      "highlight_reason": "기승전결이 명확하고 핵심 주장이 완결됨",
      "emotion_tags": ["surprising", "informative"],
      "assets": {
        "video_url": "https://cdn.example.com/clips/job_e65b744b_clip_001.mp4",
        "thumbnail_url": "https://cdn.example.com/clips/job_e65b744b_clip_001_thumb.jpg",
        "subtitle_url": "https://cdn.example.com/clips/job_e65b744b_clip_001.srt",
        "audio_url": "https://cdn.example.com/tts/job_e65b744b_clip_001_tts.mp3"
      },
      "music": {
        "track_id": "ncs_042",
        "title": "Elektronomia - Sky High",
        "mood": "energetic",
        "bpm": 128,
        "volume_db": -18
      },
      "created_at": "2026-04-13T02:25:20.000000Z"
    }
  ]
}
```

#### Error
- `404`: job_id 없음
- `409`: job 아직 완료 전 (`status != done`)

---

## 4) 옵션 스키마

| 필드 | 타입 | 기본값 | 설명 |
|---|---|---:|---|
| `clip_count` | int | 3 | 생성 클립 수 (1~10) |
| `clip_duration_range.min_sec` | int | 30 | 최소 길이 |
| `clip_duration_range.max_sec` | int | 60 | 최대 길이 |
| `content_type` | enum | lecture | `lecture / entertainment / vlog` |
| `language` | enum | ko | `ko / en / ja / auto` |
| `tts_enabled` | bool | true | TTS 사용 여부 |
| `tts_mode` | enum | voice_clone | `voice_clone / preset / disabled` |
| `tts_speed` | float | 1.25 | TTS 배속 (0.8~1.5) |
| `subtitle_style` | enum | dynamic | `dynamic / static / disabled` |
| `music_enabled` | bool | true | 음악 매칭 여부 |
| `music_mood` | enum | auto | `auto / energetic / calm / funny / tense` |
| `webhook_url` | str\|null | null | 완료 콜백 URL |

---

## 5) 파이프라인 단계 정의

| 순서 | step | 설명 | 산출물 |
|---:|---|---|---|
| 1 | `stt` | 전사/타임스탬프 생성 | TranscriptDocument |
| 2 | `highlight_extraction` | 클립 후보 선정/랭킹 | HighlightResult |
| 3 | `video_edit` | 구간 컷팅/리프레임 | clip video |
| 4 | `tts` | 요약 음성 생성 (옵션) | clip tts audio |
| 5 | `subtitle` | 자막 생성 (옵션) | `.srt` |
| 6 | `music` | 감정 기반 BGM 매칭 (옵션) | selected track + mix config |
| 7 | `packaging` | 최종 에셋 메타 조합 | ClipsResponse |

---

## 6) 내부 워커 계약 (I/O)

### 6.1 TranscriptDocument

```json
{
  "job_id": "job_xxx",
  "language": "ko",
  "duration_sec": 1823.5,
  "segments": [
    {
      "seg_id": 0,
      "start_sec": 0.0,
      "end_sec": 4.82,
      "text": "안녕하세요...",
      "speaker": "SPEAKER_00",
      "words": [
        { "word": "안녕하세요", "start_sec": 0.0, "end_sec": 0.72, "confidence": 0.98 }
      ]
    }
  ],
  "full_text": "...",
  "model": "faster-whisper-large-v3",
  "processed_at": "2026-04-13T02:00:00Z"
}
```

### 6.2 HighlightResult

```json
{
  "job_id": "job_xxx",
  "model_used": "llama3-70b-instruct",
  "highlights": [
    {
      "rank": 1,
      "start_sec": 312.4,
      "end_sec": 367.1,
      "title": "AI가 바꿀 미래 직업들",
      "summary": "...",
      "highlight_reason": "...",
      "emotion_tags": ["surprising", "informative"],
      "score": 0.94
    }
  ],
  "extracted_at": "2026-04-13T02:01:00Z"
}
```

### 6.3 TTS

```json
{
  "clip_id": "clip_001",
  "mode": "voice_clone",
  "reference_audio_url": "https://storage/job_xxx/sample_30s.mp3",
  "text": "요약 문장",
  "speed": 1.25,
  "model": "xtts-v2",
  "language": "ko"
}
```

```json
{
  "clip_id": "clip_001",
  "audio_url": "https://cdn.example.com/tts/clip_001_tts.mp3",
  "duration_sec": 43.2,
  "sample_rate": 24000,
  "model_used": "xtts-v2"
}
```

### 6.4 Music Match

```json
{
  "clip_id": "clip_001",
  "emotion_tags": ["surprising", "informative"],
  "content_type": "lecture",
  "clip_duration_sec": 54.7,
  "mood_override": null
}
```

```json
{
  "clip_id": "clip_001",
  "matched_tracks": [
    {
      "track_id": "ncs_042",
      "title": "Elektronomia - Sky High",
      "source": "NCS",
      "license": "CC-BY 3.0",
      "bpm": 128,
      "mood_tags": ["energetic", "uplifting"],
      "similarity_score": 0.87,
      "url": "https://storage/music/ncs_042.mp3"
    }
  ],
  "selected_track_id": "ncs_042",
  "mix_config": {
    "fade_in_sec": 1.0,
    "fade_out_sec": 1.5,
    "volume_db": -18,
    "ducking_enabled": true,
    "duck_db": -12
  }
}
```

---

## 7) 상태 전이

```text
queued
  -> processing (stt)
  -> processing (highlight_extraction)
  -> processing (video_edit)
  -> processing (tts)
  -> processing (subtitle)
  -> processing (music)
  -> processing (packaging)
  -> done

실패 시: any step -> failed
```

---

## 8) 오류 처리 규칙

- 입력 오류: `400 Bad Request`
- 리소스 없음: `404 Not Found`
- 상태 충돌(완료 전 clips 조회): `409 Conflict`
- 내부 처리 실패: `status=failed`, `error` 필드에 원인 문자열 저장

---

## 9) 웹훅(권장 확장)

Job 생성 시 `webhook_url` 제공하면 `done` 시 콜백 발송:

```json
{
  "event": "job.completed",
  "job_id": "job_xxx",
  "clips_url": "/api/v1/jobs/job_xxx/clips",
  "timestamp": "2026-04-13T02:10:00Z"
}
```

---

## 10) 현재 구현 범위 vs 실제 연동 TODO

### 현재 구현됨
- API 계약, 상태조회, 기본 파이프라인 시뮬레이션
- In-memory job store
- 테스트(생성/상태/클립/입력오류)

### 실제 서비스 연동 필요
- STT: Faster-Whisper 연동
- Highlight: LLM(vLLM/Ollama) 연동
- Video edit: FFmpeg 컷팅/자막 burn-in
- TTS: XTTS/MeloTTS 연동
- Music: DB + 임베딩 유사도 매칭
- 저장소/DB: S3(or MinIO), PostgreSQL

---

## 11) BE 전달 체크리스트

- [ ] 프론트와 `options` 필드명 최종 합의 (`music_mood`)
- [ ] Job 상태 Polling 주기(예: 2~3초) 합의
- [ ] 완료 후 `clips` 응답 캐시 정책 합의
- [ ] 웹훅 보안(HMAC signature) 합의
- [ ] 실패코드/에러메시지 표준화 합의

