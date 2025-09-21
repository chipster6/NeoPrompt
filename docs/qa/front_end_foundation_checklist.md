# Front-end Foundation QA Checklist

This checklist covers the MVP DoD for Console, Toolbar, Output, History, and Settings.

- Console
  - Multiline input accepts paste and manual typing
  - Ctrl/⌘+Enter triggers generation once (no double submission)
  - Token estimate updates as text changes and shows cost when configured

- Toolbar
  - Assistant and Category selects update internal state and POST /choose payload
  - Enhance toggle flips options.enhance in /choose payload (UI-only for M1)
  - Optional: Force JSON toggle included in payload when checked

- Output Panel
  - Engineered prompt renders in monospace area
  - Copy button copies to clipboard and returns a success toast
  - 👍 and 👎 call /feedback with expected reward_components and show toasts
  - Token estimate for output appears when engineered_prompt is present

- History
  - Items load with default limit (10 in UI)
  - Assistant and Category filters update the list
  - with_text toggle displays raw_input/engineered_prompt only when allowed
  - Load more appends results and disables while loading

- Settings
  - Modal opens and closes; backdrop click closes
- Diagnostics/Packs view loads and renders data (temporary: legacy recipes until UI migrates)
- Reload diagnostics refreshes data (planned: /engine/*; temporary: legacy /recipes)
  - STORE_TEXT checkbox toggles preference in localStorage
  - Token cost input updates localStorage and affects estimates

- Accessibility & UX basics
  - Focus is visible for interactive elements (selects, buttons, checkboxes)
  - Modals trap focus and Close returns focus to the trigger
  - ARIA live region announces toasts
  - Color contrast meets AA on key surfaces

- Error handling
  - Network failure shows a toast in Console generate, Settings recipes load, and Stats fetch
  - Copy failure shows a toast

- Non-regression quicks
  - No console errors in dev tools
  - Vite dev server compiles cleanly; TS checker shows no errors
- Backend endpoints reachable with API_BASE
  - V2: /engine/plan, /engine/transform, /engine/score, /diagnostics
  - Legacy (until migration): /recipes, /choose, /feedback, /history
