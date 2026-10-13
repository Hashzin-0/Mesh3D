# Mesh3D UI/UX specification

## 1. Product experience

Mesh3D should feel like a professional 3D evaluation workstation, not a generic upload form. The main task is to create a reconstruction job and compare genuine outputs from different engines with minimal navigation.

**Information architecture**
- **Studio:** create a reconstruction, select mode, add images, configure engines, launch work.
- **Jobs:** active and past jobs with status, stages, logs, warnings, and artifacts.
- **Compare:** side-by-side model review for runs from the same input set and task class.
- **Benchmarks:** reproducible test sets, run history, raw metrics, and human ratings.
- **Settings:** resource limits, artifact retention, user preferences, and engine availability (admin/operator).

The MVP can expose Studio, Jobs, and Compare first; Benchmarking and operational settings can follow the engine proof-of-capability phase.

## 2. Core screen: Studio

### Desktop layout
- Top bar: Mesh3D mark, current project/input set, job queue indicator, user menu.
- Left workflow rail: **1. Input → 2. Engines → 3. Settings → 4. Run** with clear completed/current/error states.
- Main panel: image drop zone, thumbnails, image count, reorder/delete actions, image validation, and capture guidance.
- Right configuration panel: mode-aware engine list with capability badges, license status, hardware requirements, settings, and estimated resource category (not invented time estimates).
- Sticky footer: selected image count, selected engines, validation summary, and primary “Run reconstruction” action.

### Mode selection

Use two explicit options with explanations:
- **Single image:** one photograph; AI estimates unseen geometry. Best for a quick visual asset, not dimensional measurement.
- **Multiple images:** overlapping photographs of the same object; camera registration and surface reconstruction. Best for recovering observed geometry and texture.

Changing mode must preserve compatible inputs but must not silently keep incompatible engines selected. Explain why a selected engine becomes unavailable.

### Upload interaction
- Support drag-and-drop and file picker.
- Display thumbnails, filenames, dimensions, file size, and upload state.
- Multi-view mode allows reordering and removal and displays a capture checklist (coverage, focus, overlap, lighting).
- Detect likely duplicates, unsupported/corrupt images, too-small images, extreme dimensions, and mismatched image sets.
- Client checks are for UX only; the server validates actual file content and limits.
- Never imply that an image has been reconstructed before a real worker result exists.

## 3. Engine selection

Each engine card should show:
- Engine name and version/checkpoint when known.
- Supported mode(s) and input count limits.
- Output capabilities: mesh, UVs, textures, export formats, and any limitations.
- License badge: **Permissive**, **Review required**, or **Disabled**; link to the exact upstream license/weight terms.
- Hardware requirements and whether the engine is available on the current deployment.
- A short explanation of what the engine optimizes (speed, generative plausibility, observed-surface fidelity, or texture pipeline).

Do not show fake star ratings, fake benchmark scores, or default “recommended” rankings without measured data. A “Recommended” marker can only appear after an explicit policy is documented and backed by real benchmark evidence.

## 4. Job monitor

Show a real event timeline, not a generic spinner:
- Queued
- Input validation
- Preprocessing / camera registration
- Reconstruction
- Meshing
- Texturing
- Export
- Output validation
- Completed / Failed / Cancelled

Only show stages applicable to the engine; mark inapplicable stages as skipped. Percent progress is displayed only when the engine reports a meaningful counter or when clearly labeled as a stage-based estimate. Otherwise show the current stage and elapsed time.

Actions:
- Cancel a running job, with confirmation for jobs that have started consuming GPU.
- Retry only when the error is classified as retryable.
- Open logs in a sanitized diagnostic panel.
- Download successful artifacts.
- Compare completed runs from the same input set.

Failure screens must identify the actionable cause (e.g. camera registration failed because too few images aligned) and recommend concrete next steps without exposing secrets or raw stack traces by default.

## 5. Compare workspace

Desktop comparison is the key differentiator:
- Two or more viewer panels with independent labels and engine metadata.
- Synchronized orbit, pan, and zoom by default; a toggle permits independent cameras.
- View modes: textured, solid, wireframe, and geometry/texture diagnostics where supported.
- Shared controls: reset camera, fit model, toggle grid/axes, background selection, and screenshot capture for review.
- Per-model metadata drawer: input set, engine/checkpoint, run time, mesh counts, texture dimensions, validation warnings, and file size.
- Artifact actions: download GLB, OBJ package, PLY, or STL only when that format exists and has been validated.
- A “differences” panel reports measured metrics with their method and reference source. Missing or inapplicable metrics show “Not available”, never zero or a fabricated score.

Compare only like-for-like modes by default. A deliberate cross-mode view can be offered with a warning that generated single-image geometry and reconstructed multi-view geometry have different evidence and objectives.

## 6. Visual direction

- Dark, neutral workspace optimized for 3D viewport contrast; light theme may be added later.
- Use one restrained accent color for primary actions and state indicators.
- High information density in the desktop comparison area, with typography and spacing that preserve hierarchy.
- Avoid decorative 3D animations that compete with the model. Motion should explain transitions, loading, and camera interactions.
- Keep image thumbnails and result metadata readable without forcing horizontal scrolling.
- Use clear labels instead of internal engine slugs or unexplained acronyms; expose technical details in expandable diagnostics.

## 7. Responsive behavior

### Desktop (>= 1200px)
- Three-zone Studio: workflow/input area, main content, engine settings panel.
- Compare uses side-by-side viewports and synchronized camera controls.
- Logs and metadata open in drawers or resizable panels.

### Tablet (768–1199px)
- Input and configuration panels become collapsible.
- Compare uses two viewports when practical, with compact metadata tabs.
- Keep primary job actions visible without covering the viewer.

### Mobile (< 768px)
- Single-column wizard; do not place input selection, viewport, and settings on top of one another.
- Use a full-width upload area and horizontally scrollable thumbnails.
- Engine selection is a separate step or bottom sheet; do not squeeze a desktop sidebar into the same page.
- Job details show a vertical timeline.
- Compare shows one model at a time with a clear next/previous switcher; optional swipe comparison must not hide essential controls.
- Use touch-sized controls, safe-area padding, keyboard-safe dialogs, and avoid hover-only interactions.

## 8. Design system and accessibility

Use semantic design tokens for color, typography, spacing, radius, elevation, and state colors. Suggested implementation primitives:
- Radix UI for accessible dialogs, tabs, popovers, menus, and tooltips.
- Tailwind CSS for token-backed layout and responsive styling.
- Lucide icons for consistent UI icons.
- Three.js for the model viewer; do not use a video/GIF as a substitute for interactive geometry.

Accessibility requirements:
- WCAG AA contrast for text and controls.
- Visible keyboard focus, correct heading order, labels, and keyboard-operable menus/dialogs.
- Progress updates announced politely without announcing every rapid event.
- Errors associated with the relevant input/control and described in text, not color alone.
- Respect prefers-reduced-motion.
- Viewer controls have accessible labels and an alternative textual metadata view.

## 9. Empty, loading, error, and success states

- **Empty Studio:** explains both modes and provides a real upload action; no fake recent jobs.
- **Uploading:** per-file state and retry; preserve successfully uploaded files if another fails.
- **Validating:** show checks that are actually running.
- **Queued/running:** real queue position only if available, actual stage events, elapsed time, and cancellation.
- **Failed:** stage, concise cause, diagnostic reference, and recovery guidance.
- **Completed:** real model preview, verified formats, validation warnings, and download.
- **No benchmark data:** explain that a benchmark must be run before metrics appear.
- **Engine unavailable:** clear reason (not installed, hardware unavailable, or license review pending).

## 10. Figma / design handoff status

A new Figma file was created for **Mesh3D — Image to 3D Studio**:
https://www.figma.com/design/3Z13oCTbuj4WYeQB7AFVg8

The connected Figma MCP reached its Starter-plan call limit during design-system discovery, before any UI layers were written. Therefore, this document is the current UX specification; it must not be represented as a completed Figma mockup. When Figma tool access is available again, create editable layers for:
1. Studio desktop (single-image mode).
2. Studio desktop (multi-view mode with capture guidance).
3. Job monitor with real stage states.
4. Compare workspace with synchronized viewports.
5. Mobile upload wizard and mobile job details.

The new Figma file is currently blank. Do not treat it as implementation or visual validation evidence.
