# Technology Stack: Chat Bubble UI Revamp (v2.0)

**Project:** VN Phishing Detection Demo — bilingual chat-bubble UI
**Milestone:** v2.0 Chat UI Revamp
**Researched:** 2026-06-08
**Scope:** Additions and changes ONLY for the new chat UI. Backend (Python wsgiref WSGI, POST /api/analyze) is unchanged.

---

## Executive Recommendation

Stay 100% vanilla HTML/CSS/JS with exactly two CDN additions:

1. **Be Vietnam Pro** from Google Fonts — a font built specifically for Vietnamese diacritics.
2. **marked.js + DOMPurify** — only if the bot bubble ever renders markdown; skip entirely if output stays plain-text strings.

The existing API contract (`AnalysisResult`) returns plain-text strings (`summary`, `recommendations[]`, `top_cues[].reason`). As of the code audit on 2026-06-08, none of those fields contain markdown. **Recommendation: do not add marked.js in the initial revamp.** Add it only if a future backend change produces markdown-formatted text, and add DOMPurify alongside it when you do.

---

## Stack Changes Table

| Layer | Current | Change | Justification | Confidence |
| --- | --- | --- | --- | --- |
| Font | Segoe UI Variable Display / Bahnschrift (Windows system stack) | Add Be Vietnam Pro via Google Fonts CDN | System fonts do not guarantee correct Vietnamese diacritic stacking on non-Windows hosts | HIGH |
| CSS reset | `box-sizing: border-box` only | No change needed | Existing reset is sufficient; a full Normalize.css adds ~7 KB with no benefit here | HIGH |
| JS dependency | None (vanilla) | None for initial revamp; marked.js + DOMPurify as opt-in later | API output is plain text; markdown rendering is not justified yet | HIGH |
| Build step | None | None | Constraint is unchanged; all additions must be zero-build CDN links or inline code | HIGH |
| Backend | Python wsgiref, POST /api/analyze | No change | API contract (`AnalysisResult`) is stable and already serves the needed structured fields | HIGH |

---

## Font: Be Vietnam Pro

**Why this font, not a system font stack.**

The existing CSS declares `"Segoe UI Variable Display", "Bahnschrift", "Trebuchet MS", sans-serif`. All three are Windows-only fonts. On macOS/Linux the browser falls back to the generic `sans-serif`, which is typically Helvetica or Liberation Sans. Neither was designed with Vietnamese diacritics in mind and both can produce collisions between stacked tone marks (e.g., the circumflex-plus-grave stack in `ầ`) and the descenders or ascenders of adjacent lines at typical chat-bubble font sizes (14–16 px).

Vietnamese diacritics stack two combining marks on a single vowel (a base circumflex/horn, then a tone mark above). The Vietnamese Typography resource confirms that many Western typefaces neglect the specific vertical spacing requirements, causing stacked diacritics to collide with the line above at line-height values below ~1.65.

Be Vietnam Pro is a Neo Grotesk typeface explicitly designed for Vietnamese letterforms, with diacritic-adaptive ascender metrics and optimized diacritical spacing. It ships 9 weights plus italics and supports the full Vietnamese Unicode subset. It is available on Google Fonts at no cost and loads via a single CDN `<link>` with no build step.

**Subset strategy.** Request only `vietnamese` and `latin` subsets, and only the weights used in the UI (400 regular, 600 semibold, 700 bold). Google Fonts serves the minimum WOFF2 bytes for the declared subsets.

**Google Fonts CDN embed (copy-paste ready):**

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;600;700&display=swap" rel="stylesheet">
```

Note: the `subset=vietnamese` parameter is not needed in the URL — Google Fonts automatically serves Vietnamese glyphs when the text on the page requires them (unicode-range subsetting is handled server-side). The `display=swap` ensures text is visible during font load.

**CSS change in demo.css:**

Replace the body `font-family` declaration:

```css
/* Before */
font-family: "Segoe UI Variable Display", "Bahnschrift", "Trebuchet MS", sans-serif;

/* After */
font-family: "Be Vietnam Pro", "Segoe UI Variable Display", system-ui, sans-serif;
```

The legacy Windows fonts stay as fallbacks for the offline edge case where Google Fonts is unavailable (e.g., a machine with no internet but the demo running).

**Line-height requirement for Vietnamese.** Chat bubbles displaying Vietnamese text MUST use `line-height: 1.65` or higher. The current CSS already sets `line-height: 1.65` on the `textarea` and `1.7` on the lede paragraph — carry that value into the new `.bubble` class. Do not drop below `1.6` for any Vietnamese-content element.

**Sources:**

- [Be Vietnam Pro — Google Fonts](https://fonts.google.com/specimen/Be+Vietnam+Pro)
- [Vietnamese Typography — Design Challenges](https://vietnamesetypography.com/design-challenges/)
- [Stacked diacritical marks and line spacing — TypeDrawers](https://typedrawers.com/discussion/2274/stacked-diacritical-marks-and-line-spacing)

---

## CSS Reset: No Change Needed

The existing `* { box-sizing: border-box; }` is the only reset in demo.css. This is correct for a small, self-contained UI. Adding Normalize.css (~7 KB minified) or a CSS Reset stylesheet would:

- Add a network round-trip with no functional benefit (the existing CSS already overrides all relevant browser defaults).
- Risk overriding the custom focus ring and border-radius patterns already in place.

**Verdict: keep the single-property reset as-is.**

---

## JS Libraries: Conditional Decision Tree

### marked.js — Do Not Add for v2.0 Initial Revamp

The API contract (`AnalysisResult`) declares all output fields as plain Python `str` or `list[str]`. Code inspection of `contracts.py` confirms:

- `summary: str` — plain text
- `recommendations: list[RecommendationText]` — plain text items
- `top_cues: list[SuspiciousCue]` with `.span: str` and `.reason: str` — plain text

There is no markdown in the output today. Rendering plain text through a markdown parser adds ~47 KB (minified UMD, v16.x), requires a separate DOMPurify pass (~20 KB), and introduces `innerHTML` writes to the DOM where `textContent` is currently safe.

**Decision: skip marked.js in the initial revamp. Revisit if the backend starts returning markdown in any field.**

### marked.js — How to Add It Safely If Needed Later

When (and only when) a backend field is confirmed to return markdown:

```html
<!-- Load both together; marked without DOMPurify is an XSS risk -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/16.3.0/lib/marked.umd.min.js"
        integrity="sha512-..." crossorigin="anonymous" defer></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.2.7/purify.min.js"
        integrity="sha512-..." crossorigin="anonymous" defer></script>
```

Usage pattern (never use `innerHTML` with raw marked output):

```js
function safeMarkdown(mdString) {
  const rawHtml = marked.parse(mdString);
  return DOMPurify.sanitize(rawHtml);
}

// Then:
bubbleElement.innerHTML = safeMarkdown(result.summary);
```

- marked.js v16.3.0 does not have a built-in `sanitize` option (removed in earlier v1 cycle). DOMPurify is mandatory alongside it.
- Pin to explicit versions (`16.3.0`, `3.2.7`) rather than `@latest` to avoid silent breaking changes in a no-build environment.
- Fetch SRI hashes from [cdnjs](https://cdnjs.com/libraries/marked) at pin time; the integrity attribute values shown above are placeholders.

**Sources:**

- [marked.js documentation](https://marked.js.org/)
- [marked — cdnjs (v16.3.0)](https://cdnjs.com/libraries/marked)
- [DOMPurify — cdnjs (v3.2.7)](https://cdnjs.com/libraries/dompurify)
- [marked sanitize option discussion](https://github.com/markedjs/marked/discussions/1232)

---

## Vietnamese Encoding: No Special Handling Required

All modern browsers handle UTF-8 Vietnamese natively. The existing `<meta charset="utf-8">` in `index.html` is sufficient. There is no need for:

- Any `Content-Type` header change (wsgiref already sends `text/html; charset=utf-8` by default for static files).
- JavaScript encoding/decoding helpers.
- Separate font files for diacritics (Unicode subsetting via the Google Fonts CDN handles this automatically).

The one active risk is **clipboard paste of Vietnamese text** from SMS/Zalo apps that use precomposed vs decomposed NFC forms. The existing `normalize_text()` call in `service.py` handles normalization before analysis; the UI does not need additional JS normalization for display.

---

## CSS: Key Properties for Chat Bubble Layout

These are not new dependencies — they are vanilla CSS patterns. Documenting them here as the integration points for the implementation phase:

```css
/* Chat thread container */
.chat-thread {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  padding: 16px;
}

/* Bubble base */
.bubble {
  max-width: 75%;
  padding: 12px 16px;
  border-radius: 18px;
  line-height: 1.65;          /* Required minimum for Vietnamese stacked diacritics */
  overflow-wrap: break-word;  /* Handles long URLs and Vietnamese compounds */
  word-break: break-word;     /* Fallback for older browsers */
}

/* User message — right-aligned */
.bubble--user {
  align-self: flex-end;
  background: /* accent color */;
  color: #fff;
  border-bottom-right-radius: 4px;  /* Tail shape */
}

/* Bot message — left-aligned */
.bubble--bot {
  align-self: flex-start;
  background: /* panel color */;
  border-bottom-left-radius: 4px;   /* Tail shape */
}
```

`overflow-wrap: break-word` is critical for chat bubbles: it prevents long unbroken strings (URLs, bank account numbers common in phishing messages) from breaking the bubble layout, while allowing Vietnamese words to wrap naturally at their soft-wrap boundaries.

---

## What NOT to Add

| Candidate | Verdict | Reason |
| --- | --- | --- |
| React / Vue / Svelte | No | Build step required; out of scope |
| Tailwind CSS | No | Build step required; out of scope |
| Normalize.css / CSS Reset | No | No functional benefit; existing reset is adequate |
| Bootstrap / UIkit | No | Heavyweight; chat bubble is 40–60 lines of custom CSS |
| Socket.IO / WebSockets | No | POST /api/analyze is request-response; no streaming needed |
| DOMPurify (now) | No | Only needed if marked.js is added; currently unnecessary |
| marked.js (now) | No | API returns plain text; no markdown in contract |
| Bunny Fonts (privacy-first CDN) | Optional | If offline-first privacy matters more than convenience, self-host Be Vietnam Pro WOFF2. Not required for a local demo. |
| `@import` in CSS for Google Fonts | No | Use `<link>` in HTML; CSS `@import` blocks rendering |

---

## Integration Points with Existing WSGI Server

The existing `demo.py` serves static files from `demo_assets/` under `/static/`. No backend change is needed:

- The new `<link>` tags for Google Fonts go in `index.html` `<head>`.
- The `demo.css` font-family change is a one-line edit.
- The chat UI JavaScript replaces the `form.addEventListener("submit", analyzeMessage)` call pattern but keeps `fetch("/api/analyze", { method: "POST", ... })` unchanged.
- No new Python dependencies, no new routes, no WSGI middleware changes.

---

## Summary of Additions

| Asset | CDN URL | Size (approx) | When |
| --- | --- | --- | --- |
| Be Vietnam Pro (3 weights) | `fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;600;700&display=swap` | ~30–45 KB WOFF2 (Vietnamese+Latin subset) | Immediately in v2.0 |
| marked.js v16.3.0 (UMD min) | `cdnjs.cloudflare.com/ajax/libs/marked/16.3.0/lib/marked.umd.min.js` | ~47 KB | Only if API returns markdown |
| DOMPurify v3.2.7 (min) | `cdnjs.cloudflare.com/ajax/libs/dompurify/3.2.7/purify.min.js` | ~20 KB | Always paired with marked.js |

Total immediate addition: ~35–45 KB (font only). Total if markdown is added later: ~100 KB.
