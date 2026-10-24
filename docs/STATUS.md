# V2 engineering status

## Implemented

- Session-scoped, range-aware Read deduplication with cross-platform state locking.
- Incremental SQLite transcript indexer using offsets and metadata only.
- Offline replacement compaction with immutable full-transcript archives.
- Rolling token/error/compaction metrics and a supervisor circuit breaker.
- `hache doctor --strict`, cross-platform packaging, RTK detection and hook wiring.
- Hook-enforced per-session subagent admission and release accounting.
- macOS/Linux/Windows CI with package, installer and regression coverage.

## Current limitations

- The proxy is a transport pass-through until provider-specific streaming usage
  accounting is enabled; OAuth/Subscription CLI enforcement remains hook/supervisor based.
- RTK is not copied into the repository. Its hook is wired when installed and
  the internal fallback remains the portable default.
- Live API token-savings and quality benchmarks require a controlled fixture or
  provider test account; CI never sends real prompts.

## Verification rule

Never call the product production-ready from unit tests alone. Every release must
run the platform matrix, installer lifecycle tests, fake-Claude supervisor tests,
state-concurrency tests, and the controlled benchmark suite.
