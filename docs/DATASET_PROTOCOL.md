# Real image-set and benchmark fixture protocol

Status: protocol only. No fixture has yet been added to this repository and no benchmark has been run.

## Fixture requirements

Maintain separate datasets for:
1. **Single image:** one rights-cleared photograph of one isolated object, with enough visible silhouette and surface detail to make the input meaningful. Hidden geometry is not ground truth.
2. **Multi-view:** a rights-cleared sequence of overlapping photographs of the same physical object, captured around it with stable exposure/focus and sufficient parallax. Preserve the original file ordering and document any calibration/capture metadata available.

Do not treat a generated image, stock preview, rendered synthetic object, or unverified internet image as a real benchmark fixture without explicitly documenting that provenance and the reason it is suitable. Do not commit copyrighted/private user uploads merely to make a smoke test convenient.

## Dataset manifest

For every fixture, record:
- Stable fixture ID and version.
- Origin/creator, license or written permission, and redistribution scope.
- Capture date/method where known; camera/lens and calibration metadata only when actually known.
- Input mode, ordered relative filenames, actual byte sizes, decoded dimensions, file formats, and SHA-256 per file.
- Known limitations, object category, occlusions, lighting changes, reflective/transparent surfaces, and whether a reference scan exists.
- Consent/privacy review and EXIF/GPS handling.
- Expected engine capability and validation checks; do not encode a guessed “correct” mesh.

## Reproducible run protocol

- Use the same immutable input hashes for all engines within a task class.
- Record code revision, checkpoint hash, container digest, dependencies, engine settings, hardware, cold/warm state, start/end timestamps, wall time, peak CPU/RAM/GPU/VRAM when available, exit code, logs, output hashes, and validation report.
- Separate single-image rankings from multi-view rankings.
- Report missing outputs and failed runs. Do not omit failed engines from the denominator without explaining the policy.
- Store subjective human ratings separately from automated geometry/texture measurements.
- Never display benchmark metrics until a real run produced them.

## Current blocker

A reproducible fixture cannot be committed until the project confirms an appropriate rights-cleared source and records its terms. Until then, engine setup can be developed, but the Phase 1 real-artifact acceptance gate remains blocked.
