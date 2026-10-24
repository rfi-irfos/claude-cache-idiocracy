# claude-cache-idiocracy

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

Requires an authenticated `gh` CLI because the repository is private.

```sh
curl -fsSL https://raw.githubusercontent.com/rfi-irfos/claude-cache-idiocracy/main/install.sh | sh
```

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/rfi-irfos/claude-cache-idiocracy/main/install.ps1 | iex
```

For a local checkout: `python3 -m pip install --user . && python3 -m hache_guard install`.

For full retry/compaction supervision, launch Claude through:

```sh
hache-claude -- claude
```

The supervisor is local-only. It watches the Claude transcript, emits one soft
warning, then writes a handover and terminates the process at the hard threshold.

To compact a large existing transcript without sending it back to the API:

```sh
hache-compact compact ~/.claude/projects/<project>/<session>.jsonl
```

This writes a deterministic local handover and leaves the original transcript untouched.

See `docs/upstream.md` for the open-source inspirations and attribution.
