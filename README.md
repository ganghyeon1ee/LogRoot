# shortform-ai-music-pipeline

롱폼→숏폼 서비스에서 사용할 **무료 BGM 수집/태깅 파이프라인**의 AI 파트 초안입니다.

## 제공 기능

- URL 기반 음원 다운로드
- LAION-CLAP 기반 분위기 태깅 (`top_k` 라벨 + 점수)
- SQLite 메타데이터 저장 (추후 BE DB 이관 용이)
- 선택적으로 S3 업로드 후 URI 저장
- FE/BE 연동용 JSON payload 출력

## 구조

- `shortform_ai/music_tagging.py`: CLAP 태거
- `shortform_ai/downloader.py`: 음원 다운로드 및 파일 해시
- `shortform_ai/storage.py`: SQLite 저장소 + S3 업로더
- `shortform_ai/pipeline.py`: 전체 오케스트레이션
- `shortform_ai/cli.py`: 실행 진입점

## 빠른 실행

```bash
python -m shortform_ai.cli "https://example.com/sample.mp3" --title "sample"
```

S3 업로드 사용 시:

```bash
python -m shortform_ai.cli "https://example.com/sample.mp3" --s3-bucket your-bucket
```

## BE 연동 포인트

`MusicIngestionPipeline.to_api_payload(asset)` 결과를 API 응답으로 그대로 사용하면 FE에서 바로 소비 가능:

```json
{
  "source_url": "...",
  "local_path": "downloads/foo.mp3",
  "sha256": "...",
  "title": "foo",
  "tags": [
    {"label": "peaceful music", "score": 0.43}
  ],
  "extra": {"s3_uri": "s3://bucket/music/..."},
  "created_at": "2026-04-09T09:00:00.000000"
}
```

## 설치 의존성

- 필수: `torch`, `laion_clap`
- 선택: `boto3` (S3 업로드)

> 실제 운영에서는 다운로드 소스의 라이선스 검증/중복 제거/실패 재시도/비동기 큐(Celery, SQS 등) 추가를 권장합니다.
