# claude-cache-idiocracy

Private RFI-IRFOS guard for Claude Code. It combines persistent read deduplication,
context budgets, retry circuit breaking, handovers, and bounded subagent fan-out.

The guard stores hashes and counters locally. It never stores credentials or
complete transcripts. Offline compaction deliberately retains only bounded,
local summary excerpts so a replaced session can resume with context.

## Defaults

- 10 concurrent tool calls
- 3 concurrent subagents
- no nested subagents
- 1-hour prompt-cache TTL for main and subagent conversations (supported Claude Code versions)
- 100M cache-read soft warning
- 250M cache-read hard breaker
- 20 API-error soft warning / 50 hard breaker in a 15-minute window

## Install

Requires an authenticated `gh` CLI because the repository is private.

```sh
gh repo clone rfi-irfos/claude-cache-idiocracy "$HOME/.claude/claude-cache-idiocracy" && sh "$HOME/.claude/claude-cache-idiocracy/install.sh"
```

Windows PowerShell:

```powershell
gh repo clone rfi-irfos/claude-cache-idiocracy "$HOME/.claude/claude-cache-idiocracy"; powershell -ExecutionPolicy Bypass -File "$HOME/.claude/claude-cache-idiocracy/install.ps1"
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

This writes a deterministic local handover without sending transcript data to an API.
Add `--replace` to archive the original as `.full-<timestamp>.jsonl` and leave a
single synthetic compact-summary entry at the original session path for `--resume`.
The archive is never deleted; only the resume-visible path is replaced.

See `docs/upstream.md` for the open-source inspirations and attribution.
