# Claude Cache Idiocracy

[![test](https://github.com/rfi-irfos/claude-cache-idiocracy/actions/workflows/test.yml/badge.svg)](https://github.com/rfi-irfos/claude-cache-idiocracy/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![Platforms](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-555)](.github/workflows/test.yml)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-hooks-D97757?logo=anthropic&logoColor=white)](https://docs.anthropic.com/en/docs/claude-code/hooks)

Open-source RFI-IRFOS enforcement layer for Claude Code. It combines persistent,
session-scoped read deduplication, incremental transcript indexing, offline
compaction, retry/cost circuit breaking, RTK integration and bounded subagent fan-out.

The guard stores hashes and counters locally. It never stores credentials or
complete transcripts. Offline compaction deliberately retains only bounded,
local summary excerpts so a replaced session can resume with context.

## Defaults

- 10 concurrent tool calls
- 3 concurrent subagents
- no nested subagents
- hook-enforced per-session agent admission limit
- 1-hour prompt-cache TTL for main and subagent conversations (supported Claude Code versions)
- 100M cache-read soft warning
- 250M cache-read hard breaker
- 20 API-error soft warning / 50 hard breaker in a 15-minute window

## Install

Requires `git` and Python 3.9+.

The installer is the only setup step: it updates the checkout, installs the
package, migrates settings, wires hooks, detects RTK, runs the strict doctor,
and fails if any required check is unsuccessful.

```sh
H="$HOME/.claude/claude-cache-idiocracy"; if [ -d "$H/.git" ]; then git -C "$H" pull --ff-only; else git clone https://github.com/rfi-irfos/claude-cache-idiocracy.git "$H"; fi && sh "$H/install.sh" --all
```

Windows PowerShell:

```powershell
if (!(Test-Path "$HOME/.claude/claude-cache-idiocracy/.git")) { git clone https://github.com/rfi-irfos/claude-cache-idiocracy.git "$HOME/.claude/claude-cache-idiocracy" } else { git -C "$HOME/.claude/claude-cache-idiocracy" pull --ff-only }; powershell -ExecutionPolicy Bypass -File "$HOME/.claude/claude-cache-idiocracy/install.ps1" -All
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
See `docs/STATUS.md` for verified capabilities and explicit limitations.

To remove only Hache-managed settings and hooks while preserving all other
Claude configuration, run `hache-guard uninstall`.

Local operational metrics are available without exposing prompt bodies:
`hache-stats` or `python3 -m hache_guard stats`.

## License

MIT, see [LICENSE](LICENSE). Built by Laura Serna Gaviria at RFI-IRFOS.
