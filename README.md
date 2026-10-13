# Mesh3D

Mesh3D is an image-to-3D reconstruction studio for comparing **real engine outputs** from one image or a multi-view capture. It includes a responsive web client, FastAPI API, Redis/Celery worker, gated engine registry, persistent local job metadata, and a Three.js viewer for actual GLB/GLTF artifacts.

> **Status:** the application scaffold is implemented, but no model engine, checkpoint, GPU runtime, or rights-cleared fixture is bundled or claimed as tested. Engines remain unavailable until a real wrapper is installed, its exact code/checkpoint terms are reviewed, and the approval flags are configured. No fake models or benchmark scores are generated.

## Features

- Responsive Studio for single-image and multi-view intake, thumbnails, removal, and capture guidance.
- Registry for TripoSR, InstantMesh, Stable Fast 3D, Hunyuan3D 2.1, AliceVision/Meshroom, COLMAP + OpenMVS, and VGGT.
- Server-side image signature, dimensions, file-size, image-count, and duplicate validation.
- Async jobs through Redis + Celery, SQLite metadata for local development, run logs, output manifest validation, and artifact SHA-256 hashes.
- Actual GLB/GLTF loading with Three.js. Compare stays empty until real outputs exist.
- CI workflow for frontend build and backend unit tests.

## Run with Docker Compose

Requirements: Docker Engine and Compose plugin. For actual reconstruction, provide a compatible CPU/GPU runtime and pinned engine dependencies/checkpoints. The generic API image does not include model runtimes or CUDA.

1. Copy `.env.example` to `.env`.
2. Run `docker compose up --build`.
3. Open `http://localhost:5173`; API health is at `http://localhost:8000/health`, and OpenAPI docs are at `http://localhost:8000/docs`.

The UI works as a studio shell without engines configured. The registry will report license review or missing wrapper configuration. Jobs cannot be submitted to unavailable engines.

## Add a real engine wrapper

Configure each approved engine as a JSON argv array, not a shell command string. Mesh3D substitutes `{input_dir}`, `{output_dir}`, and `{mode}` in argv entries. The wrapper must run the actual pinned upstream engine, return a non-zero exit code on failure, and write `manifest.json` only after actual artifacts exist. Example manifest:

    { "artifacts": [{ "path": "reconstruction.glb", "format": "glb" }] }

Paths must be relative to the output directory. Mesh3D hashes the actual artifact file; it does not fabricate geometry, texture, metrics, or runtime. See [wrapper contract](engine-wrappers/README.md), [.env.example](.env.example), and [engine provenance register](docs/ENGINE_PROVENANCE.md). Some candidates require a second deployment/checkpoint review flag. Do not enable it before review. Restart API and worker after environment changes.

**Deployment warning:** the generic worker invokes the configured wrapper as a child process and is not a substitute for per-engine isolated, versioned GPU containers. The SQLite/local-volume setup is for controlled evaluation, not public or multi-tenant production. Before public deployment, implement worker isolation, authentication/authorization, quotas, network restrictions, retention, and deployment-grade storage.

## Run checks locally

Frontend: `npm install && npm run build`

Backend: `cd backend && pip install -r requirements.txt pytest && pytest`

Tests cover engine registry/license gates and job persistence. They do not prove an engine works. Real smoke tests require documented rights-cleared fixtures, pinned code/checkpoint versions, intended hardware, and manual artifact inspection.

## Project documents

- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [Engine comparison matrix](docs/ENGINE_COMPARISON.md)
- [UI/UX specification](docs/UX_UI_SPEC.md)
- [Acceptance criteria](docs/ACCEPTANCE_CRITERIA.md)
- [Phase 0 status](docs/PHASE_0_STATUS.md)
- [Project rules](Rules.md)
- [Threat model](docs/THREAT_MODEL.md)
- [Engine provenance](docs/ENGINE_PROVENANCE.md)
- [Real engine test report template](docs/ENGINE_TEST_REPORT.md)
- [Dataset protocol](docs/DATASET_PROTOCOL.md)
- [Architecture decisions](docs/adr/)

## Next checks

1. Run CI and fix any build/test failures.
2. Provision a worker runtime and real, rights-cleared fixtures for each mode.
3. Implement and validate TripoSR and Meshroom wrappers, then compare actual outputs.
4. Verify GPU passthrough and environment propagation in Docker Compose.
5. Replace SQLite/local volume with database and object storage before shared/public use.
6. Complete license/provenance records and security hardening before public deployment.
