# Engine comparison matrix

This matrix is a candidate list for implementation and benchmarking, not a claim that every engine has already been installed or tested. Revalidate upstream versions, checkpoints, model-weight terms, dependencies, and GPU requirements before each engine is enabled.

## Task classes

### A. Single-image generative reconstruction

Input: one photo of one object. The engine infers hidden surfaces; those surfaces are estimates, not measured geometry. Evaluate the results for visual plausibility, mesh usability, texture quality, and runtime.

| Engine | Upstream | Role | License / constraints to verify | Initial priority |
|---|---|---|---|---|
| TripoSR | https://github.com/VAST-AI-Research/TripoSR | Fast single-image mesh generation; useful baseline for speed and output inspection | Upstream README states MIT for code and pretrained model; still archive exact revision and dependency notices | P0 |
| InstantMesh | https://github.com/TencentARC/InstantMesh | Single-image mesh generation using sparse-view reconstruction components | Apache-2.0 repository license; audit model weights, dependencies, and model card separately | P0 |
| Stable Fast 3D | https://github.com/Stability-AI/stable-fast-3d | Fast textured asset generation from a single image | Stability AI Community License is not an OSI-style permissive license; commercial registration, attribution/UI notice, and revenue limits may apply | P1, behind license gate |
| Hunyuan3D 2.1 | https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1 | Candidate for a higher-quality generative baseline and future texture pipeline | Community-license terms are territory- and deployment-sensitive; individual model packages may carry separate non-commercial terms. Audit every submodel/checkpoint and target market before activation | P2, license gate only |

**Adapter contract:** accept one validated image plus explicit generation settings; return a normalized artifact manifest and engine metrics. Keep each engine's native outputs for debugging and convert to GLB only in a separate export stage.

### B. Multi-image reconstruction

Input: multiple overlapping photographs of the same physical object. This mode should reconstruct camera poses and observed surface geometry rather than simply generating independent views from each photo.

| Pipeline / engine | Upstream | Role | License / constraints to verify | Initial priority |
|---|---|---|---|---|
| COLMAP + OpenMVS | https://github.com/colmap/colmap · https://github.com/cdcseacave/openMVS | SfM camera calibration and sparse reconstruction, then dense reconstruction, mesh refinement, and texture projection | COLMAP is BSD-3-Clause; OpenMVS is AGPL-3.0. Keep the pipeline isolated and obtain a license review before hosting/distribution | P0 technical baseline; deployment gated |
| AliceVision / Meshroom | https://github.com/alicevision/AliceVision · https://github.com/alicevision/Meshroom | Full photogrammetry pipeline for camera estimation, dense reconstruction, meshing, and texturing | MPL-2.0 project; audit bundled third-party dependencies and deployment requirements | P0 |
| VGGT | https://github.com/facebookresearch/vggt | Feed-forward multi-view geometry estimator; can predict camera and point-map information and export COLMAP-compatible data | Code and checkpoint licensing are not interchangeable. The commercial checkpoint may require approval; the original checkpoint has separate restrictions | P1 research comparator, checkpoint gate |

Do not label VGGT output as a production-ready textured watertight mesh unless the selected pipeline actually produces and validates those properties. It is a geometry-estimation candidate that may require additional surface reconstruction, UV generation, and texture projection.

### C. Supporting libraries

| Library | Purpose | Upstream |
|---|---|---|
| Blender (headless Python) | Optional mesh cleanup, decimation, normal repair, material checks, and export conversion | https://github.com/blender/blender |
| Trimesh | Mesh inspection and basic transformations / validation | https://github.com/mikedh/trimesh |
| Open3D | Point-cloud processing, geometry analysis, and reconstruction utilities | https://github.com/isl-org/Open3D |
| Three.js | Browser-based GLB viewer with synchronized cameras and lighting | https://github.com/mrdoob/three.js |
| glTF Transform | GLB optimization and texture/geometry processing where supported | https://github.com/donmccurdy/glTF-Transform |

Use supporting libraries only for responsibilities they can actually perform. A viewer is not a reconstruction engine; decimation does not repair missing geometry; format conversion does not improve source fidelity.

## Benchmark design

Run each candidate against the same versioned, real image sets and record:

1. Input mode, image count, image dimensions, capture metadata, and a hash of each input.
2. Engine name, code revision, checkpoint identifier/hash, container digest, settings, and dependency manifest.
3. End-to-end and per-stage duration, CPU/GPU/RAM/VRAM peak where observable, exit status, and failure reason.
4. Artifact type, byte size, vertex/face counts, texture dimensions, UV/material presence, and validation results.
5. Human ratings from blinded side-by-side review: visual likeness, unseen-side plausibility (single image), observed-surface fidelity (multi-view), texture quality, and editability.

### Metrics and their limitations

- **Camera registration rate:** fraction of input images registered by SfM; not meaningful for single-image generators.
- **Observed-surface completeness:** compare the reconstruction with available reference geometry or a calibrated scan; do not invent a score when no reference exists.
- **Geometry error:** use scale-aligned reference metrics only when a trustworthy reference mesh/scan exists.
- **Mesh integrity:** report boundary edges, non-manifold edges, connected components, degenerate faces, and normals; watertightness is not a universal requirement for visual assets.
- **Texture quality:** record texture resolution and use blinded visual assessment; resolution alone is not quality.
- **Performance:** report hardware and cold/warm-cache conditions, not only elapsed time.

Do not combine all values into a single “best engine” score until the product owner defines weights. Preserve raw metrics and allow comparisons within the correct task class.

## License gate

Before enabling an engine in a hosted or distributed product, record:
- repository license and exact commit;
- model checkpoint / weight license and accepted terms;
- licenses for dependencies and external binaries;
- attribution and notice requirements;
- restrictions on commercial use, redistribution, hosted use, or revenue;
- whether legal review is required.

A repository being public or labeled “open source” does not by itself establish that its pretrained weights are commercially usable.
