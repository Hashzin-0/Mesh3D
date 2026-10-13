# Engine wrapper contract

This directory is mounted read-only into the worker. Add one wrapper per engine after pinning the upstream revision, checkpoint, runtime, and license decision. Do not commit downloaded weights, credentials, private datasets, or large model binaries.

The configured command is a JSON argv array (never a shell command string). Mesh3D replaces these exact placeholders in each argv item:
- `{input_dir}`: read-only-by-convention source images for the job
- `{output_dir}`: engine-specific output directory, writable by the worker
- `{mode}`: `single_image` or `multi_view`

The wrapper must:
1. Validate its arguments and reject unsupported input mode/counts.
2. Invoke the real, pinned upstream engine with explicit resource/time limits.
3. Exit non-zero on any failure; write diagnostics to stdout/stderr without secrets.
4. Write `manifest.json` in `{output_dir}` only after successful processing. Shape:

```json
{
  "artifacts": [
    { "path": "reconstruction.glb", "format": "glb" }
  ]
}
```

Each artifact path must be relative to the output directory and point to an existing real file. Mesh3D calculates SHA-256 and byte size from the actual file. It does not generate substitute geometry or synthesize benchmark scores.

A wrapper is not considered verified merely because the command is configured. Run it against a rights-cleared real fixture, inspect the output manually, verify formats, and record engine/checkpoint revisions, hardware, elapsed time, warnings, and hashes in the provenance register. The API registry stays gated until the license approval flags are explicitly enabled.
