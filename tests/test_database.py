from app.database import Database


def test_meter_reading_review_and_audit(tmp_path):
    db = Database(tmp_path / "wbrain.db")
    meter = db.create_meter(
        {"serial_number": "WM-001", "name": "Main", "address": "A"}, "req-1"
    )
    assert meter["serial_number"] == "WM-001"
    image_id = db.add_image(meter["id"], "hash", "image/jpeg", 10, None)
    reading = db.add_reading(
        {
            "meter_id": meter["id"],
            "image_id": image_id,
            "raw_text": "12X",
            "value": None,
            "confidence": 0.4,
            "status": "review_required",
            "anomaly_reason": "low confidence",
            "model_version": "test",
            "processing_ms": 1.2,
        },
        "req-2",
    )
    reviews = db.list_reviews("pending", 10, 0)
    assert reviews[0]["reading_id"] == reading["id"]
    db.review(reviews[0]["id"], "approved", 12, "operator", "checked", "req-3")
    assert db.list_readings(meter["id"], 10, 0)[0]["status"] == "approved"
    assert len(db.list_audit(None, 10)) >= 3
