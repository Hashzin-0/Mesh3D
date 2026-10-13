# Mesh3D

Mesh3D is an image-to-3D reconstruction studio for comparing real outputs from one image or a multi-view capture. It includes a responsive web client, FastAPI API, Redis/Celery worker, gated engine registry, persistent local job metadata, and a Three.js viewer for GLB/GLTF artifacts.

> **Status:** seven concrete upstream adapter entry points are included. Upstream checkouts, engine-specific environments, checkpoints and accelerator runtime remain operator-provisioned. We have not claimed a successful model/GPU smoke test or bundled any model weights. Engines remain unavailable until their license approval flags and runtime commands are configured.

## Features

- Responsive Studio for single-image and multi-view intake, thumbnails, removal, and capture guidance.
- Adapter entry points for TripoSR, InstantMesh, Stable Fast 3D, Hunyuan3D 2.1, AliceVision/Meshroom, COLMAP + OpenMVS, and VGGT.
- Server-side image signature, dimensions, file-size, image-count, and duplicate validation.
- Async jobs through Redis + Celery, SQLite metadata for local development, run logs, output manifest validation, and artifact SHA-256 hashes.
- Actual GLB/GLTF loading with Three.js. Comparison stays empty until real outputs exist.
- CI workflow for frontend build, backend unit tests, and adapter syntax checks.

## Run the Studio

Requirements: Docker Engine and Compose plugin.

1. Copy `.env.example` to `.env`.
2. Run `docker compose up --build`.
3. Open `http://localhost:5173`; API health is at `http://localhost:8000/health`, OpenAPI docs at `http://localhost:8000/docs`.

The Studio/API can start without model runtimes. To run reconstruction, clone and provision the appropriate upstream engines, configure the environment variables in `.env`, provide compatible GPU/runtime access, and complete the engine-specific license review. Do not set approval flags simply to make a candidate appear enabled.

## Engine integration

See [Engine integration and runtime setup](docs/ENGINE_INTEGRATION.md), the [wrapper contract](engine-wrappers/README.md), [.env.example](.env.example), [engine provenance register](docs/ENGINE_PROVENANCE.md), and [real engine test report template](docs/ENGINE_TEST_REPORT.md).

Important distinctions:
- The four single-image engines use different dependency and checkpoint stacks; keep their Python environments separate.
- Meshroom and COLMAP + OpenMVS are photogrammetry pipelines for multi-view captures.
- VGGT outputs camera/scene geometry and point-cloud data; it is not automatically a textured watertight mesh.
- The viewer currently targets GLB/GLTF. Other supported artifacts may be delivered as files but are not guaranteed to preview in the in-app viewer.
- The generic worker is for controlled local evaluation, not a hardened multi-tenant public service. Public deployment still needs worker isolation, authentication/authorization, quotas, network restrictions, retention policy, and deployment-grade storage.

## Checks

Frontend: `npm install && npm run build`

Backend: `cd backend && pip install -r requirements.txt pytest && pytest`

Adapter syntax: `python -m compileall -q engine-wrappers`

Passing CI does not prove any upstream model can run. Real smoke tests require rights-cleared fixtures, pinned source/checkpoint versions, intended hardware, and manual artifact inspection.
