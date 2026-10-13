# Engine provenance and license gates

Status: initial register. Candidate descriptions below are planning references, not proof of successful installation, execution, or license clearance for a particular deployment.

## Activation policy

No engine becomes selectable in a release until the project records: exact upstream revision, code license, model/checkpoint identifier and license, dependency/license inventory, source of downloaded weights, cryptographic hashes, supported hardware, setup instructions, smoke-test command, expected output contract, and a reviewed deployment decision.

| Candidate | Intended mode | Upstream | Initial gate | Current evidence |
|---|---|---|---|---|
| TripoSR | Single image | https://github.com/VAST-AI-Research/TripoSR | Verify exact revision, checkpoint provenance, dependency notices, and runtime | Not installed or smoke-tested |
| InstantMesh | Single image | https://github.com/TencentARC/InstantMesh | Verify exact revision, weight/model-card terms, dependency notices, and runtime | Not installed or smoke-tested |
| Stable Fast 3D | Single image | https://github.com/Stability-AI/stable-fast-3d | Community License and deployment/commerce conditions must be approved | Disabled pending review |
| Hunyuan3D 2.1 | Single image | https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1 | Review territory, hosting/deployment terms, and every submodel/checkpoint license | Disabled pending review |
| AliceVision / Meshroom | Multi-view | https://github.com/alicevision/AliceVision · https://github.com/alicevision/Meshroom | Pin revisions, inventory bundled dependencies, confirm installation and CLI workflow | Not installed or smoke-tested |
| COLMAP + OpenMVS | Multi-view | https://github.com/colmap/colmap · https://github.com/cdcseacave/openMVS | Separate license review for COLMAP and AGPL-3.0 OpenMVS before hosted deployment | Deployment gated; not smoke-tested |
| VGGT | Multi-view geometry comparator | https://github.com/facebookresearch/vggt | Verify exact checkpoint and commercial-use terms; downstream mesh/texturing remains separate | Disabled pending checkpoint review |

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
