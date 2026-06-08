# Architecture Patterns

**Domain:** Localized explainable LLM for Vietnamese financial phishing/social engineering text detection  
**Project:** Localized Explainable AI (XAI) Engine for Vietnamese phishing triage  
**Researched:** 2026-03-18

## Recommended Architecture

Use an offline-first, modular pipeline with strict stage boundaries:

1. Ingestion and normalization
2. Threat analysis (rules + retrieval + LLM classifier)
3. Explanation synthesis (evidence-grounded)
4. User recommendation generation
5. Logging and evaluation feedback loop

Design principle: high recall on threat detection, deterministic evidence capture, and explainable outputs that are safe for non-technical users.

## Component Boundaries and Interfaces

- **Client Adapter** — Accepts raw text from UI, clipboard, or message paste. Input: `POST /analyze` request payload. Output: canonical analysis request object. Talks to: Preprocessor.
- **Preprocessor** — Language normalization, typo/slang cleanup, PII masking tags, URL/phone/entity extraction. Input: canonical analysis request. Output: enriched text document with extracted artifacts. Talks to: Retrieval, Rule Engine, LLM Orchestrator.
- **Rule Engine** — Fast deterministic high-recall signals (domain spoofing, urgency, payment pressure, impersonation markers). Input: enriched text document. Output: rule signal set with confidence priors. Talks to: LLM Orchestrator, Evidence Store.
- **Retrieval Layer** — Fetches known scam patterns, local financial entity knowledge, phrase templates. Input: enriched text + extracted entities. Output: ranked context snippets. Talks to: LLM Orchestrator.
- **LLM Orchestrator** — Runs local model prompt chain for threat class, confidence, rationale candidates. Input: enriched text + rule signals + retrieved context. Output: structured threat assessment JSON. Talks to: Explanation Engine.
- **Explanation Engine** — Converts model output + evidence into user-readable explanation with citation links to evidence spans. Input: structured threat assessment + evidence bundle. Output: explanation object. Talks to: Recommendation Engine.
- **Recommendation Engine** — Generates action checklist (block/report/verify channel) by risk level. Input: explanation object + threat level. Output: user action plan. Talks to: Response Assembler.
- **Response Assembler** — Composes final API response in stable schema. Input: assessment + explanation + recommendations. Output: API response payload. Talks to: Client Adapter.
- **Event Logger** — Persists anonymized events, model metadata, latency, confidence, and user feedback. Input: events from all stages. Output: append-only local log records. Talks to: Eval Harness, Monitoring.
- **Eval Harness** — Replays benchmark datasets, computes metrics, compares against release gates. Input: dataset + model bundle + pipeline version. Output: scorecards and pass/fail report. Talks to: CI, Release Manager.
- **Model Runtime** — Offline inference engine (GGUF model + tokenizer + runtime config). Input: prompt requests. Output: token stream/JSON output. Talks to: LLM Orchestrator.
- **Model/Rules Registry** — Versioned model, prompts, rules, and retrieval snapshots. Input: version query. Output: immutable artifact references. Talks to: Orchestrator, Eval Harness.

## Interface Contracts (Suggested)

### 1. Analyze Request

```json
{
  "request_id": "uuid",
  "channel": "sms|zalo|messenger|telegram|facebook|other",
  "text": "raw user-provided text",
  "locale_hint": "vi|en|mixed",
  "timestamp": "ISO-8601"
}
```

### 2. Threat Assessment

```json
{
  "request_id": "uuid",
  "threat_label": "safe|suspicious|phishing|social_engineering|job_scam",
  "risk_score": 0.0,
  "confidence": 0.0,
  "signals": [
    {"type": "spoofed_domain", "value": "example-paypa1.com", "source": "rule"},
    {"type": "urgency_language", "value": "khoa tai khoan ngay", "source": "llm"}
  ],
  "evidence_spans": [
    {"start": 14, "end": 41, "text": "...", "reason": "impersonation cue"}
  ],
  "model_version": "xai-vi-8b-lora-q4_0@2026-03-18",
  "policy_version": "ruleset-0.1.0"
}
```

### 3. Explanation and Recommendation

```json
{
  "summary": "High risk financial phishing likely.",
  "why": [
    "Message creates urgency to bypass verification.",
    "Sender requests credential or transfer action.",
    "Link/domain pattern is inconsistent with official institution naming."
  ],
  "recommendations": [
    "Do not click links or share OTP/password.",
    "Call official hotline from bank website, not message contact.",
    "Report message in the platform and block sender."
  ],
  "user_safe_mode": true
}
```

### 4. Logging Event

```json
{
  "event_id": "uuid",
  "request_id": "uuid",
  "stage": "preprocess|rules|retrieval|llm|explanation|recommendation",
  "latency_ms": 0,
  "artifact_versions": {
    "model": "...",
    "prompt": "...",
    "rules": "..."
  },
  "risk_score": 0.0,
  "decision": "...",
  "feedback": "optional_user_feedback"
}
```

## Data Flow (Ingestion -> Analysis -> Explanation -> Recommendation -> Logging/Eval)

1. Ingestion receives raw text and metadata from the client adapter.
2. Preprocessor normalizes Vietnamese/mixed text, extracts URLs, entities, and suspicious lexical cues.
3. Rule Engine computes deterministic risk signals to protect recall and catch obvious fraud patterns.
4. Retrieval Layer pulls local threat patterns and institution references to ground model reasoning.
5. LLM Orchestrator runs offline model inference and emits a structured threat assessment.
6. Explanation Engine transforms assessment into human-readable rationale tied to evidence spans.
7. Recommendation Engine maps risk level and scam type to concrete user actions.
8. Response Assembler returns stable schema to client.
9. Event Logger stores per-stage telemetry and prediction artifacts.
10. Eval Harness consumes logs plus benchmark sets to produce quality, recall, and latency reports.
11. Release Manager promotes model/rules only if evaluation gates are met.

## Offline Deployment Architecture

### Topology

- Desktop or local service host (consumer laptop, CPU/iGPU baseline)
- Embedded model runtime process (GGUF + quantized 8B LoRA merge)
- Local vector/rule store and retrieval index (on-device)
- Local encrypted event store (SQLite or append-only JSONL + encryption)
- Optional air-gapped update package import for model/rule updates

### Runtime Packaging

- Single installer bundle contains:
  - Inference runtime binaries
  - Quantized model artifacts
  - Prompt templates and rules
  - Local knowledge snapshot (financial entities, known patterns)
- No outbound network requirement for inference path.
- Update mechanism is explicit and versioned (manual package or signed internal updater).

### Security/Privacy Boundaries

- Raw user text never leaves local device in production mode.
- PII masking for logs by default; full raw text logging disabled unless debug mode is explicitly enabled.
- Tamper-evident version metadata for model and rules to preserve auditability.

## Evaluation Harness Architecture

### Core Harness Components

- **Dataset Manager** — Curates train/validation/test sets (real + synthetic Vietnamese scams, mixed-language edge cases).
- **Scenario Generator** — Builds adversarial and mutation tests (typo, slang, obfuscation, unicode confusables).
- **Runner** — Executes pipeline versions against fixed benchmark suites.
- **Metrics Engine** — Computes recall, precision, F1, calibration, explanation quality, latency.
- **Threshold Gate** — Enforces release criteria with recall-priority policy.
- **Regression Tracker** — Compares current run vs previous approved baseline.
- **Error Analyzer** — Clusters false negatives/positives and maps to remediation actions.

### Evaluation Data Flow

1. Select immutable benchmark suite by version.
2. Run full pipeline end-to-end (not model-only) to capture system behavior.
3. Store predictions, explanations, and recommendations.
4. Score across detection, explanation fidelity, and user-action quality.
5. Produce fail report highlighting high-severity false negatives.
6. Feed errors into data improvement loop (rules update, retrieval update, fine-tune data updates).

### Minimum Release Gates (suggested)

- Recall on phishing/social-engineering classes: prioritize as primary gate.
- Macro F1 for overall classification stability.
- Explanation quality checks:
  - Evidence-grounded reasons present
  - No hallucinated institution/action claims
- Latency budget on consumer hardware.

## Patterns to Follow

### Pattern 1: Hybrid Detection (Rules + Retrieval + LLM)

**What:** Combine deterministic rules with grounded LLM reasoning.  
**When:** Safety-critical scam detection where recall is critical.  
**Why:** Rules catch known high-risk patterns quickly; LLM handles nuanced language and social context.

### Pattern 2: Structured Output First

**What:** Force model outputs into fixed JSON schema before user rendering.  
**When:** Need stable downstream explanation/recommendation logic and evaluability.  
**Why:** Prevent brittle parsing and enable robust regression testing.

### Pattern 3: Evidence-Bound Explanations

**What:** Every explanation claim should map to explicit text spans/rule hits.  
**When:** XAI requirements and trust-sensitive product context.  
**Why:** Improves user trust and reduces unsafe overclaiming.

## Anti-Patterns to Avoid

### Anti-Pattern 1: LLM-Only Classification Without Rules

- What goes wrong: misses simple but dangerous patterns under prompt variance.
- Consequence: preventable false negatives in phishing detection.
- Instead: always include deterministic high-recall guards.

### Anti-Pattern 2: Binary Output Without Action Layer

- What goes wrong: user knows something is risky but has no safe next steps.
- Consequence: reduced practical safety impact.
- Instead: attach scenario-specific recommendations.

### Anti-Pattern 3: Evaluating Model in Isolation

- What goes wrong: hidden failures in retrieval, rules, or rendering are missed.
- Consequence: production regressions despite good offline model scores.
- Instead: evaluate full pipeline end-to-end.

## Build-Order Implications for Phase Planning

Suggested build order for a greenfield milestone:

1. Foundation and contracts first

- Define canonical schemas (`AnalyzeRequest`, `ThreatAssessment`, `Explanation`, `Recommendation`, `EventLog`).
- Establish artifact versioning (model/prompt/rules/retrieval snapshot IDs).

1. Ingestion + preprocessing + logging skeleton

- Build deterministic text normalization and extraction pipeline.
- Wire end-to-end request tracing and event logging before advanced model work.

1. Rule Engine v1 + baseline retrieval

- Implement high-recall deterministic signals for known Vietnamese financial scam patterns.
- Add minimal local knowledge base and retrieval API.

1. Offline model runtime integration

- Integrate quantized local model serving with structured output constraints.
- Produce initial threat labels and confidence.

1. Explanation and recommendation layers

- Add evidence-to-rationale mapping and user action templates by scam type.
- Harden for non-technical clarity and safe guidance wording.

1. Evaluation harness and release gates

- Build benchmark runner, metrics, and regression dashboard/reporting.
- Enforce recall-priority gate and latency gate.

1. Data flywheel and hardening

- Use error clusters to update data, rules, prompts, and retrieval.
- Add adversarial robustness tests (obfuscation, mixed-language manipulation).

### Why this order

- Early schema and logging avoid costly rewrites.
- Rule-first detection provides immediate safety baseline before model maturity.
- Evaluation harness before optimization prevents blind tuning.
- Explanation/recommendation after stable detection avoids amplifying unstable predictions.

## Architecture Risks to Track During Planning

- Retrieval contamination from low-quality synthetic patterns can degrade explanations.
- Over-aggressive normalization can erase signal (slang/spoof tokens).
- Quantization settings may impact calibration and confidence reliability.
- Recommendation policy drift can produce unsafe or outdated advice.

## Planning Notes for Next Milestone Draft

- Treat evaluation harness as a first-class subsystem, not a post-hoc script.
- Allocate explicit phase capacity for Vietnamese linguistic edge cases.
- Include offline packaging and update strategy as part of core architecture, not deployment afterthought.

---

## Chat-Bubble UI Integration Architecture (Milestone v2.0)

**Researched:** 2026-06-08  
**Scope:** Frontend redesign only — Python WSGI backend (`demo.py`) is unchanged.

### Integration Point Summary

The existing system provides a single stable integration seam: `POST /api/analyze` returning `AnalysisResult` JSON. Everything else — HTML, CSS, JS — is static asset serving with no server-side templating. The chat-bubble redesign is a purely frontend concern.

**Backend contract (unchanged):**

Request body:

```json
{ "text": "<string>", "channel": "<ChannelName>" }
```

Response on success (`200`):

```json
{
  "risk_tier": "benign | suspicious | high-risk",
  "summary": "<string>",
  "top_cues": [{"span": "<string>", "reason": "<string>", "cue_type": "<string|null>"}],
  "threat_labels": ["bank_impersonation | zalo_social_engineering | task_scam | benign"],
  "recommendations": ["<string>"],
  "backend_name": "<string>",
  "provisional": true,
  "normalized_text": "<string|null>"
}
```

Response on error (`400` or `503`):

```json
{ "error": { "message": "<string>", "steps": ["<string>"] } }
```

`demo.py` needs zero changes for the core API contract. No new routes. No server-side rendering.

### File Change Map

All paths below are relative to `src/runtime/demo_assets/` unless otherwise noted.

**Modified files (in-place rewrites):**

- **index.html** — Replace card-layout shell with chat-window shell. Remove old result/error templates. Add `#chat-thread` scroll container, `#composer` input bar with channel pill, and new bubble templates (`bubble-user`, `bubble-bot`, `bubble-error`, `bubble-typing`).
- **demo.css** — Remove panel/grid rules. Add chat-window, bubble, typing-indicator, composer-bar, and channel-pill rules. Retain all existing CSS variables and font stack.
- **demo.js** — Replace `renderResult`, `renderError`, `resetPanel`, and `setBusyState` with bubble-append functions and typing lifecycle. Keep the fetch call to `POST /api/analyze` intact.

**New files:**

- **demo_assets/i18n.js** — Bilingual string table (Vietnamese primary, English for technical terms). Plain JS object global, no module bundler needed. Served by a new static route in `demo.py`.

No new Python files beyond the one added route. No `package.json`, no build step.

### Data Flow: User Input to Bot Bubble

```text
User types text + selects channel
  -> clicks Send (or Ctrl+Enter)
  -> appendUserBubble(text, channel)         // instant, right-aligned
  -> appendTypingIndicator()                  // animated dots, left-aligned
  -> scrollToBottom()
  -> fetch POST /api/analyze {text, channel}
       [demo.py: DemoApp._handle_analyze -> service.analyze_text -> AnalysisResult]
  -> response.json()
  -> removeTypingIndicator()
  -> if response.ok:
       appendBotBubble(result)               // structured left-aligned bubble
     else:
       appendErrorBubble(error)             // error left-aligned bubble
  -> scrollToBottom()
  -> clear textarea, re-enable send
```

### Component Structure (HTML/CSS/JS breakdown)

**HTML shell (index.html after rewrite):**

```html
<body>
  <div class="chat-window">
    <header class="chat-header"><!-- app name + trust strip --></header>
    <div id="chat-thread" role="log" aria-live="polite">
      <!-- bubbles injected here by JS -->
    </div>
    <form id="composer" class="composer-bar">
      <div class="channel-pill">
        <select id="channel-select"><!-- options --></select>
      </div>
      <textarea id="message-input"></textarea>
      <div class="send-actions">
        <button id="sample-button"><!-- "Thu mau" --></button>
        <button type="submit" id="analyze-button"><!-- "Phan tich" --></button>
      </div>
    </form>
  </div>
</body>
```

**Bot bubble template (inside `<template id="bubble-bot">`):**

```html
<article class="bubble bubble--bot">
  <span class="risk-badge" data-risk-tier=""></span>
  <p class="bubble__verdict"></p>
  <ul class="cue-list"></ul>
  <ul class="rec-list"></ul>
  <footer class="bubble__meta">
    <span class="threat-tags"></span>
    <span class="backend-name"></span>
  </footer>
</article>
```

**Typing indicator template (inside `<template id="bubble-typing">`):**

```html
<div class="bubble bubble--bot bubble--typing" id="typing-indicator">
  <span class="dot"></span><span class="dot"></span><span class="dot"></span>
</div>
```

### Bilingual Text Management

**Decision: hardcode in `i18n.js`, reference from `demo.js`. No HTML `data-*` attributes for strings, no separate JSON file fetched at runtime.**

Rationale:

- The page is fully local and static. A runtime `fetch('i18n.json')` adds an async dependency before the UI is usable and complicates the WSGI routing (needs another static route or inline into HTML).
- HTML `data-*` attributes on elements would scatter string definitions across markup and make adding a second language non-trivial.
- A plain JS object in `i18n.js` loaded via a second `<script src="/static/i18n.js">` tag is zero-infrastructure, consistent with the no-build constraint, and makes all strings findable in one place.

`demo.py` needs one new static route: `GET /static/i18n.js` returning `i18n.js` as `application/javascript`. This is the only change to `demo.py` — one `if` branch mirroring the existing `demo.css` and `demo.js` patterns.

**i18n.js shape:**

```javascript
const I18N = {
  ui: {
    appName: "Kiem tra tin nhan dang ngo",
    inputPlaceholder: "Dan tin nhan dang ngo vao day...",
    sendButton: "Phan tich",
    sampleButton: "Thu mau",
    channelLabel: "Kenh",
    typingText: "Dang phan tich...",
    errorTitle: "Loi ket noi runtime",
  },
  riskTier: {
    "benign":     { vi: "Binh thuong",   en: "Benign" },
    "suspicious": { vi: "Nghi ngo",      en: "Suspicious" },
    "high-risk":  { vi: "Nguy hiem cao", en: "High risk" },
  },
  threatLabel: {
    "bank_impersonation":      "Gia mao ngan hang",
    "zalo_social_engineering": "Lua dao Zalo",
    "task_scam":               "Lua dao viec lam",
    "benign":                  "Binh thuong",
  },
  channels: {
    "unknown":   "Khong ro",
    "sms":       "SMS",
    "zalo":      "Zalo",
    "messenger": "Messenger",
    "telegram":  "Telegram",
    "facebook":  "Facebook",
  },
  sections: {
    cues:    "Dau hieu dang ngo",
    steps:   "Buoc an toan tiep theo",
    backend: "Mo hinh",
  },
  errors: {
    networkFail: "Khong the ket noi toi runtime cuc bo.",
    networkStep: "Thu lai sau khi runtime khoi dong xong.",
  },
};
```

Note: Vietnamese diacritics are intentionally omitted in the JS snippet above to avoid encoding issues in the planning file. The actual `i18n.js` source file should use full UTF-8 Vietnamese with diacritics.

**Note on technical terms:** Risk tier label displays as bilingual — e.g., "Nguy hiem cao (High risk)" — using the `riskTier` map's `vi` + `en` fields concatenated. Other UI text is Vietnamese-only.

### Async Flow in demo.js (typing indicator lifecycle)

```javascript
async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text) return;

  appendUserBubble(text, channelSelect.value);  // 1. user bubble
  messageInput.value = "";
  setInputDisabled(true);

  const typingEl = appendTypingIndicator();     // 2. typing dots appear
  scrollToBottom();

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, channel: channelSelect.value }),
    });
    const payload = await response.json();
    typingEl.remove();                           // 3. remove dots

    if (response.ok) {
      appendBotBubble(payload);                  // 4a. bot bubble
    } else {
      appendErrorBubble(payload.error ?? { message: I18N.errors.networkFail, steps: [] });
    }
  } catch {
    typingEl.remove();
    appendErrorBubble({ message: I18N.errors.networkFail, steps: [I18N.errors.networkStep] });
  } finally {
    setInputDisabled(false);
    scrollToBottom();
    messageInput.focus();
  }
}
```

`appendTypingIndicator` clones `#bubble-typing` template, appends to `#chat-thread`, and returns the element reference so the caller can `.remove()` it precisely when the response arrives — no timeouts, no polling.

### CSS Architecture for Bubbles

The existing CSS variable palette (`--accent-deep`, `--accent-cool`, `--success-tint`, `--warning-tint`, `--danger-tint`, `--ink-strong`, `--ink-muted`) maps directly to the chat-bubble semantics and must be retained verbatim. The full `.workspace-panel` grid layout is replaced by a single-column flex column:

```css
.chat-window {
  display: flex;
  flex-direction: column;
  height: 100dvh;            /* full viewport, no scroll on body */
  max-width: 760px;
  margin: 0 auto;
}

.chat-thread {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.composer-bar {
  flex-shrink: 0;
  /* sticky bottom — part of flex column, not position:fixed */
}

.bubble {
  max-width: 72%;
  border-radius: 18px;
  padding: 14px 18px;
  line-height: 1.6;
}

.bubble--user {
  align-self: flex-end;
  background: linear-gradient(135deg, var(--accent-deep), #b95f46);
  color: #fff8f4;
}

.bubble--bot {
  align-self: flex-start;
  background: var(--panel-background);
  border: 1px solid var(--panel-border);
}

.bubble--typing {
  padding: 16px 22px;
}

/* Three-dot typing animation */
.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ink-muted);
  animation: blink 1.2s infinite;
}
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink {
  0%, 80%, 100% { opacity: 0.25; }
  40% { opacity: 1; }
}

.risk-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 700;
  margin-bottom: 8px;
}
.risk-badge[data-risk-tier="benign"]     { background: var(--success-tint); color: #22543d; }
.risk-badge[data-risk-tier="suspicious"] { background: var(--warning-tint); color: #8a4b08; }
.risk-badge[data-risk-tier="high-risk"]  { background: var(--danger-tint);  color: #8a2424; }
```

The `.channel-pill` inside the composer wraps the `<select>` element and renders as a small rounded badge-like selector flush with the textarea, matching the existing button border-radius convention.

### demo.py Change: One Additional Static Route

```python
# Add alongside existing /static/demo.css and /static/demo.js handlers:
if method == "GET" and path == "/static/i18n.js":
    return _text_response(
        start_response, "200 OK",
        "application/javascript; charset=utf-8",
        _load_asset("i18n.js"),
    )
```

No other changes to `demo.py`. `DemoApp.__call__`, `_handle_analyze`, `build_demo_app`, and `run_demo_server` are untouched.

### New vs Modified File List (Implementation Reference)

Files that change in this milestone, in build order:

- **src/runtime/demo_assets/demo.css** — Modified, full rewrite. Replaces panel and grid CSS with chat-window and bubble CSS. All existing CSS variables retained.
- **src/runtime/demo_assets/index.html** — Modified, full rewrite. Replaces card layout with chat window shell and new bubble templates.
- **src/runtime/demo_assets/i18n.js** — New file. Bilingual string table; must be loaded as a script tag before demo.js.
- **src/runtime/demo.py** — Modified, minimal. Adds one if-branch to serve GET /static/i18n.js.
- **src/runtime/demo_assets/demo.js** — Modified, full rewrite. Replaces render functions with bubble builders and typing lifecycle.

### Build Order for Implementation Phases

Dependencies flow in this direction: CSS defines visual tokens → HTML provides structure → JS wires behavior → i18n fills text. Build in this order to avoid blocking:

**Phase 1 — CSS skeleton.**
Write the full `demo.css` rewrite. Define `.chat-window`, `.chat-thread`, `.composer-bar`, `.bubble`, `.bubble--user`, `.bubble--bot`, `.bubble--typing`, `.risk-badge`, `.channel-pill`. Keep all existing CSS variables. No JS dependency. Can visually verify with static HTML.

**Phase 2 — HTML shell.**
Write the full `index.html` rewrite with the new chat-window structure, new `<template>` elements (`bubble-user`, `bubble-bot`, `bubble-error`, `bubble-typing`). Add `<script src="/static/i18n.js">` before `demo.js`. At this point the page renders (empty thread + composer) without any JS.

**Phase 3 — i18n.js + demo.py route.**
Write `i18n.js` with the full `I18N` object. Add the one static-route branch to `demo.py`. Verify `http://localhost:8765/static/i18n.js` returns the file. No JS behavior yet needed.

**Phase 4 — demo.js rewrite.**
Write the full `demo.js` rewrite. Wire `sendMessage`, `appendUserBubble`, `appendTypingIndicator`, `appendBotBubble`, `appendErrorBubble`, `scrollToBottom`. Reference `I18N` object (loaded before this script). Test end-to-end: paste text → user bubble → dots → bot bubble.

**Phase 5 — polish and edge cases.**
Handle empty input guard, long-text truncation in user bubble, `sampleButton` prefill (port from existing behavior), mobile viewport (ensure `100dvh` composer stays on-screen with soft keyboard), accessibility (`role="log"`, `aria-live="polite"` on thread, `aria-label` on buttons).

### Constraints Carried From Existing Architecture

- No framework, no build step, no npm — pure vanilla HTML/CSS/JS.
- Python WSGI backend `demo.py` serves static files from `demo_assets/` via `_load_asset()`. Any new static file needs a matching route in `demo.py`.
- The `AnalysisResult` contract (`contracts.py`) is frozen. JS must consume fields as-is: `risk_tier`, `summary`, `top_cues[].span`, `top_cues[].reason`, `threat_labels`, `recommendations`, `backend_name`.
- `ChannelName` values are the literal option `value` attributes in the channel select: `unknown`, `sms`, `zalo`, `messenger`, `telegram`, `facebook`.
- Inference on consumer hardware is slow (13+ seconds on CPU). The typing indicator is not cosmetic — it is the primary loading affordance. It must appear before the `fetch` resolves, not after.
