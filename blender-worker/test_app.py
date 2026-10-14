import io
import json
from pathlib import Path

import pytest
from PIL import Image

import app as worker


def test_pixel_comparison_reports_exact_equality(tmp_path):
    source = Image.new("RGB", (8, 8), (20, 40, 60))
    reference = tmp_path / "reference.png"
    render = tmp_path / "render.png"
    diff = tmp_path / "diff.png"
    source.save(reference)
    source.save(render)
    metrics = worker._compare(reference, render, diff)
    assert metrics["exact_pixel_match"] is True
    assert metrics["changed_pixel_count"] == 0
    assert metrics["mean_absolute_error"] == 0
    assert diff.is_file()


def test_pixel_comparison_counts_changed_pixels(tmp_path):
    Image.new("RGB", (8, 8), (20, 40, 60)).save(tmp_path / "reference.png")
    image = Image.new("RGB", (8, 8), (20, 40, 60))
    image.putpixel((2, 3), (255, 0, 0))
    image.save(tmp_path / "render.png")
    metrics = worker._compare(tmp_path / "reference.png", tmp_path / "render.png", tmp_path / "diff.png")
    assert metrics["exact_pixel_match"] is False
    assert metrics["changed_pixel_count"] == 1
    assert metrics["mean_absolute_error"] > 0


def test_script_validator_rejects_unapproved_imports():
    script = "import os\nOUTPUT_IMAGE = __MESH3D_OUTPUT_IMAGE__\nOUTPUT_BLEND = __MESH3D_OUTPUT_BLEND__\nFRAME_PREFIX = __MESH3D_FRAME_PREFIX__\nbpy.ops.render.render(write_still=True)\nbpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND)"
    with pytest.raises(RuntimeError, match="allowlist"):
        worker._validate_script(script)


def test_script_validator_rejects_dynamic_execution():
    script = "import bpy\nOUTPUT_IMAGE = __MESH3D_OUTPUT_IMAGE__\nOUTPUT_BLEND = __MESH3D_OUTPUT_BLEND__\nFRAME_PREFIX = __MESH3D_FRAME_PREFIX__\nexec('bad')\nbpy.ops.render.render(write_still=True)\nbpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND)"
    with pytest.raises(RuntimeError, match="forbidden"):
        worker._validate_script(script)


def test_script_validator_accepts_required_blender_script():
    script = "import bpy\nfrom mathutils import Vector\nOUTPUT_IMAGE = __MESH3D_OUTPUT_IMAGE__\nOUTPUT_BLEND = __MESH3D_OUTPUT_BLEND__\nFRAME_PREFIX = __MESH3D_FRAME_PREFIX__\nbpy.ops.render.render(write_still=True)\nbpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND)"
    worker._validate_script(script)


def test_worker_requires_authentication(monkeypatch):
    monkeypatch.setenv("MESH3D_BLENDER_WORKER_TOKEN", "secret-token")
    with pytest.raises(Exception) as error:
        worker._authorized("Bearer wrong-token")
    assert getattr(error.value, "status_code", None) == 401
