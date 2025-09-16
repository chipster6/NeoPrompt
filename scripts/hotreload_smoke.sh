#!/usr/bin/env bash
set -euo pipefail
API=${API:-http://127.0.0.1:7070}
RECIPES_DIR=${RECIPES_DIR:-"prompt-templates"}

info() { printf "\033[1;34m==> %s\033[0m\n" "$*"; }

info "Listing recipes before change"
curl -s "$API/recipes" | jq '.recipes | length'

TMP_FILE="$RECIPES_DIR/chatgpt.coding.smoke.yaml"

cleanup() {
  rm -f "$TMP_FILE" || true
}
trap cleanup EXIT

info "Creating a temporary recipe"
cat > "$TMP_FILE" <<'YAML'
id: chatgpt.coding.smoke
assistant: chatgpt
category: coding
operators: [role_hdr, io_format]
hparams: { temperature: 0.2 }
YAML

sleep 1
info "Verifying recipe is picked up"
curl -s "$API/recipes" | jq '.recipes | map(.id) | contains(["chatgpt.coding.smoke"])'

info "Introducing a YAML error"
echo 'bad: [unclosed' >> "$TMP_FILE"

sleep 1
info "Verifying diagnostics report the error"
curl -s "$API/recipes" | jq '.errors | length'

info "Fixing the YAML"
sed -i.bak '$ d' "$TMP_FILE" && rm -f "$TMP_FILE.bak"

sleep 1
info "Verifying error clears"
curl -s "$API/recipes" | jq '.errors | length'