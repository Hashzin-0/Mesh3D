# Engine provenance and license gates

Status: register updated with real-run evidence from 2026-10-14 (CPU-only host, AMD EPYC 7763, 2 cores, 7.76 GB RAM, no accelerator). Only engines with a validated report under `.validation/reports/*-validation.json` remain in the registry. Candidates whose real-run attempt failed were removed from the registry together with their adapters; their attempt records under `.validation/reports/*-attempt.json` are kept here as the audit trail.

## Activation policy

No engine becomes selectable in a release until the project records: exact upstream revision, code license, model/checkpoint identifier and license, dependency/license inventory, source of downloaded weights, cryptographic hashes, supported hardware, setup instructions, smoke-test command, expected output contract, and a reviewed deployment decision. The machine-readable record is the schema-v1 validation report (see `ENGINE_VALIDATION_GATE.md`); the legacy `*_LICENSE_APPROVED` environment flags were removed as redundant.

### In the registry (validated)

| Engine | Intended mode | Upstream | Initial gate | Current evidence (2026-10-14) |
|---|---|---|---|---|
| TripoSR | Single image | https://github.com/VAST-AI-Research/TripoSR | Verify exact revision, checkpoint provenance, dependency notices, and runtime | **Smoke test passed** via wrapper (exit 0, 139 s, CPU); checkpoint `stabilityai/TripoSR` rev `5b521936b01fbe1890f6f9baed0254ab6351c04a`, MIT; mesh inspected (15,391 verts). Report: `.validation/reports/triposr-validation.json` |
| AliceVision / Meshroom | Multi-view | https://github.com/alicevision/AliceVision · https://github.com/alicevision/Meshroom | Pin revisions, inventory bundled dependencies, confirm installation and CLI workflow | **Smoke test passed** via wrapper (exit 0, 41 s, `photogrammetryDraft` pipeline; full pipeline needs CUDA depth maps); textured mesh inspected. Report: `.validation/reports/meshroom-validation.json` |
| COLMAP + OpenMVS | Multi-view | https://github.com/colmap/colmap · https://github.com/cdcseacave/openMVS | Separate license review for COLMAP and AGPL-3.0 OpenMVS before hosted deployment | **Smoke test passed** via wrapper (exit 0, 105 s, COLMAP 3.9.1 + OpenMVS v2.4.0, CPU); textured mesh inspected; AGPL obligations recorded in report license review. Report: `.validation/reports/colmap_openmvs-validation.json` |


### Removed after failed real-run attempts (2026-10-14)

These candidates are **not in the registry**; the rows are retained only as the provenance/audit record of why they were dropped.

| Candidate | Intended mode | Upstream | Initial gate | Failure evidence (2026-10-14) |
|---|---|---|---|---|
| InstantMesh | Single image | https://github.com/TencentARC/InstantMesh | Verify exact revision, weight/model-card terms, dependency notices, and runtime | **Removed from the registry after failed attempt** (adapter `engine-wrappers/instantmesh.py` deleted): `nvdiffrast` cannot build (no `CUDA_HOME`/nvcc) and upstream hardcodes `device='cuda'`; no GPU. Attempt: `.validation/reports/instantmesh-attempt.json` |
| Stable Fast 3D | Single image | https://github.com/Stability-AI/stable-fast-3d | Community License and deployment/commerce conditions must be approved | **Removed from the registry after failed attempt** (adapter `engine-wrappers/stable_fast_3d.py` deleted): gated HF checkpoint (`GatedRepoError 401`) — access must be granted upstream; Community License review still required. Attempt: `.validation/reports/stable_fast_3d-attempt.json` |
| Hunyuan3D 2.1 | Single image | https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1 | Review territory, hosting/deployment terms, and every submodel/checkpoint license | **Removed from the registry after failed attempt** (adapter `engine-wrappers/hunyuan3d.py` deleted): 7.4 GB `model.fp16.ckpt` downloaded (sha256 recorded) then OOM-killed during `torch.load` on this host; territory-restricted Community License review still required. Attempt: `.validation/reports/hunyuan3d-attempt.json` |
| VGGT | Multi-view geometry comparator | https://github.com/facebookresearch/vggt | Verify exact checkpoint and commercial-use terms; downstream mesh/texturing remains separate | **Removed from the registry after failed attempt** (adapter `engine-wrappers/vggt.py` deleted): process OOM-killed (SIGTERM from PID 0) during `VGGT()` fp32 weight init; 5.03 GB checkpoint would exceed host RAM; local CPU compat patch recorded. Attempt: `.validation/reports/vggt-attempt.json` |

## Record format for each approved engine

Create one version-controlled record per engine with:
- Upstream URL and immutable commit/tag.
- Source license and required notices.
- Model/checkpoint URL, revision, hash, and license.
- Third-party dependency/license inventory.
- Container image digest, base image, OS, Python/CUDA/runtime versions.
- Hardware profile and supported input constraints.
- Installation/setup command and exact smoke-test command.
- Real fixture identifier, rights/source, input SHA-256, and output artifact hashes.
- Observed exit status, wall time, peak resource usage, warnings, and validation report.
- Reviewer, decision date, deployment scope, and conditions for enabling/disabling.

## No fabricated benchmark rule

Do not fill this register with guessed commit hashes, guessed weight hashes, invented run times, or inferred test outcomes. Unknown fields remain explicitly pending until verified from upstream and actual execution.
