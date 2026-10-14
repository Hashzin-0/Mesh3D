import json
import os
import re
from dataclasses import dataclass
from pathlib import Path


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

    @property
    def validation_report_env(self) -> str:
        return f"MESH3D_ENGINE_{self.id.upper()}_VALIDATION_REPORT"


ENGINES = (
    Engine("triposr", "TripoSR", "single_image", "https://github.com/VAST-AI-Research/TripoSR", "Source + checkpoint verification", "Fast single-view generative reconstruction.", "MESH3D_ENGINE_TRIPOSR_CMD", "MESH3D_ENGINE_TRIPOSR_LICENSE_APPROVED"),
    Engine("instantmesh", "InstantMesh", "single_image", "https://github.com/TencentARC/InstantMesh", "Source + checkpoint verification", "Single-image reconstruction with mesh generation.", "MESH3D_ENGINE_INSTANTMESH_CMD", "MESH3D_ENGINE_INSTANTMESH_LICENSE_APPROVED"),
    Engine("stable_fast_3d", "Stable Fast 3D", "single_image", "https://github.com/Stability-AI/stable-fast-3d", "Community License review required", "Single-image textured asset generation.", "MESH3D_ENGINE_STABLE_FAST_3D_CMD", "MESH3D_ENGINE_STABLE_FAST_3D_LICENSE_APPROVED", True),
    Engine("hunyuan3d", "Hunyuan3D 2.1", "single_image", "https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1", "Deployment and checkpoint review required", "Image-conditioned 3D generation.", "MESH3D_ENGINE_HUNYUAN3D_CMD", "MESH3D_ENGINE_HUNYUAN3D_LICENSE_APPROVED", True),
    Engine("meshroom", "AliceVision / Meshroom", "multi_view", "https://github.com/alicevision/Meshroom", "Dependency and distribution audit", "Photogrammetry pipeline for overlapping photographs.", "MESH3D_ENGINE_MESHROOM_CMD", "MESH3D_ENGINE_MESHROOM_LICENSE_APPROVED"),
    Engine("colmap_openmvs", "COLMAP + OpenMVS", "multi_view", "https://github.com/colmap/colmap", "OpenMVS AGPL-3.0 review required", "Camera registration and dense reconstruction pipeline.", "MESH3D_ENGINE_COLMAP_OPENMVS_CMD", "MESH3D_ENGINE_COLMAP_OPENMVS_LICENSE_APPROVED", True),
    Engine("vggt", "VGGT", "multi_view", "https://github.com/facebookresearch/vggt", "Checkpoint and downstream mesh review", "Multi-view geometry estimation; a mesh/texturing pipeline is still required.", "MESH3D_ENGINE_VGGT_CMD", "MESH3D_ENGINE_VGGT_LICENSE_APPROVED", True),
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


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


def _validation_report_error(engine: Engine) -> str | None:
    raw_path = os.getenv(engine.validation_report_env, "").strip()
    if not raw_path:
        return f"No real-run validation report configured in {engine.validation_report_env}."
    path = Path(raw_path)
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return f"Cannot read validation report from {engine.validation_report_env}: {exc}."
    if not isinstance(report, dict):
        return "Validation report must be a JSON object."
    if report.get("schema_version") != 1 or report.get("engine_id") != engine.id:
        return "Validation report schema version or engine ID does not match."
    if report.get("result") != "passed":
        return "Validation report does not record a passed real-engine smoke test."
    if not _GIT_SHA.fullmatch(str(report.get("upstream_commit", ""))):
        return "Validation report must pin the upstream source to a full commit SHA."
    checkpoint = report.get("checkpoint")
    if not isinstance(checkpoint, dict) or not all(str(checkpoint.get(key, "")).strip() for key in ("id", "revision", "license")):
        return "Validation report must identify the checkpoint revision and license."
    if not _SHA256.fullmatch(str(checkpoint.get("sha256", ""))):
        return "Validation report must include the checkpoint SHA-256."
    if not _SHA256.fullmatch(str(report.get("dependency_lock_sha256", ""))):
        return "Validation report must include the dependency-lock SHA-256."
    hardware = report.get("hardware")
    if not isinstance(hardware, dict) or not str(hardware.get("cpu", "")).strip() or not str(hardware.get("accelerator", "")).strip():
        return "Validation report must identify the CPU and accelerator (or explicitly say none)."
    try:
        if float(hardware.get("ram_gb", 0)) <= 0:
            return "Validation report must include measured RAM in GB."
    except (TypeError, ValueError):
        return "Validation report must include measured RAM in GB."
    smoke = report.get("smoke_test")
    if not isinstance(smoke, dict) or smoke.get("exit_code") != 0:
        return "Validation report must record a successful smoke-test exit code."
    if not _SHA256.fullmatch(str(smoke.get("input_sha256", ""))) or not _SHA256.fullmatch(str(smoke.get("output_sha256", ""))):
        return "Validation report must include input and output SHA-256 hashes."
    try:
        if int(smoke.get("output_bytes", 0)) <= 0:
            return "Validation report must record a non-empty output artifact."
    except (TypeError, ValueError):
        return "Validation report must record a non-empty output artifact."
    output_path = Path(str(smoke.get("output_path", "")))
    if not str(smoke.get("output_path", "")).strip() or output_path.is_absolute() or ".." in output_path.parts:
        return "Validation report output_path must be a relative path inside the report's output directory."
    if smoke.get("opened_in_viewer") is not True:
        return "Validation report must confirm the generated artifact was opened and inspected."
    license_review = report.get("license_review")
    if not isinstance(license_review, dict) or license_review.get("decision") != "approved":
        return "Validation report must record an explicit license review decision of approved."
    if not str(license_review.get("reviewer", "")).strip() or not str(license_review.get("reviewed_at", "")).strip():
        return "Validation report must identify the reviewer and review date."
    return None


def public_engine(engine: Engine) -> dict:
    try:
        command = _command(engine)
        command_error = None
    except ValueError as exc:
        command = None
        command_error = str(exc)
    approved = os.getenv(engine.approval_env, "").lower() == "true"
    extra_review_passed = not engine.requires_extra_review or os.getenv(f"{engine.approval_env}_EXTRA", "").lower() == "true"
    validation_error = _validation_report_error(engine)
    if command_error:
        status, reason = "not_configured", command_error
    elif not approved:
        status, reason = "license_review", f"Review and explicitly approve the license gate using {engine.approval_env}=true."
    elif engine.requires_extra_review and not extra_review_passed:
        status, reason = "license_review", "Additional deployment/checkpoint review is required before this candidate can be enabled."
    elif not command:
        status, reason = "not_configured", f"No wrapper command configured in {engine.command_env}."
    elif validation_error:
        status, reason = "validation_required", validation_error
    else:
        status, reason = "ready", "License gates, wrapper command, and real-run validation report are present. Revalidate after changing runtime, checkpoint, dependencies, or deployment target."
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
