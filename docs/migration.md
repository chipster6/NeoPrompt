# Migration Guide

This document helps migrate recipes to the enhanced loader.

## Key changes
- Introduced `_fragments/` for reusable blocks. Move reusable keys there.
- `operators+` supports appending with order preservation.
- ENV substitution supports `${ENV:VAR:-default}` with allow/deny policies.
- Hot-reload via events first with polling fallback.

## Steps
1. Ensure IDs follow `<assistant>.<category>.<name>` where possible.
2. Move common blocks to `_fragments/` and include them.
3. Verify `guards.max_temperature` aligns with category caps.
4. Run the validator:
   ```bash
   PYTHONPATH=. .venv/bin/python -m backend.cli.recipes_validate --format text --reload
   ```
5. Enable strict mode in CI to block semantic-invalid in critical categories:
   ```bash
   VALIDATION_STRICT=1 VALIDATION_STRICT_SCOPE=critical PYTHONPATH=. .venv/bin/python -m backend.cli.recipes_validate --format text --reload --fail-on error
   ```