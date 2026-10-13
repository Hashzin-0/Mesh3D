# Acceptance criteria and validation plan

This checklist defines evidence required before calling the application functional. It is not a report of tests already run.

## 1. Input and mode handling
- [ ] Single-image mode accepts exactly one valid image per run and exposes only compatible engines.
- [ ] Multi-view mode accepts a configured set of images, preserves file order/identity, and runs preflight checks.
- [ ] Invalid, corrupt, unsupported, oversized, duplicate, and low-resolution inputs produce actionable errors.
- [ ] Multi-view validation detects when camera registration is unsuccessful and does not silently claim reconstruction success.
- [ ] Client validation is repeated server-side.

## 2. Engine correctness
- [ ] Each enabled engine has a pinned revision, checkpoint provenance, license record, setup documentation, and isolated runtime.
- [ ] Each adapter declares input modes, image limits, hardware requirements, output formats, and known limitations.
- [ ] A smoke test invokes the actual engine on a real, rights-cleared fixture.
- [ ] The result manifest contains real paths, hashes, byte sizes, timing, logs, and exit status.
- [ ] An engine that fails setup, license review, or smoke tests is shown as unavailable with a reason.

## 3. Artifact quality and exports
- [ ] Every completed job has at least one existing, non-empty artifact verified in storage.
- [ ] GLB artifacts parse successfully and preserve geometry, materials, UVs, and embedded textures where produced.
- [ ] OBJ export includes required MTL/texture files where applicable.
- [ ] PLY/STL are offered only when an actual valid artifact exists.
- [ ] Mesh validation reports measurable topology and texture properties; unavailable metrics are omitted rather than fabricated.
- [ ] Downloads enforce user/job authorization and signed URL expiry.

## 4. Comparison and benchmark
- [ ] Comparisons record input hashes, engine/checkpoint versions, configuration, hardware, and benchmark protocol.
- [ ] Single-image and multi-view rankings are separated by task class.
- [ ] Synchronized camera controls work across all selected models.
- [ ] Human ratings are stored separately from automated metrics.
- [ ] Exported CSV/JSON results match the persisted raw measurements.
- [ ] No benchmark values are displayed before actual benchmark runs have completed.

## 5. Reliability and security
- [ ] Worker crash, timeout, out-of-memory, cancellation, and storage failure have distinct states and sanitized diagnostics.
- [ ] Retries are bounded and idempotent.
- [ ] Concurrent work respects configured CPU, GPU, memory, disk, and per-user quotas.
- [ ] Cross-user reads, unauthorized artifact downloads, path traversal, malformed uploads, and expired URLs are rejected.
- [ ] Secrets and signed URLs do not appear in logs.
- [ ] Temporary files are cleaned after success, failure, and cancellation according to policy.

## 6. UX and accessibility
- [ ] Studio, job monitor, and compare views have loading, empty, error, disabled, and success states.
- [ ] Mobile upload and job monitoring do not overlay the workflow, canvas, and settings panels.
- [ ] Keyboard navigation, focus visibility, semantic labels, reduced motion, and WCAG AA text contrast are checked.
- [ ] Engine restrictions and license status are understandable without knowing internal names.
- [ ] Viewer loading failure does not hide the artifact metadata or download errors.

## 7. Performance and release evidence
- [ ] Benchmarks report hardware, model/checkpoint, image dimensions/count, cold/warm run condition, elapsed time, and resource usage.
- [ ] Representative small and large image sets have been tested on the declared minimum hardware.
- [ ] Queue load, storage use, artifact download, and worker cancellation have been exercised.
- [ ] Production release has a deployment health check, log evidence, rollback procedure, and verified license notices.

## 8. Reporting rule

At each milestone, report:
1. Exact commands or workflows executed.
2. Test result and relevant logs/artifact references.
3. Hardware and engine versions for model benchmarks.
4. What could not be tested and why.
5. Known failures and the next blocking action.

Do not state “implemented”, “tested”, “deployed”, or “best engine” without corresponding evidence.
