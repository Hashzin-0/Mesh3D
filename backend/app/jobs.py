import json
import os
import sqlite3
from pathlib import Path
from typing import Any

# Vercel's writable filesystem is temporary and instance-local. Keep the local
# Docker default, but never assume this path is durable across serverless calls.
_default_data_dir = "/tmp/mesh3d-data" if os.getenv("VERCEL") == "1" else "/data"
DATA_DIR = Path(os.getenv("MESH3D_DATA_DIR", _default_data_dir))
DB_PATH = DATA_DIR / "mesh3d.sqlite3"


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS jobs (
          id TEXT PRIMARY KEY, mode TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
          image_count INTEGER NOT NULL, input_dir TEXT NOT NULL, runs_json TEXT NOT NULL, error TEXT
        )""")


def save_job(job: dict[str, Any]) -> None:
    with connect() as db:
        db.execute("INSERT OR REPLACE INTO jobs (id,mode,status,created_at,image_count,input_dir,runs_json,error) VALUES (?,?,?,?,?,?,?,?)",
                   (job["id"], job["mode"], job["status"], job["created_at"], job["image_count"], job["input_dir"], json.dumps(job["runs"]), job.get("error")))


def update_job(job_id: str, **changes: Any) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            return None
        job = dict(row)
        job["runs"] = json.loads(job["runs_json"])
        job.update(changes)
        db.execute("UPDATE jobs SET status=?, runs_json=?, error=? WHERE id=?", (job["status"], json.dumps(job["runs"]), job.get("error"), job_id))
        return job


def get_job(job_id: str) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        return None
    job = dict(row)
    job["runs"] = json.loads(job.pop("runs_json"))
    return job


def list_jobs() -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 100").fetchall()
    jobs = []
    for row in rows:
        job = dict(row)
        job["runs"] = json.loads(job.pop("runs_json"))
        jobs.append(job)
    return jobs


def public_job(job: dict[str, Any]) -> dict[str, Any]:
    result = {key: job.get(key) for key in ("id", "mode", "status", "created_at", "image_count", "error")}
    result["runs"] = [{key: run.get(key) for key in ("engine_id", "engine_name", "status", "started_at", "finished_at", "elapsed_seconds", "error", "artifacts", "log")} for run in job.get("runs", [])]
    return result
