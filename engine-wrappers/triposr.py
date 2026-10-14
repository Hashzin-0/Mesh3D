#!/usr/bin/env python3
"""TripoSR adapter. Requires a separately installed, license-reviewed upstream checkout."""
from pathlib import Path
import os, sys
from common import parse_args, validate_inputs, required_env, engine_python, run_command, collect_outputs, write_manifest

args = parse_args("Run official TripoSR inference for one uploaded image.")
images = validate_inputs(args, single=True)
root = Path(required_env("MESH3D_TRIPOSR_ROOT")).resolve()
run_py = root / "run.py"
if not run_py.is_file():
    raise SystemExit(f"TripoSR checkout does not contain run.py: {root}")
argv = [engine_python("MESH3D_TRIPOSR", root), str(run_py), str(images[0]), "--output-dir", str(args.output_dir.resolve()), "--device", os.getenv("MESH3D_TRIPOSR_DEVICE", "cpu")]
if os.getenv("MESH3D_TRIPOSR_BAKE_TEXTURE", "true").lower() == "true":
    argv.append("--bake-texture")
chunk_size = os.getenv("MESH3D_TRIPOSR_CHUNK_SIZE", "").strip()
if chunk_size.isdigit():
    argv.extend(["--chunk-size", chunk_size])
mc_resolution = os.getenv("MESH3D_TRIPOSR_MC_RESOLUTION", "").strip()
if mc_resolution.isdigit():
    argv.extend(["--mc-resolution", mc_resolution])
run_command(argv, cwd=root)
write_manifest(args.output_dir, collect_outputs(args.output_dir))
