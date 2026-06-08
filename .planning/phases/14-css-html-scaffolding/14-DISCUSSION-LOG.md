# Phase 14: CSS + HTML Scaffolding - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-08
**Phase:** 14-CSS + HTML Scaffolding
**Areas discussed:** Chat Shell Layout, Empty Thread State, Template Contract, Visual Tone

---

## Chat Shell Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Full-viewport messenger | Header at top, thread fills the page, input bar pinned at bottom; best match for `100dvh` and mobile keyboard behavior. | ✓ |
| Centered app surface | Chat sits in a max-width container with margins; calmer on desktop but less phone-like. | |
| You decide | Keep it aligned with the roadmap and existing demo constraints. | |

**User's choice:** Full-viewport messenger layout.
**Notes:** Header should emphasize local safety status chips. Desktop width should be readable on projectors and flexible enough to shrink beside code during defense. Composer should be pinned inside the app shell with independent thread scrolling and safe-area padding.

---

## Empty Thread State

| Option | Description | Selected |
|--------|-------------|----------|
| Welcome bot bubble | Left-aligned assistant bubble with a short Vietnamese-first greeting and privacy reminder; fits the messenger concept. | ✓ |
| Quiet placeholder | No bubble, just subtle centered empty text; cleaner but less chat-like. | |
| Sample prompt card | Shows an example message immediately; useful for demos but risks feeling like the old card layout. | |

**User's choice:** Welcome bot bubble.
**Notes:** The bubble should use a warmer helper tone: "Mình sẽ giúp bạn kiểm tra dấu hiệu lừa đảo tài chính." Include a small hint row under the bubble and keep the bubble inside the static `role="log"` thread at page load.

---

## Template Contract

| Option | Description | Selected |
|--------|-------------|----------|
| User, bot, typing, error | All chat bubble shapes Phase 16 will need, with `data-slot` internals and no duplicate IDs. | ✓ |
| User + bot only | Smaller Phase 14 scope, but Phase 16 must add typing/error structure later. | |
| Bot only | Minimal static scaffold, weakest handoff to JS. | |

**User's choice:** Scaffold user, bot, typing, and error templates.
**Notes:** Bot template should include the full result skeleton. Remove old inner IDs and use `data-slot` only. Preserve current functional IDs for form/control compatibility: `analysis-form`, `message-input`, `channel-select`, `sample-button`, and `analyze-button`.

---

## Visual Tone

| Option | Description | Selected |
|--------|-------------|----------|
| Trustworthy light clinical | White/soft gray base, navy/teal accents, restrained red/amber/green for risk tiers; presentation-safe and avoids the old warm marketing gradient. | ✓ |
| Messenger playful | More saturated bubbles and accents; friendly, but less thesis-demo serious. | |
| Dark mode first | Dramatic and projector-friendly in some rooms, but risk tiers and Vietnamese text need more contrast work. | |

**User's choice:** Trustworthy light clinical tone.
**Notes:** Use defense-readable comfort density. User bubble should be navy/teal filled on the right; bot bubble should be white with a border on the left. Risk tier badges should be compact bilingual labeled pills with semantic color.

---

## the agent's Discretion

- Exact spacing, CSS custom property names, and responsive breakpoints.
- Whether old outer template IDs should be kept as compatibility aliases during Phase 14, provided inner template nodes use `data-slot` only.

## Deferred Ideas

None.
