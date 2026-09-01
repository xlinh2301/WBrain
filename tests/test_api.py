import numpy as np
from app.main import app
from app.pipeline import run_pipeline
from fastapi.testclient import TestClient


class Detector:
    def detect(self, image):
        return [([1, 2, 5, 6], 0.9)]


class Recognizer:
    def recognize(self, crop):
        return "1234", 0.8


def test_health():
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["device"] == "cpu"
    assert response.headers["x-request-id"]


def test_pipeline_contract():
    rows, elapsed = run_pipeline(
        np.zeros((10, 10, 3), dtype=np.uint8), Detector(), Recognizer()
    )
    assert rows[0][2:] == ("1234", 0.8)
    assert elapsed >= 0


def test_rejects_non_image_with_stable_error():
    response = TestClient(app).post(
        "/api/v1/recognize", files={"file": ("a.txt", b"hello", "text/plain")}
    )
    assert response.status_code == 415
    body = response.json()["error"]
    assert body["code"] == "WBRAIN-API-001"
    assert body["request_id"] == response.headers["x-request-id"]
    assert "traceback" not in response.text.lower()


def test_requires_configured_api_key(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.settings, "api_key", "test-key")
    response = TestClient(app).get("/api/v1/meters")
    assert response.status_code == 401
    monkeypatch.setattr(main.settings, "api_key", None)


def test_preserves_client_request_id():
    request_id = "support-case-123"
    response = TestClient(app).get(
        "/api/v1/health", headers={"X-Request-ID": request_id}
    )
    assert response.headers["x-request-id"] == request_id


def test_pipeline_failure_is_safe(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("license=super-secret model bytes")

    monkeypatch.setattr("app.main.run_pipeline", fail)
    response = TestClient(app).post(
        "/api/v1/recognize", files={"file": ("a.jpg", b"not-an-image", "image/jpeg")}
    )
    # Decode happens before inference for malformed input.
    assert response.status_code == 400

    image = np.zeros((10, 10, 3), dtype=np.uint8)
    import cv2

    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    response = TestClient(app).post(
        "/api/v1/recognize", files={"file": ("a.jpg", encoded.tobytes(), "image/jpeg")}
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "WBRAIN-PIPELINE-001"
    assert "super-secret" not in response.text
