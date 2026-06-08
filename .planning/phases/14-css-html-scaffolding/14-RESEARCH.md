# Phase 14 Research: CSS + HTML Scaffolding

## RESEARCH COMPLETE

**Phase:** 14 - CSS + HTML Scaffolding  
**Date:** 2026-06-08  
**Source:** Inline research from Phase 14 context, roadmap, requirements, and current demo assets.

## Scope Anchor

Phase 14 is a static shell phase. It should make the demo page load as a real chat interface before new JavaScript behavior exists. The phase covers:

- `src/runtime/demo_assets/index.html`
- `src/runtime/demo_assets/demo.css`
- `tests/runtime/test_demo.py`

It should not modify `src/runtime/demo.py`, `POST /api/analyze`, `demo.js` fetch behavior, or add `i18n.js`.

## Current Code Findings

- `index.html` is currently a hero plus two-column card layout. This conflicts with the v2.0 goal of making the first viewport the actual chat experience.
- `demo.css` is built around warm gradients, rounded panels, and result cards. This should be replaced with a light clinical chat shell and semantic risk color tokens.
- `demo.js` currently depends on existing form IDs and outer result/error template IDs. Phase 14 should preserve the current functional form IDs and can keep compatibility-oriented outer template IDs, but template internals must use `data-slot` only.
- `tests/runtime/test_demo.py` already verifies the static assets are served. It should be extended to assert the chat shell, Be Vietnam Pro font link, ARIA live log, preserved form IDs, and no inner template IDs.

## Key Implementation Constraints

- Use vanilla HTML/CSS only. No JS framework and no build step.
- Use `height: 100dvh` for the root app shell and `flex: 1 1 0; min-height: 0` for the scrollable thread area.
- Put `<div role="log" aria-live="polite">` in the static HTML at page load.
- Keep the static welcome bot bubble inside that live log.
- Avoid duplicate IDs inside templates. Use `data-slot` attributes for all clone targets.
- Load Be Vietnam Pro from Google Fonts CDN and keep Vietnamese text line height at or above 1.65.
- Preserve current functional IDs: `analysis-form`, `message-input`, `channel-select`, `sample-button`, and `analyze-button`.

## Recommended Plan Shape

Use one plan in one wave:

- Update tests first so the static contract is explicit.
- Rewrite `index.html` into the chat shell with preserved controls and clone-safe templates.
- Rewrite `demo.css` around the chat shell, bubble layout, risk badges, responsive behavior, and reduced-motion baseline.
- Run focused runtime demo tests.

## Pitfalls To Guard

- Duplicate IDs in cloned template internals.
- Page-load JavaScript errors from missing existing form/template selectors.
- A static empty state outside the ARIA live region.
- Full-height layout that fails because the thread lacks `min-height: 0`.
- Returning to a marketing/card layout instead of a messenger-like tool surface.
