import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from PIL import Image, UnidentifiedImageError

from .engine_registry import ENGINES, public_engine, resolve_engine
from .jobs import DATA_DIR, get_job, init_db, list_jobs, public_job, save_job
from .tasks import run_job
from .media_engines import media_engine_status as get_media_engine_status, submit_generation, generation_status, read_artifact

MAX_FILE_BYTES = int(os.getenv("MESH3D_MAX_IMAGE_BYTES", str(25 * 1024 * 1024)))
MAX_IMAGES = int(os.getenv("MESH3D_MAX_IMAGES", "80"))
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}

app = FastAPI(title="Mesh3D API", version="0.1.0", description="Image-to-3D job orchestration API. Engine wrappers must emit a real manifest.json.")
allowed_origins = [origin.strip() for origin in os.getenv("MESH3D_CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=False, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type"])


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "mesh3d-api"}



@app.get("/api/media/engines")
def media_engines_status() -> dict:
    return get_media_engine_status()


@app.post("/api/media/generate", status_code=202)
def media_generate(payload: dict) -> dict:
    kind = payload.get("kind")
    prompt = payload.get("prompt")
    if kind not in ("image", "video") or not isinstance(prompt, str):
        raise HTTPException(status_code=422, detail="Provide kind=image|video and a prompt string.")
    try:
        return submit_generation(kind, prompt)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/media/jobs/{generation_id}")
def media_job_status(generation_id: str) -> dict:
    try:
        return generation_status(generation_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/media/artifact")
def media_artifact(filename: str, subfolder: str = "", artifact_type: str = "output") -> Response:
    try:
        content, content_type = read_artifact(filename, subfolder, artifact_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return Response(content=content, media_type=content_type, headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@app.get("/api/engines")
def engines() -> dict:
    return {"engines": [public_engine(engine) for engine in ENGINES]}


@app.get("/api/jobs")
def jobs() -> dict:
    return {"jobs": [public_job(job) for job in list_jobs()]}


@app.get("/api/jobs/{job_id}")
def job_detail(job_id: str) -> dict:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return public_job(job)


async def save_validated_image(upload: UploadFile, destination: Path) -> None:
    if upload.filename is None:
        raise HTTPException(status_code=400, detail="Every uploaded image must have a filename.")
    total = 0
    with destination.open("wb") as target:
        while chunk := await upload.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_FILE_BYTES:
                target.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail=f"{upload.filename}: exceeds the {MAX_FILE_BYTES // (1024 * 1024)} MB per-image limit.")
            target.write(chunk)
    if total == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"{upload.filename}: empty file.")
    try:
        with Image.open(destination) as image:
            if image.format not in ALLOWED_FORMATS:
                raise HTTPException(status_code=415, detail=f"{upload.filename}: unsupported image format.")
            width, height = image.size
            if width < 64 or height < 64:
                raise HTTPException(status_code=400, detail=f"{upload.filename}: image dimensions must be at least 64 × 64.")
            if width * height > 80_000_000:
                raise HTTPException(status_code=413, detail=f"{upload.filename}: pixel dimensions exceed the server limit.")
            image.verify()
    except UnidentifiedImageError:
        raise HTTPException(status_code=415, detail=f"{upload.filename}: file signature is not a supported image.")
    except OSError:
        raise HTTPException(status_code=400, detail=f"{upload.filename}: corrupt image.")


@app.post("/api/jobs", status_code=202)
async def create_job(
    background_tasks: BackgroundTasks,
    mode: Annotated[str, Form()],
    engines: Annotated[list[str], Form()],
    images: Annotated[list[UploadFile], File()],
) -> dict:
    if mode not in ("single_image", "multi_view"):
        raise HTTPException(status_code=422, detail="Mode must be single_image or multi_view.")
    if not engines or len(set(engines)) != len(engines):
        raise HTTPException(status_code=422, detail="Select one or more unique engines.")
    if not images or len(images) > (1 if mode == "single_image" else MAX_IMAGES):
        raise HTTPException(status_code=422, detail=f"Mode {mode} accepts {'exactly one' if mode == 'single_image' else f'1 to {MAX_IMAGES}'} image(s).")
    for engine_id in engines:
        try:
            engine, _ = resolve_engine(engine_id)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if engine.mode != mode:
            raise HTTPException(status_code=422, detail=f"{engine.name} does not support mode {mode}.")

    job_id = str(uuid.uuid4())
    input_dir = (DATA_DIR / "jobs" / job_id / "inputs").resolve()
    input_dir.mkdir(parents=True, exist_ok=False)
    try:
        seen = set()
        for index, upload in enumerate(images, start=1):
            suffix = Path(upload.filename or "").suffix.lower()
            if suffix not in (".jpg", ".jpeg", ".png", ".webp"):
                suffix = ".img"
            target = input_dir / f"{index:03d}{suffix}"
            await save_validated_image(upload, target)
            import hashlib
            fingerprint = hashlib.sha256(target.read_bytes()).hexdigest()
            if fingerprint in seen:
                target.unlink(missing_ok=True)
                raise HTTPException(status_code=422, detail="Duplicate images detected; remove exact duplicates and resubmit.")
            seen.add(fingerprint)
    except Exception:
        shutil.rmtree(input_dir.parent, ignore_errors=True)
        raise

    job = {
        "id": job_id,
        "mode": mode,
        "status": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "image_count": len(images),
        "input_dir": str(input_dir),
        "runs": [
            {"engine_id": engine_id, "engine_name": next(engine.name for engine in ENGINES if engine.id == engine_id), "status": "queued", "artifacts": []}
            for engine_id in engines
        ],
        "error": None,
    }
    save_job(job)
    # BackgroundTasks runs in this API invocation; it replaces Celery only for
    # local/lightweight execution and is not a durable serverless work queue.
    background_tasks.add_task(run_job, job_id)
    return public_job(job)


@app.get("/api/artifacts/{job_id}/{engine_id}/{filename}")
def artifact(job_id: str, engine_id: str, filename: str) -> FileResponse:
    if Path(filename).name != filename or filename in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid artifact name.")
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Artifact not found.")
    run = next((item for item in job["runs"] if item["engine_id"] == engine_id), None)
    if not run:
        raise HTTPException(status_code=404, detail="Artifact not found.")
    metadata = next((item for item in run.get("artifacts", []) if item["name"] == filename), None)
    if not metadata:
        raise HTTPException(status_code=404, detail="Artifact not found.")
    path = (DATA_DIR / "jobs" / job_id / "outputs" / engine_id / filename).resolve()
    expected = (DATA_DIR / "jobs" / job_id / "outputs" / engine_id).resolve()
    if expected not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found.")
    media = {"glb": "model/gltf-binary", "gltf": "model/gltf+json", "obj": "text/plain", "ply": "application/octet-stream", "stl": "model/stl"}.get(metadata["format"], "application/octet-stream")
    return FileResponse(path, media_type=media, filename=filename)
