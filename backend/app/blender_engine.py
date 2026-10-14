"""Secure adapter from the Vercel-hosted API to a separately hosted Blender worker."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any

MAX_PROMPT_CHARS = 8000
MAX_REFERENCE_BYTES = 20 * 1024 * 1024
SAFE_ID = re.compile(r"^[a-f0-9-]{36}$")
SAFE_FILENAME = re.compile(r"^[A-Za-z0-9._-]{1,180}$")
ALLOWED_ARTIFACT_TYPES = {
    "image/png", "image/jpeg", "image/webp", "video/mp4", "text/plain",
    "application/json", "application/octet-stream",
}


def _config() -> tuple[str, str, bool]:
    return (
        os.getenv("MESH3D_BLENDER_WORKER_URL", "").strip().rstrip("/"),
        os.getenv("MESH3D_BLENDER_WORKER_TOKEN", "").strip(),
        os.getenv("MESH3D_BLENDER_ENABLED", "false").lower() == "true",
    )


def _request(url: str, token: str, payload: bytes | None = None, content_type: str | None = None, timeout: float = 10) -> bytes:
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if payload is not None and content_type:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read(100 * 1024 * 1024 + 1)
            if len(data) > 100 * 1024 * 1024:
                raise RuntimeError("Blender worker response exceeded the 100 MB limit.")
            return data
    except urllib.error.HTTPError as exc:
        # Do not forward upstream bodies that might contain internal paths or secrets.
        if exc.code in (400, 413, 415, 422):
            raise ValueError(f"Blender worker rejected the request (HTTP {exc.code}).") from exc
        if exc.code in (401, 403):
            raise RuntimeError("Blender worker authentication failed; verify the server-side worker token.") from exc
        raise RuntimeError(f"Blender worker request failed (HTTP {exc.code}).") from exc
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("Blender worker is unreachable. Check its URL, network access, and health endpoint.") from exc


def _json_request(url: str, token: str, payload: dict[str, Any] | None = None, timeout: float = 10) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    decoded = _request(url, token, body, "application/json" if body is not None else None, timeout)
    try:
        result = json.loads(decoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Blender worker returned invalid JSON.") from exc
    if not isinstance(result, dict):
        raise RuntimeError("Blender worker returned an unexpected response.")
    return result


def blender_engine_status() -> dict[str, Any]:
    url, token, enabled = _config()
    status: dict[str, Any] = {
        "engine": "blender-python",
        "name": "Blender + Python",
        "configured": bool(url and token and enabled),
        "ready": False,
        "reachable": False,
        "blender_version": None,
        "gemini_configured": False,
        "max_iterations": 0,
        "reason": "Set MESH3D_BLENDER_ENABLED=true and configure the worker URL/token in Vercel." if not enabled else "Configure MESH3D_BLENDER_WORKER_URL and MESH3D_BLENDER_WORKER_TOKEN on the Vercel backend.",
    }
    if not enabled or not url or not token:
        return status
    try:
        result = _json_request(url + "/v1/status", token, timeout=4)
    except (RuntimeError, ValueError):
        status["reason"] = "Blender worker is unreachable or rejected authentication. Verify its deployment and token."
        return status
    status.update({
        "reachable": True,
        "ready": result.get("blender_ready") is True,
        "blender_version": result.get("blender_version"),
        "gemini_configured": result.get("gemini_configured") is True,
        "max_iterations": int(result.get("max_iterations", 0) or 0),
        "reason": str(result.get("reason") or ("Ready" if result.get("blender_ready") else "Blender executable is not available on the worker.")),
    })
    return status


def submit_blender_job(kind: str, prompt: str, reference_name: str | None = None, reference_bytes: bytes | None = None, reference_content_type: str | None = None) -> dict[str, Any]:
    if kind not in ("image", "video"):
        raise ValueError("kind must be image or video")
    prompt = prompt.strip()
    if not prompt:
        raise ValueError("Prompt is required.")
    if len(prompt) > MAX_PROMPT_CHARS:
        raise ValueError(f"Prompt must be at most {MAX_PROMPT_CHARS} characters.")
    if reference_bytes is not None and len(reference_bytes) > MAX_REFERENCE_BYTES:
        raise ValueError("Reference image exceeds the 20 MB limit.")
    if reference_bytes is not None and reference_content_type not in ("image/png", "image/jpeg", "image/webp"):
        raise ValueError("Reference must be a PNG, JPEG, or WebP image.")
    url, token, enabled = _config()
    if not enabled:
        raise RuntimeError("Blender engine is disabled. Set MESH3D_BLENDER_ENABLED=true after configuring the worker.")
    if not url or not token:
        raise RuntimeError("Blender worker is not configured for this Vercel deployment.")
    status = blender_engine_status()
    if not status["ready"]:
        raise RuntimeError(status["reason"])
    boundary = "mesh3d-" + uuid.uuid4().hex
    chunks: list[bytes] = []

    def field(name: str, value: str) -> None:
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
            value.encode("utf-8"), b"\r\n",
        ])

    field("kind", kind)
    field("prompt", prompt)
    if reference_bytes is not None:
        safe_name = (reference_name or "reference.png").replace('"', "").replace("\\", "_").replace("/", "_")[:120]
        mime = reference_content_type or "image/png"
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="reference_image"; filename="{safe_name}"\r\n'.encode(),
            f"Content-Type: {mime}\r\n\r\n".encode(),
            reference_bytes, b"\r\n",
        ])
    chunks.append(f"--{boundary}--\r\n".encode())
    raw = _request(url + "/v1/jobs", token, b"".join(chunks), f"multipart/form-data; boundary={boundary}", timeout=30)
    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Blender worker returned invalid job data.") from exc
    if not isinstance(result, dict) or not isinstance(result.get("id"), str):
        raise RuntimeError("Blender worker did not return a job ID.")
    return result


def blender_job_status(job_id: str) -> dict[str, Any]:
    if not SAFE_ID.fullmatch(job_id):
        raise ValueError("Invalid Blender job ID.")
    url, token, enabled = _config()
    if not enabled or not url or not token:
        raise RuntimeError("Blender worker is not configured or the engine is disabled.")
    return _json_request(url + "/v1/jobs/" + urllib.parse.quote(job_id, safe=""), token, timeout=8)


def read_blender_artifact(job_id: str, filename: str) -> tuple[bytes, str]:
    if not SAFE_ID.fullmatch(job_id) or not SAFE_FILENAME.fullmatch(filename):
        raise ValueError("Invalid artifact reference.")
    job = blender_job_status(job_id)
    allowed = [item for item in job.get("outputs", []) if isinstance(item, dict) and item.get("filename") == filename]
    if not allowed:
        raise ValueError("Artifact is not part of the requested Blender job.")
    url, token, enabled = _config()
    if not enabled or not url or not token:
        raise RuntimeError("Blender worker is not configured or the engine is disabled.")
    raw = _request(url + "/v1/jobs/" + urllib.parse.quote(job_id, safe="") + "/artifacts/" + urllib.parse.quote(filename, safe=""), token, timeout=30)
    mime = str(allowed[0].get("content_type", "application/octet-stream")).split(";")[0].lower()
    if mime not in ALLOWED_ARTIFACT_TYPES:
        raise RuntimeError("Blender worker reported an unsupported artifact type.")
    return raw, mime
