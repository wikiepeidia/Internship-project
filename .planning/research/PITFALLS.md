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
|-------------|----------------|------------------|------------|
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
