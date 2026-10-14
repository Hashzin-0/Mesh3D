# Blender + Python + Gemini engine

## Architecture and Vercel boundary

The Mesh3D frontend and FastAPI API can remain on Vercel. Blender is **not installed or executed inside a Vercel Function**. Deploy `blender-worker/` as a separate Docker service with a persistent volume mounted at `/data`. The Vercel backend proxies authenticated requests to that worker.

Flow:

1. The browser submits a prompt and optional reference image to `POST /api/blender/jobs`.
2. The Vercel API checks configuration and forwards the multipart request using a server-side bearer token.
3. The worker validates the image and creates a persistent job record.
4. The worker generates a Python script, runs the Blender executable in background mode, captures logs, saves a preview and editable `.blend`, and returns real artifact metadata.
5. With `GEMINI_API_KEY` configured on the worker and a reference image attached, Gemini reviews the reference and render, revises the complete script, and Blender renders again. This repeats until RGB pixel equality is reached or the configured iteration limit is exhausted.
6. The frontend polls job status and displays the real render, pixel-difference image, iteration metrics, Python scripts, editable project, and MP4 when requested.

## Deployment configuration

### On the separate Blender worker

Deploy from the repository's `blender-worker/` directory using its Dockerfile. Mount a persistent disk/volume at `/data`; use one worker process for the current file-backed job store. The image installs Blender and FFmpeg. Do not deploy this container on Vercel.

Required environment variables:

- `MESH3D_BLENDER_WORKER_TOKEN`: long random bearer token shared with the Vercel backend.
- `MESH3D_BLENDER_DATA_DIR`: persistent directory, normally `/data`.
- `MESH3D_BLENDER_MAX_ITERATIONS`: optional, 1–8, default 5.
- `MESH3D_BLENDER_TIMEOUT_SECONDS`: optional, 30–1800 seconds per Blender invocation, default 900.
- `GEMINI_API_KEY`: optional; stored only on the worker, never in browser code or Vercel client variables.
- `MESH3D_GEMINI_MODEL`: optional model ID, default `gemini-2.5-flash`.

The worker's public `/health` endpoint exposes only liveness. `/v1/status`, job creation, job status and artifact retrieval require the bearer token. Put the worker behind HTTPS, restrict network access to the backend where possible, and rotate the token if exposed. Render jobs are serialized to avoid concurrent Blender renders exhausting worker memory.

### On the Vercel backend

Set these server-side environment variables in Vercel project settings (Preview/Production as appropriate):

- `MESH3D_BLENDER_ENABLED=true`: explicit opt-in; otherwise the engine remains disabled.
- `MESH3D_BLENDER_WORKER_URL=https://your-private-worker-host`: worker base URL without a trailing slash.
- `MESH3D_BLENDER_WORKER_TOKEN`: the same secret as the worker's token.

Do not set `GEMINI_API_KEY` as a `VITE_*` variable. The key belongs on the worker. This implementation does not modify any existing `.env*` file or Vercel environment variables. **Security gate:** this repository does not currently demonstrate user authentication or per-user quotas for these public API routes. Keep `MESH3D_BLENDER_ENABLED=false` on a public deployment until the app is protected by authentication and rate/usage limits; the worker token authenticates only the backend-to-worker hop, not end users.

## Detailed script-generation contract

Gemini is instructed to produce a complete Blender Python script, not a shell script or a workflow JSON. The script should use the installed Blender's bundled Python and `bpy`, consult the official API reference (`https://docs.blender.org/api/current/`), and deliberately select the Blender features appropriate to the scene:

- Scene and data organization: `bpy.data`, collections, objects, meshes, curves, text, cameras and lights.
- Geometry: primitive operators, mesh data, curves, bevels, subdivision, weighted normals, modifiers, transforms and object origins.
- Materials: node-based Principled BSDF, textures and material properties.
- Lighting and environment: world shader nodes, area/point/sun lights, shadows, ambient/world strength and color management.
- Camera and composition: focal length, perspective, camera orientation, depth of field when useful, framing and render aspect ratio.
- Rendering: compatible Eevee/Cycles engine, bounded samples, denoising, resolution, output format and color management.
- Compositing and effects: compositor nodes, transparency and effects only when they support the target.
- Animation for video: frame range, FPS, keyframes, interpolation, camera/object motion and an actual rendered image sequence.

The script must define the output placeholders required by the worker, render a still preview, save an editable `.blend`, and for video render a short sequence for FFmpeg. It must not rely on optional add-ons, unpinned downloaded assets, internet access, subprocesses, arbitrary filesystem reads/writes, dynamic imports, `eval` or `exec`. A basic AST allowlist rejects unapproved imports and known dangerous operations; this is defense in depth, not a replacement for deploying the worker in an isolated, unprivileged container with resource limits.

When Gemini is not configured, the worker uses a deterministic keyword-driven procedural primitive generator. This is real Blender rendering, but it is not a general-purpose semantic text-to-3D model and it does not perform LLM-based refinement.

## Reference-image comparison loop

When both the reference image and Gemini key are available:

1. Decode and validate the reference image; preserve the original file.
2. Use the reference as a visual target for geometry, silhouette, framing, perspective, color, materials and lighting. Do not paste the reference into a full-frame plane or compositor merely to fake a match.
3. Render a PNG at the reference's pixel dimensions.
4. Compare RGB arrays and save a difference image. Record exact pixel count, changed pixel count, mean absolute error (MAE), RMSE and PSNR.
5. Send the reference, latest render, metrics and previous script to Gemini for targeted corrections.
6. Repeat up to `MESH3D_BLENDER_MAX_ITERATIONS`. Stop early only if every compared RGB pixel is equal, or when the iteration limit is reached.

**Pixel-perfect equality is not guaranteed.** A 3D scene rendered through a different projection/renderer will often never match every pixel in a photograph. The system reports exact equality only when the compared pixel arrays are actually identical; it never labels a merely similar render as exact. The loop is bounded to control time, memory and Gemini cost.

Video output uses the final script's actual rendered frame sequence and FFmpeg. The reference comparison is against the still preview, not every frame of the video.

## API contract

- `GET /api/blender/engine`: worker reachability, Blender version, and whether Gemini is configured.
- `POST /api/blender/jobs`: multipart `kind=image|video`, `prompt`, optional `reference_image`.
- `GET /api/blender/jobs/{id}`: actual job status, iteration history, pixel metrics and artifact manifest.
- `GET /api/blender/artifact/{id}/{filename}`: server-side proxy for an artifact belonging to that job.

The browser cannot supply worker URLs, shell commands, Python scripts, file paths, or API credentials. Artifact paths are allow-listed against the job manifest.

## Verification checklist

1. Build the worker image and verify `blender --version` and `ffmpeg -version`.
2. Start the worker with a persistent volume and confirm `/health` and authenticated `/v1/status`.
3. Configure the same worker token and URL in Vercel Preview, with `MESH3D_BLENDER_ENABLED=true`.
4. Test a prompt without a reference; verify a real preview and editable `.blend`.
5. Test a reference image with Gemini enabled; verify each render, diff image, metrics, and actual script revisions.
6. Test video; verify the MP4 plays and its frame sequence came from Blender.
7. Run the worker unit tests, backend tests and frontend build.
8. Record worker image digest, Blender version, Gemini model, render settings, output hashes, resource use and manual visual review.

Repository CI can validate Python logic and the frontend build. It cannot prove a real Blender render or Gemini inference unless those runtimes and credentials are provisioned in the test environment.
