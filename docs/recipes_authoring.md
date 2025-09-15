# Authoring NeoPrompt Recipes

This guide shows how to create and maintain recipes.

## File layout
- Main recipes live under `recipes/`.
- Reusable fragments live under `recipes/_fragments/`.

## Minimal recipe
```yaml
id: chatgpt.coding.baseline
assistant: chatgpt
category: coding
operators: [role_hdr, constraints, io_format, quality_bar]
hparams: { temperature: 0.2, top_p: 0.9, max_tokens: 1200 }
guards: { max_temperature: 0.4 }
examples: []
```

## Includes (fragments)
- Use `include: ["_fragments/foo.yaml", "_fragments/bar.yaml"]` to merge fragments.
- Fragment keys allowed: `operators`, `hparams`, `guards`, `examples`.
- Includes are restricted to `_fragments/` for safety.
- Use `operators+` to append operators and preserve order (deduplicated).

## Extends
- A recipe can extend a parent id with `extends: parent.id`.
- Assistant and category must match between child and parent.

## ENV substitution
- Pattern: `${ENV:VAR:-default}`.
- Policy is controlled via `RECIPES_ENV_ALLOWLIST` and `RECIPES_ENV_DENYLIST`.

## Validation modes
- `VALIDATION_STRICT=1` excludes semantic-invalid recipes.
- `VALIDATION_STRICT_SCOPE=critical` limits exclusion to law/medical.