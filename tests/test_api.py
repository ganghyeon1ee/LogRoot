import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_job_and_get_status_and_clips():
    options = {
        "clip_count": 2,
        "clip_duration_range": {"min_sec": 30, "max_sec": 60},
        "content_type": "lecture",
        "language": "ko",
        "tts_enabled": True,
        "tts_mode": "voice_clone",
        "tts_speed": 1.25,
        "subtitle_style": "dynamic",
        "music_enabled": True,
        "music_mood": "auto",
    }
    files = {"file": ("sample.mp4", b"fake-video-bytes", "video/mp4")}
    data = {"options": json.dumps(options)}

    create_resp = client.post("/api/v1/jobs", files=files, data=data)
    assert create_resp.status_code == 202
    body = create_resp.json()

    status_resp = client.get(f"/api/v1/jobs/{body['job_id']}/status")
    assert status_resp.status_code == 200
    status_body = status_resp.json()
    assert status_body["status"] == "done"
    assert status_body["progress"]["overall_pct"] == 100

    clips_resp = client.get(f"/api/v1/jobs/{body['job_id']}/clips")
    assert clips_resp.status_code == 200
    clips_body = clips_resp.json()
    assert len(clips_body["clips"]) == 2


def test_invalid_options_returns_400():
    files = {"file": ("sample.mp4", b"fake-video-bytes", "video/mp4")}
    data = {"options": "not-a-json"}

    resp = client.post("/api/v1/jobs", files=files, data=data)
    assert resp.status_code == 400
