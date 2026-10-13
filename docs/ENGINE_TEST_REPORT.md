# Real engine test report

Use this template after configuring and running each actual engine. Do not report an engine as successful based only on its process exit code: inspect the generated geometry and confirm the output files open in a 3D viewer.

## Environment

- Test date/time and timezone:
- OS and version:
- CPU:
- GPU(s) and VRAM:
- RAM:
- CUDA / driver / Python / Blender or native runtime versions:
- Git commit of Mesh3D:
- Fixture identifier and permission/source:
- SHA-256 of every input image:
- Input mode (`single_image` or `multi_view`):

## One section per engine

- Engine ID and exact upstream commit/tag:
- Checkpoint/model identifier, revision, and SHA-256:
- Code license and checkpoint license decision:
- Wrapper revision and command configuration (redact secrets):
- Start/end time and wall-clock seconds measured by the worker:
- Exit status:
- Peak RAM / VRAM (if measured; state measurement method):
- Logs/warnings:
- Output files and formats:
- SHA-256 and size of each output:
- Did GLB/GLTF/OBJ/PLY open successfully? Which application/version?
- Mesh inspection: vertex/face count, normals, connected components, UVs/materials/textures where available:
- Visual quality observations: missing geometry, artifacts, texture issues, scale/orientation:
- Failure/recovery steps:
- Conclusion: passed / partial / failed / not runnable, with evidence:

## Multi-view capture-specific fields

- Number of input images:
- Image overlap/capture coverage notes:
- Registered cameras / total cameras (only if the engine reports them):
- Registration failures and actionable log excerpt:
- Sparse/dense reconstruction and texturing stage outcomes:

## Do not infer

- Do not invent runtimes, VRAM, camera counts, mesh metrics, quality scores, or successful artifacts.
- Use `not measured` when a metric was not captured and `not applicable` when it does not apply.
- Keep single-image generative results separate from multi-view photogrammetry results; their evidence and objectives differ.
- Never attach private or unlicensed source images to the report. Use hashes and a fixture identifier where sharing the images is not permitted.
