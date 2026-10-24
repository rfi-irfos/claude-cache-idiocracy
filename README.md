# claude-hache-idiocracy

Private RFI-IRFOS guard for Claude Code. It combines persistent read deduplication,
context budgets, retry circuit breaking, handovers, and bounded subagent fan-out.

The guard stores hashes and counters locally. It never stores raw prompts, file
contents, credentials, or complete transcripts.

## Defaults

- 10 concurrent tool calls
- 3 concurrent subagents
- no nested subagents
- 100M cache-read soft warning
- 250M cache-read hard breaker
- 20 API-error soft warning / 50 hard breaker in a 15-minute window

## Install

```sh
python3 -m hache_guard install --global
```

See `docs/upstream.md` for the open-source inspirations and attribution.
