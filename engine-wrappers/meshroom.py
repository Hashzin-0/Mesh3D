#!/usr/bin/env python3
"""AliceVision/Meshroom multi-view photogrammetry adapter."""
from pathlib import Path
import os, shutil
from common import parse_args, validate_inputs, required_env, run_command, collect_outputs, write_manifest

args = parse_args("Run Meshroom photogrammetry for a multi-view image set.")
validate_inputs(args, minimum=2)
root = Path(required_env("MESH3D_MESHROOM_ROOT")).resolve()
batch = os.getenv("MESH3D_MESHROOM_BATCH", "meshroom_batch")
if not shutil.which(batch) and not Path(batch).is_file():
    raise SystemExit("meshroom_batch not found; set MESH3D_MESHROOM_BATCH to its executable path.")
project = args.output_dir.resolve() / "meshroom_project.mg"
# Full photogrammetry needs CUDA depth maps; photogrammetryDraft runs CPU-only SfM+meshing+texturing.
pipeline = os.getenv("MESH3D_MESHROOM_PIPELINE", "photogrammetryDraft").strip() or "photogrammetryDraft"
argv = [batch, "--input", str(args.input_dir.resolve()), "--output", str(args.output_dir.resolve()), "--save", str(project), "--pipeline", pipeline]
run_command(argv, cwd=root)
write_manifest(args.output_dir, collect_outputs(args.output_dir))
