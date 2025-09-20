#!/usr/bin/env bash
set -euo pipefail
FILE="backend/Dockerfile"
if grep -Fq '"--host", "*******"' "$FILE"; then
# Replace redacted placeholder with 0.0.0.0
  sed -i.bak 's/"--host", "\*\*\*\*\*\*\*"/"--host", "0.0.0.0"/' "$FILE"
  rm -f "$FILE.bak"
fi
grep -n "uvicorn" "$FILE" || true
