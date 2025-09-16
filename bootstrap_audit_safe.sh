#!/usr/bin/env bash
# NeoPrompt SAFE audit helper — no installs, no git changes, no profile edits
# Usage: chmod +x bootstrap_audit_safe.sh && ./bootstrap_audit_safe.sh

set -euo pipefail

export LANG=C
: "${REPO_DIR:=${PWD}}"
OUT="bootstrap-audit.md"

cd "$REPO_DIR"

# Ensure output file exists and is empty
: > "$OUT"

{
  echo "# NeoPrompt Bootstrap Safe Audit — $(date)"
  echo "- REPO_DIR: $REPO_DIR"
  echo "- macOS: $(sw_vers -productVersion 2>/dev/null || echo n/a)"
  echo "- Shell: ${SHELL:-n/a}"
  echo
  echo "## Tool detection"
  for cmd in rg fd jq gsed sed tree find grep node pnpm npm python3 uvicorn git; do
    if command -v "$cmd" >/dev/null 2>&1; then
      ver=$({ "$cmd" --version 2>/dev/null | head -n1 || "$cmd" -v 2>/dev/null | head -n1 || "$cmd" -V 2>/dev/null | head -n1 || true; })
      echo "- $cmd: ${ver:-present}"
    else
      echo "- $cmd: not found"
    fi
  done
  echo
} >> "$OUT"

{
  echo "## Template and schema presence"
  test -d recipes && echo "- recipes/ present"
  test -d prompt_templates && echo "- prompt_templates/ present"
  test -f docs/recipe.schema.json && echo "- docs/recipe.schema.json present"
  test -f docs/prompt_template.schema.json && echo "- docs/prompt_template.schema.json present"
  echo
} >> "$OUT"

{
  echo "## Candidate bootstrap/setup scripts"
  if command -v fd >/dev/null 2>&1; then
    fd -t f -HI -g 'bootstrap*.sh' -g 'setup*.sh' -g '*neoprompt*bootstrap*.sh' . 2>/dev/null || true
  else
    find . -type f \( -iname 'bootstrap*.sh' -o -iname 'setup*.sh' -o -iname '*neoprompt*bootstrap*.sh' \) -print 2>/dev/null || true
  fi
  echo
} >> "$OUT"

{
  echo "## Marker search (DO_RENAME | REPO_DIR | brew install | rename)"
  if command -v rg >/dev/null 2>&1; then
    rg -n --hidden -g '!node_modules' -e 'DO_RENAME|REPO_DIR|brew install|rename' . || true
  else
    grep -RInE 'DO_RENAME|REPO_DIR|brew install|rename' --exclude-dir=node_modules . || true
  fi
  echo
} >> "$OUT"

{
  echo "## Functions found in scripts/"
  if [ -d scripts ]; then
    if command -v rg >/dev/null 2>&1; then
      rg -n -g 'scripts/**/*.sh' '^(function[[:space:]]+[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*[[:space:]]*\(\)[[:space:]]*\{)' || true
    else
      grep -RInE '^(function[[:space:]]+[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*[[:space:]]*\(\)[[:space:]]*\{)' scripts --include='*.sh' || true
    fi
  else
    echo "(no scripts/ directory)"
  fi
  echo
} >> "$OUT"

{
  echo "## Phases (heuristic)"
  if [ -d scripts ]; then
    if command -v rg >/dev/null 2>&1; then
      rg -n -g 'scripts/**/*.sh' -e 'preflight|env|dependency|audit|rename|start|stop|cleanup|doctor|install|run' || true
    else
      grep -RInE 'preflight|env|dependency|audit|rename|start|stop|cleanup|doctor|install|run' scripts --include='*.sh' || true
    fi
  fi
  echo
} >> "$OUT"

{
  echo "## Script env assignments"
  if [ -d scripts ]; then
    if command -v rg >/dev/null 2>&1; then
      rg -n -g 'scripts/**/*.sh' '^[A-Z0-9_]+[[:space:]]*=' | sed 's/:.*/:/' || true
    else
      grep -RInE '^[A-Z0-9_]+[[:space:]]*=' scripts --include='*.sh' | sed 's/:.*/:/' || true
    fi
  fi
  echo
} >> "$OUT"

{
  echo "## Code references to recipe paths"
  if command -v rg >/dev/null 2>&1; then
    rg -n --hidden -g '!node_modules' -S -e '\\brecipes?/' . || true
  else
    grep -RInE '\\brecipes?/' --exclude-dir=node_modules . || true
  fi
  echo
} >> "$OUT"

{
  echo "## Backend endpoints/URLs/ports"
  if [ -d backend ]; then
    if command -v rg >/dev/null 2>&1; then
      rg -n --hidden -g '!node_modules' -e '/(choose|feedback|history|recipes)\\b' backend || true
    else
      grep -RInE '/(choose|feedback|history|recipes)\\b' backend || true
    fi
  fi
  if command -v rg >/dev/null 2>&1; then
    rg -n --hidden -g '!node_modules' -e 'http://localhost:[0-9]+' -e 'https?://[^" )]+' . || true
    rg -n --hidden -g '!node_modules' -e '\\bPORT\\b|--port|-p[[:space:]]*[0-9]{2,5}' . || true
  else
    grep -RInE 'http://localhost:[0-9]+' --exclude-dir=node_modules . || true
    grep -RInE 'https?://[^" )]+' --exclude-dir=node_modules . || true
    grep -RInE '\\bPORT\\b|--port|-p[[:space:]]*[0-9]{2,5}' --exclude-dir=node_modules . || true
  fi
  echo
} >> "$OUT"

{
  echo "## Environment variables (frontend/backend)"
  if [ -d frontend ]; then
    if command -v rg >/dev/null 2>&1; then
      rg -n --hidden -g '!node_modules' -e 'process\\.env\\.[A-Z0-9_]+' -e 'NEXT_PUBLIC_[A-Z0-9_]+' -e 'VITE_[A-Z0-9_]+' frontend || true
    else
      grep -RInE 'process\\.env\\.[A-Z0-9_]+|NEXT_PUBLIC_[A-Z0-9_]+|VITE_[A-Z0-9_]+' --exclude-dir=node_modules frontend || true
    fi
  fi
  if [ -d backend ]; then
    if command -v rg >/dev/null 2>&1; then
      rg -n --hidden -g '!node_modules' -e 'os\\.environ\\[' -e 'os\\.getenv\\(' backend || true
    else
      grep -RInE 'os\\.environ\\[|os\\.getenv\\(' backend || true
    fi
  fi
  echo
} >> "$OUT"

if [ -f frontend/package.json ]; then
  {
    echo "## frontend/package.json (first 200 lines)"
    sed -n '1,200p' frontend/package.json
    echo
  } >> "$OUT"
fi

{
  echo "## Side-effects (static grep)"
  echo "### Filesystem ops"
  if [ -d scripts ]; then
    if command -v rg >/dev/null 2>&1; then
      rg -n --hidden -g '!node_modules' -e '\\bgit mv\\b|\\bmv\\b|\\bcp\\b|\\brm\\b|\\bmkdir -p\\b|\\btouch\\b|\\bchmod\\b' scripts || true
    else
      grep -RInE '\\bgit mv\\b|\\bmv\\b|\\bcp\\b|\\brm\\b|\\bmkdir -p\\b|\\btouch\\b|\\bchmod\\b' scripts || true
    fi
    echo "### Git ops"
    if command -v rg >/dev/null 2>&1; then
      rg -n --hidden -g '!node_modules' -e '\\bgit (checkout|switch|branch|commit|tag|push|pull|stash|rebase|reset)\\b' scripts || true
    else
      grep -RInE '\\bgit (checkout|switch|branch|commit|tag|push|pull|stash|rebase|reset)\\b' scripts || true
    fi
    echo "### Processes"
    if command -v rg >/dev/null 2>&1; then
      rg -n --hidden -g '!node_modules' -e '\\buvicorn\\b|\\bnpm run dev\\b|\\bpnpm dev\\b|\\bdocker compose\\b' scripts || true
    else
      grep -RInE '\\buvicorn\\b|\\bnpm run dev\\b|\\bpnpm dev\\b|\\bdocker compose\\b' scripts || true
    fi
    echo "### Ports"
    if command -v rg >/dev/null 2>&1; then
      rg -n --hidden -g '!node_modules' -e '\\b(3000|5173|7070|8000)\\b' scripts || true
    else
      grep -RInE '\\b(3000|5173|7070|8000)\\b' scripts || true
    fi
  else
    echo "(no scripts/ directory)"
  fi
  echo
} >> "$OUT"

cat > NEXT_STEPS_SAFE.md <<'MD'
# Next Steps (SAFE audit — no installs, no git changes)
1) Review bootstrap-audit.md for:
   - functions, phases, env vars in scripts/
   - endpoints, URLs, and ports
   - env var usage in frontend/backend
   - presence of recipes/ and/or prompt_templates/
2) If everything looks good and you want to spin up dev (still no rename yet):
   export REPO_DIR="/Users/cody/NeoPrompt"
   DO_RENAME=0 ./run_neoprompt.sh
3) If you later want to attempt a rename:
   - create a branch first
   - dry-run your rename script if available
MD

echo "SAFE audit complete. See bootstrap-audit.md and NEXT_STEPS_SAFE.md"
