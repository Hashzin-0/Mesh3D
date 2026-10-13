#!/usr/bin/env python3
"""Shared safety and artifact helpers for Mesh3D's upstream engine adapters."""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
from PIL import Image, UnidentifiedImageError

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
ARTIFACT_SUFFIXES = {".glb", ".gltf", ".obj", ".ply", ".stl"}

def parse_args(description: str):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--mode", choices=("single_image", "multi_view"), required=True)
    return parser.parse_args()

def validate_inputs(args, *, single: bool = False, minimum: int = 1) -> list[Path]:
    source = args.input_dir.resolve()
    if not source.is_dir():
        raise SystemExit(f"Input directory does not exist: {source}")
    images = sorted(p for p in source.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)
    if len(images) < minimum:
        raise SystemExit(f"Expected at least {minimum} supported image(s); found {len(images)}.")
    if single and (args.mode != "single_image" or len(images) != 1):
        raise SystemExit("This engine requires exactly one image in single_image mode.")
    if not single and args.mode != "multi_view":
        raise SystemExit("This engine adapter requires multi_view mode.")
    for path in images:
        try:
            with Image.open(path) as image:
                image.verify()
        except (OSError, UnidentifiedImageError) as exc:
            raise SystemExit(f"Invalid input image {path.name}: {exc}") from exc
    args.output_dir.mkdir(parents=True, exist_ok=True)
    return images

def required_env(name: str, *, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if not value:
        raise SystemExit(f"Required environment variable {name} is not configured.")
    return value

def engine_python(prefix: str, root: Path) -> str:
    """Resolve a dedicated interpreter without silently changing environments."""
    configured = os.getenv(f"{prefix}_PYTHON")
    if configured:
        return configured
    candidates = (root / ".venv" / "bin" / "python", root / "venv" / "bin" / "python")
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return sys.executable

def run_command(argv: list[str], *, cwd: Path | None = None) -> None:
    import subprocess
    print("Running upstream command:", " ".join(argv), flush=True)
    result = subprocess.run(argv, cwd=str(cwd) if cwd else None, check=False)
    if result.returncode:
        raise SystemExit(f"Upstream engine exited with code {result.returncode}.")

def write_manifest(output_dir: Path, paths: list[Path]) -> None:
    root = output_dir.resolve()
    artifacts = []
    for path in paths:
        resolved = path.resolve()
        if not resolved.is_file() or resolved.suffix.lower() not in ARTIFACT_SUFFIXES:
            continue
        if root not in resolved.parents:
            raise SystemExit(f"Refusing artifact outside output directory: {resolved}")
        artifacts.append({"path": resolved.relative_to(root).as_posix(), "format": resolved.suffix.lower().lstrip(".")})
    if not artifacts:
        raise SystemExit("The upstream engine finished but produced no supported 3D artifact. No manifest was written.")
    (root / "manifest.json").write_text(json.dumps({"artifacts": artifacts}, indent=2), encoding="utf-8")
    print(f"Manifest contains {len(artifacts)} real artifact(s).", flush=True)

def collect_outputs(output_dir: Path, *, preferred: tuple[str, ...] = (".glb", ".gltf", ".obj", ".ply", ".stl")) -> list[Path]:
    root = output_dir.resolve()
    candidates = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in ARTIFACT_SUFFIXES and p.name != "manifest.json"]
    rank = {suffix: i for i, suffix in enumerate(preferred)}
    candidates.sort(key=lambda p: (rank.get(p.suffix.lower(), 99), len(p.parts), p.name))
    if not candidates:
        raise SystemExit(f"No supported mesh/point-cloud output found under {root}.")
    chosen = [p for p in candidates if p.suffix.lower() in {".glb", ".gltf"}]
    if not chosen:
        chosen = [p for p in candidates if p.suffix.lower() in {".obj", ".ply", ".stl"}]
    return chosen[:10]
