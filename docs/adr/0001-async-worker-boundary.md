# ADR 0001: Isolate reconstruction engines in asynchronous workers

- Status: Proposed
- Date: 2026-10-13
- Context: Image-to-3D engines and photogrammetry pipelines can consume substantial GPU/CPU, memory, disk, and wall-clock time. The repository currently contains planning documents only.
- Decision: The API will validate and enqueue work, then return a durable job identifier. Reconstruction runs in separately deployable, versioned worker containers. A normalized adapter interface isolates engine-specific commands and outputs.
- Alternatives considered:
  - Run reconstruction inside the web request: rejected because request timeouts, serverless limits, resource contention, and cancellation semantics are unsuitable for heavy jobs.
  - One shared environment for every engine: rejected as the default because native dependencies, CUDA versions, licenses, and resource requirements can conflict.
  - Separate service per engine from day one: deferred; start with isolated per-engine container images and a common orchestration contract, then split operationally where justified.
- Consequences:
  - Requires queue, worker health/heartbeat, timeouts, cancellation, bounded retries, idempotency, and job-stage persistence.
  - Each engine must declare capabilities and resource requirements.
  - No progress percentage may be fabricated; progress comes from real stage events/counters or a clearly identified stage-based estimate.
- Validation required: demonstrate queue recovery, worker crash/timeout behavior, cancellation, bounded concurrency, and one real reconstruction run for each supported input mode before declaring the architecture operational.
