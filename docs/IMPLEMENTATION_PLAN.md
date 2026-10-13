# Mesh3D implementation plan

## 1. Goal and scope

Build an image-to-3D studio that lets a user upload either one image or a set of overlapping images, run multiple real reconstruction engines, compare the resulting assets side by side, and export usable 3D files. The first release is an evaluation workbench, not an assertion that all engines will have equal capabilities or fidelity.

### In scope
- Single-image generative reconstruction and multi-image photogrammetry as separate workflows.
- Engine adapters with explicit capability declarations, versioned configuration, and normalized result manifests.
- Asynchronous, observable, cancellable jobs and per-stage logs.
- Side-by-side model inspection with linked camera controls.
- Real output artifact storage, validation, download, and reproducible benchmark history.
- Mobile-friendly intake and job monitoring; desktop-first 3D comparison workspace.
- License gates for code, checkpoints, and dependencies.

### Out of scope for the initial milestone
- Claiming metrology-grade accuracy without calibrated reference scans.
- Automatic completion of unobserved surfaces in photogrammetry and presenting them as measured facts.
- A public multi-tenant service without authentication, quotas, isolation, and storage policies.
- Training new 3D foundation models.
- Faking engine results or pre-populating comparison scores with synthetic data.

## 2. Repository status and architecture decision

The repository was empty when this plan was created. There is no existing application architecture, dependency graph, local AGENTS.md, CLAUDE.md, GEMINI.md, or project Rules.md to preserve. The following is therefore a proposed baseline, not a detected stack.

### Recommended stack

- **Web app:** Next.js + React + TypeScript.
- **UI:** accessible component primitives (e.g. Radix UI), Tailwind CSS tokens, and a restrained custom design system. Prefer shadcn/ui patterns where useful; do not pull in large visual libraries without a specific need.
- **3D viewport:** Three.js with GLTFLoader, OrbitControls, and a shared camera/light/environment setup. Consider React Three Fiber only if the chosen React architecture benefits from declarative scene composition.
- **API:** FastAPI + Pydantic schemas for validation and OpenAPI contracts.
- **Queue / workers:** Celery + Redis (or an equivalent durable queue selected after deployment constraints are known).
- **Metadata:** PostgreSQL. If Supabase is selected, inspect and version schema/migrations and apply RLS for all user-owned records.
- **Binary artifacts:** S3-compatible object storage; use signed URLs and server-side ownership checks.
- **Engine runtime:** versioned container images; isolate each native/ML pipeline, pin checkpoints, cap resources, and do not run GPU inference inside serverless request handlers.
- **Observability:** structured logs with job IDs, stage events, worker heartbeats, exit codes, and resource metrics where available.

The web/API and reconstruction workers must deploy independently. The API accepts jobs quickly and returns a job ID; workers perform heavy processing asynchronously.

## 3. Logical architecture

1. **Web client** validates file type/size for user feedback, uploads files through a controlled upload path, creates jobs, receives real job events, and loads final GLB artifacts.
2. **API** authenticates the user, checks ownership/quota, validates mode and engine compatibility, creates a job record, and enqueues an idempotent job message.
3. **Object storage** holds original images, temporary inputs, intermediate outputs where required, and final assets. Each artifact is linked to its owning job and has retention metadata.
4. **Orchestrator** runs a state machine and selects adapters based on mode, engine availability, license status, hardware profile, and user settings.
5. **Engine adapter** translates a normalized request into a version-pinned CLI/Python invocation; captures stdout/stderr and resource usage; reports actual stage events; and returns artifact paths plus measurements.
6. **Post-processing** validates outputs, optionally normalizes them to GLB, and records conversion warnings. It must not silently fabricate texture or geometry.
7. **Comparison service** groups results that share an input set and task class, exposes raw metrics, and calculates only explicitly defined metrics.
8. **Viewer** renders real artifacts, supports synchronized camera controls, and shows geometry/texture/metadata panels.
9. **Audit trail** preserves input hashes, engine/checkpoint/container versions, parameters, elapsed times, warnings, and output hashes so a comparison can be reproduced.

## 4. Domain contracts

Use explicit discriminated unions rather than a single ambiguous “images” field.

- `ReconstructionMode`: `single_image` | `multi_view`.
- `EngineCapability`: supported modes, minimum/maximum image counts, GPU/CPU requirements, accepted formats, output types, license gate, and feature flags.
- `ReconstructionJob`: ID, owner, mode, source asset IDs, selected engine IDs, normalized parameters, status, progress events, timestamps, and failure classification.
- `EngineRun`: job ID, engine ID/version, checkpoint revision/hash, runtime/container digest, resolved parameters, stage events, resource usage, exit status, warnings, and artifact manifest.
- `Artifact`: storage key, media type, format, size, hash, provenance, retention status, and validation report.
- `MeshValidationReport`: vertex/face counts, connected components, degenerate faces, boundary/non-manifold edges, normal checks, texture/UV/material presence, and GLB parse status. Values unavailable for a format must be null/omitted, not guessed.
- `BenchmarkCase`: versioned input-set ID, mode, reference asset (optional), evaluation protocol, and human-rating results.

All external and persisted data must be runtime-validated. Avoid TypeScript `any`; generate or share API contracts where practical.

## 5. Engine adapter design

Each engine lives behind a stable adapter interface, for example:
- `capabilities()`
- `validateInput(request)`
- `estimateRequirements(request)`
- `run(request, eventSink, cancellationSignal)`
- `collectArtifacts(workspace)`
- `normalizeArtifacts(manifest)`
- `healthCheck()`

Adapters must not contain UI logic. The orchestrator must not depend on engine-specific filesystem layouts. Each engine has its own container, dependency lock, model-weight setup instructions, license file, smoke test, and benchmark profile.

### Initial engine lineup

**Single image**
1. TripoSR — speed and permissive-license baseline.
2. InstantMesh — alternate generative mesh baseline.
3. Stable Fast 3D — enable only after its Community License conditions have been reviewed and met.
4. Hunyuan3D 2.1 — optional candidate only after verifying the exact revision, each model-weight license, territory restrictions, and hosted-service terms.

**Multiple images**
1. AliceVision/Meshroom — first complete open-source photogrammetry pipeline to validate.
2. COLMAP + OpenMVS — second pipeline for comparison; isolate OpenMVS due to AGPL-3.0 obligations and do not deploy it before a licensing decision.
3. VGGT — research comparator for camera/geometry estimation; enable only with a suitable checkpoint license and a verified downstream mesh/texturing pipeline.

Single-image and multi-view engines must not be ranked together as if they solved the same task. Single-image generation invents unseen surfaces; multi-view reconstruction should be evaluated on observed-surface fidelity and image registration.

## 6. Job lifecycle and failure model

Proposed job states:
`queued` → `validating` → `preprocessing` → `reconstructing` → `meshing` → `texturing` → `exporting` → `validating_output` → `completed`.

Any stage may transition to `failed` or `cancelled`; stages that do not apply for an engine should be skipped explicitly. Persist each transition and the reason. Progress must come from stage events, real engine counters, or clearly labeled stage-based estimates—not a fake continuously increasing percentage.

Failure categories: invalid input, insufficient image overlap, camera-registration failure, unsupported hardware, missing checkpoint, out-of-memory, timeout, engine exit failure, artifact validation failure, license-disabled engine, quota exceeded, and infrastructure/storage error.

Retries must be bounded and applied only to retryable failures. Use idempotency keys so retries do not create duplicate runs or charge resource quotas twice. Cancellation must terminate child processes and clean temporary files without deleting completed artifacts.

## 7. Security, privacy, and operations

- Validate actual file signatures, MIME type, extension, pixel dimensions, image count, decompressed size, and archive contents where applicable.
- Limit request size, image count, image dimensions, job concurrency, CPU/GPU memory, runtime, and temporary disk.
- Generate storage keys on the server; never trust client-provided paths.
- Authenticate every job/artifact read and download; use short-lived signed URLs.
- Keep model downloads and binaries pinned, checksummed, and acquired from trusted upstreams.
- Run workers as non-root with least privilege, no arbitrary shell input, no unrestricted network access, and isolated scratch directories.
- Redact EXIF/GPS metadata from shared artifacts unless the user explicitly opts in; do not log image contents or signed URLs.
- Define retention and deletion for originals, intermediates, and final files.
- Track model-weight license and provenance independently from source code.
- Do not edit or overwrite existing `.env*` files; document variable names in `.env.example` if implementation later requires them.

## 8. Implementation phases

### Phase 0 — Baseline and reproducibility
- [ ] Add project-level rules, threat model, data-flow diagram, and ADRs for queue/storage/worker deployment.
- [ ] Pin candidate upstream revisions and create a license/provenance register for code, checkpoints, and third-party binaries.
- [ ] Define one real, redistributable single-object test set and one real multi-view test set with documented capture protocol and rights.
- [ ] Define hardware profiles and benchmark protocol; record baseline measurements manually before claiming performance.
- **Exit gate:** every candidate has a verified source, license status, setup method, expected outputs, and a documented smoke-test procedure.

### Phase 1 — Engine proof of capability
- [ ] Build isolated worker images and smoke-test each engine independently.
- [ ] Produce real artifacts from the same fixed single-image input for each enabled single-image engine.
- [ ] Produce real artifacts from the same fixed multi-view capture for each enabled multi-view pipeline.
- [ ] Normalize manifests, record runtime/resource metrics, and verify GLB/OBJ/PLY parsing.
- [ ] Keep any engine failing setup, licensing, output, or hardware checks marked unavailable with the reason.
- **Exit gate:** at least one verified engine for each input mode, with real saved outputs and reproducible run metadata.

### Phase 2 — API, persistence, and queue
- [ ] Define migrations/schema for projects, assets, jobs, engine runs, stage events, artifacts, benchmark cases, and ratings.
- [ ] Implement upload authorization, signed URLs, job creation, idempotent enqueue, cancellation, and status/event endpoints.
- [ ] Implement worker heartbeat, timeouts, resource caps, cleanup, bounded retries, and structured logs.
- [ ] Add authorization and data-isolation tests.
- **Exit gate:** integration tests can create a job, process a real test set, persist outputs, recover a worker failure, and reject unauthorized access.

### Phase 3 — UX/UI and 3D comparison
- [ ] Implement responsive workspace and accessible design tokens/components.
- [ ] Build single-image and multi-image intake with previews, reorder/delete, overlap guidance, and preflight checks.
- [ ] Build engine selection with capability/license status, hardware requirements, and incompatible-engine explanations.
- [ ] Build real-time job timeline, stage-specific errors, retry/cancel, and job history.
- [ ] Build synchronized side-by-side GLB viewers with wireframe/solid/textured modes, reset camera, metadata, and downloads.
- [ ] Show missing metrics as unavailable; never synthesize scores or previews.
- **Exit gate:** usability tests pass on mobile intake and desktop comparison, with keyboard accessibility and loading/empty/error/success states.

### Phase 4 — Benchmarking and quality gates
- [ ] Add benchmark runner and versioned test manifests.
- [ ] Compute only metrics supported by real output data; add reference geometry only where licensing and ground truth permit.
- [ ] Add blinded human rating workflow and export raw benchmark results to CSV/JSON.
- [ ] Compare quality, reliability, runtime, memory, and output size by task class.
- **Exit gate:** results can be reproduced from saved input hashes and engine versions; no fabricated metrics.

### Phase 5 — Hardening and release
- [ ] Load-test queue, storage, cancellation, and concurrent GPU workers.
- [ ] Test corrupt files, extreme dimensions, duplicate images, low-overlap sets, transparent/reflective objects, and engine crashes.
- [ ] Verify licensing and notices for all enabled engines and checkpoints.
- [ ] Add monitoring, retention policy, backups, operator runbook, and deployment rollback.
- [ ] Document minimum/recommended hardware and known limitations.
- **Exit gate:** release checklist and security review signed off; deployment verified from logs and health checks.

## 9. Testing strategy

- Unit tests: request schemas, capability compatibility, state transitions, retry classification, artifact manifest validation, metric calculations.
- Adapter tests: mocked process boundaries only for unit tests; integration/smoke tests must run the actual engine against licensed real fixtures.
- Integration tests: API → queue → worker → storage → database → viewer artifact path.
- Security tests: upload validation, path traversal, authorization, signed URL expiry, rate limits, secret redaction, tenant isolation.
- Visual tests: responsive layouts, keyboard navigation, reduced motion, contrast, viewer loading/error states.
- Benchmark tests: repeated runs with pinned versions; report variance and hardware. Do not assert a model is “best” based on a single run.

## 10. Key risks and decisions

| Risk | Mitigation / decision needed |
|---|---|
| GPU cost and long-running jobs | Start with a dedicated worker; quotas, concurrency caps, queue visibility, and early hardware profiling |
| License incompatibility | Per-engine license gate; legal review for OpenMVS and model checkpoints before hosted use |
| Incomparable results | Separate task classes, fixed inputs, documented metrics, blind ratings, and raw data export |
| Poor capture quality | Client-side preflight guidance plus server-side registration checks and actionable remediation |
| Model output not a clean mesh | Validation report, optional cleanup pipeline, and transparent warnings |
| Hidden surfaces guessed by single-image models | Label generative inference and do not claim measured accuracy |
| Browser memory for large models | GLB optimization, lazy load, texture-size caps, explicit large-model warning |
| Empty repository / unknown deploy target | Confirm hosting, GPU provider, storage provider, and authentication choice before implementation phase 2 |

## 11. Reference links

- COLMAP: https://github.com/colmap/colmap
- AliceVision / Meshroom: https://github.com/alicevision/AliceVision and https://github.com/alicevision/Meshroom
- OpenMVS: https://github.com/cdcseacave/openMVS
- TripoSR: https://github.com/VAST-AI-Research/TripoSR
- InstantMesh: https://github.com/TencentARC/InstantMesh
- Stable Fast 3D: https://github.com/Stability-AI/stable-fast-3d
- Hunyuan3D: https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1
- VGGT: https://github.com/facebookresearch/vggt
- Three.js: https://github.com/mrdoob/three.js
- Trimesh: https://github.com/mikedh/trimesh
- Open3D: https://github.com/isl-org/Open3D
- glTF Transform: https://github.com/donmccurdy/glTF-Transform
