"""Hosted image/video providers for Mesh3D.

Only server-configured providers are callable. Provider outputs are copied to local
artifact storage after strict URL, MIME and size validation; browser input never
controls an upstream URL or arbitrary Gradio arguments.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .jobs import DATA_DIR

MAX_PROMPT_CHARS = 8000
SAFE_ID = re.compile(r"^remote_[0-9a-f]{32}$")
SAFE_FILENAME = re.compile(r"^[A-Za-z0-9._-]{1,120}$")
IMAGE_MIMES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
VIDEO_MIMES = {"video/mp4": ".mp4", "video/webm": ".webm"}
DEFAULT_TIMEOUT = 240
DEFAULT_MAX_BYTES = 100 * 1024 * 1024


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timeout() -> int:
    return max(10, min(int(os.getenv("MESH3D_REMOTE_MEDIA_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT))), 300))


def _max_bytes() -> int:
    return max(1024 * 1024, min(int(os.getenv("MESH3D_REMOTE_MEDIA_MAX_BYTES", str(DEFAULT_MAX_BYTES))), DEFAULT_MAX_BYTES))


def _provider_defs() -> list[dict[str, Any]]:
    pollinations_ready = bool(os.getenv("POLLINATIONS_API_KEY", "").strip())
    cloudflare_ready = bool(os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip() and os.getenv("CLOUDFLARE_API_TOKEN", "").strip())
    space_url = os.getenv("MESH3D_HF_SPACE_URL", "").strip()
    space_host_ok = False
    try:
        parsed = urllib.parse.urlparse(space_url)
        space_host_ok = parsed.scheme == "https" and bool(parsed.hostname) and parsed.hostname.endswith(".hf.space") and not parsed.username and not parsed.password
    except ValueError:
        pass
    hf_image_ready = space_host_ok and bool(os.getenv("MESH3D_HF_IMAGE_API_NAME", "").strip()) and _valid_args(os.getenv("MESH3D_HF_IMAGE_ARGS_JSON", '["__PROMPT__"]'))
    hf_video_ready = space_host_ok and bool(os.getenv("MESH3D_HF_VIDEO_API_NAME", "").strip()) and _valid_args(os.getenv("MESH3D_HF_VIDEO_ARGS_JSON", '["__PROMPT__"]'))
    return [
        {"id": "pollinations", "name": "Pollinations API", "supports": ["image"], "configured": pollinations_ready, "ready": pollinations_ready, "free_tier": "Account key and current quota required.", "reason": "Configured; live availability and current plan quota are checked only during a real request." if pollinations_ready else "Set POLLINATIONS_API_KEY on the API server. Free access and model limits depend on the current account plan."},
        {"id": "cloudflare-workers-ai", "name": "Cloudflare Workers AI · FLUX Schnell", "supports": ["image"], "configured": cloudflare_ready, "ready": cloudflare_ready, "free_tier": "Uses your Cloudflare Workers AI daily allocation, if eligible.", "reason": "Configured; the account quota and model availability are checked by the provider during generation." if cloudflare_ready else "Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN on the API server."},
        {"id": "huggingface-spaces", "name": "Hugging Face Space (Gradio API)", "supports": ["image", "video"], "configured": space_host_ok and (hf_image_ready or hf_video_ready), "ready": hf_image_ready or hf_video_ready, "free_tier": "Space GPU quotas, queues and uptime vary; no free quota is guaranteed.", "reason": "Configure a separate API function and args JSON for each supported media type." if space_host_ok and (hf_image_ready or hf_video_ready) else "Set MESH3D_HF_SPACE_URL to the Space's https://<owner>-<space>.hf.space URL and configure its API function/arguments."},
    ]


def _valid_args(raw: str) -> bool:
    try:
        args = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return False
    return isinstance(args, list) and sum(item == "__PROMPT__" for item in args) == 1


def provider_status() -> list[dict[str, Any]]:
    return _provider_defs()


def _job_dir(generation_id: str) -> Path:
    if not SAFE_ID.fullmatch(generation_id):
        raise ValueError("Invalid remote generation ID.")
    return (DATA_DIR / "media" / "remote-jobs" / generation_id).resolve()


def _save_job(job: dict[str, Any]) -> None:
    directory = _job_dir(job["id"])
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "job.json"
    temporary = directory / "job.json.tmp"
    temporary.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def _load_job(generation_id: str) -> dict[str, Any]:
    path = _job_dir(generation_id) / "job.json"
    try:
        job = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError("Remote generation not found.") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Could not read remote generation status.") from exc
    if not isinstance(job, dict) or job.get("id") != generation_id:
        raise ValueError("Remote generation not found.")
    return job


def submit_remote_generation(provider: str, kind: str, prompt: str) -> dict[str, Any]:
    if kind not in ("image", "video"):
        raise ValueError("kind must be image or video")
    prompt = prompt.strip() if isinstance(prompt, str) else ""
    if not prompt:
        raise ValueError("Prompt is required.")
    if len(prompt) > MAX_PROMPT_CHARS:
        raise ValueError(f"Prompt must be at most {MAX_PROMPT_CHARS} characters.")
    definition = next((item for item in _provider_defs() if item["id"] == provider), None)
    if definition is None:
        raise ValueError("Unknown media provider.")
    if kind not in definition["supports"]:
        raise ValueError(f"{definition['name']} does not support {kind}.")
    if not definition["ready"]:
        raise RuntimeError(definition["reason"])
    generation_id = "remote_" + uuid.uuid4().hex
    _save_job({"id": generation_id, "kind": kind, "provider": provider, "status": "queued", "created_at": _now(), "outputs": [], "error": None})
    return {"id": generation_id, "kind": kind, "status": "queued", "engine": provider}


def _request(url: str, method: str = "GET", payload: Any = None, headers: dict[str, str] | None = None, timeout: int | None = None) -> tuple[bytes, str]:
    request_headers = {"User-Agent": "Mesh3D-Media/1.0", **(headers or {})}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout or _timeout()) as response:
        content_type = response.headers.get_content_type()
        body = response.read(_max_bytes() + 1)
    if len(body) > _max_bytes():
        raise RuntimeError("Provider response exceeded the configured media size limit.")
    return body, content_type


def _download_result(url: str, base_url: str) -> tuple[bytes, str]:
    absolute = urllib.parse.urljoin(base_url.rstrip("/") + "/", url)
    parsed = urllib.parse.urlparse(absolute)
    host = (parsed.hostname or "").lower()
    allowed = host.endswith(".hf.space") or host == "hf.space" or host.endswith(".huggingface.co") or host == "huggingface.co" or host.endswith(".gradio.live") or host == "gradio.live"
    if parsed.scheme != "https" or not allowed or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise RuntimeError("The Space returned a file URL outside the allowed Hugging Face/Gradio hosts.")
    return _request(absolute, headers={"Accept": "image/*,video/mp4,video/webm,application/octet-stream"})


def _walk_file(value: Any) -> dict[str, str] | None:
    if isinstance(value, dict):
        candidate_url = value.get("url")
        if isinstance(candidate_url, str) and candidate_url:
            return {"url": candidate_url, "name": str(value.get("orig_name") or value.get("filename") or "generated")}
        for nested in value.values():
            result = _walk_file(nested)
            if result:
                return result
    elif isinstance(value, list):
        for nested in value:
            result = _walk_file(nested)
            if result:
                return result
    return None


def _gradio_result(provider: str, kind: str, prompt: str) -> tuple[bytes, str]:
    base_url = os.getenv("MESH3D_HF_SPACE_URL", "").strip().rstrip("/")
    api_name = os.getenv(f"MESH3D_HF_{kind.upper()}_API_NAME", "").strip()
    args_raw = os.getenv(f"MESH3D_HF_{kind.upper()}_ARGS_JSON", '["__PROMPT__"]')
    args = json.loads(args_raw)
    if not _valid_args(args_raw):
        raise RuntimeError("The configured Hugging Face arguments must be a JSON array with one __PROMPT__ marker.")
    args = [prompt if item == "__PROMPT__" else item for item in args]
    headers = {"Accept": "application/json"}
    token = os.getenv("HF_TOKEN", "").strip()
    if token:
        headers["Authorization"] = "Bearer " + token
    escaped_api_name = urllib.parse.quote(api_name, safe="/")
    start_body, _ = _request(base_url + "/gradio_api/call/" + escaped_api_name, method="POST", payload={"data": args}, headers=headers)
    try:
        start = json.loads(start_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Hugging Face Space did not return a valid Gradio queue response.") from exc
    event_id = start.get("event_id") if isinstance(start, dict) else None
    if not isinstance(event_id, str) or not event_id or len(event_id) > 200:
        raise RuntimeError("Hugging Face Space did not return a queue event ID.")
    request = urllib.request.Request(base_url + "/gradio_api/call/" + escaped_api_name + "/" + urllib.parse.quote(event_id, safe=""), headers={**headers, "Accept": "text/event-stream"})
    with urllib.request.urlopen(request, timeout=_timeout()) as response:
        stream = response.read(min(_max_bytes(), 5 * 1024 * 1024) + 1).decode("utf-8", errors="replace")
    if len(stream) > 5 * 1024 * 1024:
        raise RuntimeError("Gradio status stream exceeded the allowed size.")
    completed: Any = None
    current_event = ""
    for line in stream.splitlines():
        if line.startswith("event:"):
            current_event = line[6:].strip()
        elif line.startswith("data:"):
            data = line[5:].strip()
            if current_event in ("complete", "done") or "process_completed" in data:
                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, list):
                    completed = parsed
                elif isinstance(parsed, dict):
                    output = parsed.get("output")
                    if isinstance(output, dict):
                        completed = output.get("data")
                    elif isinstance(output, list):
                        completed = output
    if completed is None:
        raise RuntimeError("Hugging Face Space ended without a successful completion event.")
    file_info = _walk_file(completed)
    if not file_info:
        raise RuntimeError("Hugging Face Space completed but returned no downloadable media file.")
    return _download_result(file_info["url"], base_url)


def _generate(provider: str, kind: str, prompt: str) -> tuple[bytes, str]:
    if provider == "pollinations":
        model = os.getenv("MESH3D_POLLINATIONS_MODEL", "flux").strip() or "flux"
        url = "https://gen.pollinations.ai/image/" + urllib.parse.quote(prompt, safe="") + "?" + urllib.parse.urlencode({"model": model, "width": 1024, "height": 1024, "nologo": "true"})
        body, content_type = _request(url, headers={"Authorization": "Bearer " + os.environ["POLLINATIONS_API_KEY"], "Accept": "image/*"})
        if content_type not in IMAGE_MIMES:
            raise RuntimeError("Pollinations returned an unsupported image format.")
        return body, content_type
    if provider == "cloudflare-workers-ai":
        account = os.environ["CLOUDFLARE_ACCOUNT_ID"].strip()
        token = os.environ["CLOUDFLARE_API_TOKEN"].strip()
        model = os.getenv("MESH3D_CLOUDFLARE_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell").strip()
        if not re.fullmatch(r"@cf/[A-Za-z0-9._/-]{1,180}", model):
            raise RuntimeError("Invalid Cloudflare model identifier.")
        url = f"https://api.cloudflare.com/client/v4/accounts/{urllib.parse.quote(account, safe='')}/ai/run/{urllib.parse.quote(model, safe='/@')}"
        body, content_type = _request(url, method="POST", payload={"prompt": prompt}, headers={"Authorization": "Bearer " + token, "Accept": "application/json"})
        try:
            result = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            result = None
        if isinstance(result, dict) and isinstance(result.get("result"), dict):
            encoded = result["result"].get("image")
            if isinstance(encoded, str):
                image_bytes = base64.b64decode(encoded, validate=True)
                if len(image_bytes) > _max_bytes():
                    raise RuntimeError("Cloudflare image exceeded the configured media size limit.")
                return image_bytes, "image/png"
        if content_type in IMAGE_MIMES:
            return body, content_type
        raise RuntimeError("Cloudflare Workers AI returned no supported image payload.")
    if provider == "huggingface-spaces":
        body, content_type = _gradio_result(provider, kind, prompt)
        if content_type not in (IMAGE_MIMES if kind == "image" else VIDEO_MIMES):
            raise RuntimeError(f"Hugging Face Space returned an unsupported {kind} MIME type.")
        return body, content_type
    raise RuntimeError("Unknown media provider.")


def run_remote_generation(generation_id: str, provider: str, kind: str, prompt: str) -> None:
    job = _load_job(generation_id)
    if job.get("provider") != provider or job.get("kind") != kind or job.get("status") != "queued":
        return
    job["status"] = "running"
    job["started_at"] = _now()
    _save_job(job)
    started = time.monotonic()
    try:
        content, content_type = _generate(provider, kind, prompt)
        allowed = IMAGE_MIMES if kind == "image" else VIDEO_MIMES
        if content_type not in allowed:
            raise RuntimeError(f"Provider returned an unsupported {kind} MIME type.")
        suffix = allowed[content_type]
        filename = "generated" + suffix
        directory = _job_dir(generation_id)
        artifact = directory / filename
        artifact.write_bytes(content)
        job["status"] = "completed"
        job["finished_at"] = _now()
        job["elapsed_seconds"] = round(time.monotonic() - started, 3)
        job["outputs"] = [{"filename": filename, "subfolder": "", "type": "remote", "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(), "content_type": content_type}]
        job["error"] = None
    except Exception as exc:
        job["status"] = "failed"
        job["finished_at"] = _now()
        job["elapsed_seconds"] = round(time.monotonic() - started, 3)
        # Avoid exposing upstream response bodies, credentials, or internal URLs.
        job["error"] = str(exc) if isinstance(exc, (ValueError, RuntimeError)) else "Remote provider request failed."
        job["outputs"] = []
    _save_job(job)


def remote_generation_status(generation_id: str) -> dict[str, Any]:
    job = _load_job(generation_id)
    result = {key: job.get(key) for key in ("id", "kind", "status", "provider", "created_at", "started_at", "finished_at", "elapsed_seconds", "error", "outputs")}
    result["engine"] = job.get("provider")
    return result


def read_remote_artifact(generation_id: str, filename: str, artifact_type: str = "remote") -> tuple[bytes, str]:
    if artifact_type != "remote" or not SAFE_FILENAME.fullmatch(filename):
        raise ValueError("Invalid remote artifact reference.")
    job = _load_job(generation_id)
    metadata = next((item for item in job.get("outputs", []) if item.get("filename") == filename and item.get("type") == "remote"), None)
    if job.get("status") != "completed" or not metadata:
        raise ValueError("Artifact is not part of the requested generation.")
    path = (_job_dir(generation_id) / filename).resolve()
    if _job_dir(generation_id) not in path.parents or not path.is_file():
        raise ValueError("Artifact not found.")
    if path.stat().st_size > _max_bytes():
        raise RuntimeError("Generated artifact exceeds the configured media size limit.")
    content_type = metadata.get("content_type")
    if content_type not in set(IMAGE_MIMES) | set(VIDEO_MIMES):
        raise ValueError("Unsupported remote artifact type.")
    return path.read_bytes(), content_type
