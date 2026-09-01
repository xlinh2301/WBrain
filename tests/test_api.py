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


def test_pipeline_contract():
    rows, elapsed = run_pipeline(
        np.zeros((10, 10, 3), dtype=np.uint8), Detector(), Recognizer()
    )
    assert rows[0][2:] == ("1234", 0.8)
    assert elapsed >= 0


def test_rejects_non_image():
    response = TestClient(app).post(
        "/api/v1/recognize", files={"file": ("a.txt", b"hello", "text/plain")}
    )
    assert response.status_code == 415
