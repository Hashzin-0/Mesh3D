import hashlib
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from .engine_registry import resolve_engine
from .jobs import DATA_DIR, get_job, update_job


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _engine_environment(run_dir: Path) -> dict[str, str]:
    """Pass only runtime configuration needed by adapters; never pass arbitrary host secrets."""
    base_keys = {"PATH", "LANG", "LC_ALL", "CUDA_VISIBLE_DEVICES", "NVIDIA_VISIBLE_DEVICES", "LD_LIBRARY_PATH"}
    prefixes = (
        "MESH3D_TRIPOSR_", "MESH3D_INSTANTMESH_", "MESH3D_STABLE_FAST_3D_",
        "MESH3D_HUNYUAN3D_", "MESH3D_MESHROOM_", "MESH3D_COLMAP_", "MESH3D_OPENMVS_",
        "MESH3D_VGGT_",
    )
    safe_env = {key: value for key, value in os.environ.items() if key in base_keys or key.startswith(prefixes)}
    for key in ("HF_HOME", "HF_HUB_CACHE", "TRANSFORMERS_CACHE", "TORCH_HOME", "PYTHONPATH"):
        if key in os.environ:
            safe_env[key] = os.environ[key]
    home_dir = run_dir / "home"
    temp_dir = run_dir / "tmp"
    home_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    safe_env.update({"HOME": str(home_dir), "TMPDIR": str(temp_dir), "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")})
    for key in ("HF_TOKEN", "HUGGINGFACE_HUB_TOKEN"):
        if os.getenv(key):
            safe_env[key] = os.environ[key]
    return safe_env


def run_job(job_id: str) -> None:
    """Run a job inside the current FastAPI invocation (no Celery/Redis broker).

    This is suitable for local development and short, bounded work only. Vercel
    invocations have a finite duration and ephemeral per-instance storage; this
    function is not a durable queue or a supported GPU inference worker.
    """
    job = get_job(job_id)
    if not job:
        return
    job = update_job(job_id, status="running", error=None)
    if not job:
        return
    for run in job["runs"]:
        if run["status"] == "cancelled":
            continue
        run["status"] = "running"
        run["started_at"] = now()
        update_job(job_id, status="running", runs=job["runs"])
        start = time.monotonic()
        try:
            engine, template = resolve_engine(run["engine_id"])
            run_dir = DATA_DIR / "jobs" / job_id / "outputs" / engine.id
            run_dir.mkdir(parents=True, exist_ok=True)
            input_dir = Path(job["input_dir"]).resolve()
            command = [part.replace("{input_dir}", str(input_dir)).replace("{output_dir}", str(run_dir.resolve())).replace("{mode}", job["mode"]) for part in template]
            completed = subprocess.run(
                command,
                cwd=str(run_dir),
                capture_output=True,
                text=True,
                timeout=int(os.getenv("MESH3D_ENGINE_TIMEOUT_SECONDS", "3600")),
                check=False,
                env=_engine_environment(run_dir),
            )
            run["log"] = (completed.stdout + "\n" + completed.stderr)[-12000:]
            if completed.returncode != 0:
                raise RuntimeError(f"Engine wrapper exited with code {completed.returncode}. Review sanitized run logs.")
            manifest_path = run_dir / "manifest.json"
            if not manifest_path.is_file():
                raise RuntimeError("Wrapper completed but did not create manifest.json.")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifacts = []
            for item in manifest.get("artifacts", []):
                relative = Path(str(item.get("path", "")))
                resolved = (run_dir / relative).resolve()
                if relative.is_absolute() or (resolved != run_dir.resolve() and run_dir.resolve() not in resolved.parents) or not resolved.is_file():
                    raise RuntimeError("Manifest contains an invalid or missing artifact path.")
                if resolved.parent != run_dir.resolve():
                    target = run_dir / resolved.name
                    if target.exists() and target != resolved:
                        target = run_dir / f"{resolved.parent.name}_{resolved.name}"
                    if target != resolved:
                        shutil.copy2(resolved, target)
                    resolved = target
                digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
                artifacts.append({"name": resolved.name, "format": str(item.get("format", resolved.suffix.lstrip("."))).lower(), "url": f"/api/artifacts/{job_id}/{engine.id}/{resolved.name}", "bytes": resolved.stat().st_size, "sha256": digest})
            if not artifacts:
                raise RuntimeError("Wrapper returned no artifacts; manifest must list actual output files.")
            run["artifacts"] = artifacts
            run["status"] = "completed"
            run["finished_at"] = now()
            run["elapsed_seconds"] = round(time.monotonic() - start, 3)
        except Exception as exc:
            run["status"] = "failed"
            run["finished_at"] = now()
            run["elapsed_seconds"] = round(time.monotonic() - start, 3)
            run["error"] = str(exc)[:600]
        update_job(job_id, status="running", runs=job["runs"])
    completed_count = sum(run["status"] == "completed" for run in job["runs"])
    failed_count = sum(run["status"] == "failed" for run in job["runs"])
    final_status = "completed" if completed_count == len(job["runs"]) else ("partial" if completed_count and failed_count else "failed")
    update_job(job_id, status=final_status, runs=job["runs"])
