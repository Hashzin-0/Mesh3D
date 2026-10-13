# ADR 0002: Store artifacts separately from job metadata

- Status: Proposed
- Date: 2026-10-13
- Context: Inputs and outputs are large binary files; benchmark reproducibility requires provenance and integrity checks. No storage integration exists yet.
- Decision: Persist job state and metadata in a relational database; store originals, intermediates, and outputs in private object storage. Every artifact manifest records a server-generated storage key, media type, format, byte size, SHA-256, producing run, validation report, and retention state. Download access is authorized and uses short-lived signed URLs.
- Alternatives considered:
  - Store binary artifacts directly in relational rows: rejected as the default due to large-object lifecycle and delivery costs.
  - Public object URLs: rejected because uploads and outputs may contain private images or metadata.
  - Store only final GLB: rejected because retaining original inputs and native engine outputs supports debugging and reproducibility; retention must still be configurable.
- Consequences:
  - Storage provider, database provider, retention policy, and deletion semantics remain open decisions.
  - Hashes and existence checks must be performed on actual bytes, not inferred from file names.
  - Temporary artifacts require lifecycle cleanup; completed artifacts must not be deleted by another job's cleanup.
- Validation required: prove owner isolation, signed URL expiry, integrity/hash verification, deletion behavior, and recovery from partial upload/storage failure.
