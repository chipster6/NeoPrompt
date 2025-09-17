#!/usr/bin/env bash
set -euo pipefail

# Force replace placeholder host with 0.0.0.0 in backend/Dockerfile if present
FILE="backend/Dockerfile"
if grep -q '"--host", "*******"' "$FILE"; then
  sed -i.bak 's/"--host", "\*\*\*\*\*\*\*"/"--host", "0.0.0.0"/' "$FILE" || true
  rm -f "$FILE.bak"
fi

grep -n "uvicorn" "$FILE" || true
