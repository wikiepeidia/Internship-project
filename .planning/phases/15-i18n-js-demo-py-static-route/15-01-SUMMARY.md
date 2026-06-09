---
phase: 15-i18n-js-demo-py-static-route
plan: 01
status: complete
completed: 2026-06-09
---

# Phase 15 Plan 01 — Summary

## What shipped

**New file: `src/runtime/demo_assets/i18n.js`**
- `window.I18N` global with 50+ bilingual keys across 10 groups: page/header, status strips,
  ARIA labels, welcome bubble, composer, channel options, risk tiers, result/template labels,
  error/typing strings, and Phase 16 bot-reply keys.
- No ES module syntax. No defer. Synchronous parse-time assignment.

**Modified: `src/runtime/demo.py`**
- Added one `if method == "GET" and path == "/static/i18n.js":` branch (3 lines) after the
  `demo.js` route, using existing `_load_asset` + `_text_response` pattern.
- Zero changes to any other route, handler, or function.

**Modified: `src/runtime/demo_assets/index.html`**
- `<script src="/static/i18n.js"></script>` added in `<head>` after `demo.css`, no defer.
- `data-i18n` attributes added to all 20 live-DOM visible-string elements (eyebrow, h1, status
  chips, welcome bubble meta/text/hint spans, input label, channel label/options, buttons).
- `data-i18n` markers added to 9 template internals (user-meta, result-meta, dt labels, h3
  headings, typing-meta, error-meta, error-steps-heading) as inert Phase 16 cloneNode hints.
- `data-i18n-aria="TYPING_ARIA"` on `typing-dots` div (avoids textContent on a div with children).
- Hardcoded `aria-label` removed from 6 structural elements (shell, status-strip, chat-frame,
  result-panel, analysis-form, hint-row) — injected via `applyI18n` at DOMContentLoaded instead.
- `role="log"`, `aria-live="polite"`, `aria-relevant="additions text"` preserved on #result-panel.
- Inline `applyI18n` script block (~18 lines, `var`, `textContent` only) before deferred demo.js:
  sets `document.title`, `placeholder`, loops `[data-i18n]` for textContent, sets 6 ARIA attrs.

**Modified: `tests/runtime/test_demo.py`**
- Line 59 assertion changed from literal Vietnamese string to `data-i18n="WELCOME_TEXT"`.
- New `test_demo_i18n_js_is_served` test: asserts 200, `application/javascript`, `window.I18N`,
  `PLACEHOLDER`, `ANALYZE_BTN`, `RISK_HIGH` present in response body.

## Verification

```
pytest tests/runtime/test_demo.py -v
5 passed in 0.18s
```

All success criteria met:
- GET /static/i18n.js → 200 application/javascript with window.I18N ✓
- Zero literal visible strings hardcoded in index.html body (all data-i18n + fallback) ✓
- 50+ keys covering all string groups including Phase 16 bot-reply/error keys ✓
- i18n.js synchronous in <head> (no defer/async) ✓
- applyI18n fires before deferred demo.js ✓
- 5/5 tests pass ✓
- demo.py diff: +3 lines only, no other changes ✓

## Requirements closed

- I18N-01: Flat namespaced window.I18N keys, direct access ✓
- I18N-02: All UI strings from I18N; ARIA/welcome bubble zero-literal via data-i18n + JS inject ✓
- INFRA-02: Static route follows existing _load_asset pattern ✓
