#!/usr/bin/env bash
set -euo pipefail

# BHUMISETU Antigravity CLI Adapter
# Reads task text from stdin and invokes the installed agy CLI non-interactively.

TASK="$(cat)"

if [[ -z "${TASK// }" ]]; then
  echo "Error: No task provided on stdin to Antigravity adapter." >&2
  exit 1
fi

AGY_BIN="${ANTIGRAVITY_COMMAND:-/Users/sakshantwaghmare/.local/bin/agy}"

if ! command -v "$AGY_BIN" >/dev/null 2>&1 && [[ ! -x "$AGY_BIN" ]]; then
  echo "Error: Antigravity CLI binary '$AGY_BIN' not found or not executable." >&2
  exit 78
fi

exec "$AGY_BIN" --dangerously-skip-permissions -p "$TASK"
