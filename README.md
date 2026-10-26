# Claude Cache Idiocracy

[![test](https://github.com/rfi-irfos/claude-cache-idiocracy/actions/workflows/test.yml/badge.svg)](https://github.com/rfi-irfos/claude-cache-idiocracy/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![Platforms](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-555)](.github/workflows/test.yml)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-hooks-D97757?logo=anthropic&logoColor=white)](https://docs.anthropic.com/en/docs/claude-code/hooks)

**Keeps Claude Code from burning tokens on things it already did.** 🧠💸

Long Claude Code sessions get expensive in silly ways: the same file gets read
again and again, a retry loop keeps hammering a failing API, subagents spawn
subagents, and a giant transcript has to be sent back just to compact it.
Claude Cache Idiocracy is a small local guard that says "nope" to all of that.

## What it does

- 📖 **Reads each file once.** If a file is unchanged and that part was already
  read in this session, the repeat read is skipped. Edit the file and it reads again.
- 🔌 **Stops runaway sessions.** Too many API errors or a huge cache-read bill?
  You get one soft warning, then a clean stop with a handover note.
- 🤖 **Keeps subagents in check.** At most 3 at a time, and no subagents inside subagents.
- 🗜️ **Compacts offline.** Big transcripts are summarised locally, nothing goes
  back to the API. The full original is archived, never deleted.
- 📊 **Shows you the numbers.** `hache-stats` prints reads, agents and usage, without prompt text.

Everything runs on your machine. The guard stores hashes and counters only,
never credentials and never full transcripts.

## Quick start

You need `git` and Python 3.9+. One line installs everything, wires the hooks
and runs a self-check:

```sh
H="$HOME/.claude/claude-cache-idiocracy"; if [ -d "$H/.git" ]; then git -C "$H" pull --ff-only; else git clone https://github.com/rfi-irfos/claude-cache-idiocracy.git "$H"; fi && sh "$H/install.sh" --all
```

<details>
<summary>Windows (PowerShell)</summary>

```powershell
if (!(Test-Path "$HOME/.claude/claude-cache-idiocracy/.git")) { git clone https://github.com/rfi-irfos/claude-cache-idiocracy.git "$HOME/.claude/claude-cache-idiocracy" } else { git -C "$HOME/.claude/claude-cache-idiocracy" pull --ff-only }; powershell -ExecutionPolicy Bypass -File "$HOME/.claude/claude-cache-idiocracy/install.ps1" -All
```

</details>

Already have a checkout? `python3 -m pip install --user . && python3 -m hache_guard install`

Then restart Claude Code. That's it. 🎉

## Using it

**Run Claude with the full safety net** (soft warning, then a clean stop with a handover):

```sh
hache-claude -- claude
```

**Shrink a huge transcript locally** so you can keep going with `--resume`:

```sh
hache-compact compact ~/.claude/projects/<project>/<session>.jsonl
```

Add `--replace` to swap in the compact version. The full original stays next to
it as `.full-<timestamp>.jsonl`.

**See what it saved you:** `hache-stats`

**Check the setup:** `hache-doctor`

**Remove it again:** `hache-guard uninstall` removes only its own settings and
hooks and leaves the rest of your Claude config alone.

## Default limits

| Guard | Default |
|---|---|
| Parallel tool calls | 10 |
| Parallel subagents | 3, none nested |
| Prompt-cache TTL | 1 hour, main and subagents (on Claude Code versions that support it) |
| Cache reads | warning at 100M, stop at 250M |
| API errors (15 min window) | warning at 20, stop at 50 |

## Good to know

- [`docs/STATUS.md`](docs/STATUS.md) lists what is verified and the current limits.
- [`docs/upstream.md`](docs/upstream.md) credits the open-source projects that inspired it,
  including [RTK](https://github.com/rtk-ai/rtk), which is used when you have it installed.
- Tests run on Linux, macOS and Windows on every push.

Issues and pull requests are welcome! 💛

## License

MIT, see [LICENSE](LICENSE). Built with care by Laura Serna Gaviria at RFI-IRFOS.
