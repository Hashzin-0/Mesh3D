from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "engine-wrappers"))
from common import collect_outputs, validate_inputs, write_manifest


def make_image(path: Path) -> None:
    Image.new("RGB", (96, 96), (120, 120, 120)).save(path)


def test_single_image_adapter_rejects_multi_view_mode(tmp_path: Path) -> None:
    input_dir = tmp_path / "inputs"
    output_dir = tmp_path / "outputs"
    input_dir.mkdir()
    make_image(input_dir / "one.png")
    args = SimpleNamespace(input_dir=input_dir, output_dir=output_dir, mode="multi_view")
    with pytest.raises(SystemExit, match="single_image"):
        validate_inputs(args, single=True)


def test_multiview_requires_two_real_images(tmp_path: Path) -> None:
    input_dir = tmp_path / "inputs"
    output_dir = tmp_path / "outputs"
    input_dir.mkdir()
    make_image(input_dir / "one.png")
    args = SimpleNamespace(input_dir=input_dir, output_dir=output_dir, mode="multi_view")
    with pytest.raises(SystemExit, match="at least 2"):
        validate_inputs(args, minimum=2)


def test_manifest_only_contains_real_artifacts_inside_output(tmp_path: Path) -> None:
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    artifact = output_dir / "model.glb"
    artifact.write_bytes(b"test artifact bytes")
    write_manifest(output_dir, [artifact])
    manifest = output_dir / "manifest.json"
    assert manifest.is_file()
    assert '"path": "model.glb"' in manifest.read_text(encoding="utf-8")


def test_manifest_rejects_artifact_outside_output(tmp_path: Path) -> None:
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    outside = tmp_path / "outside.obj"
    outside.write_text("not a real mesh", encoding="utf-8")
    with pytest.raises(SystemExit, match="outside output directory"):
        write_manifest(output_dir, [outside])


def test_collector_prefers_viewer_ready_glb(tmp_path: Path) -> None:
    output_dir = tmp_path / "outputs"
    nested = output_dir / "upstream"
    nested.mkdir(parents=True)
    (nested / "pointcloud.ply").write_bytes(b"ply")
    glb = nested / "model.glb"
    glb.write_bytes(b"glb")
    assert collect_outputs(output_dir) == [glb]
