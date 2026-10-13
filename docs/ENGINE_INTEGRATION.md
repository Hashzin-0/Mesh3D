# Engine integration and local runtime setup

This document describes the real upstream adapters in `engine-wrappers/`. The adapter scripts are committed; upstream repositories, Python/CUDA environments, weights, and hardware are intentionally provisioned by the operator and are not vendored into Mesh3D. **A committed adapter is not proof that its model has run successfully.** Do not approve an engine until the smoke test below passes on the intended host.

## Runtime topology

- API and Celery worker share the persistent `/data` volume, so the worker can read uploaded images and store outputs.
- The worker mounts `./engine-wrappers` read-only at `/opt/mesh3d/wrappers` and optional upstream checkouts from `./engines` at `/opt/mesh3d/engines`.
- Each Python engine should have its own environment. Configure its interpreter with the corresponding `MESH3D_*_PYTHON` variable or place a `.venv/bin/python` inside that checkout.
- Model caches belong under `/data/model-cache`; do not commit model weights, tokens, private fixtures, or output artifacts.
- The engine registry's license approval flags are explicit launch gates, not legal advice. Keep them false until you have reviewed the exact upstream revision, checkpoint license, intended use, redistribution, and commercial deployment terms.

## Adapters and upstream contracts

| Mesh3D ID | Adapter | Input | Upstream invocation / output |
|---|---|---|---|
| `triposr` | `triposr.py` | Exactly one image | Official `run.py IMAGE --output-dir DIR`; optionally requests baked texture; publishes real GLB/GLTF or mesh output discovered in the directory. |
| `instantmesh` | `instantmesh.py` | Exactly one image | Official `run.py CONFIG IMAGE --output_path DIR`; default config is `configs/instant-mesh-large.yaml`; publishes the generated mesh. |
| `stable_fast_3d` | `stable_fast_3d.py` | Exactly one image | Official `run.py IMAGE --output-dir DIR`; requires access to the gated Stability AI checkpoint. |
| `hunyuan3d` | `hunyuan3d.py` | Exactly one image | Loads `Hunyuan3DDiTFlowMatchingPipeline` from the Hunyuan3D 2.1 checkout and exports the returned mesh to GLB. |
| `meshroom` | `meshroom.py` | At least two views | Runs `meshroom_batch --input DIR --output DIR --save PROJECT.mg`; reports actual mesh files produced by the photogrammetry graph. |
| `colmap_openmvs` | `colmap_openmvs.py` | At least two views | Runs COLMAP feature extraction, exhaustive matching and mapper, then OpenMVS `InterfaceCOLMAP`, `DensifyPointCloud`, `ReconstructMesh`, and `TextureMesh`. |
| `vggt` | `vggt.py` | At least two views | Runs official `demo_colmap.py --scene_dir=...`; reports the actual point-cloud/COLMAP-derived PLY or OBJ artifact. VGGT estimates geometry; it does not by itself promise a watertight textured mesh. |

Official references:
- TripoSR: https://github.com/VAST-AI-Research/TripoSR
- InstantMesh: https://github.com/TencentARC/InstantMesh
- Stable Fast 3D: https://github.com/Stability-AI/stable-fast-3d
- Hunyuan3D 2.1: https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1
- Meshroom: https://github.com/alicevision/Meshroom
- COLMAP: https://github.com/colmap/colmap
- OpenMVS: https://github.com/cdcseacave/openMVS
- VGGT: https://github.com/facebookresearch/vggt

## Provisioning

1. Create the local directory `engines/`. Clone each upstream project at a reviewed commit; record that full commit SHA and checkpoint revision in `docs/ENGINE_PROVENANCE.md`.
2. Install dependencies following each upstream repository's current instructions in a separate environment. Do not share one environment across the four PyTorch generators: their dependency/CUDA constraints differ.
3. Configure `*_ROOT`, `*_PYTHON`, and binary paths in a private `.env`. For gated weights, configure `HF_TOKEN` privately only after access has been granted.
4. Confirm Docker can access the host GPU. The default Compose file intentionally does not force GPU reservations, so the UI/API can start on machines without NVIDIA runtime. For GPU inference, use a Compose GPU override compatible with the host's NVIDIA Container Toolkit or run the worker on a GPU-enabled host. Model runtimes and CUDA are not installed by the generic API Dockerfile.
5. Start the stack with `docker compose up --build`. For a host configured with the NVIDIA Container Toolkit, use `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build` to request GPU access for the worker. Inspect `GET /api/engines`; a candidate remains unavailable until command configuration and approval gates are both satisfied.

Example command configuration (the actual `.env.example` contains all seven):
```dotenv
MESH3D_ENGINE_TRIPOSR_CMD=["python","/opt/mesh3d/wrappers/triposr.py","--input-dir","{input_dir}","--output-dir","{output_dir}","--mode","{mode}"]
MESH3D_TRIPOSR_ROOT=/opt/mesh3d/engines/TripoSR
MESH3D_TRIPOSR_PYTHON=/opt/mesh3d/engines/TripoSR/.venv/bin/python
MESH3D_ENGINE_TRIPOSR_LICENSE_APPROVED=false
```

## Smoke test and release gate

For each engine, using the exact intended runtime and a rights-cleared fixture:

1. Leave the license flag false while provisioning and checking dependencies.
2. Invoke the wrapper manually with `--input-dir`, `--output-dir`, and the correct `--mode`. Confirm it exits non-zero on missing weights or incompatible dependencies.
3. Confirm `manifest.json` is created only after a real output file exists, and that each manifest path is relative, remains within the output directory, and opens in a suitable viewer.
4. Submit a job through the UI/API and verify status, elapsed time, logs, artifact byte count and SHA-256.
5. Inspect geometry, scale, normals, UVs/materials, holes, floating parts, camera coverage, and output format manually. A successful process exit is not a quality score.
6. Record GPU/CPU model, VRAM/RAM, driver/CUDA/PyTorch versions, upstream commit SHA, checkpoint revision and license, elapsed time, errors, output hash, and reviewer in `docs/ENGINE_TEST_REPORT.md`.
7. Only then set the matching license approval flags after completing the legal review. Stable Fast 3D, Hunyuan3D 2.1, COLMAP + OpenMVS, and VGGT have an additional review gate in the registry.

## Known boundaries

- These adapters are not model binaries or a universal Docker image. The actual upstream runtimes and checkpoints must be installed separately.
- The generic worker shares a process/container and is suitable only for controlled local evaluation. It is not a hardened multi-tenant job sandbox.
- Meshroom and COLMAP/OpenMVS can consume substantial CPU, RAM, and disk; single-image generators generally need compatible accelerator memory.
- VGGT's native output is scene geometry/point cloud and camera data; do not label it a finished textured mesh unless a separate, verified meshing/texturing stage is added.
- The API's current 3D viewer is optimized for GLB/GLTF. PLY/OBJ/STL artifacts can be returned and downloaded, but should not be described as viewer-previewable unless the UI explicitly supports their format.
- No real engine, checkpoint, GPU inference, quality benchmark, or hardware compatibility test has been run by this change. CI validates application code, not model execution.
