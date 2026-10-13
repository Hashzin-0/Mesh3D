#!/usr/bin/env python3
"""Hunyuan3D 2.1 adapter using its Python shape-generation pipeline."""
from pathlib import Path
import os
from common import parse_args, validate_inputs, required_env, write_manifest

args = parse_args("Run Hunyuan3D 2.1 shape generation for one image.")
images = validate_inputs(args, single=True)
root = Path(required_env("MESH3D_HUNYUAN3D_ROOT")).resolve()
if not (root / "hy3dgen").is_dir():
    raise SystemExit(f"Hunyuan3D 2.1 checkout missing hy3dgen package: {root}")
# Run in a fresh interpreter so the upstream checkout is imported from its own root.
import subprocess, sys
script = r'''
import os, sys
from pathlib import Path
from PIL import Image
import trimesh
root, image_path, output_dir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(root))
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
model_id = os.getenv("MESH3D_HUNYUAN3D_MODEL", "tencent/Hunyuan3D-2.1")
subfolder = os.getenv("MESH3D_HUNYUAN3D_SUBFOLDER", "hunyuan3d-dit-v2-1")
pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(model_id, subfolder=subfolder)
result = pipe(image=Image.open(image_path).convert("RGBA"), num_inference_steps=int(os.getenv("MESH3D_HUNYUAN3D_STEPS", "30")), octree_resolution=int(os.getenv("MESH3D_HUNYUAN3D_OCTREE_RESOLUTION", "256")), output_type="trimesh")
mesh = result[0] if isinstance(result, (list, tuple)) else result
if not isinstance(mesh, trimesh.Trimesh):
    mesh = trimesh.Trimesh(vertices=mesh.vertices, faces=mesh.faces, process=False)
target = output_dir / "hunyuan3d_mesh.glb"
mesh.export(target)
if not target.is_file() or target.stat().st_size == 0:
    raise RuntimeError("Hunyuan3D pipeline did not produce a non-empty GLB.")
print(f"Exported {target} ({target.stat().st_size} bytes)")
'''
completed = subprocess.run([sys.executable, "-c", script, str(root), str(images[0]), str(args.output_dir.resolve())], cwd=root, check=False)
if completed.returncode:
    raise SystemExit(f"Hunyuan3D upstream pipeline exited with code {completed.returncode}.")
write_manifest(args.output_dir, [args.output_dir / "hunyuan3d_mesh.glb"])
