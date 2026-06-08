# Feature Landscape: Chat-Bubble UI Revamp (v2.0)

**Domain:** Messenger-style single-page demo app wrapping a phishing-detection backend
**Researched:** 2026-06-08
**Scope anchor:** Vanilla HTML/CSS/JS, no framework, no build step; Python WSGI backend unchanged
**Existing contract:** `POST /api/analyze` — synchronous JSON, no streaming, no WebSocket, no session state on server

---

## API Contract (constraints on every feature below)

The backend is a stateless WSGI server. One POST in, one JSON object out. Every chat-UI feature must be
implemented entirely in the browser. The backend cannot be asked to store history, push events, or stream tokens.

**Request shape (unchanged):**

```json
{ "text": "string", "channel": "unknown|sms|zalo|messenger|telegram|facebook" }
```

**Success response fields used in the current card:**

- `risk_tier` — "benign" | "suspicious" | "high-risk"
- `summary` — plain-text verdict string
- `top_cues` — array of up to 3 `{span, reason}` objects
- `threat_labels` — array of up to 2 label strings
- `recommendations` — array of up to 3 plain-text strings
- `backend_name` — string (e.g., "heuristic", "gguf")
- `provisional` — boolean

**Error response:**

```json
{ "error": { "message": "string", "steps": ["string"] } }
```

No new backend fields are needed or available for the chat UI unless the WSGI app is modified.

---

## Table Stakes

Features the chat UI must have to feel like a real messenger, not a card with bubbles painted on top.

| Feature | Why Expected | Complexity | Backend Dependency | Notes |
| --- | --- | --- | --- | --- |
| Right-aligned user message bubble | Messenger-standard: user text = right, right-to-left visual reading direction | Low | None — text is in the DOM before the POST fires | Bubble text is the raw textarea value captured at submit time |
| Left-aligned bot reply bubble containing full analysis | Counterpart to user bubble; single structured bubble per analysis | Low-Med | Reads `risk_tier`, `summary`, `top_cues`, `recommendations` from existing response | Replaces the result-card template; must contain all the card's semantic content |
| Risk tier badge inside bot bubble | Non-negotiable visual anchor — `benign`/`suspicious`/`high-risk` with color coding | Low | `risk_tier` field (existing) | Re-use existing `.risk-pill` color logic via `data-risk-tier` attribute |
| Vietnamese verdict text | Bilingual requirement from PROJECT.md — primary language is Vietnamese | Low | `summary` field from existing response (English) — may need a static VI mapping or the summary must be localised at model layer | If backend keeps English summary, the UI needs a static tier→Vietnamese-verdict map as fallback |
| Grounded cues list inside bot bubble | Core explainability feature; users need to see why | Low | `top_cues` array (existing, max 3 items each with `span`+`reason`) | Quoted span + reason; same content as existing `<ul id="result-cues">` |
| Safe next steps list inside bot bubble | Actionability is part of the existing design contract | Low | `recommendations` array (existing, max 3 strings) | Same content as existing `<ul id="result-recommendations">` |
| Typing / loading indicator in bot position | Without this the UI freezes silently during inference — inference on CPU can take 5-30s | Low | None — purely presentational, driven by fetch lifecycle | Show on submit, hide when response arrives; animated dots or pulsing bubble |
| Scroll-to-bottom on new message | Standard messenger behavior; without it old messages obscure new ones as thread grows | Low | None — pure DOM/scroll logic | `scrollIntoView({behavior: "smooth"})` on each appended message; must not fight manual scroll |
| Single-line input bar replacing textarea | Chat UIs use a compact input bar, not a 12-row textarea | Low-Med | None | Must expand vertically for multi-line paste (e.g., `contenteditable` div or `textarea` with `rows=1` and `max-height`) |
| Channel selector embedded in input bar | Existing channel context is required by the API (`channel` field); must not disappear in new layout | Low | `channel` field in POST body (existing) | Compact inline `<select>` or pill-style toggle beside the send button |
| Send on Enter / Ctrl+Enter | Existing keyboard shortcut; users expect it in a chat context | Low | None | Keep existing `keydown` handler logic; decide whether bare Enter sends or inserts newline |
| "Try sample" equivalent as a pre-fill action | Existing `#sample-button` functionality must survive layout change | Low | None | In chat context, becomes a "paste sample" action that pre-fills the input bar and optionally auto-submits |
| Disabled state during pending request | Existing `setBusyState()` pattern; prevents double-submit | Low | None — already implemented | Extend to input bar disable + send button spinner |
| Error message in chat thread | Backend errors (`503`, `400`) must appear as a bot message, not a page-level alert | Low | Existing `{error: {message, steps}}` shape | Left-aligned error bubble with distinct styling; same `steps` list rendered inline |
| Session history within page lifetime | Messages persist in the DOM for the duration of the browser tab; no backend required | Low | None — in-memory JS array or DOM-only | Reload clears history; this is intentional and appropriate for a privacy-first local demo |

---

## Differentiators

Features that make the demo feel polished and reinforce the phishing-checker context without expanding scope.

| Feature | Value Proposition | Complexity | Backend Dependency | Notes |
| --- | --- | --- | --- | --- |
| Collapsible detail sections inside bot bubble | Verdict + tier are shown by default; grounded cues and next steps behind a "Show details" toggle | Low | None | Reduces initial visual noise; user opens detail on demand; `<details>`/`<summary>` HTML elements with no JS needed |
| Timestamp on each bubble | Adds authenticity and allows users to track when analyses occurred within a session | Low | None — `new Date()` at message append time | HH:MM format is sufficient; date only if crossing midnight |
| Bot identity label ("PhishGuard" or similar) | Left-aligned bubbles get a small avatar or label to reinforce it's the local model speaking | Low | None | Static label; optionally show `backend_name` value from response as subtitle |
| Clear thread button | Lets user start fresh without reloading the page | Low | None | Clears the message array and DOM; resets input bar; no backend call |
| Smooth bubble entrance animation | Bubbles slide in from the appropriate side on append; reinforces chat metaphor | Low | None | CSS `@keyframes` only; 150-200ms; must be `prefers-reduced-motion` safe |
| Provisional result indicator | `provisional: true` flag from response signals the result is a heuristic, not a full model analysis | Low | `provisional` field (existing) | Small inline badge or footnote inside bot bubble; communicates uncertainty honestly |
| Backend name disclosure | Shows which backend produced the analysis (`heuristic`, `gguf`, etc.) | Low | `backend_name` field (existing) | Already shown in existing card; move into bot bubble footer |
| Input character count or paste-size warning | If user pastes a very long message, warn before sending (the backend has no documented max; long prompts slow CPU inference) | Low | None — client-side only | Soft warning at e.g. 1,000 characters; not a hard block |

---

## Anti-Features

Features to explicitly avoid in this scope because they add complexity disproportionate to a local single-page demo.

| Anti-Feature | Why Avoid | What to Do Instead | Complexity Cost if Included |
| --- | --- | --- | --- |
| WebSocket or SSE for streaming output | Backend is synchronous WSGI (`wsgiref.simple_server`); adding streaming requires rewriting the server, not just the UI | Show typing indicator for full round-trip latency | High — requires async server (ASGI), protocol change, token-by-token rendering logic |
| Multi-session or persistent chat history across reloads | No backend session; adding `localStorage` persistence adds edge cases (stale data, privacy surface) for a demo app | In-memory tab-lifetime history only | Low-Medium — mostly risk: users may paste sensitive text that persists across sessions, violating privacy promise |
| Markdown rendering in bot bubbles | The API returns plain strings; adding a Markdown parser (marked.js, etc.) adds a dependency and risks XSS if not sandboxed | Use DOM text nodes everywhere (`textContent`, not `innerHTML`) | Medium — sanitization requirement; dependency footprint |
| User identity / profile / avatar | This is a single-user local tool; identity is meaningless | Static "You" label on right bubbles if needed | Low complexity, zero value |
| Message editing or deletion | Stateless chat: each analyze call is independent; editing a past message has no effect on the backend record | Allow re-submission by sending a new message | Medium — complex DOM state tracking |
| Reaction / emoji support | No value in a security-tool demo context | None needed | Low complexity, zero value |
| File or image upload in input bar | Strict text-only v1 scope; backend rejects non-text; would require UI upload handling, MIME validation, and user confusion | Keep input as text-only; surface "text only" note near input | Medium — file API, MIME checks, UX for unsupported files |
| Auto-scroll lock detect (pause scroll when user scrolls up) | Standard in messaging apps; significant JS complexity for a demo with short sessions | Simple scroll-to-bottom on every new message; demo sessions are short | Medium — IntersectionObserver logic, scroll state machine |
| Typing characters sent to backend in real time (live analysis) | Sends incomplete fragments; spams the CPU-bound local model; backend has no debounce or partial-text contract | Analyze only on explicit submit | High — debounce, partial-text UX, server-side rate limiting |

---

## Feature Dependencies

```text
Input bar (single-line, expandable)
  -> Channel selector embedded in bar  (channel field in POST body)
  -> Send / Ctrl+Enter handler
  -> Disabled state during pending request

Submit action
  -> Append user bubble (right-aligned, input text)
  -> Append typing indicator (left-aligned)
  -> POST /api/analyze {text, channel}
  -> On success: remove typing indicator, append bot bubble
  -> On error:   remove typing indicator, append error bubble
  -> Scroll-to-bottom after each append
  -> Re-enable input bar

Bot bubble content depends on existing API fields:
  risk_tier       -> risk tier badge (color-coded)
  summary         -> verdict text (+ Vietnamese mapping if needed)
  top_cues        -> grounded cues list (span + reason, max 3)
  recommendations -> safe next steps list (max 3)
  provisional     -> provisional badge (optional differentiator)
  backend_name    -> backend footnote (optional differentiator)

"Try sample" button
  -> Pre-fills input bar text
  -> Sets channel selector to "sms"
  -> Optionally auto-submits (auto-submit is cleaner in chat context)

Clear thread button
  -> Clears DOM message list
  -> Resets JS message array
  -> No backend call
```

---

## MVP Recommendation

Prioritize in order:

1. Right-aligned user bubble + left-aligned bot reply bubble with all analysis fields (risk tier, summary, cues, steps) — this is the entire visible value of the milestone
2. Typing indicator — without it the UI feels broken during 5-30s CPU inference
3. Scroll-to-bottom — without it the user cannot see new messages without manual scroll
4. Single-line input bar with channel selector embedded and send button
5. Error messages as chat bubbles (not page alerts) — preserves UX consistency
6. Disabled state during request — prevents double-submit

Defer to differentiator pass:

- Collapsible detail sections (`<details>`) — useful but not blocking
- Timestamps — cosmetic, add in the same CSS/HTML pass as bubble styling
- Clear thread button — simple, add last before QA
- Smooth entrance animations — CSS-only, add after functional pass is stable

---

## Scope Creep Warnings

1. Streaming temptation: the typing indicator may prompt requests to "stream tokens as they arrive." The backend is synchronous WSGI; streaming requires a server rewrite. Hold the line.
2. localStorage persistence: privacy-first framing means in-memory only. If localStorage is added for convenience, sensitive text pastes persist across sessions.
3. Markdown in bubbles: model output is plain strings. Do not introduce a Markdown parser; it adds a dependency and `innerHTML` XSS surface.
4. Multi-turn conversation illusion: this is not a conversational AI. Each message is an independent analysis request. Do not add context-chaining or thread-level state sent to the backend.
5. Channel selector evolution: the existing backend accepts exactly six channel values. Do not add UI channels that the backend cannot receive — validation will reject them.
