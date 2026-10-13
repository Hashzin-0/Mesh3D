# Engine wrapper contract

Each adapter calls a real upstream project; no generated placeholder geometry or fabricated scores are allowed. The adapters in this directory are the concrete entry points:
- `triposr.py`
- `instantmesh.py`
- `stable_fast_3d.py`
- `hunyuan3d.py`
- `meshroom.py`
- `colmap_openmvs.py`
- `vggt.py`

See [the engine integration guide](../docs/ENGINE_INTEGRATION.md) for the upstream CLI/API contract, environment variables, licensing gates, provisioning and smoke-test procedure.

## Shared contract

Mesh3D substitutes these exact placeholders in each configured JSON argv array:
- `{input_dir}`: validated uploaded source images
- `{output_dir}`: engine-specific output directory writable by the worker
- `{mode}`: `single_image` or `multi_view`

The wrapper must validate mode/count, invoke the real upstream code, return a non-zero exit code on failure, and write `manifest.json` only after real artifacts exist. Manifest shape:

```json
{
  "artifacts": [
    { "path": "reconstruction.glb", "format": "glb" }
  ]
}
```

Paths must be relative to the output directory. Mesh3D validates paths, copies nested outputs into the engine output root for artifact delivery, and computes SHA-256/byte size from actual files.

Do not commit downloaded weights, credentials, private datasets, or generated outputs. Do not enable license flags until the exact code and checkpoint terms are reviewed. An adapter file or a configured command is not evidence that the model was smoke-tested. Record real test outcomes in `docs/ENGINE_TEST_REPORT.md`.
