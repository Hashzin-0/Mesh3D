# Mesh3D

Mesh3D is planned as an image-to-3D evaluation studio that compares multiple reconstruction engines on real image inputs. It will support both single-image generation and multi-view reconstruction, with textured mesh export and reproducible benchmark records.

## Project status

**Planning + Phase 0 governance baseline.** The repository started with planning documents only. Phase 0 has added project rules, a threat model, architecture decisions, engine provenance gates, and a real-dataset protocol. No conversion engine, worker, or production UI is implemented yet; Phase 0 remains incomplete.

## Documents

- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [Engine comparison matrix](docs/ENGINE_COMPARISON.md)
- [UI/UX specification](docs/UX_UI_SPEC.md)
- [Acceptance criteria and validation](docs/ACCEPTANCE_CRITERIA.md)
- [Phase 0 status and blockers](docs/PHASE_0_STATUS.md)
- [Project rules](Rules.md)
- [Threat model](docs/THREAT_MODEL.md)
- [Engine provenance and license gates](docs/ENGINE_PROVENANCE.md)
- [Real dataset protocol](docs/DATASET_PROTOCOL.md)
- [Architecture decisions](docs/adr/)

## Product principles

- Support one image and multiple images as separate, explicit reconstruction modes.
- Compare real engine outputs; never substitute mock models, synthetic benchmark scores, or fabricated progress.
- Preserve the original uploads and record engine versions, parameters, timings, errors, and output artifacts.
- Treat image-to-3D generation and multi-view photogrammetry as different task classes.
- Review model-weight and dependency licenses separately from source-code licenses before enabling an engine.
- Keep heavy inference and reconstruction in isolated asynchronous workers, not in the web request lifecycle.

## Proposed baseline

- **Web:** Next.js, React, TypeScript, accessible component primitives, and Three.js for GLB inspection.
- **API / orchestration:** FastAPI, typed request/response schemas, and Celery + Redis for asynchronous jobs.
- **Persistence:** PostgreSQL for job metadata and benchmark results; S3-compatible object storage for uploads and generated assets.
- **Engine workers:** isolated, versioned containers for generative single-image models and classical/neural multi-view reconstruction.
- **Exports:** GLB as the primary web-delivery artifact; OBJ + MTL + textures, PLY, and STL where applicable.

These are proposed choices, not detected dependencies: the repository had no source files or project-specific instructions at planning time.
