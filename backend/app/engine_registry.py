import json
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Engine:
    id: str
    name: str
    mode: str
    upstream: str
    license: str
    description: str
    command_env: str
    approval_env: str
    requires_extra_review: bool = False

ENGINES = (
    Engine("triposr", "TripoSR", "single_image", "https://github.com/VAST-AI-Research/TripoSR", "Source + checkpoint verification", "Fast single-view generative reconstruction.", "MESH3D_ENGINE_TRIPOSR_CMD", "MESH3D_ENGINE_TRIPOSR_LICENSE_APPROVED"),
    Engine("instantmesh", "InstantMesh", "single_image", "https://github.com/TencentARC/InstantMesh", "Source + checkpoint verification", "Single-image reconstruction with mesh generation.", "MESH3D_ENGINE_INSTANTMESH_CMD", "MESH3D_ENGINE_INSTANTMESH_LICENSE_APPROVED"),
    Engine("stable_fast_3d", "Stable Fast 3D", "single_image", "https://github.com/Stability-AI/stable-fast-3d", "Community License review required", "Single-image textured asset generation.", "MESH3D_ENGINE_STABLE_FAST_3D_CMD", "MESH3D_ENGINE_STABLE_FAST_3D_LICENSE_APPROVED", True),
    Engine("hunyuan3d", "Hunyuan3D 2.1", "single_image", "https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1", "Deployment and checkpoint review required", "Image-conditioned 3D generation.", "MESH3D_ENGINE_HUNYUAN3D_CMD", "MESH3D_ENGINE_HUNYUAN3D_LICENSE_APPROVED", True),
    Engine("meshroom", "AliceVision / Meshroom", "multi_view", "https://github.com/alicevision/Meshroom", "Dependency and distribution audit", "Photogrammetry pipeline for overlapping photographs.", "MESH3D_ENGINE_MESHROOM_CMD", "MESH3D_ENGINE_MESHROOM_LICENSE_APPROVED"),
    Engine("colmap_openmvs", "COLMAP + OpenMVS", "multi_view", "https://github.com/colmap/colmap", "OpenMVS AGPL-3.0 review required", "Camera registration and dense reconstruction pipeline.", "MESH3D_ENGINE_COLMAP_OPENMVS_CMD", "MESH3D_ENGINE_COLMAP_OPENMVS_LICENSE_APPROVED", True),
    Engine("vggt", "VGGT", "multi_view", "https://github.com/facebookresearch/vggt", "Checkpoint and downstream mesh review", "Multi-view geometry estimation; a mesh/texturing pipeline is still required.", "MESH3D_ENGINE_VGGT_CMD", "MESH3D_ENGINE_VGGT_LICENSE_APPROVED", True),
)

def _command(engine: Engine) -> list[str] | None:
    raw = os.getenv(engine.command_env, "").strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{engine.command_env} must be a JSON array of command arguments") from exc
    if not isinstance(parsed, list) or not parsed or not all(isinstance(part, str) and part for part in parsed):
        raise ValueError(f"{engine.command_env} must be a non-empty JSON array of strings")
    return parsed

def public_engine(engine: Engine) -> dict:
    try:
        command = _command(engine)
        command_error = None
    except ValueError as exc:
        command = None
        command_error = str(exc)
    approved = os.getenv(engine.approval_env, "").lower() == "true"
    extra_review_passed = not engine.requires_extra_review or os.getenv(f"{engine.approval_env}_EXTRA", "").lower() == "true"
    if command_error:
        status, reason = "not_configured", command_error
    elif engine.requires_extra_review and not extra_review_passed:
        status, reason = "license_review", "Additional deployment/checkpoint review is required before this candidate can be enabled."
    elif not approved:
        status, reason = "license_review", f"Review and explicitly approve the license gate using {engine.approval_env}=true."
    elif not command:
        status, reason = "not_configured", f"No wrapper command configured in {engine.command_env}."
    else:
        status, reason = "ready", "Wrapper command and license approval are configured; actual engine execution still needs validation."
    return {"id": engine.id, "name": engine.name, "mode": engine.mode, "upstream": engine.upstream, "license": engine.license, "description": engine.description, "status": status, "reason": reason}

def resolve_engine(engine_id: str) -> tuple[Engine, list[str]]:
    engine = next((candidate for candidate in ENGINES if candidate.id == engine_id), None)
    if engine is None:
        raise ValueError(f"Unknown engine: {engine_id}")
    public = public_engine(engine)
    if public["status"] != "ready":
        raise RuntimeError(f"{engine.name} is unavailable: {public['reason']}")
    command = _command(engine)
    if not command:
        raise RuntimeError(f"{engine.name} wrapper is not configured.")
    return engine, command
