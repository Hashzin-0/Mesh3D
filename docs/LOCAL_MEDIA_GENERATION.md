# Local image and video generation

## Decision

Mesh3D uses a self-hosted ComfyUI instance as the first local generation runtime. The API integrates through ComfyUI HTTP endpoints; no paid/hosted generation API is used. ComfyUI and model weights are not bundled; operators install them on a trusted machine or GPU host. The browser cannot submit arbitrary workflows.

## Supported local pipeline

- Images: ComfyUI API workflow with a local image model (e.g. a license-reviewed Stable Diffusion checkpoint or compatible FLUX checkpoint). Hugging Face Diffusers + PyTorch is the programmatic alternative for dedicated Python pipelines; add it as a separate adapter only when its environment and checkpoints are provisioned.
- Video: ComfyUI workflow using a locally installed supported video model, initially Wan 2.2 or LTX-Video. Exact node packs and workflow graphs are version-specific and must be reviewed and pinned.
- Post-processing: FFmpeg for transcoding, frame extraction, audio muxing and format normalization. It is not a generative model.
- Existing 3D: preserve the current reconstruction registry and Three.js viewer.

## API integration

- GET /api/media/engines: checks reachability and whether local image/video workflow files and prompt-node mappings are configured.
- POST /api/media/generate: accepts only kind=image|video and a prompt; reads the workflow configured by the server, injects the prompt into one explicitly configured node and queues it in local ComfyUI.
- GET /api/media/jobs/{id}: reads real ComfyUI history and returns generated outputs only after they exist.
- GET /api/media/artifact: proxies an allow-listed image/video MIME type from the configured ComfyUI instance after validating filename/subfolder references.

The browser never supplies workflow JSON, upstream URLs, file-system paths, command strings or model checkpoints. The ComfyUI URL is operator configuration, not client input.

## Configuration

Set these variables in the runtime config or local untracked .env:

- MESH3D_COMFYUI_URL (default http://127.0.0.1:8188)
- MESH3D_COMFYUI_IMAGE_WORKFLOW
- MESH3D_COMFYUI_IMAGE_PROMPT_NODE
- MESH3D_COMFYUI_IMAGE_PROMPT_INPUT (default text)
- MESH3D_COMFYUI_VIDEO_WORKFLOW
- MESH3D_COMFYUI_VIDEO_PROMPT_NODE
- MESH3D_COMFYUI_VIDEO_PROMPT_INPUT (default text)

Workflow files must use ComfyUI API-format JSON and prompt node ID/input name must match. Keep model weights and workflow files outside Git unless the repository explicitly licenses and intends to distribute them. Do not mark a workflow ready until it has been tested against the exact installed ComfyUI version and node packs.

## Model and library candidates

| Layer | Candidate | Purpose | License / deployment gate |
|---|---|---|---|
| Workflow runtime | ComfyUI | Local node graph and execution queue | Review project license, custom nodes, and custom node code |
| Python inference | Hugging Face Diffusers + PyTorch | Direct local inference for compatible diffusion models | Review code, checkpoint, tokenizer/text encoder, VAE, and dependency licenses separately |
| Image checkpoints | Stable Diffusion family; compatible FLUX checkpoints | Text-to-image and image editing when supported | Terms vary by exact checkpoint/version; do not assume commercial permission |
| Video checkpoints | Wan 2.2; LTX-Video | Text/image-conditioned video, according to selected model and workflow | Checkpoint license and hardware requirements differ; local execution is not zero-cost |
| Media utilities | FFmpeg; Pillow | Video muxing/transcoding and image validation | Respect codec/build and asset licensing requirements |
| Existing 3D | Three.js + current Mesh3D adapters | Preview and compare real 3D outputs | Preserve existing engine-specific approval gates |

## Deployment boundary

The existing Vercel setup exposes the Vite app and FastAPI API only. Do not run GPU inference inside Vercel Functions and do not assume a local ComfyUI process is present in a Vercel instance. For production generation, deploy ComfyUI on an operator-managed local/GPU host and configure a private network path from the API, or run the whole stack locally with Docker Compose. The current keep-local persistence and bindings=none choices remain unchanged. Public exposure requires authentication, quotas, network isolation, and artifact retention review.

## Verification gate

1. Start ComfyUI and confirm GET /system_stats works from the API host.
2. Configure a real API-format image workflow and verify an actual image is returned.
3. Configure a real API-format video workflow and verify a playable video is returned.
4. Run the API unit tests, frontend build, and existing backend test suite.
5. Record ComfyUI commit, custom-node versions, model checkpoint revision/hash, model license, GPU/VRAM, settings, output hashes and manual visual review. Repository-level unit tests do not prove real inference.
