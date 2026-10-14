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
if not shutil.which(colmap) and not Path(colmap).is_file():
    raise SystemExit(f"Required executable not found: {colmap}")
required = ["InterfaceCOLMAP", "DensifyPointCloud", "ReconstructMesh", "TextureMesh"]
binaries = {name: (mvs / name) for name in required}
missing = [str(path) for path in binaries.values() if not path.is_file()]
if missing:
    raise SystemExit("Missing OpenMVS executables: " + ", ".join(missing))

# OpenMVS links Qt GUI; allow headless hosts to force the offscreen platform.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

use_gpu = os.getenv("MESH3D_COLMAP_USE_GPU", "0").lower() == "1"
feature_flags = [] if use_gpu else ["--SiftExtraction.use_gpu", "0"]
match_flags = [] if use_gpu else ["--SiftMatching.use_gpu", "0"]

image_dir = args.input_dir.resolve()
run_command([colmap, "feature_extractor", "--database_path", str(database), "--image_path", str(image_dir), *feature_flags])
run_command([colmap, "exhaustive_matcher", "--database_path", str(database), *match_flags])
run_command([colmap, "mapper", "--database_path", str(database), "--image_path", str(image_dir), "--output_path", str(sparse)])
models = sorted(p for p in sparse.iterdir() if p.is_dir() and (p / "cameras.bin").is_file())
if not models:
    raise SystemExit("COLMAP did not register a sparse model; check image overlap and feature matching.")
model = models[0]

# OpenMVS requires undistorted PINHOLE cameras; default COLMAP models are radial.
undistorted = work / "undistorted"
run_command([
    colmap, "image_undistorter",
    "--image_path", str(image_dir),
    "--input_path", str(model),
    "--output_path", str(undistorted),
    "--output_type", "COLMAP",
])
if not (undistorted / "sparse" / "cameras.bin").is_file():
    raise SystemExit("COLMAP image_undistorter did not produce a PINHOLE sparse model for OpenMVS.")

scene = work / "scene.mvs"
run_command([
    str(binaries["InterfaceCOLMAP"]),
    "-i", str(undistorted),
    "-o", str(scene),
    "--image-folder", str(undistorted / "images"),
])
if not scene.is_file() or scene.stat().st_size == 0:
    raise SystemExit("InterfaceCOLMAP did not write scene.mvs.")

dense = work / "scene_dense.mvs"
run_command([str(binaries["DensifyPointCloud"]), "-i", str(scene), "-o", str(dense), "--max-threads", os.getenv("MESH3D_OPENMVS_THREADS", "2")], cwd=work)
if not dense.is_file() or dense.stat().st_size == 0:
    raise SystemExit("DensifyPointCloud did not write scene_dense.mvs.")

mesh_ply = work / "scene_dense_mesh.ply"
run_command([str(binaries["ReconstructMesh"]), "-i", str(dense), "-o", str(mesh_ply), "--export-type", "ply", "--max-threads", os.getenv("MESH3D_OPENMVS_THREADS", "2")], cwd=work)
if not mesh_ply.is_file() or mesh_ply.stat().st_size == 0:
    raise SystemExit("ReconstructMesh did not write scene_dense_mesh.ply.")

textured = out / "textured_model.obj"
run_command([
    str(binaries["TextureMesh"]),
    "-i", str(dense),
    "-m", str(mesh_ply),
    "-o", str(textured),
    "--export-type", "obj",
    "--max-threads", os.getenv("MESH3D_OPENMVS_THREADS", "2"),
], cwd=work)
if not textured.is_file() or textured.stat().st_size == 0:
    raise SystemExit("TextureMesh did not write textured_model.obj.")

artifacts = collect_outputs(out)
write_manifest(out, artifacts)
