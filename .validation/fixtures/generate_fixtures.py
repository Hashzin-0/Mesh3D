#!/usr/bin/env python3
"""Generate rights-cleared synthetic fixtures for Mesh3D engine smoke tests.

Origin: created by this script in this workspace (no third-party assets).
Rights: original work produced for pipeline smoke testing; no external copyright claims.
Purpose: provide deterministic single-image and multi-view inputs with documented provenance
so real engine runs can be validated without uploading private or licensed photographs.

Multi-view images render a textured sphere over a textured ground plane using a
z-buffered scanline rasterizer with 3D-consistent procedural texturing, so SfM
pipelines can register real geometric correspondences across views.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
SINGLE = ROOT / "single_image" / "input"
MULTI = ROOT / "multi_view" / "input"


def _hash3(cell: np.ndarray) -> np.ndarray:
    """Deterministic pseudo-random values in [0,1) for integer 3D cells."""
    x = cell[:, 0].astype(np.float64)
    y = cell[:, 1].astype(np.float64)
    z = cell[:, 2].astype(np.float64)
    n = np.sin(x * 127.1 + y * 311.7 + z * 74.7) * 43758.5453123
    return n - np.floor(n)


def procedural_color(points: np.ndarray) -> np.ndarray:
    """3D-consistent high-frequency texture with sharp features for SIFT."""
    # Multi-scale binary hash noise (sharp transitions -> strong gradients).
    acc = np.zeros(points.shape[0])
    amp = 1.0
    freq = 3.0
    for _ in range(5):
        cells = np.floor(points * freq)
        acc += amp * (_hash3(cells) - 0.5)
        freq *= 2.1
        amp *= 0.55
    base = 128.0 + 110.0 * np.tanh(acc * 3.0)

    # Fine salt-and-pepper for additional corners.
    fine = _hash3(np.floor(points * 24.0))
    base = base + (fine - 0.5) * 70.0

    # Directional bands (help orientation).
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    bands = 25.0 * np.sin(y * 30.0) + 15.0 * np.sin((x + z) * 22.0)

    r = base + bands + 20.0 * np.sin(x * 9.0)
    g = base - bands * 0.5 + 20.0 * np.sin(y * 9.0 + 1.3)
    b = base + 15.0 * np.sin(z * 9.0 + 2.6) - bands * 0.3
    colors = np.stack([r, g, b], axis=1)

    # Unique spherical cap markers at fixed 3D directions.
    markers = [
        (np.array([1.0, 0.0, 0.0]), np.array([255, 30, 30])),
        (np.array([0.0, 1.0, 0.0]), np.array([30, 255, 30])),
        (np.array([0.0, 0.0, 1.0]), np.array([30, 30, 255])),
        (np.array([-1.0, 0.0, 0.0]), np.array([255, 255, 30])),
        (np.array([0.0, -1.0, 0.0]), np.array([255, 30, 255])),
        (np.array([0.0, 0.0, -1.0]), np.array([30, 255, 255])),
        (np.array([0.577, 0.577, 0.577]), np.array([255, 128, 0])),
        (np.array([-0.577, 0.577, -0.577]), np.array([0, 128, 255])),
    ]
    norms = points / (np.linalg.norm(points, axis=1, keepdims=True) + 1e-9)
    for direction, color in markers:
        d = direction / np.linalg.norm(direction)
        dots = norms @ d
        mask = dots > 0.97
        colors[mask] = color
    return np.clip(colors, 0, 255)


def make_sphere(radius: float = 1.0, stacks: int = 48, slices: int = 64):
    verts = []
    for i in range(stacks + 1):
        phi = np.pi * i / stacks
        for j in range(slices):
            theta = 2 * np.pi * j / slices
            x = radius * np.sin(phi) * np.cos(theta)
            y = radius * np.cos(phi)
            z = radius * np.sin(phi) * np.sin(theta)
            verts.append([x, y, z])
    verts = np.array(verts)

    def vid(i, j):
        return i * slices + (j % slices)

    tris = []
    for i in range(stacks):
        for j in range(slices):
            a, b = vid(i, j), vid(i, j + 1)
            c, d = vid(i + 1, j + 1), vid(i + 1, j)
            if i != 0:
                tris.append((a, b, c))
            if i != stacks - 1:
                tris.append((a, c, d))
    return verts, np.array(tris, dtype=np.int32)


def make_plane(size: float = 4.0, n: int = 24):
    """XZ ground plane triangulation at y=-1.05."""
    verts = []
    xs = np.linspace(-size, size, n)
    zs = np.linspace(-size, size, n)
    for z in zs:
        for x in xs:
            verts.append([x, -1.05, z])
    verts = np.array(verts)

    def vid(i, j):
        return i * n + j

    tris = []
    for i in range(n - 1):
        for j in range(n - 1):
            a, b, c, d = vid(i, j), vid(i, j + 1), vid(i + 1, j + 1), vid(i + 1, j)
            tris.append((a, b, c))
            tris.append((a, c, d))
    return verts, np.array(tris, dtype=np.int32)


def camera_transform(yaw_deg: float, pitch_deg: float, distance: float = 4.2):
    yaw, pitch = np.deg2rad(yaw_deg), np.deg2rad(pitch_deg)
    eye = np.array(
        [
            distance * np.cos(pitch) * np.sin(yaw),
            distance * np.sin(pitch),
            distance * np.cos(pitch) * np.cos(yaw),
        ]
    )
    target = np.array([0.0, 0.0, 0.0])
    up = np.array([0.0, 1.0, 0.0])
    forward = target - eye
    forward = forward / np.linalg.norm(forward)
    right = np.cross(forward, up)
    right = right / np.linalg.norm(right)
    true_up = np.cross(right, forward)
    return eye, right, true_up, forward


def render_view(yaw_deg: float, pitch_deg: float, size: int = 640) -> Image.Image:
    eye, right, up, forward = camera_transform(yaw_deg, pitch_deg)
    focal = size * 1.1
    center = size / 2.0

    sphere_v, sphere_t = make_sphere(1.0, stacks=40, slices=56)
    plane_v, plane_t = make_plane(3.5, n=20)
    # Small satellite sphere for parallax/depth variety.
    sat_v, sat_t = make_sphere(0.35, stacks=20, slices=28)
    sat_v = sat_v + np.array([1.7, -0.3, 0.6])

    objects = [
        (sphere_v, sphere_t, True),
        (sat_v, sat_t, True),
        (plane_v, plane_t, False),
    ]

    color_buf = np.full((size, size, 3), 235.0)
    depth_buf = np.full((size, size), 1e9)

    def to_camera(points_world):
        rel = points_world - eye
        cam = np.stack(
            [rel @ right, rel @ up, rel @ forward],
            axis=1,
        )
        return cam

    def draw_mesh(verts_world, tris, smooth_normals):
        cam = to_camera(verts_world)
        # Project
        z = cam[:, 2]
        z_safe = np.where(np.abs(z) < 1e-6, 1e-6, z)
        u = center + (cam[:, 0] * focal) / z_safe
        v = center - (cam[:, 1] * focal) / z_safe
        proj = np.stack([u, v, z], axis=1)

        if smooth_normals:
            normals = verts_world / (
                np.linalg.norm(verts_world, axis=1, keepdims=True) + 1e-9
            )
            # For satellite offset, recompute normals relative to its center.
            if verts_world is sat_v:
                center_pt = verts_world.mean(axis=0, keepdims=True)
                normals = (verts_world - center_pt) / (
                    np.linalg.norm(verts_world - center_pt, axis=1, keepdims=True) + 1e-9
                )
        else:
            normals = None

        # Sort triangles back-to-front for correctness not needed with zbuffer;
        # process all.
        for tri in tris:
            i0, i1, i2 = tri
            p0, p1, p2 = proj[i0], proj[i1], proj[i2]
            # Near-plane reject
            if p0[2] <= 0.05 or p1[2] <= 0.05 or p2[2] <= 0.05:
                continue
            min_x = max(int(np.floor(min(p0[0], p1[0], p2[0]))), 0)
            max_x = min(int(np.ceil(max(p0[0], p1[0], p2[0]))), size - 1)
            min_y = max(int(np.floor(min(p0[1], p1[1], p2[1]))), 0)
            max_y = min(int(np.ceil(max(p0[1], p1[1], p2[1]))), size - 1)
            if max_x < min_x or max_y < min_y:
                continue
            x0, y0 = p0[0], p0[1]
            x1, y1 = p1[0], p1[1]
            x2, y2 = p2[0], p2[1]
            denom = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
            if abs(denom) < 1e-12:
                continue
            xs = np.arange(min_x, max_x + 1)
            ys = np.arange(min_y, max_y + 1)
            grid_x, grid_y = np.meshgrid(xs, ys)
            w0 = ((y1 - y2) * (grid_x - x2) + (x2 - x1) * (grid_y - y2)) / denom
            w1 = ((y2 - y0) * (grid_x - x2) + (x0 - x2) * (grid_y - y2)) / denom
            w2 = 1.0 - w0 - w1
            inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            if not inside.any():
                continue
            z = w0 * p0[2] + w1 * p1[2] + w2 * p2[2]
            depth_region = depth_buf[min_y : max_y + 1, min_x : max_x + 1]
            update = inside & (z < depth_region)
            if not update.any():
                continue
            if smooth_normals:
                n = (
                    w0[..., None] * normals[i0]
                    + w1[..., None] * normals[i1]
                    + w2[..., None] * normals[i2]
                )
                # Reconstruct approximate world position for texturing:
                # interpolate world verts.
                pw = (
                    w0[..., None] * verts_world[i0]
                    + w1[..., None] * verts_world[i1]
                    + w2[..., None] * verts_world[i2]
                )
                colors = procedural_color(pw.reshape(-1, 3)).reshape(pw.shape)
            else:
                # Textured ground plane via 3D-consistent hash noise on world XZ.
                pw = (
                    w0[..., None] * verts_world[i0]
                    + w1[..., None] * verts_world[i1]
                    + w2[..., None] * verts_world[i2]
                )
                flat = pw.reshape(-1, 3)
                # Reuse procedural_color restricted to XZ variation.
                cols = procedural_color(np.column_stack([flat[:, 0], np.zeros_like(flat[:, 0]), flat[:, 2]]))
                colors = cols.reshape(pw.shape)
            color_region = color_buf[min_y : max_y + 1, min_x : max_x + 1]
            color_region[update] = colors[update]
            depth_region[update] = z[update]

    # Draw ground first, then spheres (z-buffer handles occlusion anyway).
    draw_mesh(plane_v, plane_t, False)
    draw_mesh(sphere_v, sphere_t, True)
    draw_mesh(sat_v, sat_t, True)

    image = Image.fromarray(np.clip(color_buf, 0, 255).astype(np.uint8), "RGB")
    return image


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    SINGLE.mkdir(parents=True, exist_ok=True)
    MULTI.mkdir(parents=True, exist_ok=True)

    single_path = SINGLE / "sphere_front.png"
    render_view(30.0, 18.0, size=512).save(single_path)

    multi_paths = []
    # Orbit with moderate overlap for SfM.
    for index, yaw in enumerate(np.linspace(0.0, 150.0, 10)):
        path = MULTI / f"sphere_view_{index:02d}.png"
        render_view(float(yaw), 14.0, size=512).save(path)
        multi_paths.append(path)

    manifest = {
        "origin": "synthetic-render generated by .validation/fixtures/generate_fixtures.py",
        "rights": "original work created for Mesh3D smoke tests; no third-party assets or claims",
        "purpose": "rights-cleared engine smoke-test inputs; textured sphere+plane for SfM",
        "generated_on": date.today().isoformat(),
        "single_image": [
            {"path": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size}
            for p in [single_path]
        ],
        "multi_view": [
            {"path": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size}
            for p in multi_paths
        ],
    }
    (ROOT / "PROVENANCE.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
