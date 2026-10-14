import json
import pytest
from app import media_engines

def test_media_status_is_explicit_when_workflows_are_not_configured(monkeypatch):
    monkeypatch.setenv("MESH3D_MEDIA_GENERATION_ENABLED", "false")
    monkeypatch.setattr(media_engines.urllib.request, "urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("offline")))
    status = media_engines.media_engine_status()
    assert status["engine"] == "comfyui-local"
    assert status["configured"] is False
    assert status["image"]["ready"] is False
    assert status["video"]["ready"] is False

def test_submit_requires_prompt_and_kind():
    with pytest.raises(ValueError, match="Prompt is required"):
        media_engines.submit_generation("image", "  ")
    with pytest.raises(ValueError, match="kind must be image or video"):
        media_engines.submit_generation("3d", "asset")

def test_submit_injects_prompt_only_into_configured_node(monkeypatch, tmp_path):
    workflow = {"6": {"class_type": "CLIPTextEncode", "inputs": {"text": "old prompt", "clip": ["1", 0]}}}
    path = tmp_path / "image-workflow.json"
    path.write_text(json.dumps(workflow), encoding="utf-8")
    monkeypatch.setenv("MESH3D_MEDIA_GENERATION_ENABLED", "true")
    monkeypatch.setenv("MESH3D_COMFYUI_URL", "http://localhost:8188")
    monkeypatch.setenv("MESH3D_COMFYUI_IMAGE_WORKFLOW", str(path))
    monkeypatch.setenv("MESH3D_COMFYUI_IMAGE_PROMPT_NODE", "6")
    monkeypatch.setenv("MESH3D_COMFYUI_IMAGE_PROMPT_INPUT", "text")
    monkeypatch.setattr(media_engines, "media_engine_status", lambda: {"image": {"ready": True}})
    captured = {}
    monkeypatch.setattr(media_engines, "_request_json", lambda url, payload, timeout=10: captured.update({"url": url, "payload": payload}) or {"prompt_id": "abc-123"})
    result = media_engines.submit_generation("image", "a real prompt")
    assert result == {"id": "abc-123", "kind": "image", "status": "queued", "engine": "comfyui-local"}
    assert captured["payload"]["prompt"]["6"]["inputs"]["text"] == "a real prompt"
    assert workflow["6"]["inputs"]["text"] == "old prompt"

def test_artifact_validation_rejects_path_traversal():
    with pytest.raises(ValueError, match="Invalid artifact reference"):
        media_engines.read_artifact("../secret.png")
    with pytest.raises(ValueError, match="Invalid artifact subfolder"):
        media_engines.read_artifact("image.png", "../private")
