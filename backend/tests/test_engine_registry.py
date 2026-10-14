import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.engine_registry import ENGINES, public_engine, resolve_engine


def _valid_report(engine_id: str) -> dict:
    return {
        "schema_version": 1,
        "engine_id": engine_id,
        "result": "passed",
        "upstream_commit": "a" * 40,
        "checkpoint": {
            "id": "test-model",
            "revision": "immutable-test-revision",
            "sha256": "b" * 64,
            "license": "reviewed-license",
        },
        "dependency_lock_sha256": "c" * 64,
        "hardware": {"cpu": "test CPU", "accelerator": "none", "ram_gb": 8},
        "smoke_test": {
            "exit_code": 0,
            "input_sha256": "d" * 64,
            "output_path": "outputs/reconstruction.glb",
            "output_sha256": "e" * 64,
            "output_bytes": 1024,
            "opened_in_viewer": True,
        },
        "license_review": {
            "decision": "approved",
            "reviewer": "test reviewer",
            "reviewed_at": "2026-10-14",
        },
    }


def _write_report(tmp_path: Path, engine_id: str, report: dict | None = None) -> Path:
    path = tmp_path / f"{engine_id}-validation.json"
    path.write_text(json.dumps(report or _valid_report(engine_id)), encoding="utf-8")
    return path


def test_candidates_are_explicitly_gated_by_default():
    with patch.dict("os.environ", {}, clear=True):
        entries = [public_engine(engine) for engine in ENGINES]
    assert len(entries) == 3
    assert all(entry["status"] != "ready" for entry in entries)
    assert all(entry["reason"] for entry in entries)


def test_engine_requires_command_and_real_validation_report(tmp_path):
    engine = next(item for item in ENGINES if item.id == "triposr")
    command = json.dumps(["python", "wrapper.py", "--input-dir", "{input_dir}", "--output-dir", "{output_dir}"])
    base_env = {engine.command_env: command}

    with patch.dict("os.environ", base_env, clear=True):
        assert public_engine(engine)["status"] == "validation_required"
        with pytest.raises(RuntimeError, match="unavailable"):
            resolve_engine("triposr")

    report_path = _write_report(tmp_path, engine.id)
    with patch.dict("os.environ", {**base_env, engine.validation_report_env: str(report_path)}, clear=True):
        assert public_engine(engine)["status"] == "ready"
        resolved, resolved_command = resolve_engine("triposr")
        assert resolved.id == "triposr" and "{input_dir}" in resolved_command


def test_extra_review_engine_needs_only_command_and_validation_report(tmp_path):
    engine = next(item for item in ENGINES if item.id == "colmap_openmvs")
    env = {
        engine.command_env: json.dumps(["python", "wrapper.py"]),
        engine.validation_report_env: str(_write_report(tmp_path, engine.id)),
    }
    with patch.dict("os.environ", env, clear=True):
        assert public_engine(engine)["status"] == "ready"


def test_legacy_license_approved_env_is_ignored(tmp_path):
    engine = next(item for item in ENGINES if item.id == "triposr")
    command = json.dumps(["python", "wrapper.py"])
    legacy_env = {
        engine.command_env: command,
        "MESH3D_ENGINE_TRIPOSR_LICENSE_APPROVED": "true",
        "MESH3D_ENGINE_TRIPOSR_LICENSE_APPROVED_EXTRA": "true",
    }
    with patch.dict("os.environ", legacy_env, clear=True):
        assert public_engine(engine)["status"] == "validation_required"
    report_path = _write_report(tmp_path, engine.id)
    with patch.dict("os.environ", {**legacy_env, engine.validation_report_env: str(report_path)}, clear=True):
        assert public_engine(engine)["status"] == "ready"


def test_report_must_include_real_artifact_evidence(tmp_path):
    engine = next(item for item in ENGINES if item.id == "triposr")
    report = _valid_report(engine.id)
    report["smoke_test"]["output_bytes"] = 0
    report_path = _write_report(tmp_path, engine.id, report)
    env = {
        engine.command_env: json.dumps(["python", "wrapper.py"]),
        engine.validation_report_env: str(report_path),
    }
    with patch.dict("os.environ", env, clear=True):
        entry = public_engine(engine)
    assert entry["status"] == "validation_required"
    assert "non-empty output artifact" in entry["reason"]


def test_report_without_approved_license_review_is_rejected(tmp_path):
    engine = next(item for item in ENGINES if item.id == "triposr")
    report = _valid_report(engine.id)
    report["license_review"]["decision"] = "pending"
    report_path = _write_report(tmp_path, engine.id, report)
    env = {
        engine.command_env: json.dumps(["python", "wrapper.py"]),
        engine.validation_report_env: str(report_path),
    }
    with patch.dict("os.environ", env, clear=True):
        entry = public_engine(engine)
    assert entry["status"] == "validation_required"
    assert "license review" in entry["reason"]


def test_unknown_engine_is_rejected():
    with pytest.raises(ValueError):
        resolve_engine("not-an-engine")


def test_malformed_command_is_not_accepted():
    engine = next(item for item in ENGINES if item.id == "triposr")
    with patch.dict("os.environ", {engine.command_env: "python wrapper.py"}, clear=True):
        assert public_engine(engine)["status"] == "not_configured"
