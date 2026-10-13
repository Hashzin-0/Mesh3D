#!/usr/bin/env python3
"""VGGT multi-view geometry adapter; exports its real COLMAP/point-cloud output, not a fabricated mesh."""
from pathlib import Path
import os, sys
from common import parse_args, validate_inputs, required_env, engine_python, run_command, collect_outputs, write_manifest

args = parse_args("Run VGGT geometry inference for a multi-view image set.")
validate_inputs(args, minimum=2)
root = Path(required_env("MESH3D_VGGT_ROOT")).resolve()
demo = root / "demo_colmap.py"
if not demo.is_file():
    raise SystemExit(f"VGGT checkout missing demo_colmap.py: {root}")
scene = args.output_dir.resolve() / "vggt_scene"
(scene / "images").mkdir(parents=True, exist_ok=True)
# Copy inputs into VGGT's documented scene/images structure; no synthetic images or geometry.
import shutil
for image in sorted(args.input_dir.resolve().iterdir()):
    if image.is_file() and image.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
        shutil.copy2(image, scene / "images" / image.name)
argv = [engine_python("MESH3D_VGGT", root), str(demo), f"--scene_dir={scene}"]
if os.getenv("MESH3D_VGGT_USE_BA", "false").lower() == "true":
    argv.append("--use_ba")
run_command(argv, cwd=root)
# VGGT's official export is a COLMAP scene/point cloud, not a watertight textured mesh.
artifacts = []
for path in scene.rglob("*"):
    if path.is_file() and path.suffix.lower() in {".ply", ".obj"}:
        artifacts.append(path)
if not artifacts:
    raise SystemExit("VGGT completed without a PLY/OBJ artifact. The official COLMAP output may exist, but no viewer-ready point cloud was found.")
write_manifest(args.output_dir, artifacts)
