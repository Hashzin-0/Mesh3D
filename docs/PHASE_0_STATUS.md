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
| Candidate upstream and license register | Partial | Candidate sources and known gates recorded; exact revisions, hashes, full dependency audits, and deployment reviews remain pending |
| Rights-cleared real test sets | Blocked | No fixture added; source/permission must be documented before use |
| Hardware profiles and measured baseline | Blocked | No execution environment or engine runtime available through the repository editing connector |
| Real engine smoke tests | Not started | Requires a provisioned CPU/GPU runtime and actual model downloads |

## Next gate

Phase 0 is **not complete**. The next meaningful implementation gate is to provision/identify an execution environment, select and document a rights-cleared real fixture for each mode, pin immutable engine revisions and checkpoints, and run the first real smoke tests. Do not build a benchmark dashboard that implies results exist before those runs.
