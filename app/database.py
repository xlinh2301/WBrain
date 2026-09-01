from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


class Database:
    """Small SQLite repository; the API contract is independent of the backend."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path), timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def init_schema(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS meters (
                    id TEXT PRIMARY KEY, serial_number TEXT NOT NULL UNIQUE,
                    name TEXT, meter_type TEXT, address TEXT, status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS meter_images (
                    id TEXT PRIMARY KEY, meter_id TEXT REFERENCES meters(id),
                    sha256 TEXT NOT NULL, content_type TEXT NOT NULL, size_bytes INTEGER NOT NULL,
                    storage_path TEXT, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS model_versions (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, version TEXT NOT NULL,
                    checksum TEXT, created_at TEXT NOT NULL, UNIQUE(name, version)
                );
                CREATE TABLE IF NOT EXISTS readings (
                    id TEXT PRIMARY KEY, meter_id TEXT REFERENCES meters(id), image_id TEXT REFERENCES meter_images(id),
                    request_id TEXT NOT NULL, raw_text TEXT NOT NULL, value REAL, confidence REAL NOT NULL,
                    status TEXT NOT NULL, anomaly_reason TEXT, model_version TEXT, processing_ms REAL NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS review_tasks (
                    id TEXT PRIMARY KEY, reading_id TEXT NOT NULL REFERENCES readings(id),
                    status TEXT NOT NULL DEFAULT 'pending', reason TEXT NOT NULL,
                    corrected_value REAL, reviewer TEXT, review_note TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY, request_id TEXT, actor TEXT, action TEXT NOT NULL,
                    resource_type TEXT NOT NULL, resource_id TEXT, details_json TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_readings_meter_time ON readings(meter_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_review_status ON review_tasks(status, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_audit_request ON audit_events(request_id);
                """
            )

    @staticmethod
    def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row else None

    def create_meter(self, data: dict[str, Any], request_id: str) -> dict[str, Any]:
        meter_id, now = new_id(), utc_now()
        with self.connect() as db:
            db.execute(
                "INSERT INTO meters(id,serial_number,name,meter_type,address,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    meter_id,
                    data["serial_number"],
                    data.get("name"),
                    data.get("meter_type"),
                    data.get("address"),
                    "active",
                    now,
                    now,
                ),
            )
            self.audit(db, request_id, "create", "meter", meter_id, data)
            return (
                self._row(
                    db.execute(
                        "SELECT * FROM meters WHERE id=?", (meter_id,)
                    ).fetchone()
                )
                or {}
            )

    def list_meters(self, limit: int, offset: int) -> list[dict[str, Any]]:
        with self.connect() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM meters ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                )
            ]

    def get_meter(self, meter_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            return self._row(
                db.execute("SELECT * FROM meters WHERE id=?", (meter_id,)).fetchone()
            )

    def add_image(
        self,
        meter_id: str | None,
        sha256: str,
        content_type: str,
        size: int,
        storage_path: str | None,
    ) -> str:
        image_id = new_id()
        with self.connect() as db:
            db.execute(
                "INSERT INTO meter_images VALUES(?,?,?,?,?,?,?)",
                (
                    image_id,
                    meter_id,
                    sha256,
                    content_type,
                    size,
                    storage_path,
                    utc_now(),
                ),
            )
        return image_id

    def add_reading(self, data: dict[str, Any], request_id: str) -> dict[str, Any]:
        reading_id, now = new_id(), utc_now()
        with self.connect() as db:
            db.execute(
                "INSERT INTO readings VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    reading_id,
                    data.get("meter_id"),
                    data.get("image_id"),
                    request_id,
                    data["raw_text"],
                    data.get("value"),
                    data["confidence"],
                    data["status"],
                    data.get("anomaly_reason"),
                    data.get("model_version"),
                    data["processing_ms"],
                    now,
                ),
            )
            if data["status"] == "review_required":
                db.execute(
                    "INSERT INTO review_tasks VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        new_id(),
                        reading_id,
                        "pending",
                        data.get("anomaly_reason") or "manual review",
                        None,
                        None,
                        None,
                        now,
                        now,
                    ),
                )
            self.audit(
                db,
                request_id,
                "create",
                "reading",
                reading_id,
                {"status": data["status"], "meter_id": data.get("meter_id")},
            )
            return (
                self._row(
                    db.execute(
                        "SELECT * FROM readings WHERE id=?", (reading_id,)
                    ).fetchone()
                )
                or {}
            )

    def previous_value(self, meter_id: str) -> float | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT value FROM readings WHERE meter_id=? AND value IS NOT NULL ORDER BY created_at DESC LIMIT 1",
                (meter_id,),
            ).fetchone()
            return float(row[0]) if row else None

    def list_readings(
        self, meter_id: str | None, limit: int, offset: int
    ) -> list[dict[str, Any]]:
        with self.connect() as db:
            if meter_id:
                rows = db.execute(
                    "SELECT * FROM readings WHERE meter_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (meter_id, limit, offset),
                )
            else:
                rows = db.execute(
                    "SELECT * FROM readings ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                )
            return [dict(row) for row in rows]

    def list_reviews(
        self, status: str, limit: int, offset: int
    ) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM review_tasks WHERE status=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (status, limit, offset),
            )
            return [dict(row) for row in rows]

    def review(
        self,
        task_id: str,
        status: str,
        corrected_value: float | None,
        reviewer: str | None,
        note: str | None,
        request_id: str,
    ) -> dict[str, Any] | None:
        now = utc_now()
        with self.connect() as db:
            task = db.execute(
                "SELECT * FROM review_tasks WHERE id=?", (task_id,)
            ).fetchone()
            if not task:
                return None
            db.execute(
                "UPDATE review_tasks SET status=?,corrected_value=?,reviewer=?,review_note=?,updated_at=? WHERE id=?",
                (status, corrected_value, reviewer, note, now, task_id),
            )
            if corrected_value is not None:
                db.execute(
                    "UPDATE readings SET value=?,status=? WHERE id=?",
                    (corrected_value, "approved", task["reading_id"]),
                )
            self.audit(
                db,
                request_id,
                "review",
                "reading",
                task["reading_id"],
                {
                    "task_id": task_id,
                    "status": status,
                    "corrected_value": corrected_value,
                },
            )
            row = db.execute(
                "SELECT * FROM review_tasks WHERE id=?", (task_id,)
            ).fetchone()
            return self._row(row)

    def add_model(
        self, name: str, version: str, checksum: str | None, request_id: str
    ) -> dict[str, Any]:
        model_id, now = new_id(), utc_now()
        with self.connect() as db:
            db.execute(
                "INSERT INTO model_versions VALUES(?,?,?,?,?)",
                (model_id, name, version, checksum, now),
            )
            self.audit(
                db,
                request_id,
                "create",
                "model_version",
                model_id,
                {"name": name, "version": version},
            )
            return (
                self._row(
                    db.execute(
                        "SELECT * FROM model_versions WHERE id=?", (model_id,)
                    ).fetchone()
                )
                or {}
            )

    def list_models(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM model_versions ORDER BY created_at DESC"
                )
            ]

    def audit(
        self,
        db: sqlite3.Connection,
        request_id: str,
        action: str,
        resource_type: str,
        resource_id: str | None,
        details: dict[str, Any],
        actor: str | None = None,
    ) -> None:
        db.execute(
            "INSERT INTO audit_events VALUES(?,?,?,?,?,?,?,?)",
            (
                new_id(),
                request_id,
                actor,
                action,
                resource_type,
                resource_id,
                json.dumps(details, ensure_ascii=False),
                utc_now(),
            ),
        )

    def list_audit(self, request_id: str | None, limit: int) -> list[dict[str, Any]]:
        with self.connect() as db:
            if request_id:
                rows = db.execute(
                    "SELECT * FROM audit_events WHERE request_id=? ORDER BY created_at DESC LIMIT ?",
                    (request_id, limit),
                )
            else:
                rows = db.execute(
                    "SELECT * FROM audit_events ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                )
            result = []
            for row in rows:
                item = dict(row)
                item["details"] = json.loads(item.pop("details_json"))
                result.append(item)
            return result
