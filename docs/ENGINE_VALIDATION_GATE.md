# Engine validation gate

Status: enforcement implemented; the report below is the only approval mechanism.

## Why this gate exists

A wrapper command alone proves neither that a checkpoint is installed nor that inference succeeded, and a bare `MESH3D_ENGINE_*_LICENSE_APPROVED=true` environment flag proved neither a report of a real run nor a recorded license review. The registry therefore returns `validation_required` and refuses execution unless a machine-readable real-run report is present and valid, and that report embeds an explicit `license_review` decision with reviewer and date.

The legacy `MESH3D_ENGINE_*_LICENSE_APPROVED` (and `..._EXTRA`) environment flags were removed as redundant: any report that satisfies the schema already carries the approval record, and unreported runs stay blocked. Fail-closed behavior is unchanged — an engine with no passing report is never `ready`.

This report is an auditable release record, not a cryptographic signature or a substitute for legal review. Keep it on the trusted inference host, restrict who can modify it, and rerun validation whenever the upstream commit, checkpoint, dependency lock, hardware class, wrapper, or deployment target changes.

## Required environment variable

Each engine has a corresponding report path:

| Engine ID | Environment variable |
|---|---|
| `triposr` | `MESH3D_ENGINE_TRIPOSR_VALIDATION_REPORT` |
| `meshroom` | `MESH3D_ENGINE_MESHROOM_VALIDATION_REPORT` |
| `colmap_openmvs` | `MESH3D_ENGINE_COLMAP_OPENMVS_VALIDATION_REPORT` |

The path must be readable by the process that executes the registry. For a remote GPU worker, the report and the registry that consumes it must live on that worker or use a deliberately implemented authenticated validation service. A file path on a Vercel Function is not a path on a separate GPU host.

## Required JSON fields

Store one JSON report per engine outside the public web root and do not commit actual reports containing private fixture information.

```json
{
  "schema_version": 1,
  "engine_id": "triposr",
  "result": "passed",
  "upstream_commit": "40-character immutable source commit SHA",
  "checkpoint": {
    "id": "official model identifier",
    "revision": "immutable checkpoint revision",
    "sha256": "64-character SHA-256 of the checkpoint artifact or documented checkpoint manifest",
    "license": "exact checkpoint license identifier and source"
  },
  "dependency_lock_sha256": "64-character SHA-256 of the resolved dependency lock or environment manifest",
  "hardware": {
    "cpu": "exact CPU model",
    "accelerator": "exact GPU model and VRAM, or none",
    "ram_gb": 32
  },
  "smoke_test": {
    "exit_code": 0,
    "input_sha256": "64-character SHA-256 of a rights-cleared test input",
    "output_path": "outputs/reconstruction.glb",
    "output_sha256": "64-character SHA-256 of the real output artifact",
    "output_bytes": 123456,
    "opened_in_viewer": true
  },
  "license_review": {
    "decision": "approved",
    "reviewer": "reviewer identifier",
    "reviewed_at": "YYYY-MM-DD"
  }
}
```

The example is a schema illustration, not test evidence. Replace every placeholder with observed values. Never use the example itself to enable an engine.

## Validation procedure

1. Pin the upstream source to a full immutable commit and record the exact checkpoint revision.
2. Review source, checkpoint, and third-party dependency licenses for the intended hosting, commercial use, redistribution, and geographic scope.
3. Install the runtime and weights on the intended inference host. Record the resolved dependency lock or environment manifest.
4. Run the real adapter against a rights-cleared fixture. Capture exit code, logs, resource use, elapsed time, input hash, output hash, and output byte count.
5. Open the generated file in a suitable 3D viewer and inspect geometry, normals, scale, UVs/materials, texture, and defects. A zero exit code alone is insufficient.
6. Complete the license review and produce the report with the actual evidence.
7. Configure the report path on the same trusted execution host. Extra-review engines (Stable Fast 3D, Hunyuan3D 2.1, COLMAP + OpenMVS, VGGT) must capture that additional deployment/checkpoint review inside the report's `license_review` notes; no separate environment gate exists.
8. Re-run tests after any change to the runtime, weights, dependencies, wrapper, or deployment architecture.

## Deployment limitation

The current Vercel setup is not a GPU inference worker and uses ephemeral local storage. Do not configure a report path or enable engines on Vercel expecting that to provision runtimes, checkpoints, durable artifacts, or a remote worker. Production use requires a separately provisioned inference service with durable storage and an authenticated job/artifact contract. The registry gate prevents falsely labelling an engine as ready; it does not create that infrastructure.
