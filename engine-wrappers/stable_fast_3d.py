#!/usr/bin/env python3
"""Stable Fast 3D adapter; requires Hugging Face access to the gated checkpoint."""
from pathlib import Path
import os, sys
from common import parse_args, validate_inputs, required_env, engine_python, run_command, collect_outputs, write_manifest

args = parse_args("Run official Stable Fast 3D inference for one uploaded image.")
images = validate_inputs(args, single=True)
root = Path(required_env("MESH3D_STABLE_FAST_3D_ROOT")).resolve()
run_py = root / "run.py"
if not run_py.is_file():
    raise SystemExit(f"Stable Fast 3D checkout does not contain run.py: {root}")
# Keep the official CLI as the source of truth; options match the upstream README.
argv = [engine_python("MESH3D_STABLE_FAST_3D", root), str(run_py), str(images[0]), "--output-dir", str(args.output_dir.resolve())]
run_command(argv, cwd=root)
write_manifest(args.output_dir, collect_outputs(args.output_dir))
