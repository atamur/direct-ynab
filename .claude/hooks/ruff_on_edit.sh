#!/usr/bin/env bash
set -euo pipefail

# Read the hook's JSON input from stdin
TMP="$(mktemp)"
cat > "$TMP"

# Always run from project root so Ruff finds pyproject.toml
cd "$CLAUDE_PROJECT_DIR"

# Collect edited file paths from different tool shapes
paths=$(
  {
    jq -r '.tool_input.file_path // empty' "$TMP"
    jq -r '.tool_input.edits[]?.file_path // empty' "$TMP"
  } | grep -E '\.py$' | sort -u
)

# Nothing to do?
[ -z "$paths" ] && exit 0

# Format, then lint+fix, respecting your pyproject.toml
# (use config discovery; add flags if you want)
ruff format -s $paths
ruff check --fix -q --output-format=concise $paths
