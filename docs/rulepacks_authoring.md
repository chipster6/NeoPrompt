# RulePacks Authoring (V2)

RulePacks are declarative policy bundles that guide the engine toward precise, structured, and safe prompt engineering. They combine with the PromptDoc IR and the Operator Planner.

Types
- global, model, category, org, project, user

Merge rules
- Lists append (unless override: true)
- Numbers: min for limits, max for richness
- Booleans: last-writer wins
- Operators: (baseline ∪ include) − exclude, with optional insert_at

Example — model pack
```yaml
id: pack.chatgpt.v1
type: model
priority: 40
applies_to: { models: ["gpt-4o","gpt-4.1","o4-mini","gpt-4o-mini"] }
directives:
  max_tokens_hint: 8000
  temperature_hint: 0.2
  style: { persona: "Domain expert; numbered steps", tone: "precise, neutral",
           formatting: ["section-headers","bullets","tables-when-appropriate"] }
  constraints:
    - "State assumptions explicitly"
    - "Ask for missing inputs unless STRICT_MODE=true"
    - "Include ≥1 I/O example when applicable"
  operators:
    include: ["clarify","disambiguate","structure","format_contract","tone_adjust",
              "example_inject","tighten_language","compress","safety_guard","verify_requirements"]
checklist:
  - { id: io-contract, test: "must include Goals, Inputs, Process, Output Format, Acceptance Criteria" }
```

Validation
- Author packs to conform to docs/rulepack.schema.json (stub provided; expand as needed)
- Use /engine/plan to inspect packs_applied and operator_plan for a given seed/model/category

Authoring tips
- Keep packs small and composable
- Use priorities to order overlapping packs
- Prefer guidance via directives; reserve insert_at for specific operator placement
