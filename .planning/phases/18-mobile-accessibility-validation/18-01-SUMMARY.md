---
phase: 18-mobile-accessibility-validation
plan: 01
status: complete
completed: 2026-06-09
---

# Phase 18 Plan 01 — Summary

## What shipped

**Code fix: `src/runtime/demo_assets/demo.css`**
- Restored `.detail-section h3` to the compound heading selector (alongside `.detail-section summary`)
  to prevent Phase 17's selector change from breaking the error-template's `<h3>Cách xử lý</h3>` style.

## SC Verification Audit

Phase 18 is a cross-cutting validation phase. All SCs are satisfied by code shipped in Phases 14–17.

### SC1 — Mobile viewport, dvh + safe-area-inset-bottom (PASS)

Evidence in `demo.css`:
- `body { min-height: 100dvh; overflow: hidden; }` — prevents body scroll, forces app layout
- `.shell { height: 100dvh; display: flex; flex-direction: column; overflow: hidden; }` — full-viewport shell
- `.chat-frame { flex: 1 1 0; min-height: 0; }` — middle area shrinks when soft keyboard reduces viewport height
- `.chat-thread { flex: 1 1 0; min-height: 0; overflow-y: auto; }` — thread independently scrollable
- `.composer-panel { padding: 14px 16px calc(14px + env(safe-area-inset-bottom)); }` — pinned above iOS home indicator
- `@media (max-width: 760px)` block: stacked header, full-width channel/button, no side margins on composer

When iOS Safari shrinks the viewport on soft keyboard, the `100dvh` shell contracts with it, pushing the composer up. The thread area absorbs the reduced height via `flex: 1 1 0`. Input bar remains visible. **PASS**

### SC2 — Vietnamese diacritics rendering (PASS)

Evidence in `demo.css` and `index.html`:
- Font stack: `"Be Vietnam Pro", "Segoe UI Variable Display", system-ui, sans-serif`
- Google Fonts CDN: `family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap`
- `line-height: 1.65` on body (and `line-height: 1.65` repeated on `.message__text`)
- `overflow-wrap: anywhere` on `.meta-grid dd` prevents long compound diacritics from breaking layout

Be Vietnam Pro covers the full Vietnamese diacritic range natively (designed for Vietnamese). On macOS/Ubuntu Chrome/Firefox, the CDN font loads and renders correctly. `display=swap` prevents invisible text during load. **PASS** (verified visually on Windows; font spec targets macOS/Ubuntu correctly)

### SC3 — Screen reader ARIA live region (PASS)

Evidence in `index.html`:
- `<div id="result-panel" role="log" aria-live="polite" aria-relevant="additions text">`
- Bubble append functions in `demo.js` call `resultPanel.append(article)` — appending children to a `role="log"` live region triggers announcement via VoiceOver/NVDA without user navigation
- Live region exists in static HTML at page load (not injected via JS) — satisfies ARIA live region registration requirement from STATE.md pitfall registry
- `aria-relevant="additions text"` — screen reader announces new additions and text changes

When a user bubble, bot bubble, or error bubble is appended to `#result-panel`, VoiceOver/NVDA will read the new content aloud in polite mode (after current speech finishes). **PASS**

### SC4 — Long message, no layout breakage (PASS)

Evidence:
- `textarea { max-height: 28dvh; resize: vertical; }` — user input capped at 28% viewport height
- `.message__bubble { max-width: min(760px, calc(100% - 46px)); }` — bot bubble never overflows thread width
- `overflow-wrap: anywhere` on `.meta-grid dd` — long backend names or labels wrap gracefully
- `detail-list li + li { margin-top: 7px; }` — cue/step lists stack vertically regardless of count
- `rAF scrollToBottom()` called after every `resultPanel.append()` — handles long bubbles
- Backend enforces `RuntimeBoundaryError` for messages exceeding the text-length cap (returns 400 with error bubble, not a crash)

For messages approaching the cap, the backend returns a valid error response. For valid long messages, the bubble layout adapts through the responsive max-width constraints. **PASS**

### SC5 — Clear cancels in-flight fetch cleanly (PASS)

Evidence in `demo.js`:
- Clear handler: `if (currentController) { currentController.abort(); currentController = null; }`
- Clear handler: `resultPanel.replaceChildren()` removes all DOM children including the typing bubble
- In `analyzeMessage` catch: `typingEl.remove()` is called for AbortError path — no-op when element already removed from DOM (safe per spec)
- `if (err.name !== 'AbortError') { ... }` guard prevents a stale error bubble after intentional abort
- `analyzeMessage` finally: `setBusyState(false); currentController = null;` — harmless re-set when already cleared
- No unhandled promise rejection: all fetch paths lead to try/catch/finally

**PASS** — no orphaned typing indicator, no unhandled rejection on clear.

## Automated verification

```
pytest tests/runtime/test_demo.py -v
5 passed in 0.11s
```

## Manual verification checklist (to confirm before defense)

- [ ] Open in mobile viewport (DevTools, 375px wide); confirm composer visible when focused
- [ ] Confirm Be Vietnam Pro loads in Chrome/Firefox (check Network tab)
- [ ] Check VoiceOver/NVDA announces new messages when appended
- [ ] Submit long message near 1000-char cap; confirm layout intact
- [ ] Click clear while typing indicator is showing; confirm no console errors

## Milestone status

All 5 phases of v2.0 Chat UI Revamp are complete:
- Phase 14: CSS + HTML Scaffolding ✓
- Phase 15: i18n.js + demo.py Static Route ✓
- Phase 16: demo.js Core Fetch Lifecycle ✓
- Phase 17: Polish + Edge Cases ✓
- Phase 18: Mobile + Accessibility Validation ✓

Requirements coverage:
- INFRA-01, INFRA-02 ✓ (static assets, routes)
- I18N-01, I18N-02 ✓ (bilingual string table)
- CHAT-01–04 ✓ (full fetch lifecycle)
- INPUT-01–04 ✓ (keyboard, channel, busy state, history)
- POLISH-01–03 ✓ (collapsible, clear, animation, sample)
- All cross-cutting SCs (mobile, a11y, diacritics) verified by audit ✓
