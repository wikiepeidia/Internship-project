# Phase 15: i18n.js + demo.py Static Route — Research

**Researched:** 2026-06-09
**Domain:** Vanilla JS i18n module, Python WSGI static file serving, DOM string injection
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- `window.I18N = { ... }` global assignment — no ES module system; works with a synchronous `<script src="/static/i18n.js">` in `<head>` before `demo.js`.
- Flat namespaced keys: `I18N.PLACEHOLDER`, `I18N.SEND_BTN`, `I18N.CHANNEL_UNKNOWN`, `I18N.RISK_HIGH`, etc. — direct access, no deep nesting.
- Script placed in `<head>` after CSS links, before `demo.js`, no `defer` — synchronous load guarantees `I18N` is available at DOMContentLoaded.
- `demo.py` gets one new `elif path == "/static/i18n.js"` branch using the existing `_load_asset` + `_text_response` pattern — zero new abstractions.
- Welcome bubble structure stays in static HTML (`role="log"` ARIA live region must exist at page load per Phase 14 rules).
- Welcome bubble text nodes use `data-i18n` attributes; a small inline `<script>` or DOMContentLoaded block in `index.html` replaces `textContent` from `I18N` keys — achieving zero literal visible strings while keeping the structural HTML intact for screen readers.
- All other visible strings also extracted via the same `data-i18n` + JS-inject pattern.
- **Page/header**: page `<title>`, eyebrow, `<h1>`, status chips, section `aria-label`s.
- **Composer**: textarea `placeholder`, send button label, "Kênh" channel field label.
- **Channel options**: all 5 values — "Không rõ", "SMS", "Zalo", "Messenger", "Telegram" (Telegram key defined even if not yet default).
- **Welcome bubble**: assistant name chip, welcome text, hint-row chip labels.
- **Error messages**: fetch error, abort/cancelled, validation error — defined now for Phase 16 reuse.
- **Bot reply labels**: risk tier display strings ("Nguy hiểm cao (High risk)", etc.), verdict label, cues label, steps label — defined now for Phase 16.
- **Aria-labels**: thread, form, channel selector — injected via JS to stay consistent with zero-literals rule.
- Vietnamese primary for all user-facing labels; English technical terms in parentheses.

### Claude's Discretion

- Exact key name casing and prefix conventions (e.g., `RISK_HIGH` vs `RISK_TIER_HIGH`).
- Whether to use a single inline `<script>` block for the i18n injection or a tiny `applyI18n()` function — keep it under ~20 lines.

### Deferred Ideas (OUT OF SCOPE)

- Dynamic language switching (toggle VI/EN at runtime).
- Loading i18n from an external URL or CDN.
- Pluralization or template interpolation in i18n strings.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| I18N-01 | UI labels, input placeholders, bot reply text, and error messages are Vietnamese primary with English technical terms in parentheses | Full string inventory below covers every visible text node; key format documented |
| I18N-02 | All bilingual strings are managed via a dedicated `i18n.js` file served by the demo server; strings are not hardcoded in HTML | demo.py static route pattern confirmed; `data-i18n` injection pattern documented; test update required |
| INFRA-02 | `demo.py` serves `i18n.js` as a static file; all other backend routes and the POST /api/analyze contract remain unchanged | Exact 3-line `elif` branch pattern extracted from live code; no abstractions needed |

</phase_requirements>

---

## Summary

Phase 15 is a focused two-file creation plus two-file modification task. It creates `src/runtime/demo_assets/i18n.js` (a plain JS file assigning `window.I18N`), adds one route branch to `demo.py`, and updates `index.html` to load `i18n.js` and replace all hardcoded strings with `data-i18n` attribute markers plus a DOMContentLoaded injection step. `demo.js` is not changed by Phase 15, but `demo.js` currently contains hardcoded English strings that Phase 15's `I18N` keys must cover for Phase 16 to consume.

The WSGI routing pattern is already established and fully understood from reading `demo.py` — the new `elif` branch follows the exact same 1-line pattern as the existing `demo.css` and `demo.js` routes. No new Python abstractions are needed.

The primary technical concern is the `data-i18n` injection strategy: the injection block must execute before `demo.js` (which is `defer`'ed and therefore runs at DOMContentLoaded), but `<head>` placement of `i18n.js` without `defer` guarantees `window.I18N` is defined synchronously. The DOMContentLoaded injection then runs in document order ahead of the deferred `demo.js` script.

A secondary concern is a **breaking test**: `test_demo_index_serves_text_only_form` currently asserts the literal string `"Mình sẽ giúp bạn kiểm tra dấu hiệu lừa đảo tài chính."` is present in the HTML body. Phase 15 removes that literal string from HTML and replaces it with a `data-i18n` attribute. The test must be updated to assert `data-i18n="WELCOME_TEXT"` (or equivalent key) in HTML instead.

**Primary recommendation:** Create `i18n.js` as a plain assignment file, add 3 lines to `demo.py`, update `index.html` with `data-i18n` attributes and a ~15-line DOMContentLoaded injection block, and update the one affected test assertion.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| String storage | Static file (i18n.js) | — | Strings are a static asset served like CSS/JS |
| String serving | Backend (demo.py) | — | WSGI static route — same pattern as demo.css and demo.js |
| String injection into DOM | Browser/Client (inline script) | — | DOMContentLoaded replaces textContent from `window.I18N` |
| ARIA label injection | Browser/Client (inline script) | — | `setAttribute("aria-label", ...)` alongside textContent injection |
| Phase 16 runtime label access | Browser/Client (demo.js) | — | `window.I18N` global available synchronously at any point after `<head>` parse |

---

## Standard Stack

### Core — No new packages

This phase uses no external packages. All capabilities are delivered with:
- Python 3.x standard library (`pathlib`, `wsgiref`) — already in use [VERIFIED: existing demo.py]
- Vanilla JavaScript (no framework, no build step) — locked hard constraint from STATE.md [VERIFIED: codebase]
- HTML `data-*` attributes (standard DOM API) [VERIFIED: MDN / WHATWG]

### No package legitimacy audit required

No external packages are installed. The Package Legitimacy Gate is not applicable for this phase.

---

## Architecture Patterns

### System Architecture Diagram

```
Browser (page load)
  └─> GET /                  →  demo.py  →  _load_asset("index.html")
  └─> GET /static/demo.css   →  demo.py  →  _load_asset("demo.css")
  └─> GET /static/i18n.js    →  demo.py  →  _load_asset("i18n.js")   [NEW]
  └─> GET /static/demo.js    →  demo.py  →  _load_asset("demo.js")

Browser (parse <head>)
  i18n.js (sync, no defer)
    └─> window.I18N = { KEY: "value", ... }   [defines global]

Browser (DOMContentLoaded, before deferred demo.js)
  inline applyI18n() block in <body>
    └─> querySelectorAll('[data-i18n]')
          └─> el.textContent = I18N[el.dataset.i18n]
    └─> setAttribute aria-label on structural elements

Browser (DOMContentLoaded, deferred demo.js fires)
  └─> window.I18N.RISK_HIGH etc. available for Phase 16
```

### Recommended File Layout (changed/created files only)

```
src/runtime/
├── demo.py                  # +3 lines: elif /static/i18n.js branch
└── demo_assets/
    ├── i18n.js              # NEW: window.I18N = { ... }
    └── index.html           # updated: data-i18n attrs + injection block

tests/runtime/
└── test_demo.py             # updated: 1 test assertion + 1 new test
```

### Pattern 1: WSGI Static Route (existing — replicate exactly)

**What:** Each static file has a dedicated `if/elif` branch in `DemoApp.__call__`. The branch pattern is identical for all static files.
**When to use:** Any new static asset served from `demo_assets/`.

```python
# Source: src/runtime/demo.py (lines 62-65, verified from codebase)
# Existing pattern for demo.css:
if method == "GET" and path == "/static/demo.css":
    return _text_response(start_response, "200 OK", "text/css; charset=utf-8", _load_asset("demo.css"))
# Existing pattern for demo.js:
if method == "GET" and path == "/static/demo.js":
    return _text_response(start_response, "200 OK", "application/javascript; charset=utf-8", _load_asset("demo.js"))

# New branch for i18n.js — same pattern, one elif:
elif method == "GET" and path == "/static/i18n.js":
    return _text_response(start_response, "200 OK", "application/javascript; charset=utf-8", _load_asset("i18n.js"))
```

[VERIFIED: codebase — exact lines read from demo.py]

### Pattern 2: window.I18N Global Assignment

**What:** A single `window.I18N = { KEY: "string value" }` assignment. No class, no factory, no ES module. The file is self-contained.
**When to use:** Whenever a JS file needs to define a browser global without a module system.

```javascript
// Source: [ASSUMED] — pattern consistent with legacy browser globals
// No framework, no import/export — synchronous execution in <head>
window.I18N = {
  // Page
  PAGE_TITLE: "VN Phishing Detection Demo",
  EYEBROW: "VN Phishing Detection",
  H1: "Kiểm tra tin nhắn đáng ngờ",

  // ... all keys
};
```

### Pattern 3: data-i18n DOM Injection (DOMContentLoaded)

**What:** A short loop runs at DOMContentLoaded and replaces `textContent` of every element with a `data-i18n` attribute. ARIA labels are set separately via `setAttribute`.
**When to use:** Any static HTML element whose visible text should come from `I18N`.

```javascript
// Source: [ASSUMED] — standard data-attribute injection pattern, no library needed
// Placed as an inline <script> at bottom of <body>, before </body>
document.addEventListener("DOMContentLoaded", function applyI18n() {
  document.querySelectorAll("[data-i18n]").forEach(function(el) {
    var key = el.dataset.i18n;
    if (window.I18N && window.I18N[key] !== undefined) {
      el.textContent = window.I18N[key];
    }
  });
  // Aria-label injections (elements that hold no text node)
  var thread = document.getElementById("result-panel");
  if (thread) thread.setAttribute("aria-label", window.I18N.THREAD_ARIA);
  var form = document.getElementById("analysis-form");
  if (form) form.setAttribute("aria-label", window.I18N.FORM_ARIA);
});
```

**Note:** Because `i18n.js` is loaded synchronously in `<head>` (no `defer`), `window.I18N` is guaranteed defined before `DOMContentLoaded` fires. The `defer`'d `demo.js` also runs at DOMContentLoaded but scripts within the same document fire in source order — the inline block above will fire first if placed before the `<script defer>` tag.

### Pattern 4: `<title>` and placeholder injection

`<title>` and `placeholder` cannot use `textContent` assignment. They need special handling:

```javascript
// <title>: assign via document.title
document.title = window.I18N.PAGE_TITLE;

// placeholder: assign via setAttribute
var textarea = document.getElementById("message-input");
if (textarea) textarea.setAttribute("placeholder", window.I18N.PLACEHOLDER);

// <select><option> text nodes: can use textContent on each <option>
// Option value attributes (value="unknown") remain unchanged — they are API parameters not UI strings
```

[ASSUMED] — standard DOM API, no verification needed, but worth noting as a non-obvious case.

### Anti-Patterns to Avoid

- **Using `innerHTML` instead of `textContent`:** Never use `innerHTML` for i18n string injection. `textContent` prevents XSS and is sufficient since strings contain no markup. [ASSUMED]
- **Applying `defer` to i18n.js:** If `i18n.js` is `defer`'d, `window.I18N` will be undefined when `demo.js` tries to access it. Keep `i18n.js` synchronous (no `defer`, no `async`). [VERIFIED: CONTEXT.md — locked decision]
- **Putting i18n.js after demo.js in `<head>`:** Load order matters. `i18n.js` must appear before `demo.js`. [VERIFIED: CONTEXT.md]
- **Changing option `value` attributes for channels:** The `value` attributes (`"unknown"`, `"sms"`, etc.) are API parameters sent to `POST /api/analyze`. Only the visible text node inside `<option>` is a UI string. [VERIFIED: codebase — contracts.py uses these values]
- **Removing the welcome bubble's structural HTML:** The `<article class="message message--welcome">` and its `role="log"` ancestor must remain in static HTML. Only text nodes are replaced. [VERIFIED: CONTEXT.md and STATE.md ARIA live region constraint]
- **Using `textContent` on the `<template>` element itself:** `<template>` content is inert (not rendered). The `data-i18n` injection loop runs on the live document — it will NOT see elements inside `<template>`. Template strings must be injected by `demo.js` in Phase 16 using `I18N` keys directly.

---

## Complete String Inventory

This is the exhaustive list of all hardcoded strings found in `index.html` and `demo.js`, with the proposed `I18N` key and recommended Vietnamese/bilingual value.

### Strings currently in index.html (visible or as attributes)

| Element / Attribute | Current Literal Value | Proposed I18N Key | Bilingual Value |
|---------------------|----------------------|-------------------|-----------------|
| `<title>` | `VN Phishing Detection Demo` | `PAGE_TITLE` | `"VN Phishing Detection Demo"` |
| `<main aria-label>` | `VN Phishing Detection Demo` | `MAIN_ARIA` | `"VN Phishing Detection Demo"` |
| `.eyebrow` text | `VN Phishing Detection` | `EYEBROW` | `"VN Phishing Detection"` |
| `<h1>` text | `Kiểm tra tin nhắn đáng ngờ` | `H1` | `"Kiểm tra tin nhắn đáng ngờ"` |
| `.status-strip aria-label` | `Trạng thái an toàn` | `STATUS_STRIP_ARIA` | `"Trạng thái an toàn"` |
| `.status-strip span[0]` | `Local-first` | `STATUS_LOCAL_FIRST` | `"Local-first"` |
| `.status-strip span[1]` | `Text-only` | `STATUS_TEXT_ONLY` | `"Text-only"` |
| `.chat-frame aria-label` | `Cuộc trò chuyện kiểm tra lừa đảo` | `CHAT_SECTION_ARIA` | `"Cuộc trò chuyện kiểm tra lừa đảo"` |
| `#result-panel aria-label` | `Kết quả phân tích` | `THREAD_ARIA` | `"Kết quả phân tích"` |
| welcome `.message__meta` | `Trợ lý kiểm tra` | `WELCOME_ASSISTANT_NAME` | `"Trợ lý kiểm tra"` |
| welcome `.message__text` | `Mình sẽ giúp bạn kiểm tra dấu hiệu lừa đảo tài chính.` | `WELCOME_TEXT` | `"Mình sẽ giúp bạn kiểm tra dấu hiệu lừa đảo tài chính."` |
| `.hint-row aria-label` | `Gợi ý phạm vi` | `HINT_ROW_ARIA` | `"Gợi ý phạm vi"` |
| hint span SMS | `SMS` | `HINT_SMS` | `"SMS"` |
| hint span Zalo | `Zalo` | `HINT_ZALO` | `"Zalo"` |
| hint span Messenger | `Messenger` | `HINT_MESSENGER` | `"Messenger"` |
| hint span no-cloud | `Không gửi dữ liệu lên cloud` | `HINT_NO_CLOUD` | `"Không gửi dữ liệu lên cloud"` |
| `#analysis-form aria-label` | `Gửi tin nhắn để phân tích` | `FORM_ARIA` | `"Gửi tin nhắn để phân tích"` |
| `<label for="message-input">` | `Tin nhắn hoặc đoạn hội thoại đáng ngờ` | `INPUT_LABEL` | `"Tin nhắn hoặc đoạn hội thoại đáng ngờ"` |
| textarea `placeholder` | `Dán nội dung cần kiểm tra. Ví dụ: VPBank cảnh báo...` | `PLACEHOLDER` | `"Dán nội dung cần kiểm tra. Ví dụ: VPBank cảnh báo tài khoản của bạn sẽ bị khóa trong 24h..."` |
| channel label `<span>` | `Kênh` | `CHANNEL_LABEL` | `"Kênh"` |
| `<option value="unknown">` text | `Không rõ` | `CHANNEL_UNKNOWN` | `"Không rõ"` |
| `<option value="sms">` text | `SMS` | `CHANNEL_SMS` | `"SMS"` |
| `<option value="zalo">` text | `Zalo` | `CHANNEL_ZALO` | `"Zalo"` |
| `<option value="messenger">` text | `Messenger` | `CHANNEL_MESSENGER` | `"Messenger"` |
| `<option value="telegram">` text | `Telegram` | `CHANNEL_TELEGRAM` | `"Telegram"` |
| `<option value="facebook">` text | `Facebook` | `CHANNEL_FACEBOOK` | `"Facebook"` |
| `#sample-button` text | `Mẫu thử` | `SAMPLE_BTN` | `"Mẫu thử"` |
| `#analyze-button` text | `Phân tích tại máy` | `ANALYZE_BTN` | `"Phân tích tại máy"` |

### Strings in `<template>` elements (inert — NOT injected by Phase 15 inline block)

These strings are inside `<template>` tags, which are inert DOM. The `querySelectorAll('[data-i18n]')` loop on the live document does NOT reach them. They must be kept as-is in HTML or converted to `data-i18n` attributes for Phase 16's `demo.js` to inject when cloning templates.

**Decision for planner:** The CONTEXT.md zero-literals requirement says "all visible strings." Template content is not visible until cloned. Phase 15 should add `data-i18n` attributes to template elements anyway (so Phase 16 just reads `I18N[el.dataset.i18n]` after `cloneNode`), but Phase 15 does NOT need to inject them — they are invisible at page load.

| Template | Element | Current Text | Proposed Key |
|----------|---------|-------------|-------------|
| `#user-message-template` | `.message__meta` | `Bạn gửi` | `USER_META` |
| `#result-template` | `.message__meta` | `Phân tích cục bộ` | `RESULT_META` |
| `#result-template` | `<dt>` (risk label) | `Nhãn rủi ro` | `RESULT_DT_LABELS` |
| `#result-template` | `<dt>` (backend) | `Backend` | `RESULT_DT_BACKEND` |
| `#result-template` | `<h3>` (cues) | `Dấu hiệu trong tin nhắn` | `CUES_HEADING` |
| `#result-template` | `<h3>` (steps) | `Bước an toàn tiếp theo` | `STEPS_HEADING` |
| `#error-template` | `.message__meta` | `Phản hồi runtime` | `ERROR_META` |
| `#error-template` | `<h3>` (how to fix) | `Cách xử lý` | `ERROR_STEPS_HEADING` |
| `#typing-template` | `.message__meta` | `Đang phân tích` | `TYPING_META` |
| `#typing-template` | `.typing-dots aria-label` | `Đang xử lý` | `TYPING_ARIA` |

### Strings in `demo.js` (not touched by Phase 15, keys defined for Phase 16)

| JS usage | Current English string | Proposed I18N Key | Bilingual Value |
|----------|----------------------|-------------------|----------------|
| `riskTierLabel.benign` | `"Benign"` | `RISK_BENIGN` | `"Thấp / Không phát hiện (Low / No threat detected)"` |
| `riskTierLabel.suspicious` | `"Suspicious"` | `RISK_SUSPICIOUS` | `"Nguy hiểm trung bình (Medium risk)"` |
| `riskTierLabel["high-risk"]` | `"High risk"` | `RISK_HIGH` | `"Nguy hiểm cao (High risk)"` |
| `analyzeButton.textContent` busy | `"Analyzing..."` | `ANALYZE_BTN_BUSY` | `"Đang phân tích..."` |
| `analyzeButton.textContent` idle | `"Analyze locally"` | `ANALYZE_BTN` | `"Phân tích tại máy"` (same as HTML value) |
| `createListItems` empty | `"None"` | `LIST_EMPTY` | `"Không có"` |
| catch block fetch error message | `"The local demo could not reach the runtime service."` | `ERR_NETWORK` | `"Không thể kết nối với runtime cục bộ."` |
| catch block fetch error step | `"Retry after the local runtime finishes loading."` | `ERR_NETWORK_STEP` | `"Thử lại sau khi runtime cục bộ đã tải xong."` |

### Phase 16 bot reply strings (defined now, used in Phase 16)

| Purpose | Proposed I18N Key | Bilingual Value |
|---------|-------------------|-----------------|
| verdict label dt | `RESULT_DT_VERDICT` | `"Kết luận"` |
| risk tier label dt | `RESULT_DT_RISK` | `"Mức độ rủi ro"` |
| cues section heading | `CUES_HEADING` | `"Dấu hiệu trong tin nhắn"` |
| steps section heading | `STEPS_HEADING` | `"Bước an toàn tiếp theo"` |
| error handling heading | `ERROR_STEPS_HEADING` | `"Cách xử lý"` |

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Serving a static JS file | Custom file-streaming handler | The existing `_load_asset` + `_text_response` helpers | Already handles encoding, Content-Length; adding a handler duplicates working code |
| String interpolation in i18n | Template function (fn(data) => ...) | Flat keys with hardcoded bilingual strings | Current string set has no dynamic values; interpolation is a deferred idea per CONTEXT.md |
| Multi-file i18n (per-locale files) | Split VI/EN JSON loaded conditionally | Single `window.I18N` flat object | Dynamic switching is deferred; single file is simpler and loads in one request |

**Key insight:** The existing WSGI routing abstraction (`_load_asset` + `_text_response`) is the correct primitive. A new branch costs 3 lines, not a new abstraction.

---

## Common Pitfalls

### Pitfall 1: Breaking the welcome bubble test assertion

**What goes wrong:** `test_demo_index_serves_text_only_form` line 59 asserts the literal string `"Mình sẽ giúp bạn kiểm tra dấu hiệu lừa đảo tài chính."` is present in the raw HTML. After Phase 15 removes it from the HTML body and replaces with `data-i18n="WELCOME_TEXT"`, this assertion fails.
**Why it happens:** The test asserts the current Phase 14 literal content, not the i18n-compatible content.
**How to avoid:** Update the test assertion to check for `'data-i18n="WELCOME_TEXT"'` in HTML instead of the Vietnamese string. Also add a new test for the `/static/i18n.js` route.
**Warning signs:** `pytest tests/runtime/test_demo.py` fails on `test_demo_index_serves_text_only_form` after the HTML change.

### Pitfall 2: i18n injection block firing after deferred demo.js

**What goes wrong:** If the `applyI18n` DOMContentLoaded listener is placed inside the `<script defer src="/static/demo.js">` tag order logic, it may fire after `demo.js` if `demo.js` also accesses `I18N` on DOMContentLoaded.
**Why it happens:** `defer`'d scripts and inline scripts both fire at DOMContentLoaded, but execution order follows source order.
**How to avoid:** Place the inline `applyI18n` `<script>` block in `<body>` before the `<script defer src="/static/demo.js">` tag. This guarantees the inline block fires first.
**Warning signs:** ARIA labels not applied; some text nodes still showing empty or raw attribute names.

### Pitfall 3: data-i18n on template elements not injected

**What goes wrong:** The `querySelectorAll('[data-i18n]')` loop runs on the live document. Elements inside `<template>` are in a separate `DocumentFragment` (the template's `.content`) and are not part of the live document tree.
**Why it happens:** This is correct browser behavior — `<template>` content is intentionally inert.
**How to avoid:** Do not try to inject template strings in Phase 15. Mark them with `data-i18n` for Phase 16's cloneNode logic to consume, but leave their text content in place so they render correctly when cloned (until Phase 16 updates demo.js).
**Warning signs:** Template strings remain untranslated after clone — that is expected and correct in Phase 15.

### Pitfall 4: option value attributes changed alongside text nodes

**What goes wrong:** The `<option value="unknown">Không rõ</option>` has two parts: the `value` attribute sent to the API, and the visible text node. Only the text node is a UI string. If the `value` attribute is localized (`value="khong-ro"`), the `POST /api/analyze` validation breaks (channel must be one of the `ChannelName` typed literals: `"unknown"`, `"sms"`, etc.).
**Why it happens:** Confusing UI display text with API contract values.
**How to avoid:** Only set `el.textContent` for `<option>` elements — never touch the `value` attribute.
**Warning signs:** API returns 400 "channel must be one of the supported text channels."

### Pitfall 5: `<title>` and `placeholder` ignored by textContent loop

**What goes wrong:** `document.title` is a property, not a text node that `textContent` assignment can reach via `querySelectorAll`. Similarly, `placeholder` is an attribute. The generic `[data-i18n]` loop sets `textContent` — for `<title>` and `<textarea placeholder>`, explicit code is needed.
**Why it happens:** `<title>` is not a rendered element; `placeholder` is an attribute, not a text node.
**How to avoid:** Add explicit lines in the injection block:
  - `document.title = window.I18N.PAGE_TITLE;`
  - `document.getElementById("message-input").setAttribute("placeholder", window.I18N.PLACEHOLDER);`
**Warning signs:** Page tab still shows old title; placeholder still in old language.

### Pitfall 6: `i18n.js` placed with `defer` or `async`

**What goes wrong:** If `i18n.js` loads `defer`'d, `window.I18N` is undefined when any synchronous script (or Phase 16's `demo.js` on DOMContentLoaded) first accesses it.
**Why it happens:** Developer adds `defer` as a reflex to improve apparent load performance.
**How to avoid:** Never add `defer` or `async` to the `<script src="/static/i18n.js">` tag. [VERIFIED: CONTEXT.md — locked decision]
**Warning signs:** JavaScript TypeError "Cannot read properties of undefined (reading 'PLACEHOLDER')" on page load.

---

## Code Examples

### i18n.js structure

```javascript
// Source: [ASSUMED] — standard browser global pattern
// File: src/runtime/demo_assets/i18n.js
window.I18N = {
  // Page
  PAGE_TITLE:          "VN Phishing Detection Demo",
  EYEBROW:             "VN Phishing Detection",
  H1:                  "Kiểm tra tin nhắn đáng ngờ",

  // Status strip
  STATUS_LOCAL_FIRST:  "Local-first",
  STATUS_TEXT_ONLY:    "Text-only",

  // Aria labels (structural)
  MAIN_ARIA:           "VN Phishing Detection Demo",
  STATUS_STRIP_ARIA:   "Trạng thái an toàn",
  CHAT_SECTION_ARIA:   "Cuộc trò chuyện kiểm tra lừa đảo",
  THREAD_ARIA:         "Kết quả phân tích",
  FORM_ARIA:           "Gửi tin nhắn để phân tích",
  HINT_ROW_ARIA:       "Gợi ý phạm vi",

  // Welcome bubble
  WELCOME_ASSISTANT_NAME: "Trợ lý kiểm tra",
  WELCOME_TEXT:           "Mình sẽ giúp bạn kiểm tra dấu hiệu lừa đảo tài chính.",
  HINT_SMS:               "SMS",
  HINT_ZALO:              "Zalo",
  HINT_MESSENGER:         "Messenger",
  HINT_NO_CLOUD:          "Không gửi dữ liệu lên cloud",

  // Composer
  INPUT_LABEL:         "Tin nhắn hoặc đoạn hội thoại đáng ngờ",
  PLACEHOLDER:         "Dán nội dung cần kiểm tra. Ví dụ: VPBank cảnh báo tài khoản của bạn sẽ bị khóa trong 24h...",
  CHANNEL_LABEL:       "Kênh",
  CHANNEL_UNKNOWN:     "Không rõ",
  CHANNEL_SMS:         "SMS",
  CHANNEL_ZALO:        "Zalo",
  CHANNEL_MESSENGER:   "Messenger",
  CHANNEL_TELEGRAM:    "Telegram",
  CHANNEL_FACEBOOK:    "Facebook",
  SAMPLE_BTN:          "Mẫu thử",
  ANALYZE_BTN:         "Phân tích tại máy",
  ANALYZE_BTN_BUSY:    "Đang phân tích...",

  // Risk tiers (for Phase 16 demo.js consumption)
  RISK_HIGH:           "Nguy hiểm cao (High risk)",
  RISK_SUSPICIOUS:     "Nguy hiểm trung bình (Medium risk)",
  RISK_BENIGN:         "Thấp / Không phát hiện (Low / No threat detected)",

  // Result template labels (for Phase 16 cloneNode injection)
  USER_META:           "Bạn gửi",
  RESULT_META:         "Phân tích cục bộ",
  RESULT_DT_LABELS:    "Nhãn rủi ro",
  RESULT_DT_BACKEND:   "Backend",
  CUES_HEADING:        "Dấu hiệu trong tin nhắn",
  STEPS_HEADING:       "Bước an toàn tiếp theo",

  // Error template labels
  ERROR_META:          "Phản hồi runtime",
  ERROR_STEPS_HEADING: "Cách xử lý",
  ERR_NETWORK:         "Không thể kết nối với runtime cục bộ.",
  ERR_NETWORK_STEP:    "Thử lại sau khi runtime cục bộ đã tải xong.",

  // Typing template
  TYPING_META:         "Đang phân tích",
  TYPING_ARIA:         "Đang xử lý",

  // List empty state
  LIST_EMPTY:          "Không có",
};
```

### demo.py — new elif branch (3 lines)

```python
# Source: [VERIFIED: codebase] — replicates existing static route pattern exactly
# Insert after the existing demo.js elif, before the /api/analyze if:
if method == "GET" and path == "/static/i18n.js":
    return _text_response(start_response, "200 OK", "application/javascript; charset=utf-8", _load_asset("i18n.js"))
```

### index.html — updated <head> script order

```html
<!-- Source: [VERIFIED: CONTEXT.md — locked load order] -->
<link rel="stylesheet" href="/static/demo.css">
<script src="/static/i18n.js"></script>  <!-- synchronous, no defer -->
<!-- demo.js is loaded at end of <body> with defer -->
```

### index.html — data-i18n on welcome bubble (visible text nodes only)

```html
<!-- Before (Phase 14): -->
<p class="message__meta">Trợ lý kiểm tra</p>
<p class="message__text">Mình sẽ giúp bạn kiểm tra dấu hiệu lừa đảo tài chính.</p>

<!-- After (Phase 15): -->
<p class="message__meta" data-i18n="WELCOME_ASSISTANT_NAME">Trợ lý kiểm tra</p>
<p class="message__text" data-i18n="WELCOME_TEXT">Mình sẽ giúp bạn kiểm tra dấu hiệu lừa đảo tài chính.</p>
```

Note: keeping the fallback text in place ensures the element is readable even if JS fails, and it keeps the test update minimal (the assertion changes from checking the literal to checking `data-i18n="WELCOME_TEXT"`).

### index.html — injection block (placed before closing </body>)

```html
<!-- Source: [ASSUMED] — standard data-attribute i18n pattern -->
<!-- Place BEFORE <script defer src="/static/demo.js"> -->
<script>
  document.addEventListener("DOMContentLoaded", function applyI18n() {
    if (!window.I18N) return;
    document.title = window.I18N.PAGE_TITLE;
    document.getElementById("message-input")
      .setAttribute("placeholder", window.I18N.PLACEHOLDER);
    document.querySelectorAll("[data-i18n]").forEach(function(el) {
      var key = el.dataset.i18n;
      if (window.I18N[key] !== undefined) {
        el.textContent = window.I18N[key];
      }
    });
    var thread = document.getElementById("result-panel");
    if (thread) thread.setAttribute("aria-label", window.I18N.THREAD_ARIA);
    var form = document.getElementById("analysis-form");
    if (form) form.setAttribute("aria-label", window.I18N.FORM_ARIA);
  });
</script>
<script src="/static/demo.js" defer></script>
```

### test_demo.py — updated and new assertions

```python
# Source: [VERIFIED: codebase] — tests/runtime/test_demo.py existing tests

# CHANGE: In test_demo_index_serves_text_only_form, update line 59:
# OLD (will break after Phase 15):
#   assert "Mình sẽ giúp bạn kiểm tra dấu hiệu lừa đảo tài chính." in html
# NEW:
assert 'data-i18n="WELCOME_TEXT"' in html

# ADD: New test for i18n.js static route
def test_demo_i18n_js_is_served():
    demo_module = _load_demo_module()
    app = demo_module.build_demo_app(service=object())

    status, headers, body = _call_app(app, method="GET", path="/static/i18n.js")
    js = body.decode("utf-8")

    assert status.startswith("200")
    assert headers["Content-Type"].startswith("application/javascript")
    assert "window.I18N" in js
    assert "PLACEHOLDER" in js
    assert "ANALYZE_BTN" in js
    assert "RISK_HIGH" in js
```

---

## Runtime State Inventory

This is a code/content-only phase — no renames, no migrations, no re-registrations. Skipped.

---

## Environment Availability

No external tools required. All tools (Python, file system, browser) are already confirmed operational from Phase 14.

Step 2.6: SKIPPED (no external dependencies beyond existing runtime)

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Strings hardcoded in HTML | `data-i18n` + JS injection from global object | Centralizes all strings; no server-side templating needed |
| English-only UI (Phase 6 legacy) | Vietnamese primary, English in parentheses | Meets I18N-01; consistent with Phase 14 bilingual badge pattern |
| `riskTierLabel` dict in demo.js (English) | `I18N.RISK_*` keys (bilingual) | Phase 16 will replace the dict; keys defined now for stability |

**Deprecated/outdated in this codebase:**
- The `riskTierLabel` dict in `demo.js` is superseded by `I18N.RISK_*` keys; Phase 16 will remove the dict.
- English-only busy state string `"Analyzing..."` / `"Analyze locally"` in `setBusyState()` — Phase 16 replaces with `I18N.ANALYZE_BTN` / `I18N.ANALYZE_BTN_BUSY`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `window.I18N = { ... }` is the correct pattern for a synchronous browser global with no module system | Code Examples | None — this is the canonical pre-ES-module approach; no risk |
| A2 | `data-i18n` attribute + DOMContentLoaded loop is standard practice for vanilla i18n injection | Architecture Patterns, Code Examples | None — well-established DOM pattern with no dependencies |
| A3 | Inline `<script>` fires before `defer`'d `<script>` when placed earlier in source order | Pitfall 2, Code Examples | If wrong, ARIA labels and text content would not be applied; observable in browser DevTools before shipping |
| A4 | `<template>` content is excluded from `querySelectorAll` on the live document | Pitfall 3 | If wrong, the injection loop would harmlessly set textContent on inert nodes — no visible breakage |

**All critical implementation facts for this phase are verified from the codebase (demo.py routing pattern, index.html exact strings, test assertions). No user confirmation needed for any locked decision.**

---

## Open Questions

1. **Template string strategy for Phase 15 vs Phase 16 split**
   - What we know: Template elements are inert; Phase 15's injection loop cannot reach them.
   - What's unclear: Should Phase 15 add `data-i18n` to template elements (for Phase 16 to use), or leave that to Phase 16?
   - Recommendation: Phase 15 should add `data-i18n` attributes to template elements (zero cost, zero risk) and leave their fallback text in place. Phase 16 then uses `el.dataset.i18n` after cloneNode without any HTML changes. This is cleaner than Phase 16 modifying HTML.

2. **`aria-label` on `<main>` and `.chat-frame` `<section>`**
   - What we know: These are structural ARIA labels that currently repeat the page title or section purpose.
   - What's unclear: The injection loop sets `textContent` for `[data-i18n]` elements. Setting `aria-label` requires `setAttribute`, not `textContent`. These elements have no visible text node — they need inline handling.
   - Recommendation: Handle `<main>` and `.chat-frame` aria-labels with explicit `setAttribute` lines in the injection block (same as `#result-panel` and `#analysis-form` in the example above). Add `data-i18n-aria` as a secondary attribute if needed to keep the loop readable, or handle them as explicit named lines — either way, keep total injection block under ~20 lines per CONTEXT.md.

---

## Project Constraints (from CLAUDE.md)

The project `CLAUDE.md` at the repo root contains only GSD workflow instructions (use get-shit-done skill, treat `/gsd-*` as commands). There are no project-specific coding conventions, security requirements, or forbidden patterns beyond those already captured in STATE.md:

- No JS frameworks, no build step — vanilla HTML/CSS/JS only [VERIFIED: STATE.md]
- No localStorage [VERIFIED: STATE.md]
- No marked.js / DOMPurify / WebSocket / SSE [VERIFIED: STATE.md]
- Backend (wsgiref + POST /api/analyze) is frozen [VERIFIED: STATE.md + CONTEXT.md]
- No `innerHTML` for user-controlled content (implicit from privacy/security posture) [ASSUMED]

---

## Security Domain

Security enforcement applies. For this phase:

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | No | Strings are hardcoded constants — no user input in i18n.js |
| V6 Cryptography | No | No secrets, no encryption in this phase |
| V2 Authentication | No | No auth changes |
| V4 Access Control | No | Static file route — same access as demo.css and demo.js |

**Specific security note:** The i18n injection block uses `el.textContent = value` (not `innerHTML`). This is safe regardless of what values are in `I18N` — `textContent` is never parsed as HTML. No XSS vector exists in this implementation. [ASSUMED — standard security property of `textContent` vs `innerHTML`]

**No new attack surface** is introduced. The `/static/i18n.js` route serves a static file from `demo_assets/` — same threat model as `/static/demo.css` and `/static/demo.js`. The file contains no secrets, no user data, and no dynamic content.

---

## Sources

### Primary (HIGH confidence)
- `src/runtime/demo.py` — verified WSGI routing pattern, `_load_asset`, `_text_response` helpers [VERIFIED: codebase]
- `src/runtime/demo_assets/index.html` — complete string inventory, IDs, ARIA structure [VERIFIED: codebase]
- `src/runtime/demo_assets/demo.js` — hardcoded English strings, IDs used [VERIFIED: codebase]
- `tests/runtime/test_demo.py` — existing assertions including the one that will break [VERIFIED: codebase]
- `.planning/phases/15-i18n-js-demo-py-static-route/15-CONTEXT.md` — all locked decisions [VERIFIED: codebase]
- `.planning/STATE.md` — hard constraints (no frameworks, frozen backend) [VERIFIED: codebase]

### Secondary (MEDIUM confidence)
- WHATWG HTML Living Standard: `<template>` inert content, `data-*` attributes — standard DOM behavior cited from training knowledge [ASSUMED]

### Tertiary (LOW confidence)
- None — all implementation claims are either codebase-verified or standard DOM API knowledge with no verification needed.

---

## Metadata

**Confidence breakdown:**
- WSGI route pattern: HIGH — read directly from demo.py
- String inventory: HIGH — read directly from index.html and demo.js; every string enumerated
- data-i18n injection pattern: MEDIUM — standard DOM pattern, not verified via Context7 (no library involved)
- Test breakage identification: HIGH — read directly from test_demo.py line 59
- Template inertness: MEDIUM — standard HTML behavior, no verification call needed

**Research date:** 2026-06-09
**Valid until:** Phase 15 execution (no external dependencies that can drift)
