#!/usr/bin/env bash
# Example cURL commands for Prompt Console API (local dev)
# Base URL
API_BASE=${API_BASE:-http://127.0.0.1:7070}

set -euo pipefail

info() { printf "\n==> %s\n" "$*"; }

info "GET /recipes"
curl -sS "$API_BASE/recipes" | jq '.recipes | length as $n | {recipes:$n}'

info "POST /choose (assistant=chatgpt, category=coding)"
CHOOSE_PAYLOAD='{"assistant":"chatgpt","category":"coding","raw_input":"Say hi","options":{"enhance":false,"force_json":false},"context_features":{"input_tokens":2,"store_text":true,"language":"en"}}'
RESP=$(curl -sS -X POST "$API_BASE/choose" -H 'Content-Type: application/json' -d "$CHOOSE_PAYLOAD")
echo "$RESP" | jq '{decision_id, recipe_id, propensity, notes}'
DECID=$(echo "$RESP" | jq -r .decision_id)

info "POST /feedback (reward=1.0 for decision)"
FB_PAYLOAD=$(jq -n --arg d "$DECID" '{decision_id:$d, reward:1.0, reward_components:{user_like:1, copied:1, format_ok:1}, safety_flags:[]}')
curl -sS -X POST "$API_BASE/feedback" -H 'Content-Type: application/json' -d "$FB_PAYLOAD" | jq .

info "GET /history (latest 5, no text)"
curl -sS "$API_BASE/history?limit=5&with_text=false" | jq '{total, first: (.items[0] // null)}'

info "GET /stats"
curl -sS "$API_BASE/stats" | jq .

info "POST /stats (epsilon=0.2)"
curl -sS -X POST "$API_BASE/stats" -H 'Content-Type: application/json' -d '{"epsilon":0.2}' | jq .
