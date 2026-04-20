# Phase 1: Data Foundation and Split Governance - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-10 (updated 2026-04-10)
**Phase:** 01-data-foundation-and-split-governance
**Areas discussed:** NCSC Seed Collection, Synthetic Generation, Dataset Schema, Versioning & Splits

---

## UPDATE SESSION (2026-04-10)

### Seed Collection — Backup Sources and Scraper Reliability Risk

**Context:** NCSC site (khonggianmang.vn) and other scraping targets may be down or unreliable at runtime. User identified concrete backup sources and explicit fallback strategy. This is a critical runtime risk.

| Option | Description | Selected |
|--------|-------------|----------|
| Waterfall priority | Try sources in order: NCSC -> chongluadao -> tinnhiemmang -> newspapers | ✓ |
| Parallel scrape all | Hit all 4 sources simultaneously | |
| Best two only | NCSC + chongluadao.vn only | |

**User's choice:** Waterfall priority — try each in order, aggregate all that work.
**Sources identified:**
1. khonggianmang.vn (NCSC primary)
2. chongluadao.vn (community-driven, "goldmine")
3. tinnhiemmang.vn (NCSC secondary)
4. VnExpress / Tuổi Trẻ ("Lừa đảo trực tuyến" tags)

### Seed Target with Multiple Sources

| Option | Description | Selected |
|--------|-------------|----------|
| Keep 100-300 | Multiple sources are fallbacks, not multipliers | ✓ |
| Raise to 300-500 | More sources = more seeds | |
| No fixed target | Take whatever we get | |

**User's choice:** Keep 100-300. Stop once target is reached.

### Scraper Architecture

| Option | Description | Selected |
|--------|-------------|----------|
| Unified interface | Base class with extract() -> SeedRecord[]. Each source = subclass. | ✓ |
| Separate modules | Each source is standalone script | |

**User's choice:** Unified interface — adding sources = adding a config/subclass.

---

## NCSC Seed Collection

### Q1: How to get seed threat examples from NCSC?

| Option | Description | Selected |
|--------|-------------|----------|
| Web scraping | Automated scraper pulling from khonggianmang.vn | |
| Manual collection | Browse and copy-paste examples | |
| Mixed approach | Manual first, then automate | |
| Other (custom) | Python scraper (BS4/Playwright) extracting raw phishing payloads from article DOM | ✓ |

**User's choice:** Custom — Python scraper targeting khonggianmang.vn, parsing DOM for actual SMS/Zalo phishing scripts within articles. Polite scraping with randomized delays.
**Notes:** User has clear technical vision for the scraper implementation.

### Q2: Expected seed volume?

| Option | Description | Selected |
|--------|-------------|----------|
| 50-100 seeds | Focused recent advisories, ~20-30x expansion needed | |
| 100-300 seeds | Deep archives or supplementary sources, ~10x expansion | ✓ |
| Not sure yet | Run scraper first, adjust later | |

**User's choice:** 100-300 seeds

### Q3: Supplement with other sources?

| Option | Description | Selected |
|--------|-------------|----------|
| NCSC only | Focused and traceable | |
| NCSC + other sources | Also scrape forums, news | |
| Other (custom) | NCSC first, fallback to others if insufficient | ✓ |

**User's choice:** NCSC primary, fallback to alternatives only if NCSC is insufficient/inefficient.

### Q4: Output language?

| Option | Description | Selected |
|--------|-------------|----------|
| Vietnamese only | Keep raw text authentic | |
| Vietnamese + English gloss | Add translations for review | |
| Other (custom) | Vietnamese with natural code-switching | ✓ |

**User's choice:** Vietnamese with targeted English loanwords/tech terms (OTP, Internet Banking, etc.) and teencode (SMS shorthand). Must match real-world phishing linguistic distribution.
**Notes:** Critical domain insight — synthetic generation prompts must explicitly instruct code-switching.

---

## Synthetic Generation

### Q1: Which LLM API?

| Option | Description | Selected |
|--------|-------------|----------|
| Claude API | Strong instruction following, user already in ecosystem | |
| OpenAI GPT-4o | Proven multilingual | |
| Mix / best of both | One for generation, other for validation | |
| You decide | Claude discretion | |
| Other (custom) | Claude + Gemini + OpenRouter (pilot comparison) | ✓ |

**User's choice:** Claude API for premium high-quality expansion; Gemini for bulk cost-effective variations; OpenRouter for experiment/fallback. Pilot comparison script validates model quality before scale.

### Q2: Generation pipeline approach?

| Option | Description | Selected |
|--------|-------------|----------|
| Claude API primary | Use Claude, fallback to cheaper for bulk | |
| Free-tier first | Minimize cost, Claude only for validation | |
| Tiered approach | Claude for complex, Gemini for bulk, OpenRouter for fallback/experiment | ✓ |

**User's choice:** Tiered approach — Claude for complex seed expansion and high-quality reference path; Gemini for bulk variations at optimal cost/performance; OpenRouter as experiment/fallback. Pilot comparison validates realistic Vietnamese code-switching before scale.

### Q3: Quality validation?

| Option | Description | Selected |
|--------|-------------|----------|
| Automated + spot-check | LLM-as-judge + 5-10% manual review | ✓ |
| Full manual review | Review every sample | |
| Automated only | LLM-as-judge + heuristic filters | |

**User's choice:** Automated + spot-check (recommended)

### Q4: Class distribution?

| Option | Description | Selected |
|--------|-------------|----------|
| Balanced across classes | Equal per threat class + benign | ✓ |
| Weighted by frequency | Match real-world distribution | |
| You decide | Claude discretion | |

**User's choice:** Balanced — with strong rationale about recall maximization. Real-world imbalance addressed at evaluation, not training.
**Notes:** User explicitly argued against frequency-weighted training as causing majority-class bias and recall failure on minority classes.

---

## Dataset Schema

### Q1: JSONL record fields?

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal | text, label, risk_tier, source, language_tags | |
| Rich metadata | Minimal + channel, suspicious_spans, explanation_draft, generation_model | |
| Other (custom) | Custom XAI-optimized rich schema | ✓ |

**User's choice:** Custom rich schema: text, label, suspicious_spans (array), xai_explanation (teacher model reasoning), source (provenance tag). Designed for XAI instruction tuning.
**Notes:** User argued that minimal schema bottlenecks fine-tuning. Teacher model reasoning must be captured at generation time.

### Q2: Risk tier as field or derived?

| Option | Description | Selected |
|--------|-------------|----------|
| Include as field | Explicit in training data | ✓ |
| Derive from label | Lookup table at inference | |
| You decide | Claude discretion | |

**User's choice:** Explicit field — risk is contextual (same label, different severity). Eliminates post-processing middleware.
**Notes:** Strong argument about contextual risk assessment and clean end-to-end inference architecture.

---

## Versioning & Splits

### Q1: Dataset versioning approach?

| Option | Description | Selected |
|--------|-------------|----------|
| Git + SHA hashes | Store in repo, commit tags, integrity hashes | ✓ |
| DVC | Data Version Control with remote storage | |
| HuggingFace Datasets | Push to HF Hub | |
| You decide | Claude discretion | |

**User's choice:** Git + SHA256 — proprietary data, <10MB, DVC is overkill, HF Hub violates data governance.

### Q2: Split ratios?

| Option | Description | Selected |
|--------|-------------|----------|
| 80/10/10 | Standard, maximize training data | ✓ |
| 70/15/15 | More eval/test data | |
| You decide | Claude discretion | |

**User's choice:** 80/10/10 default, adjustable based on dataset size. Multiple eval runs if feasible.

### Q3: Leakage prevention?

| Option | Description | Selected |
|--------|-------------|----------|
| Seed-level splitting | Split before expansion, keep families together | |
| Record-level splitting | Random split at record level | |
| Both + dedup check | Seed-level + semantic similarity check | ✓ |

**User's choice:** Both + dedup — seed-level mandatory, plus programmatic semantic similarity check. Belt-and-suspenders.
**Notes:** User identified this as the most critical threat to F1 validity. Detailed explanation of near-duplicate contamination risk.

---

## Claude's Discretion

- Specific scraping library choice (BS4 vs Playwright) based on NCSC site structure
- LLM-as-judge prompt design for quality validation
- Choice of lightweight embedding model for cross-split dedup
- Threshold tuning for semantic similarity dedup

## Deferred Ideas

None — discussion stayed within phase scope
