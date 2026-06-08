---
phase: 14-css-html-scaffolding
plan: "14-01"
subsystem: ui
tags: [runtime-demo, html, css, accessibility, chat-ui]

requires:
  - phase: 13-content-gap-closure-dataset-qlora
    provides: defense-ready thesis and slide baseline for the demo polish milestone
provides:
  - Static full-viewport chat shell for the local runtime demo
  - Be Vietnam Pro Google Fonts loading for Vietnamese UI text
  - ARIA live chat thread present at page load
  - Clone-safe message templates using data-slot internals
affects: [phase-15-i18n-js-demo-py-static-route, phase-16-demo-js-core-fetch-lifecycle, phase-18-mobile-accessibility-validation]

tech-stack:
  added: [Google Fonts CDN: Be Vietnam Pro]
  patterns: [100dvh flex shell, static role-log thread, data-slot template internals]

key-files:
  created: []
  modified:
    - src/runtime/demo_assets/index.html
    - src/runtime/demo_assets/demo.css
    - tests/runtime/test_demo.py

key-decisions:
  - "Kept outer result-template and error-template IDs for page-load compatibility while removing IDs from template internals."
  - "Deferred submit-render migration from old inner-ID selectors to Phase 16, matching the phase boundary."

patterns-established:
  - "Chat shell uses height: 100dvh with a flex: 1 1 0, min-height: 0 scroll thread."
  - "Template clone targets are data-slot attributes only."
  - "Vietnamese UI text uses Be Vietnam Pro and line-height >= 1.65."

requirements-completed: [INFRA-01]

duration: 35min
completed: 2026-06-08T17:33:00+07:00
---

# Phase 14: CSS + HTML Scaffolding Summary

**Static vanilla chat shell with Be Vietnam Pro, 100dvh layout, ARIA live thread, and clone-safe data-slot templates**

## Performance

- **Duration:** 35 min
- **Started:** 2026-06-08T16:58:00+07:00
- **Completed:** 2026-06-08T17:33:00+07:00
- **Tasks:** 4
- **Files modified:** 3

## Accomplishments

- Replaced the old hero/card demo page with a full-viewport messenger-style shell: compact header, scrollable thread, and pinned composer.
- Added Be Vietnam Pro loading from Google Fonts and a light clinical navy/teal visual system with semantic risk colors.
- Added static user, bot/result, typing, and error templates whose internals use `data-slot` instead of duplicate-prone IDs.
- Updated runtime demo tests to lock the Phase 14 contract: preserved form IDs, `role="log"`, `aria-live="polite"`, `100dvh`, `min-height: 0`, `flex: 1 1 0`, and safe-area composer padding.

## Task Commits

1. **Static chat shell scaffold** - `3cc54b0` (`feat(14-01): scaffold static chat UI`)

## Files Created/Modified

- `src/runtime/demo_assets/index.html` - Static Vietnamese-first chat shell, ARIA live thread, preserved controls, and clone-safe templates.
- `src/runtime/demo_assets/demo.css` - Full-height chat layout, Be Vietnam Pro stack, message bubble polarity, risk pills, typing/error styles, responsive rules, and reduced-motion guard.
- `tests/runtime/test_demo.py` - Focused assertions for the Phase 14 static UI and unchanged runtime API behavior.

## Decisions Made

- Kept `result-template` and `error-template` as outer template IDs because the current `demo.js` queries them at page load.
- Removed all inner template IDs and introduced `data-slot` targets for the Phase 16 JavaScript rewrite.
- Kept backend routes and `POST /api/analyze` untouched.

## Deviations from Plan

None - plan executed within the specified Phase 14 boundary.

## Issues Encountered

None. Existing `demo.js` submit rendering still targets the old inner IDs, but that migration is explicitly deferred to Phase 16 and does not affect Phase 14 page-load scaffolding.

## Verification

- `python -m pytest tests/runtime/test_demo.py` - 4 passed
- `git diff -- src/runtime/demo.py` - empty
- Manual source inspection confirmed the static thread has `role="log"` and `aria-live="polite"`, CSS includes `100dvh`, `flex: 1 1 0`, `min-height: 0`, `env(safe-area-inset-bottom)`, and forbidden inner template IDs are absent from `index.html`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 15 can move UI strings into `i18n.js` and add the static backend route. Phase 16 must then rewrite `demo.js` to render chat bubbles through `data-slot` selectors instead of the old inner template IDs.

---
*Phase: 14-css-html-scaffolding*
*Completed: 2026-06-08*
