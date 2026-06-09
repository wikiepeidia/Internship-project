# Phase 15: i18n.js + demo.py Static Route - Context

**Gathered:** 2026-06-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 15 ships a bilingual string table as `src/runtime/demo_assets/i18n.js` and wires a single new `GET /static/i18n.js` static route in `demo.py`. It then updates `index.html` to load `i18n.js` and replace all hardcoded strings with `data-i18n` attribute markers + a DOMContentLoaded injection step. No changes to `demo.js` behavior, no new backend routes beyond the one static file, no changes to `POST /api/analyze`.

</domain>

<decisions>
## Implementation Decisions

### i18n Module Design
- `window.I18N = { ... }` global assignment — no ES module system; works with a synchronous `<script src="/static/i18n.js">` in `<head>` before `demo.js`.
- Flat namespaced keys: `I18N.PLACEHOLDER`, `I18N.SEND_BTN`, `I18N.CHANNEL_UNKNOWN`, `I18N.RISK_HIGH`, etc. — direct access, no deep nesting.
- Script placed in `<head>` after CSS links, before `demo.js`, no `defer` — synchronous load guarantees `I18N` is available at DOMContentLoaded.
- `demo.py` gets one new `elif path == "/static/i18n.js"` branch using the existing `_load_asset` + `_text_response` pattern — zero new abstractions.

### Welcome Bubble — ARIA/i18n Conflict Resolution
- Welcome bubble structure stays in static HTML (`role="log"` ARIA live region must exist at page load per Phase 14 rules).
- Welcome bubble text nodes use `data-i18n` attributes; a small inline `<script>` or DOMContentLoaded block in `index.html` replaces `textContent` from `I18N` keys — achieving zero literal visible strings while keeping the structural HTML intact for screen readers.
- All other visible strings also extracted via the same `data-i18n` + JS-inject pattern.

### String Inventory Scope
- **Page/header**: page `<title>`, eyebrow, `<h1>`, status chips, section `aria-label`s.
- **Composer**: textarea `placeholder`, send button label, "Kênh" channel field label.
- **Channel options**: all 5 values — "Không rõ", "SMS", "Zalo", "Messenger", "Telegram" (include Telegram even if not yet in select — key defined, unused now).
- **Welcome bubble**: assistant name chip, welcome text, hint-row chip labels.
- **Error messages**: fetch error, abort/cancelled, validation error — defined now for Phase 16 reuse.
- **Bot reply labels**: risk tier display strings ("Nguy hiểm cao (High risk)", "Nguy hiểm trung bình (Medium risk)", "Thấp / Không phát hiện (Low / No threat detected)"), verdict label, cues label, steps label — defined now for Phase 16 bot bubble rendering.
- **Aria-labels**: thread, form, channel selector — injected via JS to stay consistent with the zero-literals rule.

### Language Policy
- Vietnamese primary for all user-facing labels.
- English technical terms in parentheses: e.g., `"Nguy hiểm cao (High risk)"`, `"Local-first"`, `"Text-only"`.
- Consistent with Phase 14 D-16 bilingual badge pattern.

### Claude's Discretion
- Exact key name casing and prefix conventions (e.g., `RISK_HIGH` vs `RISK_TIER_HIGH`) are at Claude's discretion.
- Whether to use a single inline `<script>` block for the i18n injection or a tiny `applyI18n()` function is at Claude's discretion — keep it under ~20 lines.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/runtime/demo.py`: static routes follow a clear `elif path == "/static/X"` pattern with `_load_asset(name)` + `_text_response(start_response, "200 OK", content_type, body)` — add one branch.
- `src/runtime/demo_assets/index.html`: Phase 14 scaffold has all strings as literal text nodes. Need to add `data-i18n` attributes and a JS injection block.
- `src/runtime/demo_assets/demo.css`: no changes needed.

### Established Patterns
- All static assets live in `src/runtime/demo_assets/` and are served by `_load_asset(name)`.
- `demo.js` uses `document.getElementById` on well-known IDs (`analysis-form`, `message-input`, `channel-select`, `sample-button`, `analyze-button`) — Phase 15 must not change those IDs.
- Backend is frozen: no new API routes, no changes to POST /api/analyze.

### Integration Points
- `index.html` `<head>` load order: CSS → i18n.js → demo.js.
- Phase 16 will reference `I18N` keys in `demo.js` for dynamic bubble text — key names chosen now must be stable.
- `tests/runtime/test_demo.py` should get a new assertion that `GET /static/i18n.js` returns HTTP 200 with `application/javascript` and contains `I18N`.

</code_context>

<specifics>
## Specific Ideas

- The `data-i18n` injection block should be self-contained and run before `demo.js` so `demo.js` can reference `window.I18N` immediately.
- Bot-reply strings should use the same bilingual format as Phase 14 risk badge labels: Vietnamese first, English in parentheses.
- Keep the injection pattern simple — a tight `document.querySelectorAll('[data-i18n]')` loop that sets `textContent` from `I18N[el.dataset.i18n]`.

</specifics>

<deferred>
## Deferred Ideas

- Dynamic language switching (toggle VI/EN at runtime) — out of v2.0 scope.
- Loading i18n from an external URL or CDN — contradicts offline-first constraint.
- Pluralization or template interpolation in i18n strings — not needed for current string set.

</deferred>

---

*Phase: 15-i18n.js + demo.py Static Route*
*Context gathered: 2026-06-09*
