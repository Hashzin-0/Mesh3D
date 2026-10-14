# Phase 0 — baseline and reproducibility status

Updated: 2026-10-13

## Repository evidence

- The repository initially contained planning documents only; no application source, manifest, CI, migrations, runtime, or tests were found.
- The canonical Hashzin-0/Rules/Rules.md was retrieved and reviewed before these changes.
- No local AGENTS.md, CLAUDE.md, GEMINI.md, Rules.md, package manifest, or Python project manifest existed on the base branch.
- The Rules Governance skill was applied as the workflow, but a separately installable/connected “Rules Governance” plugin was not found by plugin discovery. This is not a blocker for following the published Rules document and skill instructions.

## Added in this phase

- [Rules.md](../Rules.md): project-specific rules and evidence-based category classification.
- [Threat model](THREAT_MODEL.md): assets, trust boundaries, threats, required controls, and open risks.
- [ADR 0001](adr/0001-async-worker-boundary.md): asynchronous isolated worker boundary.
- [ADR 0002](adr/0002-artifact-storage-and-provenance.md): private binary artifact storage and provenance.
- [Engine provenance register](ENGINE_PROVENANCE.md): candidate-specific activation gates and evidence status.
- [Dataset protocol](DATASET_PROTOCOL.md): real fixture provenance and reproducible benchmark protocol.

## Exit gate status

| Requirement | Status | Evidence / blocker |
|---|---|---|
| Project rules and threat model | Drafted | Version-controlled documents in this branch; controls not implemented |
| Queue/storage/worker ADRs | Drafted | Two proposed ADRs; provider choice remains open |
| Candidate upstream and license register | Done for shipped engines | Register updated with exact commits, checkpoint hashes, licenses, and validation reports for the three shipped engines; failed candidates recorded with attempt evidence and removed from the registry (`ENGINE_PROVENANCE.md`) |
| Rights-cleared real test sets | Done | Self-generated synthetic fixtures with provenance: `.validation/fixtures/PROVENANCE.json`, input SHA-256 digests recorded in `ENGINE_TEST_REPORT.md` |
| Hardware profiles and measured baseline | Done | CPU-only host profiled during real runs (AMD EPYC 7763, 2 cores, 7.76 GB RAM, no GPU); no GPU baseline exists on this host |
| Real engine smoke tests | Partial | 3 of 7 candidates passed real-run validation (TripoSR, Meshroom, COLMAP+OpenMVS; reports in `.validation/reports/`); 4 failed and were removed from the registry (attempt records kept). GPU inference untested — no accelerator on this host |

## Next gate

Phase 0 is **not complete** because GPU inference, full-pipeline (CUDA depth) runs, and quality comparisons remain untested on this CPU-only host. The next meaningful implementation gate is to run at least one engine on GPU-equipped hardware, measure a baseline against the documented protocol, and only then consider re-adding candidates that failed solely for hardware reasons (Hunyuan3D, VGGT) — each with a fresh real-run attempt and report. Do not build a benchmark dashboard that implies results exist beyond the three documented runs.
