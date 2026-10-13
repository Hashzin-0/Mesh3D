# Mesh3D threat model

Status: design-time threat model for a planned application; it is not evidence that controls have already been implemented.

## Assets to protect

- Original photographs, EXIF metadata, and any embedded location/person information.
- Generated meshes, textures, intermediate files, and benchmark records.
- User/job ownership, signed download URLs, API credentials, and model-provider credentials.
- Worker hosts, GPU memory, temporary disk, queue capacity, and object-storage cost.
- Engine binaries, Python/npm dependencies, model checkpoints, and license notices.

## Trust boundaries

1. Browser → upload/API boundary.
2. API → queue boundary.
3. Queue → isolated worker/container boundary.
4. Worker → filesystem/object storage boundary.
5. Worker → optional model/checkpoint download boundary.
6. API → database and signed-URL boundary.
7. Engine output → parser, post-processor, and browser 3D viewer boundary.

## Threats and required controls

| Threat | Required controls / verification |
|---|---|
| Malformed or decompression-bomb images | Decode with maintained libraries; cap compressed bytes, decoded dimensions/pixels, image count, and processing time; reject unsupported formats server-side. |
| Path traversal or arbitrary file writes | Server-generated workspace/object keys; canonicalized paths; no client-controlled output paths; isolated scratch directories. |
| Command injection | Use argument arrays/process APIs, never shell interpolation; validate engine and parameter IDs against server-side allowlists. |
| Malicious native/model files | Isolated non-root worker; read-only base filesystem where practical; limited capabilities, network egress, memory, CPU, disk, and runtime. |
| Unauthorized job/artifact access | Authenticate and authorize each read, cancellation, and download; verify owner at API and storage boundary; short-lived signed URLs. |
| Resource exhaustion / GPU denial of service | Per-user and global concurrency limits, queue quotas, hard timeouts, cancellation, bounded retries, and worker health monitoring. |
| Supply-chain compromise | Pin source revisions and container digests; hash checkpoints; record dependency lockfiles and licenses; acquire artifacts only from reviewed upstreams. |
| Privacy leakage via EXIF/logs | Preserve originals privately; strip location metadata from shared derivatives unless explicitly requested; redact secrets and signed URLs from logs. |
| Parser/renderer attack through output artifacts | Validate generated GLB/OBJ/PLY before download/view; limit file size and geometry counts; treat artifacts as untrusted input in the browser. |
| License violation | Gate engine activation on code, weight, dependency, geography, and hosting-term review; preserve notices and decision records. |
| False benchmark claims | Record input hashes, actual runtime/resource measurements, versions and hardware; never fill missing metrics with estimates presented as measured data. |

## Operational requirements

- Keep API and GPU workers in separate deployable units.
- Use least privilege and separate service identities for database, queue, and storage.
- Apply retention/deletion policies to originals, intermediate outputs, logs, and completed artifacts.
- Record job state transitions and sanitized failure classifications.
- Provide cancellation and cleanup that cannot delete completed artifacts belonging to another job.
- Do not enable public multi-tenant access until authentication, quotas, isolation, and authorization tests exist.

## Residual risks / open decisions

- Authentication provider, tenant model, storage provider, deployment environment, and data-retention period have not been selected.
- No worker/container hardening or security tests have been executed because no runtime application exists in the repository yet.
- Model-specific license and network-egress requirements must be reviewed before each engine is enabled.
