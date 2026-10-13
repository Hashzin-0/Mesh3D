import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from celery import Celery
from .engine_registry import resolve_engine
from .jobs import DATA_DIR, get_job, update_job

celery = Celery("mesh3d", broker=os.getenv("REDIS_URL", "redis://redis:6379/0"), backend=os.getenv("REDIS_URL", "redis://redis:6379/0"))
celery.conf.update(task_track_started=True, task_acks_late=True, worker_prefetch_multiplier=1, task_time_limit=int(os.getenv("MESH3D_JOB_TIMEOUT_SECONDS", "3600")))

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

@celery.task(name="mesh3d.run_job", bind=True)
def run_job(self, job_id: str) -> None:
    job = get_job(job_id)
    if not job: return
    job = update_job(job_id, status="running", error=None)
    if not job: return
    for run in job["runs"]:
        if run["status"] == "cancelled": continue
        run["status"] = "running"; run["started_at"] = now()
        update_job(job_id, status="running", runs=job["runs"])
        start = time.monotonic()
        try:
            engine, template = resolve_engine(run["engine_id"])
            run_dir = DATA_DIR / "jobs" / job_id / "outputs" / engine.id
            run_dir.mkdir(parents=True, exist_ok=True)
            input_dir = Path(job["input_dir"]).resolve()
            command = [part.replace("{input_dir}", str(input_dir)).replace("{output_dir}", str(run_dir)).replace("{mode}", job["mode"]) for part in template]
            # No shell interpolation: commands are configured by the operator as JSON argv arrays.
            home_dir = run_dir / "home"; temp_dir = run_dir / "tmp"
            home_dir.mkdir(exist_ok=True); temp_dir.mkdir(exist_ok=True)
            safe_env = {key: value for key, value in os.environ.items() if key in ("PATH", "LANG", "LC_ALL", "CUDA_VISIBLE_DEVICES", "NVIDIA_VISIBLE_DEVICES", "LD_LIBRARY_PATH")}
            safe_env.update({"HOME": str(home_dir), "TMPDIR": str(temp_dir), "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")})
            completed = subprocess.run(command, cwd=str(run_dir), capture_output=True, text=True, timeout=int(os.getenv("MESH3D_ENGINE_TIMEOUT_SECONDS", "3600")), check=False, env=safe_env)
            run["log"] = (completed.stdout + "\n" + completed.stderr)[-12000:]
            if completed.returncode != 0:
                raise RuntimeError(f"Engine wrapper exited with code {completed.returncode}. Review sanitized run logs.")
            manifest_path = run_dir / "manifest.json"
            if not manifest_path.is_file(): raise RuntimeError("Wrapper completed but did not create manifest.json.")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifacts = []
            for item in manifest.get("artifacts", []):
                relative = Path(str(item.get("path", "")))
                resolved = (run_dir / relative).resolve()
                if relative.is_absolute() or (resolved != run_dir.resolve() and run_dir.resolve() not in resolved.parents) or not resolved.is_file():
                    raise RuntimeError("Manifest contains an invalid or missing artifact path.")
                digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
                artifacts.append({"name": resolved.name, "format": str(item.get("format", resolved.suffix.lstrip("."))).lower(), "url": f"/api/artifacts/{job_id}/{engine.id}/{resolved.name}", "bytes": resolved.stat().st_size, "sha256": digest})
            if not artifacts: raise RuntimeError("Wrapper returned no artifacts; manifest must list actual output files.")
            run["artifacts"] = artifacts; run["status"] = "completed"; run["finished_at"] = now(); run["elapsed_seconds"] = round(time.monotonic() - start, 3)
        except Exception as exc:
            run["status"] = "failed"; run["finished_at"] = now(); run["elapsed_seconds"] = round(time.monotonic() - start, 3); run["error"] = str(exc)[:600]
        update_job(job_id, status="running", runs=job["runs"])
    completed_count = sum(run["status"] == "completed" for run in job["runs"])
    failed_count = sum(run["status"] == "failed" for run in job["runs"])
    final_status = "completed" if completed_count == len(job["runs"]) else ("partial" if completed_count and failed_count else "failed")
    update_job(job_id, status=final_status, runs=job["runs"])
