# Engine integration and local runtime setup

This document describes the real upstream adapters in `engine-wrappers/`. The adapter scripts are committed; upstream repositories, Python/CUDA environments, weights, and hardware are intentionally provisioned by the operator and are not vendored into Mesh3D. **A committed adapter is not proof that its model has run successfully.** Do not approve an engine until the smoke test below passes on the intended host.

## Runtime topology

- Jobs run in-process through FastAPI `BackgroundTasks`; the API and any worker process share the persistent `/data` volume, so uploaded images and outputs are accessible.
- The API/worker mounts `./engine-wrappers` read-only at `/opt/mesh3d/wrappers` and optional upstream checkouts from `./engines` at `/opt/mesh3d/engines`.
- Each Python engine should have its own environment. Configure its interpreter with the corresponding `MESH3D_*_PYTHON` variable or place a `.venv/bin/python` inside that checkout.
- Model caches belong under `/data/model-cache`; do not commit model weights, tokens, private fixtures, or output artifacts.
- The engine registry is gated by each engine's `MESH3D_ENGINE_*_VALIDATION_REPORT` (a real-run report that embeds the license review), not by `MESH3D_ENGINE_*_LICENSE_APPROVED` environment flags — those were removed as redundant once the report schema required an explicit `license_review.decision` record. Keep engines unavailable until you have reviewed the exact upstream revision, checkpoint license, intended use, redistribution, and commercial deployment terms, and the report records that review.

## Adapters and upstream contracts

| Mesh3D ID | Adapter | Input | Upstream invocation / output |
|---|---|---|---|
| `triposr` | `triposr.py` | Exactly one image | Official `run.py IMAGE --output-dir DIR`; optionally requests baked texture; publishes real GLB/GLTF or mesh output discovered in the directory. |
| `meshroom` | `meshroom.py` | At least two views | Runs `meshroom_batch --input DIR --output DIR --save PROJECT.mg`; reports actual mesh files produced by the photogrammetry graph. |
| `colmap_openmvs` | `colmap_openmvs.py` | At least two views | Runs COLMAP feature extraction, exhaustive matching and mapper, then OpenMVS `InterfaceCOLMAP`, `DensifyPointCloud`, `ReconstructMesh`, and `TextureMesh`. |

Official references:
- TripoSR: https://github.com/VAST-AI-Research/TripoSR
- Meshroom: https://github.com/alicevision/Meshroom
- COLMAP: https://github.com/colmap/colmap
- OpenMVS: https://github.com/cdcseacave/openMVS

Candidates InstantMesh, Stable Fast 3D, Hunyuan3D 2.1 and VGGT were removed from the registry after their real-run attempts failed on the CPU-only reference host (no CUDA, insufficient RAM for large fp32/fp16 models, gated checkpoint). Their attempt records are kept in `.validation/reports/*-attempt.json`.

## Provisioning

1. Create the local directory `engines/`. Clone each upstream project at a reviewed commit; record that full commit SHA and checkpoint revision in `docs/ENGINE_PROVENANCE.md`.
2. Install dependencies following each upstream repository's current instructions in a separate environment. TripoSR needs its own Python environment (pinned `requirements.txt` venv); Meshroom and COLMAP/OpenMVS run against their own binaries. Keep environments separate: their dependency and CUDA constraints differ.
3. Configure `*_ROOT`, `*_PYTHON`, and binary paths in a private `.env`. For gated weights, configure `HF_TOKEN` privately only after access has been granted.
4. Confirm Docker can access the host GPU. The default Compose file intentionally does not force GPU reservations, so the UI/API can start on machines without NVIDIA runtime. For GPU inference, use a Compose GPU override compatible with the host's NVIDIA Container Toolkit or run the worker on a GPU-enabled host. Model runtimes and CUDA are not installed by the generic API Dockerfile.
5. Start the stack with `docker compose up --build`. For a host configured with the NVIDIA Container Toolkit, use `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build` to request GPU access for the worker. Inspect `GET /api/engines`; a candidate remains unavailable until the wrapper command is configured and a valid validation report path is set.

Example command configuration (`.env.example` covers all three shipped engines):
```dotenv
MESH3D_ENGINE_TRIPOSR_CMD=["python","/opt/mesh3d/wrappers/triposr.py","--input-dir","{input_dir}","--output-dir","{output_dir}","--mode","{mode}"]
MESH3D_TRIPOSR_ROOT=/opt/mesh3d/engines/TripoSR
MESH3D_TRIPOSR_PYTHON=/opt/mesh3d/engines/TripoSR/.venv/bin/python
MESH3D_ENGINE_TRIPOSR_VALIDATION_REPORT=/data/validation-reports/triposr-validation.json
```

## Smoke test and release gate

For each engine, using the exact intended runtime and a rights-cleared fixture:

1. Provision dependencies without configuring the validation-report path; the engine stays `validation_required` until a passing report exists.
2. Invoke the wrapper manually with `--input-dir`, `--output-dir`, and the correct `--mode`. Confirm it exits non-zero on missing weights or incompatible dependencies.
3. Confirm `manifest.json` is created only after a real output file exists, and that each manifest path is relative, remains within the output directory, and opens in a suitable viewer.
4. Submit a job through the UI/API and verify status, elapsed time, logs, artifact byte count and SHA-256.
5. Inspect geometry, scale, normals, UVs/materials, holes, floating parts, camera coverage, and output format manually. A successful process exit is not a quality score.
6. Record GPU/CPU model, VRAM/RAM, driver/CUDA/PyTorch versions, upstream commit SHA, checkpoint revision and license, elapsed time, errors, output hash, and reviewer in `docs/ENGINE_TEST_REPORT.md`.
7. Only then produce the validation report (`docs/ENGINE_VALIDATION_GATE.md`) including the completed license review in `license_review` — COLMAP + OpenMVS records the OpenMVS AGPL-3.0 deployment review — and set `MESH3D_ENGINE_*_VALIDATION_REPORT` to its path on the trusted host.

## Known boundaries

- These adapters are not model binaries or a universal Docker image. The actual upstream runtimes and checkpoints must be installed separately.
- The generic worker shares a process/container and is suitable only for controlled local evaluation. It is not a hardened multi-tenant job sandbox.
- Meshroom and COLMAP/OpenMVS can consume substantial CPU, RAM, and disk; TripoSR on CPU took ~139s on the reference host.
- The API's current 3D viewer is optimized for GLB/GLTF. PLY/OBJ/STL artifacts can be returned and downloaded, but should not be described as viewer-previewable unless the UI explicitly supports their format.
- Real engine runs for the three shipped adapters are recorded in `docs/ENGINE_TEST_REPORT.md` and `.validation/reports/*-validation.json`. CI validates application code, not model execution; no GPU inference or quality benchmark has been run on this CPU-only host.
