import pytest

from app import blender_engine


def test_blender_engine_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("MESH3D_BLENDER_ENABLED", raising=False)
    monkeypatch.delenv("MESH3D_BLENDER_WORKER_URL", raising=False)
    monkeypatch.delenv("MESH3D_BLENDER_WORKER_TOKEN", raising=False)
    status = blender_engine.blender_engine_status()
    assert status["ready"] is False
    assert status["configured"] is False
    assert "MESH3D_BLENDER_ENABLED=true" in status["reason"]


def test_submit_rejects_empty_prompt_before_worker_access():
    with pytest.raises(ValueError, match="Prompt is required"):
        blender_engine.submit_blender_job("image", " ")


def test_submit_rejects_unknown_output_kind():
    with pytest.raises(ValueError, match="kind must be image or video"):
        blender_engine.submit_blender_job("3d", "A detailed object")


def test_job_id_and_artifact_filename_are_validated():
    with pytest.raises(ValueError, match="Invalid Blender job ID"):
        blender_engine.blender_job_status("../bad")
    with pytest.raises(ValueError, match="Invalid artifact reference"):
        blender_engine.read_blender_artifact("00000000-0000-0000-0000-000000000000", "../secret")
