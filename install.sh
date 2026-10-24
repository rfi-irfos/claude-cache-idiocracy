#!/usr/bin/env sh
set -eu
if [ "${1:-}" = "--all" ]; then shift; fi
trap 'python3 -m hache_guard rollback >/dev/null 2>&1 || true' ERR
repo="${HACHE_REPO:-https://github.com/rfi-irfos/claude-cache-idiocracy.git}"
dir="${HACHE_DIR:-$HOME/.claude/claude-cache-idiocracy}"
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  if [ -d "$dir/.git" ]; then git -C "$dir" pull --ff-only; else gh repo clone rfi-irfos/claude-cache-idiocracy "$dir"; fi
elif command -v git >/dev/null 2>&1; then
  if [ -d "$dir/.git" ]; then git -C "$dir" pull --ff-only; else git clone "$repo" "$dir"; fi
else
  echo "claude-cache-idiocracy: git is required" >&2
  exit 1
fi
python3 -m pip install --user --upgrade "$dir"
python3 -m hache_guard install
python3 -m hache_guard doctor --strict
echo "claude-cache-idiocracy installed; restart Claude Code."
