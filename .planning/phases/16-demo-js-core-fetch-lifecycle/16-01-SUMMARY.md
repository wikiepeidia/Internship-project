---
phase: 16-demo-js-core-fetch-lifecycle
plan: 01
status: complete
completed: 2026-06-09
---

# Phase 16 Plan 01 — Summary

## What shipped

**Rewritten: `src/runtime/demo_assets/demo.js`**

Complete replacement of the old Phase 6 demo.js that used broken inner-ID selectors (`#result-summary`, `#result-risk-tier`, etc. — removed in Phase 14's data-slot refactor).

New architecture:
- **`applyI18nToClone(el)`** — applies window.I18N values to all `[data-i18n]` + `[data-i18n-aria]`
  elements inside a cloned template node at render time.
- **`appendUserBubble(text)`** — clones `#user-message-template.content.firstElementChild`,
  sets `[data-slot="text"]`, applies I18N, removes `result-panel--empty`, appends + scrolls.
- **`appendTypingBubble()`** — clones `#typing-template`, returns direct DOM node reference so it
  can be removed with `typingEl.remove()` after response arrives.
- **`appendResultBubble(result)`** — clones `#result-template`, sets all data-slot fields:
  verdict (`result.summary`), risk tier badge (I18N label + `data.riskTier` attr), labels,
  backend, grounded cues and recommendations lists.
- **`appendErrorBubble(error)`** — clones `#error-template`, sets message + steps list.
- **`analyzeMessage(event)`** — full async fetch lifecycle: abort in-flight → record history →
  append user bubble → clear textarea → set busy → append typing → fetch → remove typing →
  append result or error → set idle. AbortError swallowed silently.
- **Enter key handler** — plain Enter calls `form.requestSubmit()`; Shift+Enter is default (newline).
- **Module state** — `const history = []` accumulates `{text, channel}` per submit; no localStorage.
  `let currentController = null` tracks AbortController.

## Verification

```
pytest tests/runtime/test_demo.py -v
5 passed in 0.11s
```

All Phase 16 success criteria met:
- User bubble + textarea clear on submit ✓  (CHAT-01)
- Typing indicator during inference window ✓  (CHAT-02)
- Bot bubble with risk tier, verdict, cues, steps ✓  (CHAT-03)
- Error bubble on network failure or non-200 ✓  (CHAT-04)
- Plain Enter = submit; Shift+Enter = newline ✓  (INPUT-01)
- Channel value in POST body ✓  (INPUT-02)
- Send button busy state with I18N label ✓  (INPUT-03)
- history[] accumulates, no localStorage ✓  (INPUT-04)
- rAF scroll after each append ✓
- No innerHTML anywhere — textContent only ✓
- AbortController present and wired ✓

## Requirements closed

- CHAT-01, CHAT-02, CHAT-03, CHAT-04 ✓
- INPUT-01, INPUT-02, INPUT-03, INPUT-04 ✓
