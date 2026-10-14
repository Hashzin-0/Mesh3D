# Mesh3D

Mesh3D is an image-to-3D reconstruction studio for comparing real outputs from one image or a multi-view capture. It includes a responsive web client, FastAPI API, an in-process job runner for local development, a gated engine registry, local SQLite metadata, and a Three.js viewer for GLB/GLTF artifacts.

> **Status:** seven concrete upstream adapter entry points are included. Upstream checkouts, engine-specific environments, checkpoints and accelerator runtime remain operator-provisioned. No successful model/GPU smoke test or bundled model weights are claimed. Engines remain unavailable until their license approval flags and runtime commands are configured.

## Features

- Responsive Studio for single-image and multi-view intake, thumbnails, removal, and capture guidance.
- Adapter entry points for TripoSR, InstantMesh, Stable Fast 3D, Hunyuan3D 2.1, AliceVision/Meshroom, COLMAP + OpenMVS, and VGGT.
- Server-side image signature, dimensions, file-size, image-count, and duplicate validation.
- In-process job execution for local development, SQLite job metadata, run logs, output manifest validation, and artifact SHA-256 hashes.
- Actual GLB/GLTF loading with Three.js. Comparison stays empty until real outputs exist.
- CI workflow for frontend build, backend unit tests, and adapter syntax checks.

## Run the Studio locally

Requirements: Docker Engine and Compose plugin.

1. Copy `.env.example` to `.env`.
2. Run `docker compose up --build`.
3. For a host configured with the NVIDIA Container Toolkit, use `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build` to request GPU access for the API process.
4. Open `http://localhost:5173`; API health is at `http://localhost:8000/health`, OpenAPI docs at `http://localhost:8000/docs`.

The Studio/API can start without model runtimes. To run reconstruction locally, clone and provision the appropriate upstream engines, configure the environment variables in `.env`, provide compatible GPU/runtime access, and complete the engine-specific license review. Do not set approval flags simply to make a candidate appear enabled.

## Vercel deployment

The root `vercel.json` defines two deployable services:

- `app`: Vite frontend; its service-scoped rewrite sends SPA paths to `index.html`.
- `backend`: FastAPI entrypoint at `backend/main.py`; the public `/api/*` rewrite routes API requests to it. The browser uses same-origin API paths, so no service binding or hardcoded production backend URL is required.
- `/api/health` is the public health endpoint. The local `/health` and `/docs` endpoints remain available in local development but are not routed publicly by the Vercel configuration.

### Important runtime limits

Celery and Redis have been removed. The API now schedules the existing runner through FastAPI `BackgroundTasks` in the same invocation. This is a lightweight replacement for local development, **not a durable Vercel worker**. Vercel functions have finite execution time and ephemeral per-instance storage; local SQLite and uploaded/output files are not shared reliably between invocations and must not be used as production persistence.

The seven reconstruction engines are external runtimes that require operator-provisioned repositories, separate environments, checkpoints, and often GPU acceleration. This repository does not bundle those runtimes or weights, and a Vercel Function is not a GPU worker. Therefore this configuration validates service routing and API packaging; it does not establish that model inference, durable job polling, or artifact retention will work on Vercel. Production reconstruction requires a separate durable compute/storage architecture, which is intentionally not introduced here because the selected persistence option was `keep-local` and bindings were set to `none`.

Vercel Services must also be enabled as the project's framework in Vercel project settings; the presence of `services` in `vercel.json` alone does not switch that dashboard setting.

## Engine integration

See [Engine integration and runtime setup](docs/ENGINE_INTEGRATION.md), the [wrapper contract](engine-wrappers/README.md), [.env.example](.env.example), [engine provenance register](docs/ENGINE_PROVENANCE.md), and [real engine test report template](docs/ENGINE_TEST_REPORT.md).

Important distinctions:
- The four single-image engines use different dependency and checkpoint stacks; keep their Python environments separate.
- Meshroom and COLMAP + OpenMVS are photogrammetry pipelines for multi-view captures.
- VGGT outputs camera/scene geometry and point-cloud data; it is not automatically a textured watertight mesh.
- The viewer currently targets GLB/GLTF. Other supported artifacts may be delivered as files but are not guaranteed to preview in the in-app viewer.
- The generic runner is for controlled local evaluation, not a hardened multi-tenant public service. Public deployment still needs worker isolation, authentication/authorization, quotas, network restrictions, retention policy, and deployment-grade storage.

## Checks

Frontend: `npm install && npm run build`

Backend: `cd backend && pip install -r requirements.txt pytest && pytest`

Adapter syntax: `python -m compileall -q engine-wrappers`

Passing CI does not prove any upstream model can run. Real smoke tests require rights-cleared fixtures, pinned source/checkpoint versions, intended hardware, and manual artifact inspection.


## Local image and video generation

The **Create media** workspace supports local image/video generation through a self-hosted ComfyUI instance. It does not call paid generation APIs and does not bundle model weights. Generation is disabled by default; configure and validate a local API-format workflow, then explicitly enable it on a trusted runtime. Do not run GPU inference inside Vercel Functions.

- Architecture, configuration, workflow contracts and license checks: [Local image and video generation](docs/LOCAL_MEDIA_GENERATION.md).
- Image models: compatible Stable Diffusion / FLUX checkpoints through ComfyUI; Diffusers + PyTorch is the future direct-inference adapter path.
- Video models: locally installed Wan 2.2 or LTX-Video workflows through ComfyUI.
- Media processing: FFmpeg for transcoding and audio/video muxing.

The repository changes and unit tests do not prove that ComfyUI, a model checkpoint, or a GPU is installed. Validate real image and video outputs on the intended host before enabling production use.
