#!/usr/bin/env python3
"""InstantMesh adapter. Requires the official checkout, pinned dependencies and model weights."""
from pathlib import Path
import os, sys
from common import parse_args, validate_inputs, required_env, run_command, collect_outputs, write_manifest

args = parse_args("Run official InstantMesh inference for one uploaded image.")
images = validate_inputs(args, single=True)
root = Path(required_env("MESH3D_INSTANTMESH_ROOT")).resolve()
run_py = root / "run.py"
config = Path(os.getenv("MESH3D_INSTANTMESH_CONFIG", str(root / "configs/instant-mesh-large.yaml"))).resolve()
if not run_py.is_file() or not config.is_file():
    raise SystemExit("InstantMesh requires run.py and a valid MESH3D_INSTANTMESH_CONFIG YAML.")
# Official run.py interface: config YAML, input image, --output_path.
argv = [sys.executable, str(run_py), str(config), str(images[0]), "--output_path", str(args.output_dir.resolve())]
if os.getenv("MESH3D_INSTANTMESH_SAVE_VIDEO", "false").lower() == "true":
    argv.append("--save_video")
run_command(argv, cwd=root)
write_manifest(args.output_dir, collect_outputs(args.output_dir))
