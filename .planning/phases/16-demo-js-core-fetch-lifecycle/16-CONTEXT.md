# Phase 16: demo.js Core Fetch Lifecycle - Context

**Gathered:** 2026-06-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 16 rewrites `src/runtime/demo_assets/demo.js` to deliver the complete end-to-end chat
interaction: user bubble, typing indicator, bot bubble with all result fields, error bubble,
AbortController cancellation, in-memory history[], and rAF scroll anchoring. The HTML/CSS shell
(Phase 14) and the i18n string table (Phase 15) are already shipped and locked. Backend remains
frozen. Only `demo.js` changes.

</domain>

<decisions>
## Implementation Decisions

### DOM selectors
- All element queries use getElementById / querySelector with the stable IDs locked in Phase 14:
  `analysis-form`, `message-input`, `channel-select`, `analyze-button`, `sample-button`, `result-panel`,
  `user-message-template`, `result-template`, `typing-template`, `error-template`.
- No innerHTML — all text set via textContent or setAttribute. XSS safety rule from STATE.md.

### Thread model
- Thread accumulates; no `resetPanel` / `replaceChildren` on the thread. Each submit appends:
  user bubble → typing bubble → (on response) remove typing, append result OR error.
- `result-panel--empty` class removed on first user bubble append.

### Bubble cloning
- `template.content.cloneNode(true).firstElementChild` gives a direct DOM node reference (avoids
  fragment wrapper) — lets us hold a reference to the typing bubble for later removal.
- Template internals already have `data-i18n` attrs (Phase 15 markers); demo.js applies
  `window.I18N[el.dataset.i18n]` at clone time for each cloned bubble.

### Enter key behavior
- Plain `Enter` in the textarea submits (calls `form.requestSubmit()`); `Shift+Enter` inserts newline.
- Locked from ROADMAP.md SC5.

### AbortController
- Module-level `var currentController = null`.
- Before each fetch: `if (currentController) currentController.abort(); currentController = new AbortController();`
- AbortError is caught silently; other errors render the ERR_NETWORK error bubble.

### In-memory history
- Module-level `var history = [];`
- On each submit: `history.push({ text, channel })` before clearing the input.
- No localStorage. Tab close = history lost. Locked from STATE.md.

### I18N integration
- Risk tier labels from `window.I18N`: RISK_HIGH, RISK_SUSPICIOUS, RISK_BENIGN.
- Button text: ANALYZE_BTN / ANALYZE_BTN_BUSY from window.I18N.
- Error message / step strings from ERR_NETWORK / ERR_NETWORK_STEP.
- All template text nodes injected at clone time via data-i18n lookup.
- Fallback strings used if window.I18N is undefined (defensive, should not happen in prod).

### API response mapping
- `result.summary` → `[data-slot="verdict"]` textContent
- `result.risk_tier` → `[data-slot="risk-tier"]` textContent + dataset.riskTier
- `result.threat_labels.join(', ')` → `[data-slot="labels"]` textContent
- `result.backend_name` → `[data-slot="backend"]` textContent
- `result.top_cues.map(cue => '"${span}" — ${reason}')` → li items in `[data-slot="grounded-cues"]`
- `result.recommendations` → li items in `[data-slot="recommendations"]`

### Scroll anchoring
- All bubble append functions end with `requestAnimationFrame(() => { resultPanel.scrollTop = resultPanel.scrollHeight; })`

### Sample button
- Phase 16: fill textarea with sample Vietnamese phishing text + set channel to "sms" + focus.
- Auto-submit is Phase 17 (SC4 there, not here).

### Code style
- Keep existing `const`/`let` + arrow functions (current demo.js style).
- No ES module syntax (no export/import).
- defer script already set in index.html; document.getElementById safe at DOMContentLoaded.

</decisions>

<code_context>
## Existing Code Insights

### Current demo.js (to be replaced)
- Uses old inner-ID selectors (`#result-summary`, `#result-risk-tier`, etc.) — these were removed
  in Phase 14 when templates switched to `data-slot` internals. Current demo.js is broken after
  Phase 14's template refactor; Phase 16 completes the migration.
- `resetPanel()` clears the thread — Phase 16 drops this in favor of accumulation.
- `setBusyState` and `createListItems` helpers are worth keeping (updated for I18N + data-slot).

### Phase 14 templates (verified in index.html)
- `#user-message-template`: `[data-slot="text"]`, `[data-i18n="USER_META"]`
- `#result-template`: `[data-slot="verdict"]`, `[data-slot="risk-tier"]`, `[data-slot="labels"]`,
  `[data-slot="backend"]`, `[data-slot="grounded-cues"]`, `[data-slot="recommendations"]`,
  `[data-i18n="RESULT_META"]`, `[data-i18n="RESULT_DT_LABELS"]`, `[data-i18n="RESULT_DT_BACKEND"]`,
  `[data-i18n="CUES_HEADING"]`, `[data-i18n="STEPS_HEADING"]`
- `#typing-template`: `[data-i18n="TYPING_META"]`, `.typing-dots[data-i18n-aria="TYPING_ARIA"]`
- `#error-template`: `[data-slot="message"]`, `[data-slot="steps"]`,
  `[data-i18n="ERROR_META"]`, `[data-i18n="ERROR_STEPS_HEADING"]`

### Phase 15 I18N keys (verified in i18n.js)
- USER_META, RESULT_META, RESULT_DT_LABELS, RESULT_DT_BACKEND, CUES_HEADING, STEPS_HEADING
- ERROR_META, ERROR_STEPS_HEADING, TYPING_META, TYPING_ARIA, LIST_EMPTY
- RISK_HIGH, RISK_SUSPICIOUS, RISK_BENIGN
- ANALYZE_BTN, ANALYZE_BTN_BUSY, ERR_NETWORK, ERR_NETWORK_STEP

### Backend contract (frozen)
- POST /api/analyze with body {text: string, channel: ChannelName}
- 200 → {risk_tier, summary, threat_labels, top_cues: [{span, reason}], recommendations, backend_name}
- 400/503 → {error: {message, steps}}

</code_context>

<deferred>
## Deferred to Later Phases

- Collapsible cues/steps sections — Phase 17
- Bubble entrance animations — Phase 17
- Clear button — Phase 17
- Sample button auto-submit — Phase 17
- Mobile viewport / iOS keyboard validation — Phase 18
- Screen reader announcement testing — Phase 18

</deferred>

---

*Phase: 16-demo.js Core Fetch Lifecycle*
*Context gathered: 2026-06-09*
