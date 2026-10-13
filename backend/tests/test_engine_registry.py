import json
from unittest.mock import patch
import pytest
from app.engine_registry import ENGINES, public_engine, resolve_engine

def test_candidates_are_explicitly_gated_by_default():
    with patch.dict("os.environ", {}, clear=True):
        entries = [public_engine(engine) for engine in ENGINES]
    assert len(entries) >= 7
    assert all(entry["status"] != "ready" for entry in entries)
    assert all(entry["reason"] for entry in entries)

def test_engine_requires_both_approval_and_wrapper():
    engine = next(item for item in ENGINES if item.id == "triposr")
    with patch.dict("os.environ", {engine.approval_env: "true"}, clear=True):
        assert public_engine(engine)["status"] == "not_configured"
        with pytest.raises(RuntimeError): resolve_engine("triposr")
    with patch.dict("os.environ", {engine.approval_env: "true", engine.command_env: json.dumps(["python", "wrapper.py", "--input-dir", "{input_dir}", "--output-dir", "{output_dir}"])}, clear=True):
        assert public_engine(engine)["status"] == "ready"
        resolved, command = resolve_engine("triposr")
        assert resolved.id == "triposr" and "{input_dir}" in command

def test_extra_review_engines_remain_disabled_until_second_gate():
    engine = next(item for item in ENGINES if item.id == "colmap_openmvs")
    env = {engine.approval_env: "true", engine.command_env: json.dumps(["python", "wrapper.py"])}
    with patch.dict("os.environ", env, clear=True): assert public_engine(engine)["status"] == "license_review"
    with patch.dict("os.environ", {**env, f"{engine.approval_env}_EXTRA": "true"}, clear=True): assert public_engine(engine)["status"] == "ready"

def test_unknown_engine_is_rejected():
    with pytest.raises(ValueError): resolve_engine("not-an-engine")

def test_malformed_command_is_not_accepted():
    engine = next(item for item in ENGINES if item.id == "triposr")
    with patch.dict("os.environ", {engine.approval_env: "true", engine.command_env: "python wrapper.py"}, clear=True):
        assert public_engine(engine)["status"] == "not_configured"
