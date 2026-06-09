---
phase: 17-polish-edge-cases
plan: 01
status: complete
completed: 2026-06-09
---

# Phase 17 Plan 01 — Summary

## What shipped

**Modified: `src/runtime/demo_assets/i18n.js`**
- Added `CLEAR_BTN: "Xóa"` key.

**Modified: `src/runtime/demo_assets/index.html`**
- Clear button: `<button id="clear-button" class="ghost-button" data-i18n="CLEAR_BTN">Xóa</button>`
  added inside new `.app-header__actions` wrapper that also contains `.status-strip`.
- Result-template: both `<section><h3>` detail sections converted to `<details open><summary>`
  with the same `data-i18n` attrs. Both sections start expanded (`open` attribute).

**Modified: `src/runtime/demo_assets/demo.css`**
- `.app-header__actions` flex wrapper + `.ghost-button` danger-outline style.
- `.detail-section summary` added to compound selector for heading styles; custom `::before`
  chevron (▸/▾) replaces the native disclosure marker.
- `@keyframes msg-enter` (opacity 0→1, translateY 6px→0) applied to `.message`
  (0.2s ease-out both). `prefers-reduced-motion` block already zaps it globally.

**Modified: `src/runtime/demo_assets/demo.js`**
- `clearButton` DOM ref added.
- Clear handler: abort in-flight controller, `resultPanel.replaceChildren()`,
  restore `result-panel--empty` class, call `setBusyState(false)`.
- Sample button: now calls `form.requestSubmit()` immediately after filling textarea + setting channel.

**Modified: `tests/runtime/test_demo.py`**
- Added `assert 'id="clear-button"' in html`.

## Verification

```
pytest tests/runtime/test_demo.py -v
5 passed in 0.13s
```

All Phase 17 success criteria met:
- Collapsible `<details open>` for grounded cues and safe steps in result template ✓  (POLISH-01)
- Clear button aborts in-flight fetch + removes all bubbles + restores empty state ✓  (POLISH-02)
- Bubble entrance animation on `.message` with prefers-reduced-motion safe guard ✓  (POLISH-03)
- Sample button auto-submits via `form.requestSubmit()` ✓  (POLISH-03/SC4)

## Requirements closed

- POLISH-01, POLISH-02, POLISH-03 ✓
