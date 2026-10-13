#!/usr/bin/env python3
"""TripoSR adapter. Requires a separately installed, license-reviewed upstream checkout."""
from pathlib import Path
import os, sys
from common import parse_args, validate_inputs, required_env, run_command, collect_outputs, write_manifest

args = parse_args("Run official TripoSR inference for one uploaded image.")
images = validate_inputs(args, single=True)
root = Path(required_env("MESH3D_TRIPOSR_ROOT")).resolve()
run_py = root / "run.py"
if not run_py.is_file():
    raise SystemExit(f"TripoSR checkout does not contain run.py: {root}")
argv = [sys.executable, str(run_py), str(images[0]), "--output-dir", str(args.output_dir.resolve())]
if os.getenv("MESH3D_TRIPOSR_BAKE_TEXTURE", "true").lower() == "true":
    argv.append("--bake-texture")
run_command(argv, cwd=root)
write_manifest(args.output_dir, collect_outputs(args.output_dir))
