import tempfile
from pathlib import Path
from app import jobs

def test_job_round_trip_and_public_projection(monkeypatch):
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        monkeypatch.setattr(jobs, "DATA_DIR", root)
        monkeypatch.setattr(jobs, "DB_PATH", root / "mesh3d.sqlite3")
        jobs.init_db()
        job = {"id": "job-test", "mode": "single_image", "status": "queued", "created_at": "2026-01-01T00:00:00+00:00", "image_count": 1, "input_dir": str(root / "inputs"), "runs": [{"engine_id": "triposr", "engine_name": "TripoSR", "status": "queued", "artifacts": []}], "error": None}
        jobs.save_job(job)
        loaded = jobs.get_job("job-test")
        assert loaded is not None and loaded["runs"][0]["engine_id"] == "triposr"
        public = jobs.public_job(loaded)
        assert "input_dir" not in public and public["status"] == "queued"
        assert jobs.list_jobs()[0]["id"] == "job-test"
