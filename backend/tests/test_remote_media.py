import pytest
from app import remote_media


def test_provider_status_requires_secrets_and_space_api(monkeypatch):
    for key in ("POLLINATIONS_API_KEY", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN", "MESH3D_HF_SPACE_URL", "MESH3D_HF_IMAGE_API_NAME", "MESH3D_HF_VIDEO_API_NAME"):
        monkeypatch.delenv(key, raising=False)
    status = {item["id"]: item for item in remote_media.provider_status()}
    assert status["pollinations"]["ready"] is False
    assert status["cloudflare-workers-ai"]["ready"] is False
    assert status["huggingface-spaces"]["ready"] is False
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "token")
    assert {item["id"]: item for item in remote_media.provider_status()}["cloudflare-workers-ai"]["ready"] is True


def test_huggingface_args_need_exactly_one_prompt_marker():
    assert remote_media._valid_args('["__PROMPT__", 7]')
    assert not remote_media._valid_args('["__PROMPT__", "__PROMPT__"]')
    assert not remote_media._valid_args('["fixed"]')
    assert not remote_media._valid_args('{"prompt":"__PROMPT__"}')


def test_remote_submission_validates_provider_kind_prompt_and_configuration(monkeypatch, tmp_path):
    monkeypatch.setattr(remote_media, "DATA_DIR", tmp_path)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "token")
    result = remote_media.submit_remote_generation("cloudflare-workers-ai", "image", "A real subject")
    assert result["status"] == "queued"
    assert result["id"].startswith("remote_")
    assert remote_media.remote_generation_status(result["id"])["provider"] == "cloudflare-workers-ai"
    with pytest.raises(ValueError):
        remote_media.submit_remote_generation("cloudflare-workers-ai", "video", "prompt")
    with pytest.raises(ValueError):
        remote_media.submit_remote_generation("unknown", "image", "prompt")
    with pytest.raises(ValueError):
        remote_media.submit_remote_generation("cloudflare-workers-ai", "image", "  ")
    with pytest.raises(RuntimeError):
        remote_media.submit_remote_generation("huggingface-spaces", "image", "prompt")


def test_remote_generation_persists_real_bytes_and_mime(monkeypatch, tmp_path):
    monkeypatch.setattr(remote_media, "DATA_DIR", tmp_path)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "token")
    job = remote_media.submit_remote_generation("cloudflare-workers-ai", "image", "subject")
    monkeypatch.setattr(remote_media, "_generate", lambda *args: (b"\x89PNG\r\n\x1a\nactual-test-bytes", "image/png"))
    remote_media.run_remote_generation(job["id"], "cloudflare-workers-ai", "image", "subject")
    status = remote_media.remote_generation_status(job["id"])
    assert status["status"] == "completed"
    assert status["outputs"][0]["sha256"]
    content, content_type = remote_media.read_remote_artifact(job["id"], status["outputs"][0]["filename"], "remote")
    assert content == b"\x89PNG\r\n\x1a\nactual-test-bytes"
    assert content_type == "image/png"


def test_remote_generation_failure_is_not_reported_as_success(monkeypatch, tmp_path):
    monkeypatch.setattr(remote_media, "DATA_DIR", tmp_path)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "token")
    job = remote_media.submit_remote_generation("cloudflare-workers-ai", "image", "subject")
    monkeypatch.setattr(remote_media, "_generate", lambda *args: (_ for _ in ()).throw(RuntimeError("provider quota exhausted")))
    remote_media.run_remote_generation(job["id"], "cloudflare-workers-ai", "image", "subject")
    status = remote_media.remote_generation_status(job["id"])
    assert status["status"] == "failed"
    assert status["outputs"] == []
