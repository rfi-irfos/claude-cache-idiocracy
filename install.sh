#!/usr/bin/env sh
set -eu
repo="${HACHE_REPO:-https://github.com/rfi-irfos/claude-hache-idiocracy.git}"
dir="${HACHE_DIR:-$HOME/.claude/claude-hache-idiocracy}"
if command -v gh >/dev/null 2>&1; then
  if [ -d "$dir/.git" ]; then git -C "$dir" pull --ff-only; else gh repo clone rfi-irfos/claude-hache-idiocracy "$dir"; fi
elif command -v git >/dev/null 2>&1; then
  if [ -d "$dir/.git" ]; then git -C "$dir" pull --ff-only; else git clone "$repo" "$dir"; fi
else
  echo "claude-hache-idiocracy: git is required" >&2
  exit 1
fi
python3 -m pip install --user --upgrade "$dir"
python3 -m hache_guard install
echo "claude-hache-idiocracy installed; restart Claude Code."
