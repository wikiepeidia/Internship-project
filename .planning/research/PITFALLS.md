# Domain Pitfalls: Vietnamese Financial Scam Detection + Explainable Local LLM Inference

**Domain:** Offline Vietnamese financial phishing detection with explainable outputs
**Researched:** 2026-03-18
**Milestone context:** Greenfield

## Phase Map (for roadmap ownership)

- **Phase 1 - Taxonomy and Risk Policy:** Define scam classes, severity policy, explanation contract, and release gates.
- **Phase 2 - Data Acquisition and Governance:** Collect seed data, deduplicate, label, and enforce split hygiene.
- **Phase 3 - Synthetic Expansion QA:** Generate synthetic data with diversity controls and adversarial coverage.
- **Phase 4 - Fine-Tuning and Thresholding:** Train, calibrate thresholds, and optimize for false-negative risk.
- **Phase 5 - Explainability Alignment and Safety:** Verify explanation faithfulness and recommendation quality.
- **Phase 6 - Local Inference Optimization:** Quantization, latency, and edge-runtime regression controls.
- **Phase 7 - Post-Deploy Monitoring and Update Loop:** Drift detection, incident review, and rapid model/data updates.

## Critical Pitfalls

### 1) Vietnamese fraud lexicon drift is missed

**What goes wrong:** New scam slang, regional wording, and euphemisms appear faster than dataset updates.
**Warning signs:**

- Stable validation metrics but rising user-reported misses for new scam styles.
- Frequent OOV-like token spikes in recent production text.
- Classifier confidence drops on messages containing new bait phrases.
**Prevention strategy:**
- Weekly drift mining from fresh scam reports and failed cases.
- Maintain a living fraud lexicon (bait verbs, urgency markers, payment cues, spoof words).
- Add adversarial canary sets per release containing latest slang variants.
**Roadmap phase owner:** Phase 7 (primary), Phase 2 (initial setup).

### 2) Code-switching and obfuscation bypass detection

**What goes wrong:** Attackers mix Vietnamese-English, split keywords, use homoglyphs, or alter spacing/punctuation to evade pattern learning.
**Warning signs:**

- High miss rate on mixed-language samples versus pure Vietnamese samples.
- Recall collapse when characters are normalized or spacing is perturbed.
- URL/domain risk not detected when text contains altered separators.
**Prevention strategy:**
- Robust normalization pipeline (unicode normalization, spacing cleanup, obfuscation transforms).
- Train/evaluate with perturbation suites: code-switch, typo, homoglyph, punctuation noise.
- Add explicit URL and domain token features to preserve phishing cues.
**Roadmap phase owner:** Phase 2 (normalization pipeline), Phase 4 (robustness training).

### 3) False-negative risk is under-controlled

**What goes wrong:** Teams optimize for aggregate F1 and accuracy, then ship thresholds that miss high-risk scams.
**Warning signs:**

- Good macro metrics but severe misses in high-harm classes (bank impersonation, account takeover).
- Threshold chosen on convenience, not cost-weighted policy.
- No per-class recall gate in release checklist.
**Prevention strategy:**
- Use risk-weighted evaluation where high-harm classes have strict minimum recall.
- Calibrate thresholds per class, not one global score.
- Block release when high-harm recall gate fails, even if overall F1 passes.
**Roadmap phase owner:** Phase 1 (policy), Phase 4 (calibration and gating).

### 4) Explanation hallucination creates unsafe trust

**What goes wrong:** Model outputs plausible but unsupported reasons, fake evidence, or overconfident advice.
**Warning signs:**

- Explanations reference cues not present in the input text.
- Similar predictions produce inconsistent rationale.
- User testing shows high trust in wrong recommendations.
**Prevention strategy:**
- Enforce evidence-linked explanation schema (claim -> text span evidence -> recommendation).
- Add faithfulness tests: rationale overlap, counterfactual consistency, and contradiction checks.
- Refuse unsupported claims and fall back to uncertainty language when evidence is weak.
**Roadmap phase owner:** Phase 5 (primary), Phase 1 (contract definition).

### 5) Dataset leakage inflates offline metrics

**What goes wrong:** Near-duplicate or template-related examples leak across train/val/test, especially from synthetic generation.
**Warning signs:**

- Very high validation scores but weak field performance.
- Same URL patterns, phone formats, or template skeletons across splits.
- Performance drops sharply on time-based holdout.
**Prevention strategy:**
- Deduplicate with lexical + semantic similarity before split.
- Split by scam campaign/template family and by time window.
- Keep an untouched external holdout set for final acceptance.
**Roadmap phase owner:** Phase 2 (split governance), Phase 3 (synthetic controls).

### 6) Synthetic data mode collapse narrows coverage

**What goes wrong:** Synthetic expansion repeats a few templates and fails to represent real attacker creativity.
**Warning signs:**

- High n-gram/template repetition in synthetic corpus.
- Strong benchmark results but poor robustness to novel scam phrasings.
- Class coverage appears balanced numerically but not linguistically diverse.
**Prevention strategy:**
- Diversity constraints in generation prompts and post-generation filtering.
- Human-in-the-loop spot audits by scam archetype.
- Track diversity metrics (distinct n-grams, template entropy, lexical variety).
**Roadmap phase owner:** Phase 3 (primary).

### 7) Label ontology is too coarse or inconsistent

**What goes wrong:** Labels mix scam mechanism, intent, and severity without clear boundaries, causing unstable learning and explanations.
**Warning signs:**

- Frequent annotator disagreement between similar classes.
- Explanation text conflicts with assigned class semantics.
- Confusion matrix shows persistent class collapse.
**Prevention strategy:**
- Define hierarchical taxonomy: mechanism, actor claim, action requested, harm severity.
- Write annotation playbook with positive/negative examples per class.
- Run adjudication cycles and update guidelines before scaling labeling.
**Roadmap phase owner:** Phase 1 (taxonomy), Phase 2 (annotation ops).

### 8) Privacy promises break in telemetry/logging

**What goes wrong:** "Offline-first" product still leaks sensitive raw text via logs, crash reports, or debug exports.
**Warning signs:**

- Raw user messages appear in local logs by default.
- Support workflows request full message copy/paste.
- No data retention policy for local artifacts.
**Prevention strategy:**
- Redact PII and sensitive spans before any logging.
- Default telemetry off for raw text; opt-in with explicit consent.
- Add privacy test cases to CI for log output and error paths.
**Roadmap phase owner:** Phase 1 (policy), Phase 6 (runtime controls), Phase 7 (ops audits).

### 9) Quantization regression harms recall/explanation quality

**What goes wrong:** GGUF quantization and CPU-focused optimization reduce subtle linguistic detection ability and rationale quality.
**Warning signs:**

- Recall gap between FP16 reference and quantized builds exceeds safety threshold.
- Explanations become shorter, generic, or contradictory after optimization.
- Regression appears only on long, mixed-language messages.
**Prevention strategy:**
- Maintain golden evaluation suite for pre/post-quantization comparison.
- Define acceptance deltas for per-class recall and explanation faithfulness.
- Use model-size fallback tiers when low-bit variants fail safety gates.
**Roadmap phase owner:** Phase 6 (primary), Phase 4 (reference baseline).

### 10) Alert fatigue from false positives reduces real-world safety

**What goes wrong:** Overly aggressive detector flags too many benign financial messages; users start ignoring warnings.
**Warning signs:**

- High override/dismiss rate in user trials.
- Declining user trust scores despite high recall.
- Repeated complaints that recommendations are "always panic".
**Prevention strategy:**
- Introduce graded risk bands (low/medium/high) with calibrated language.
- Tune recommendation UX to match confidence and evidence strength.
- Track precision-at-action threshold, not only headline recall.
**Roadmap phase owner:** Phase 5 (recommendation design), Phase 7 (post-deploy tuning).

## Phase-Specific Warning Matrix

| Phase Topic | Likely Pitfall | Detection Signal | Mitigation |
| ------------- | ---------------- | ------------------ | ------------ |
| Taxonomy/policy | Under-specified high-harm classes | Ambiguous labels, unstable recall target | Hierarchical ontology + class-level recall gates |
| Data ingestion | Leakage and normalization blind spots | Duplicate bleed and mixed-language misses | Dedup + robust normalization + split governance |
| Synthetic expansion | Template repetition | High template similarity | Diversity constraints + human audits |
| Fine-tuning/calibration | False negatives hidden by aggregate metrics | Strong F1, weak critical-class recall | Cost-sensitive thresholds + hard release gates |
| Explainability | Hallucinated rationale | Unsupported claims in rationale | Evidence-linked schema + faithfulness checks |
| Local optimization | Quantization safety regression | Recall/fidelity drop vs reference | Golden suite + acceptance deltas + fallback models |
| Deployment | Trust erosion from false alarms | High dismiss rate | Risk bands + recommendation calibration |
| Monitoring | Lexicon drift | OOV spikes and incident misses | Weekly drift loop + canary refresh |

## Minimum Failure-Detection Dashboard (should exist before first public trial)

- Per-class recall for high-harm scam classes.
- False-negative incident tracker with root-cause tags.
- Explanation faithfulness pass rate.
- Duplicate/leakage score across splits.
- Drift indicators: lexical novelty, code-switch ratio, obfuscation ratio.
- Quantized-vs-reference regression delta.
- User trust and warning-dismiss rate.

## Confidence

- **Domain fit:** High (pitfalls are specific to Vietnamese financial scam text and local XAI inference workflow).
- **Operational specificity:** Medium (exact thresholds should be finalized during calibration with real pilot data).

---

# Chat UI Pitfalls: Vanilla JS Chat-Bubble Interface (v2.0 Revamp)

**Domain:** Chat-bubble UI, vanilla HTML/CSS/JS, bilingual Vietnamese/English, Python wsgiref backend
**Researched:** 2026-06-08
**Milestone context:** Replacing AI-demo card layout with chat thread layout — no framework, no build step

## Existing Code Context

The current demo.js architecture is stateless-per-request: one `<form>` submits once, `setBusyState()` disables both buttons, `renderResult()` replaces the result panel via `replaceChildren()`, and the existing `aria-live="polite"` is on the static result panel container. The chat revamp introduces a fundamentally different interaction model: an append-only message thread, a persistent input bar at the bottom, multiple bot bubbles, and a shared conversation history. Every pitfall below is calibrated to the gaps between the existing code and that new model.

---

## Critical Chat UI Pitfalls

### C1) Scroll Anchor Race After DOM Insertion

**What goes wrong:** `container.scrollTop = container.scrollHeight` executes before the browser has laid out the newly inserted bubble. The measured `scrollHeight` is stale — it reflects the old height. The view jumps to a position that is several pixels short of the true bottom. On slow CPUs or when a large bot bubble is rendered, the shortfall is visually obvious (last message is partially hidden).

**Why it happens:** `scrollHeight` and `clientHeight` are integer-rounded layout values. They are only reliable after a paint cycle. Calling them synchronously immediately after `appendChild` reads the pre-layout value.

**Warning signs:**
- Bottom of the last bubble is clipped by 10-50 px after each new message.
- Works fine on fast desktop, breaks on budget Android phones.
- Adding a `console.log` delay accidentally "fixes" it (masks the timing issue).

**Prevention:**
Use `requestAnimationFrame` to defer the scroll measurement until after the browser has painted:
```js
function scrollToBottom(container) {
  requestAnimationFrame(() => {
    container.scrollTop = container.scrollHeight;
  });
}
```
Add a "user has scrolled up" guard: only auto-scroll when `container.scrollHeight - container.scrollTop - container.clientHeight < 80`. This prevents yanking the user back to bottom when they are reading older messages.

**Phase:** Phase 1 of chat revamp (initial thread layout implementation).

---

### C2) Re-entrant Submit: User Sends While Bot Is Still Responding

**What goes wrong:** The existing `setBusyState(isBusy)` pattern disables the button for the duration of the single fetch. In a chat model the user will expect to type the next message before the bot has finished replying. If you carry over the same disable-everything approach, the input bar is frozen. If you remove the disable guard without replacing it, the user can submit while a prior fetch is in-flight, causing two concurrent requests to the Python wsgiref server — which is single-threaded and will queue them serially, so the second request starves until the first (potentially slow model inference) completes.

**Why it happens:** wsgiref processes one request at a time on a single thread. A second POST to `/api/analyze` while the first is still waiting for the model will be accepted at the TCP level but will not enter the WSGI app until the first request handler returns. The user sees the second submission appear to hang.

**Warning signs:**
- Submit button is clickable mid-inference and second bubble appears immediately as "pending" but never resolves.
- Server logs show requests queued serially; total latency doubles for the second request.

**Prevention:**
- Maintain a module-level `let currentController = null` (`AbortController`). On each new submit, call `currentController?.abort()` before creating a new one and passing its `signal` to `fetch`.
- In the `catch` block, check `error.name === 'AbortError'` and treat it silently (remove the pending bubble rather than showing an error).
- Disable only the send button (not the text input) during in-flight requests. This prevents a second submit while giving the user visual feedback that the first is pending.
- Show a per-bubble loading indicator on the bot bubble that was requested, not a global page lock.

**Phase:** Phase 1 of chat revamp. Must be resolved before any UX testing.

---

### C3) DOM Used as Sole Source of Truth for Conversation History

**What goes wrong:** The existing `renderResult()` approach treats the result panel as a display artifact — it is rebuilt from scratch on each response. In a chat model, if you follow the same pattern and let the DOM bubbles be the only record of the conversation, you have no recoverable state when you need to: (a) scroll to an earlier message, (b) export the thread, (c) reset/clear, or (d) replay history on page reload.

**Why it happens:** Appending `<div>` nodes is the path of least resistance in vanilla JS. Developers forget that `replaceChildren()` or `innerHTML = ''` on the container also destroys the only record of what was said.

**Warning signs:**
- "Clear chat" button calls `container.replaceChildren()` then needs to know how many turns were had — but can't.
- Refreshing the page loses the conversation without warning.
- Trying to add a "copy conversation" feature requires walking the DOM tree and re-serializing text.

**Prevention:**
- Maintain a JS array `let history = []` where each entry is `{ role: 'user'|'bot', content: string, timestamp: Date, riskTier?: string }`.
- Append to `history` first, then call `appendBubble(entry)` to render from that record.
- `clearChat()` resets both `history = []` and `container.replaceChildren()` atomically.
- This also makes scroll-to-top (re-render from history) and export trivial.

**Phase:** Phase 1 of chat revamp (data model, before DOM construction).

---

### C4) ARIA Live Region Registered Too Late

**What goes wrong:** The existing `index.html` has `aria-live="polite"` on the static `#result-panel` container, which works because it is present in the DOM at page load. In the chat revamp, if the chat thread container or individual bot bubbles are created dynamically (injected with `createElement` after the user submits), screen readers will not announce their content. The ARIA live region specification requires the region to be present and registered in the DOM *before* content is added to it.

**Why it happens:** Developers add `aria-live` to a newly created `div` and then immediately `appendChild` it with content. The browser's accessibility tree has not yet registered the live region, so the announcement never fires.

**Warning signs:**
- Screen reader announces the first message but not subsequent ones.
- NVDA/VoiceOver is silent after the bot replies.
- Adding a 200 ms delay before populating the bubble "fixes" it — this is the timing tell.

**Prevention:**
- Place a single, persistent `<div id="chat-log" role="log" aria-live="polite" aria-label="Conversation">` in `index.html` at page load, empty. Append all bubbles into it rather than replacing it.
- `role="log"` carries implicit `aria-live="polite"` and is semantically correct for a chat thread.
- For error announcements (network failure, runtime unavailable), use a separate `<div role="alert" aria-live="assertive">` that is also pre-rendered but empty.
- Do not set `aria-atomic="true"` on the chat log container: you want each new bubble announced individually, not the entire thread re-read.
- The send button should announce its state change: `analyzeButton.setAttribute('aria-label', isBusy ? 'Đang phân tích...' : 'Gửi')`.

**Phase:** Phase 1 of chat revamp (HTML scaffolding, before any JS logic).

---

### C5) Vietnamese Diacritics Rendered Poorly on macOS and Linux

**What goes wrong:** The existing CSS font stack is `"Segoe UI Variable Display", "Bahnschrift", "Trebuchet MS", sans-serif`. On Windows 11 these fonts have adequate Vietnamese diacritic coverage. On macOS and Linux, none of these fonts are available. The browser falls through to the OS generic `sans-serif`, which on Ubuntu may be DejaVu Sans — a font with incomplete Vietnamese glyph coverage, causing combining diacritics to render with incorrect positioning (floating accents, colliding marks) or fall back to tofu (empty rectangles).

Vietnamese uses stacked diacritics (a base letter + a vowel modifier + a tone mark, e.g. `ộ` = `o` + circumflex + dot below). Fonts that only partially support Latin Extended Additional will render the base character from one font and the combining mark from another, producing visually broken text.

**Why it happens:**
- NFD-encoded Vietnamese text (decomposed form, each diacritic as a separate code point) is more vulnerable to font fallback mismatches than NFC-encoded text (precomposed).
- The Python runtime returns JSON strings. If those strings are NFD-normalized somewhere in the pipeline, the browser may split glyph lookup across two fonts.

**Warning signs:**
- Test the UI on macOS Chrome/Safari or Ubuntu Firefox — diacritics look incorrect or missing.
- Vietnamese characters in bot bubbles look fine in DevTools (the Unicode is correct) but the visual rendering has floating or missing marks.
- Bold or italic variants of the fallback font lack the diacritic glyphs even if the regular weight works.

**Prevention:**
- Add `"system-ui"` as the first entry in the font stack. On macOS, system-ui resolves to SF Pro, which has full Vietnamese coverage. On modern Linux it resolves to a system font with good Unicode support.
- Add `"Noto Sans"` or `"Noto Sans Vietnamese"` as an explicit fallback after system-ui. Noto is specifically designed for full Unicode coverage including all Vietnamese precomposed and combining characters.
- Revised font stack for chat bubbles: `system-ui, "Segoe UI Variable Display", "Noto Sans", sans-serif`.
- Ensure the Python backend returns JSON text in NFC Unicode normalization. Python's `unicodedata.normalize('NFC', text)` before serializing to JSON prevents decomposed diacritic issues.
- Set `lang="vi"` on bot bubble elements that contain Vietnamese verdict text. This enables browser-level hyphenation and font-matching hints.

**Phase:** Phase 1 of chat revamp (CSS font stack) and Phase 2 (backend normalization verification).

---

### C6) Chat Container Height Collapses or Overflows on Mobile

**What goes wrong:** A chat-first layout requires the message thread to fill the available vertical space between the hero/header and the fixed input bar at the bottom. The natural approach is `height: 100vh` or `height: calc(100vh - headerHeight - inputBarHeight)`. On mobile browsers, `100vh` includes the browser chrome (address bar, navigation bar), which is not always visible. When the browser chrome auto-hides on scroll, `100vh` grows, causing a layout jump. When the on-screen keyboard appears, `100vh` does not shrink — the input bar is pushed off screen or the thread overlaps the keyboard.

**Why it happens:**
- `100vh` in mobile browsers is the "largest viewport height" (LVH) — the full height when chrome is hidden. The visible height is shorter.
- iOS Safari does not support the VirtualKeyboard API. Keyboard appearance does not trigger a `resize` event on the visual viewport in the same way as Android Chrome.
- The existing CSS uses `min-height: 100vh` on `body`, which is fine for the card layout but is wrong as a constraint for a fixed-height chat container.

**Warning signs:**
- On Android Chrome, the input bar jumps up by the keyboard height when typing.
- On iOS Safari, the input bar is completely hidden behind the keyboard.
- Thread container height is correct on desktop but wrong on all mobile tests.

**Prevention:**
- Use `height: 100dvh` (dynamic viewport height, supported in all modern browsers) for the outer shell. `dvh` recomputes as chrome shows/hides.
- For the thread container: `flex: 1 1 0; overflow-y: auto; min-height: 0;`. The `min-height: 0` override is critical — without it, a flex child's minimum height is its content height, preventing the container from shrinking.
- Add `padding-bottom: env(safe-area-inset-bottom)` to the fixed input bar to avoid iOS home indicator overlap.
- For iOS Safari keyboard, listen to `window.visualViewport.addEventListener('resize', ...)` and adjust the input bar's `bottom` offset by `window.innerHeight - window.visualViewport.height`.
- Test at 375 px width (iPhone SE) with keyboard open before shipping.

**Phase:** Phase 1 of chat revamp (CSS layout). Must be validated on a real mobile device, not only desktop DevTools emulation.

---

### C7) Long Bot Bubble Content Overflows or Breaks Layout

**What goes wrong:** The bot response bubble contains: risk tier badge, Vietnamese verdict text, a list of grounded cues (each with a quoted span + reason), and safe next steps. On narrow screens, a grounded cue span quoting the original suspicious text (e.g., a long URL like `"https://vpbank-secure.example/xac-minh-tai-khoan"`) has no natural break point. Without explicit overflow handling the text either overflows the bubble container, or the bubble expands wider than the chat column pushing sibling elements.

**Why it happens:**
- URLs and long Vietnamese compound words have no natural word-break opportunities. The browser's default `overflow-wrap: normal` will not break them.
- `overflow-wrap: anywhere` forces breaks at arbitrary character boundaries, which can make mid-word line breaks that look like spaces to readers (documented real bug in chat UIs).
- The risk pill badge (`white-space: nowrap`) at the top of the bubble occupies full row width on narrow screens, leaving no room for the verdict text beside it.

**Warning signs:**
- Bot bubble containing a URL extends past the right edge of the chat column.
- Risk pill wraps or overlaps the summary text on 375 px width.
- Vietnamese text in cue reasons displays with erratic line breaks that resemble random spaces.

**Prevention:**
- Set `overflow-wrap: break-word` (not `anywhere`) on all bubble text content. This breaks only when the word is longer than the container — correct behavior for URLs.
- Set `word-break: break-all` exclusively on elements that display raw URL spans (the `cue.span` field), not on all bubble text.
- Make the risk pill a block element on narrow screens (`display: block; width: fit-content; margin-bottom: 8px`) rather than a flex row sibling to the summary text.
- Cap maximum bubble width at `min(80%, 480px)` to prevent single-line bubbles from spanning the full chat column width.
- For the list of cues, use `<details>/<summary>` to collapse long lists behind a toggle when there are more than 3 cues, avoiding overflow-driven layout breaks.

**Phase:** Phase 2 of chat revamp (bubble component design).

---

### C8) Stale ID References After Template Cloning

**What goes wrong:** The existing `renderResult()` and `renderError()` functions use `fragment.querySelector('#result-summary')`, `#result-cues`, `#result-risk-tier`, etc. These work because only one result card exists at a time. In a chat model, multiple bot bubbles coexist in the DOM simultaneously. After the second `resultTemplate.content.cloneNode(true)`, there are two elements with `id="result-summary"` in the document. `document.querySelector('#result-summary')` will return the first one (the older bubble), not the new one, silently corrupting the older message's content.

**Why it happens:** `<template>` cloning does not automatically rename IDs. The existing single-result code uses IDs as stable query targets because only one instance ever exists. The chat model invalidates that assumption.

**Warning signs:**
- Second bot response overwrites the first bot bubble's content instead of populating its own bubble.
- DevTools HTML inspector shows duplicate `id` attributes — multiple elements with the same `id` in the live DOM.
- `document.getElementById` always returns the first match; the second bubble is never updated.

**Prevention:**
- Remove all `id` attributes from the `<template>` content in `index.html`.
- Query exclusively on the cloned `fragment` reference: `fragment.querySelector('.result-summary')` instead of `document.querySelector('#result-summary')`. This is already partially correct in `renderResult()` for the fragment itself, but the template HTML still declares `id` attributes that pollute the live DOM after insertion.
- Convert all `id`-based template targets to `data-slot` attributes or semantic class names. Example: `data-slot="summary"` queried as `fragment.querySelector('[data-slot="summary"]')`.

**Phase:** Phase 1 of chat revamp (HTML template refactor). This is a silent correctness bug — it will not be visible until the second message is sent.

---

## Moderate Chat UI Pitfalls

### C9) Clearing Chat History While a Request Is In-Flight

**What goes wrong:** User clicks "New conversation" while the bot is mid-request. `container.replaceChildren()` clears the thread, but the in-flight fetch still resolves and calls `appendBubble()`, inserting an orphaned bot response into the now-empty thread. The history array (if maintained as per C3) is also out of sync: it was cleared but the in-flight response appends to it post-clear.

**Prevention:**
- Call `currentController?.abort()` before clearing state (abort the in-flight request).
- Reset the history array to `[]` and clear the DOM container in the same synchronous block.
- The `AbortError` catch path must be a no-op (do not append a bubble).

**Phase:** Phase 2 of chat revamp (clear/reset feature).

---

### C10) Sample Button Behavior in Chat Context

**What goes wrong:** The existing `sampleButton` sets `messageInput.value = sampleText` and focuses the textarea. In a chat context, if the user previously analyzed a message and the thread has history, clicking "Try sample" mid-conversation gives no indication that it is replacing the input — and if the thread is long, the user may not see the textarea fill. This is minor but confusing in a chat-first layout where the input bar is always visible at the bottom.

**Prevention:**
- Keep the sample button. Change its label to "Thử mẫu" (primary Vietnamese).
- On click, scroll the chat input bar into view and animate a brief highlight on the textarea (`outline` flash via CSS transition) to signal that text was inserted.
- Do not auto-submit the sample — user should still press send explicitly, matching the current behavior.

**Phase:** Phase 2 of chat revamp (bilingual text pass).

---

### C11) Keyboard Submit (Ctrl+Enter) Conflict with Textarea Newlines

**What goes wrong:** The existing `keydown` listener fires `form.requestSubmit()` on `Ctrl+Enter` or `Cmd+Enter`. This is correct for the large standalone textarea. In a chat-first design with a compact single-line-style input, users coming from WhatsApp/Zalo expect `Enter` alone to submit and `Shift+Enter` for newlines. Changing to `Enter`-to-submit without guarding `Shift+Enter` breaks multi-line paste flows (users paste a multi-paragraph scam message and hit Enter to break lines, accidentally submitting early).

**Prevention:**
- For the chat input, use `Enter` alone to submit; `Shift+Enter` inserts a newline. Implementation: in the `keydown` handler, if `event.key === 'Enter' && !event.shiftKey` call `form.requestSubmit()` and `event.preventDefault()`.
- Show a helper label below the textarea: "Enter để gửi · Shift+Enter để xuống dòng".
- If the textarea is multi-line tall (user pasted a long message), still respect `Shift+Enter` for line breaks within that paste session.

**Phase:** Phase 1 of chat revamp (input bar implementation).

---

### C12) XSS Risk When Rendering Bot Response Fields

**What goes wrong:** The existing `renderResult()` uses `textContent` for all dynamic content (summary, labels, backend, cues, recommendations), which is safe against XSS. In a chat revamp, if any developer switches to `innerHTML` to render the risk tier badge with color markup, or to format cue spans with `<strong>`, and passes bot response fields directly without sanitization, a maliciously crafted backend response (or a compromised local runtime) could inject script tags.

This is a local-only demo, but the backend is a local Python process — the threat model is low. However, the user pastes raw Vietnamese scam text that may contain HTML-like content (`<script>`, `<img onerror=...>`), and if that pasted text ever reaches a DOM-setter via `innerHTML`, it executes.

**Prevention:**
- Maintain the existing pattern: use `element.textContent = value` for all dynamic text fields.
- For the risk tier badge, use `element.dataset.riskTier = tier` and CSS `[data-risk-tier="high-risk"]` selectors for styling — no `innerHTML` needed.
- If rich formatting in cues is needed (bold the quoted span), use `createElement('strong')` + `textContent`, not `innerHTML`.

**Phase:** Phase 1 of chat revamp (bubble rendering). The textContent pattern from the existing code must be preserved, not replaced.

---

## Minor Chat UI Pitfalls

### C13) `lang` Attribute Set to `"en"` While Primary Content Is Vietnamese

**What goes wrong:** The existing `index.html` declares `<html lang="en">`. After the bilingual revamp, the majority of visible UI text (verdict, cues, next steps) is Vietnamese. Screen readers use `lang` to select the correct speech synthesis voice and pronunciation engine. With `lang="en"`, NVDA/JAWS will read Vietnamese text with English phonological rules, producing unintelligible pronunciation.

**Prevention:**
- Change `<html lang="vi">` as the primary language.
- Add `lang="en"` attributes on inline elements containing English technical terms (e.g., `<span lang="en">High risk</span>` for the risk tier label).

**Phase:** Phase 1 of chat revamp (HTML scaffolding).

---

### C14) Typing Indicator Bubble Left Orphaned on Network Error

**What goes wrong:** A common UX pattern is to insert a "bot is typing" placeholder bubble immediately after the user sends, then replace it with the real response. If the fetch throws (runtime not started, network reset), the placeholder bubble must be removed. If the `finally` block only calls `setBusyState(false)` without removing the placeholder, the typing indicator sits permanently in the thread.

**Prevention:**
- Store a reference to the placeholder bubble element: `let pendingBubble = appendPlaceholder()`.
- In the `catch` block: remove `pendingBubble` from the DOM, then `appendErrorBubble(error)`.
- In the `finally` block: if `pendingBubble` is still attached (success path already replaced it with the real bubble), remove it as a safety net.

**Phase:** Phase 2 of chat revamp (typing indicator feature).

---

### C15) Missing `autocomplete="off"` and `spellcheck="false"` on Message Input

**What goes wrong:** Browsers show autocomplete suggestions for the message textarea. Vietnamese IME (input method editors) combined with browser autocomplete interact poorly: the autocomplete dropdown covers the suggestion from the IME and the user cannot complete diacritic composition. `spellcheck="true"` (the default) marks most Vietnamese-English mixed scam text as misspelled, littering the input with red underlines and confusing users about whether the text is corrupted.

**Prevention:**
- Add `autocomplete="off" spellcheck="false"` to the message textarea.
- Add `autocorrect="off" autocapitalize="none"` for iOS Safari, which auto-capitalizes the first character of input fields and attempts to correct Vietnamese words.

**Phase:** Phase 1 of chat revamp (input bar HTML attributes).

---

## Phase-Specific Warning Matrix (Chat UI)

| Implementation Phase | Pitfall | Priority | Detection Signal |
| ---------------------- | --------- | ---------- | ----------------- |
| HTML scaffolding | ARIA live region registered late (C4) | Critical | Screen reader silent on second message |
| HTML scaffolding | `lang="en"` on Vietnamese-primary page (C13) | High | NVDA reads Vietnamese with English accent |
| HTML scaffolding | Template IDs duplicated in DOM (C8) | Critical | Second bubble overwrites first |
| CSS layout | Mobile viewport height collapse (C6) | Critical | Input bar hidden by keyboard on mobile |
| CSS layout | Bot bubble overflow on narrow screens (C7) | High | URL or long text breaks container width |
| JS data model | DOM as sole history source (C3) | High | Clear button loses conversation |
| JS fetch logic | Re-entrant submit with wsgiref blocking (C2) | Critical | Second request hangs until first resolves |
| JS rendering | Scroll anchor race after insertion (C1) | High | Last bubble clipped on slow devices |
| JS rendering | textContent replaced with innerHTML (C12) | High | XSS on user-pasted content |
| Input UX | Enter/Shift+Enter submit conflict (C11) | Medium | Accidental submit on paste |
| Input UX | IME/autocomplete interference (C15) | Medium | Vietnamese diacritic composition broken |
| Font/text | Vietnamese diacritics on macOS/Linux (C5) | High | Floating/missing tone marks off-Windows |
| Features | Sample button UX in chat context (C10) | Low | User does not notice textarea was filled |
| Features | Typing indicator orphaned on error (C14) | Medium | Permanent spinner in thread |
| Features | Clear-during-in-flight request (C9) | Medium | Orphaned bot bubble after clear |

## Confidence

- **Scroll/layout pitfalls:** High (C1, C6, C7 verified against MDN, CSS-Tricks, and mobile viewport spec).
- **ARIA live region timing:** High (C4 verified against MDN ARIA live regions spec and Sara Soueidan's research).
- **Concurrent fetch / wsgiref blocking:** High (C2 verified against Python wsgiref docs and AbortController MDN spec).
- **Vietnamese font rendering cross-platform:** Medium (C5 — Segoe UI Variable has Vietnamese coverage on Windows; macOS/Linux fallback relies on system-ui and Noto Sans; actual rendering depends on specific OS font installation; recommend live testing on each platform).
- **Template ID duplication:** High (C8 — direct consequence of how `id` attributes work in HTML; no ambiguity).
- **DOM-as-history source-of-truth:** High (C3 — established pattern anti-recommendation across all JS architectures).
