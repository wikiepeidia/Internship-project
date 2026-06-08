# Phase 14: CSS + HTML Scaffolding - Context

**Gathered:** 2026-06-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 14 replaces the current static demo page scaffold with a chat-bubble interface shell. It covers `index.html` and `demo.css`: Be Vietnam Pro font loading, full-viewport `100dvh` layout, compact header, scrollable chat thread, pinned composer, pre-rendered ARIA live region, and clone-safe templates. It does not implement the Phase 16 fetch lifecycle, Phase 17 sample/clear behavior, Phase 15 `i18n.js`, or backend contract changes.

</domain>

<decisions>
## Implementation Decisions

### Chat Shell Layout
- **D-01:** Use a full-viewport messenger layout: compact header at the top, independently scrolling chat thread in the middle, and composer pinned inside the app shell at the bottom.
- **D-02:** The header should emphasize local safety status with a compact title plus small status chips such as local-first and text-only.
- **D-03:** Desktop layout should stay readable on projectors while remaining flexible enough to shrink beside code during defense. Use a responsive centered chat column instead of a fixed phone mockup.
- **D-04:** The thread area must use `flex: 1 1 0` and `min-height: 0`; the composer must stay visible with safe-area padding for mobile.

### Empty Thread State
- **D-05:** The initial page state should show a left-aligned welcome bot bubble, not a card or centered marketing placeholder.
- **D-06:** Welcome copy should use a warm Vietnamese helper tone, centered on: "Mình sẽ giúp bạn kiểm tra dấu hiệu lừa đảo tài chính."
- **D-07:** Include a small hint row under the welcome bubble, such as channel/privacy chips, without returning to a card-heavy layout.
- **D-08:** The welcome bubble must be inside the static `role="log"` chat thread at page load so screen readers and layout validation see the real chat region immediately.

### Template Contract
- **D-09:** Scaffold user, bot, typing, and error chat bubble templates in the static HTML for later JavaScript.
- **D-10:** The bot result template should contain the full result skeleton: risk badge, verdict, labels/meta, grounded cues list, and safe next steps list as empty `data-slot` nodes.
- **D-11:** Template internals must not use duplicate-prone IDs. Use `data-slot` attributes only inside templates.
- **D-12:** Preserve current functional form/control IDs for migration compatibility: `analysis-form`, `message-input`, `channel-select`, `sample-button`, and `analyze-button`.

### Visual Tone
- **D-13:** Use a trustworthy light clinical tone: white/soft gray base, navy/teal accents, and restrained semantic red/amber/green for risk tiers.
- **D-14:** Favor defense-readable comfort density: slightly larger text, generous bubble padding, clear labels, and projector-friendly spacing.
- **D-15:** Differentiate bubbles with subtle polarity: user bubble navy/teal filled on the right, bot bubble white with border on the left.
- **D-16:** Risk tier badges should be compact bilingual labeled pills, e.g. "Nguy hiểm cao (High risk)", with semantic color.

### the agent's Discretion
- The agent may choose exact spacing, CSS custom property names, and minor responsive breakpoints as long as they preserve the decisions above and the Phase 14 success criteria.
- The agent may decide whether to keep old outer template IDs as aliases during Phase 14 to avoid page-load JavaScript errors, but inner template nodes must remain `data-slot` only.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning Scope
- `.planning/ROADMAP.md` — Phase 14 goal, success criteria, and cross-phase boundaries for the v2.0 Chat UI Revamp.
- `.planning/REQUIREMENTS.md` — `INFRA-01` plus related downstream v2.0 chat, input, polish, i18n, and infrastructure requirements.
- `.planning/STATE.md` — locked v2.0 constraints and pitfall registry, including `100dvh`, ARIA live region, `data-slot`, and no-framework constraints.

### Existing Demo Code
- `src/runtime/demo_assets/index.html` — current card-based demo shell to replace.
- `src/runtime/demo_assets/demo.css` — current warm gradient/card styling to rewrite into the chat shell.
- `src/runtime/demo_assets/demo.js` — current DOM selectors and migration constraints; Phase 14 should avoid page-load JS errors while Phase 16 will rewrite behavior.
- `src/runtime/demo.py` — static asset routes and frozen backend boundary.
- `tests/runtime/test_demo.py` — existing demo expectations that may need Phase 14-aligned HTML/static asset assertions.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/runtime/demo_assets/index.html`: existing form controls already expose useful IDs (`analysis-form`, `message-input`, `channel-select`, `sample-button`, `analyze-button`) that should be retained for compatibility.
- `src/runtime/demo_assets/demo.css`: existing risk tier color hooks can inform semantic badge colors, but the warm gradient/card system should be replaced.

### Established Patterns
- The demo is a static, no-build, vanilla HTML/CSS/JS asset bundle served by `src/runtime/demo.py`.
- Current templates use inner IDs like `result-summary` and `result-risk-tier`; this conflicts with the v2.0 no-duplicate-ID rule when multiple bubbles are cloned.
- The backend serves `GET /`, `GET /static/demo.css`, `GET /static/demo.js`, and `POST /api/analyze`. Phase 14 should not change backend behavior.

### Integration Points
- `index.html` must keep linking `/static/demo.css` and `/static/demo.js`.
- `demo.css` must define the chat shell, thread, bubble, template-result, risk badge, composer, responsive, and reduced-motion-safe baseline styles.
- `tests/runtime/test_demo.py` should validate the static chat shell, Be Vietnam Pro load, `role="log"` live region, preserved form IDs, and absence of inner template IDs.

</code_context>

<specifics>
## Specific Ideas

- The UI should be readable during thesis defense on a projector.
- The browser can be narrowed so the judge can see both the demo and code side-by-side.
- The welcome bot bubble should use the Vietnamese line: "Mình sẽ giúp bạn kiểm tra dấu hiệu lừa đảo tài chính."
- Avoid a marketing hero/card feel; the first viewport should be the actual chat experience.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 14 scope.

</deferred>

---

*Phase: 14-CSS + HTML Scaffolding*
*Context gathered: 2026-06-08*
