#!/usr/bin/env python3
"""COLMAP + OpenMVS multi-view reconstruction adapter."""
from pathlib import Path
import os, shutil
from common import parse_args, validate_inputs, required_env, run_command, collect_outputs, write_manifest

args = parse_args("Run COLMAP SfM, OpenMVS densification, meshing and texturing.")
images = validate_inputs(args, minimum=2)
out = args.output_dir.resolve()
work = out / "colmap"
work.mkdir(parents=True, exist_ok=True)
database = work / "database.db"
sparse = work / "sparse"
sparse.mkdir(exist_ok=True)
colmap = os.getenv("MESH3D_COLMAP_BIN", "colmap")
mvs = Path(required_env("MESH3D_OPENMVS_BIN_DIR")).resolve()
for binary in (colmap,):
    if not shutil.which(binary) and not Path(binary).is_file():
        raise SystemExit(f"Required executable not found: {binary}")
required = ["InterfaceCOLMAP", "DensifyPointCloud", "ReconstructMesh", "TextureMesh"]
binaries = {name: (mvs / name) for name in required}
missing = [str(path) for path in binaries.values() if not path.is_file()]
if missing:
    raise SystemExit("Missing OpenMVS executables: " + ", ".join(missing))
run_command([colmap, "feature_extractor", "--database_path", str(database), "--image_path", str(args.input_dir.resolve())])
run_command([colmap, "exhaustive_matcher", "--database_path", str(database)])
run_command([colmap, "mapper", "--database_path", str(database), "--image_path", str(args.input_dir.resolve()), "--output_path", str(sparse)])
models = sorted(p for p in sparse.iterdir() if p.is_dir())
if not models:
    raise SystemExit("COLMAP did not register a sparse model; check image overlap and feature matching.")
model = models[0]
scene = work / "scene.mvs"
run_command([str(binaries["InterfaceCOLMAP"]), "-i", str(model), "-o", str(scene), "--image-folder", str(args.input_dir.resolve())])
dense = work / "scene_dense.mvs"
run_command([str(binaries["DensifyPointCloud"]), str(scene), "-o", str(dense)])
mesh = work / "scene_dense_mesh.mvs"
run_command([str(binaries["ReconstructMesh"]), str(dense), "-o", str(mesh)])
textured = out / "textured_model.obj"
run_command([str(binaries["TextureMesh"]), str(mesh), "-o", str(textured), "--export-type", "obj"])
artifacts = collect_outputs(out)
write_manifest(out, artifacts)
