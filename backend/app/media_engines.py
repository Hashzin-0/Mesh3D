"""Local self-hosted image/video generation through a configured ComfyUI instance."""
from __future__ import annotations
import json, os, re, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from typing import Any

DEFAULT_COMFY_URL = "http://127.0.0.1:8188"
MAX_PROMPT_CHARS = 8000
SAFE_FILENAME = re.compile(r"^[A-Za-z0-9._-]{1,240}$")
ALLOWED_ARTIFACT_TYPES = {"output", "temp"}

def _settings(kind: str) -> dict[str, str]:
    suffix = kind.upper()
    return {
        "url": os.getenv("MESH3D_COMFYUI_URL", DEFAULT_COMFY_URL).rstrip("/"),
        "workflow": os.getenv(f"MESH3D_COMFYUI_{suffix}_WORKFLOW", "").strip(),
        "prompt_node": os.getenv(f"MESH3D_COMFYUI_{suffix}_PROMPT_NODE", "").strip(),
        "prompt_input": os.getenv(f"MESH3D_COMFYUI_{suffix}_PROMPT_INPUT", "text").strip() or "text",
    }

def _request_json(url: str, payload: dict[str, Any] | None = None, timeout: float = 10) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"} if data is not None else {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        decoded = json.loads(response.read().decode("utf-8"))
    if not isinstance(decoded, dict):
        raise RuntimeError("ComfyUI returned an unexpected response.")
    return decoded

def media_engine_status() -> dict[str, Any]:
    url = os.getenv("MESH3D_COMFYUI_URL", DEFAULT_COMFY_URL).rstrip("/")
    enabled = os.getenv("MESH3D_MEDIA_GENERATION_ENABLED", "false").lower() == "true"
    result: dict[str, Any] = {"engine": "comfyui-local", "configured": False, "reachable": False, "enabled": enabled}
    try:
        with urllib.request.urlopen(urllib.request.Request(url + "/system_stats"), timeout=2) as response:
            result["reachable"] = response.status == 200
    except (OSError, urllib.error.URLError, TimeoutError, ValueError):
        pass
    for kind in ("image", "video"):
        config = _settings(kind)
        workflow_path = Path(config["workflow"]).expanduser() if config["workflow"] else None
        workflow_exists = bool(workflow_path and workflow_path.is_file())
        ready = bool(enabled and result["reachable"] and workflow_exists and config["prompt_node"])
        result[kind] = {
            "ready": ready, "workflow_configured": bool(config["workflow"]),
            "workflow_exists": workflow_exists, "prompt_node_configured": bool(config["prompt_node"]),
            "reason": "Ready" if ready else (
                "Local generation is disabled; set MESH3D_MEDIA_GENERATION_ENABLED=true only on a trusted runtime." if not enabled else
                "ComfyUI is unreachable; start the local service and verify MESH3D_COMFYUI_URL."
                if not result["reachable"] else
                f"Configure MESH3D_COMFYUI_{kind.upper()}_WORKFLOW and MESH3D_COMFYUI_{kind.upper()}_PROMPT_NODE with a reviewed local API workflow."
            ),
        }
    result["configured"] = result["image"]["ready"] or result["video"]["ready"]
    return result

def submit_generation(kind: str, prompt: str) -> dict[str, Any]:
    if kind not in ("image", "video"):
        raise ValueError("kind must be image or video")
    prompt = prompt.strip()
    if not prompt:
        raise ValueError("Prompt is required.")
    if len(prompt) > MAX_PROMPT_CHARS:
        raise ValueError(f"Prompt must be at most {MAX_PROMPT_CHARS} characters.")
    if os.getenv("MESH3D_MEDIA_GENERATION_ENABLED", "false").lower() != "true":
        raise RuntimeError("Local media generation is disabled. Enable it only on a trusted runtime.")
    config = _settings(kind)
    workflow_path = Path(config["workflow"]).expanduser() if config["workflow"] else None
    if not workflow_path or not workflow_path.is_file() or not config["prompt_node"]:
        raise RuntimeError(f"The local ComfyUI {kind} workflow is not configured.")
    if not media_engine_status().get(kind, {}).get("ready"):
        raise RuntimeError(media_engine_status()[kind]["reason"])
    try:
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"The configured {kind} workflow is unreadable or invalid JSON.") from exc
    if not isinstance(workflow, dict):
        raise RuntimeError("ComfyUI workflow must be a JSON object in API format.")
    node = workflow.get(config["prompt_node"])
    if not isinstance(node, dict) or not isinstance(node.get("inputs"), dict):
        raise RuntimeError("Configured prompt node does not exist or has no inputs.")
    if config["prompt_input"] not in node["inputs"]:
        raise RuntimeError("Configured prompt input is not present in the workflow node.")
    node["inputs"][config["prompt_input"]] = prompt
    try:
        response = _request_json(config["url"] + "/prompt", {"prompt": workflow}, timeout=15)
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError("Could not submit the workflow to local ComfyUI.") from exc
    prompt_id = response.get("prompt_id")
    if not isinstance(prompt_id, str) or not prompt_id:
        raise RuntimeError("ComfyUI did not return a prompt ID.")
    return {"id": prompt_id, "kind": kind, "status": "queued", "engine": "comfyui-local"}

def generation_status(prompt_id: str) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9-]{1,100}", prompt_id):
        raise ValueError("Invalid generation ID.")
    url = os.getenv("MESH3D_COMFYUI_URL", DEFAULT_COMFY_URL).rstrip("/")
    try:
        history = _request_json(url + "/history/" + urllib.parse.quote(prompt_id, safe=""), timeout=5)
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError("Could not read generation status from local ComfyUI.") from exc
    entry = history.get(prompt_id)
    if not isinstance(entry, dict):
        return {"id": prompt_id, "status": "running", "outputs": []}
    status_info = entry.get("status") if isinstance(entry.get("status"), dict) else {}
    outputs: list[dict[str, str]] = []
    raw_outputs = entry.get("outputs")
    if isinstance(raw_outputs, dict):
        for node_output in raw_outputs.values():
            if not isinstance(node_output, dict):
                continue
            for key in ("images", "gifs", "videos"):
                items = node_output.get(key)
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    filename, subfolder = item.get("filename"), item.get("subfolder", "")
                    artifact_type = item.get("type", "output")
                    if isinstance(filename, str) and SAFE_FILENAME.fullmatch(filename) and isinstance(subfolder, str) and artifact_type in ALLOWED_ARTIFACT_TYPES and ".." not in Path(subfolder).parts:
                        outputs.append({"filename": filename, "subfolder": subfolder, "type": artifact_type})
    completed = bool(status_info.get("completed"))
    return {"id": prompt_id, "status": "completed" if completed else "running", "outputs": outputs}

def read_artifact(filename: str, subfolder: str = "", artifact_type: str = "output") -> tuple[bytes, str]:
    if not SAFE_FILENAME.fullmatch(filename) or artifact_type not in ALLOWED_ARTIFACT_TYPES:
        raise ValueError("Invalid artifact reference.")
    if not isinstance(subfolder, str) or Path(subfolder).is_absolute() or ".." in Path(subfolder).parts or "\\" in subfolder:
        raise ValueError("Invalid artifact subfolder.")
    query = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": artifact_type})
    url = os.getenv("MESH3D_COMFYUI_URL", DEFAULT_COMFY_URL).rstrip("/") + "/view?" + query
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=20) as response:
            content_type = response.headers.get_content_type()
            if content_type not in ("image/png", "image/jpeg", "image/webp", "video/mp4", "video/webm", "image/gif"):
                raise RuntimeError("ComfyUI returned an unsupported artifact content type.")
            data = response.read(100 * 1024 * 1024 + 1)
            if len(data) > 100 * 1024 * 1024:
                raise RuntimeError("Generated artifact exceeds the 100 MB response limit.")
            return data, content_type
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("Could not retrieve the generated artifact from local ComfyUI.") from exc
