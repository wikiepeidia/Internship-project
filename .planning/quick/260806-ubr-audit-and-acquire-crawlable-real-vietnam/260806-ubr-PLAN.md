---
quick_id: 260806-ubr
slug: audit-and-acquire-crawlable-real-vietnam
status: planned
created: 2026-08-06T21:56:56.2252018+07:00
mode: quick
autonomous: true
files_modified:
  - src/data_pipeline/schemas.py
  - src/data_pipeline/scraper/real_sources.py
  - tests/data_pipeline/test_real_sources.py
  - .planning/quick/260806-ubr-audit-and-acquire-crawlable-real-vietnam/260806-ubr-SOURCE-AUDIT.md
  - .planning/quick/260806-ubr-audit-and-acquire-crawlable-real-vietnam/260806-ubr-ACQUISITION-MANIFEST.jsonl
  - .planning/quick/260806-ubr-audit-and-acquire-crawlable-real-vietnam/260806-ubr-REAL-SAMPLE.jsonl
must_haves:
  truths:
    - "Every investigated source has a source-specific empirical count or honest lower bound, access result, record unit, and crawl/redistribution assessment."
    - "Advisory articles, incident reports, verbatim message examples, and threat indicators are counted separately rather than presented as interchangeable real cases."
    - "Any acquired row is explicitly marked real-public, provenance-complete, deduplicated against the retained seeds, and never silently merged into synthetic training or evaluation splits."
    - "If no additional source is defensibly collectible, the result says zero and preserves the measured blockers instead of fabricating records."
  artifacts:
    - path: ".planning/quick/260806-ubr-audit-and-acquire-crawlable-real-vietnam/260806-ubr-SOURCE-AUDIT.md"
      provides: "Judge-facing source audit, empirical counts, legal/ethical caveats, and claim boundaries"
    - path: ".planning/quick/260806-ubr-audit-and-acquire-crawlable-real-vietnam/260806-ubr-ACQUISITION-MANIFEST.jsonl"
      provides: "Machine-checkable probe, provenance, deduplication, and artifact-hash evidence"
    - path: "src/data_pipeline/scraper/real_sources.py"
      provides: "Bounded scrape-only audit/collection/verification CLI for qualified sources"
    - path: "tests/data_pipeline/test_real_sources.py"
      provides: "Offline regression coverage for source adapters, provenance, safety, and deduplication"
  key_links:
    - from: "src/data_pipeline/scraper/real_sources.py"
      to: "data/raw/seeds-2026-04-24.jsonl"
      via: "NFC/case-fold/whitespace plus canonical-URL deduplication against the retained real-seed snapshot"
      pattern: "seeds-2026-04-24"
    - from: "src/data_pipeline/scraper/real_sources.py"
      to: ".planning/quick/260806-ubr-audit-and-acquire-crawlable-real-vietnam/260806-ubr-ACQUISITION-MANIFEST.jsonl"
      via: "atomic manifest write containing per-source counts and sample hash"
      pattern: "ACQUISITION-MANIFEST"
    - from: ".planning/quick/260806-ubr-audit-and-acquire-crawlable-real-vietnam/260806-ubr-SOURCE-AUDIT.md"
      to: ".planning/quick/260806-ubr-audit-and-acquire-crawlable-real-vietnam/260806-ubr-ACQUISITION-MANIFEST.jsonl"
      via: "all quantitative prose cites manifest fields rather than recalled totals"
      pattern: "incident|advisory|indicator|message"
---

# Quick Task 260806-ubr: Audit and acquire crawlable real Vietnamese scam data

## Objective

Empirically search for additional public Vietnamese scam data, distinguish genuinely useful incident/message records from editorial advisories and indicator lists, and land a safe reproducible ingestion path where access and reuse are defensible.

The retained snapshot at `data/raw/seeds-2026-04-24.jsonl` is the comparison baseline: 300 extracted snippets, 298 unique after NFC + case-fold + whitespace normalization, and 67 unique `tinnhiemmang.vn` advisory URLs. These are not 67 incident reports and the 300 snippets are not uniformly verbatim scam messages. The final 3,000-row corpus remains synthetic; it currently traces to only 26 of those 67 URLs and is highly source-concentrated. This task may improve real seed diversity, but it must not change the training/evaluation lineage or claim real-world evaluation without a separate labeling and split-governance step.

## Context

- `src/data_pipeline/scraper/ncsc_scraper.py` already tries NCSC, Chống Lừa Đảo, Tín Nhiệm Mạng, and scam.vn with Requests/BeautifulSoup and a Playwright fallback, but failures are silent and there is no scrape-only CLI or source status report.
- `src/data_pipeline/scraper/extractors.py` can extract advisory links and candidate payloads, but its broad content heuristic also admits third-person advisory prose.
- `src/data_pipeline/schemas.py::SeedRecord` supplies the downstream-compatible four-field seed contract; acquired evidence needs additional provenance without breaking legacy rows.
- `src/data_pipeline/processing/normalizer.py::normalize_text`, `src/data_pipeline/processing/dedup.py::lexical_dedup`, and `src/data_pipeline/versioning/manifest.py` provide established normalization, near-duplicate, and SHA-256 patterns.
- Raw/synthetic data is intentionally ignored by git. Durable evidence for this quick task therefore lives beside this plan; a capped real sample is retained there only when redistribution is defensible.
- Preserve the unrelated untracked `documents/references/` directory and all other user changes.

## Tasks

<tasks>

<task type="tracer">
  <name>Task 1: Empirically qualify public sources and trace one candidate from page/feed to provenance record</name>
  <files>.planning/quick/260806-ubr-audit-and-acquire-crawlable-real-vietnam/260806-ubr-SOURCE-AUDIT.md, .planning/quick/260806-ubr-audit-and-acquire-crawlable-real-vietnam/260806-ubr-ACQUISITION-MANIFEST.jsonl</files>
  <action>
Probe the live web because availability, pagination, and policies are time-dependent. Start with `tinnhiemmang.vn/canh-bao-lua-dao`, `canhbao.khonggianmang.vn`, `chongluadao.vn`, and `scam.vn`, then use targeted Vietnamese/English searches to cover official NCSC/AIS and police warning portals, public Vietnamese indicator/report feeds, and original dataset hosts or repositories (Hugging Face, GitHub, Kaggle, Zenodo or an academic dataset page). Audit at least 12 distinct candidate endpoints across at least four source families; search-result pages do not count as sources.

For each endpoint record: source and endpoint IDs; publisher; canonical URL; probe timestamp; HTTP/status or DNS result; access method (`download`, documented API, Requests/BeautifulSoup, or Playwright rendering); robots URL/result; Terms and license/reuse URL/result; whether collection and redistribution are separately allowed, forbidden, or unknown; authentication/CAPTCHA/anti-bot state; pagination or cursor pattern; pages/items actually inspected; terminal-page or repeated-cursor evidence; raw item count; unique item URLs; extracted candidate rows; normalized unique rows; duplicates within source; duplicates against the retained 300-row snapshot; net usable rows; PII risk/redaction decision; and confidence. Use `exact`, `lower_bound`, or `bounded_estimate` explicitly. An estimate must include its observed sample, formula, and bounds; when those cannot be justified, report only a lower bound.

Classify the unit for every source as `incident_report`, `verbatim_message_example`, `editorial_advisory`, `threat_indicator`, or `dataset_row`. Never add unlike units into a single “cases” total. Re-probe the current Tín Nhiệm Mạng pagination and report its current live count separately from the April snapshot. For finite pagination, enumerate until a demonstrably empty or repeated terminal page; for large/infinite sources use a documented bounded sample. Trace at least one eligible candidate through fetch, extraction, normalization, canonical URL, content hash, and duplicate comparison as the end-to-end tracer. If no additional endpoint passes the gate, complete the tracer with `eligible_new_records: 0` plus source-specific blockers.

Use ordinary HTTP first and Playwright only to render a page that permits automated access. Do not evade login, CAPTCHA, Cloudflare, robots rules, rate limits, or access controls; do not submit reports or interact with victims. Treat public access as distinct from redistribution or ML-use permission. Do not retain names, emails, phone/account numbers, or other victim identifiers; public malicious indicators may be recorded only as inert text when the source permits it. Write the manifest as one valid JSON object on one JSONL line and write the readable audit from that evidence.
  </action>
  <verify>
    <automated>python -c "import json,pathlib; p=pathlib.Path('.planning/quick/260806-ubr-audit-and-acquire-crawlable-real-vietnam/260806-ubr-ACQUISITION-MANIFEST.jsonl'); rows=[json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]; assert len(rows)==1; d=rows[0]; required={'source_id','record_unit','access','count_method','raw_items','unique_items','duplicates_existing','eligible_new_records','collection_status','redistribution_status'}; assert len(d['sources'])>=12; assert len({s['source_family'] for s in d['sources']})>=4; assert all(required.issubset(set(s)) for s in d['sources']); assert d['existing_snapshot']['rows']==300 and d['existing_snapshot']['unique_source_urls']==67 and d['existing_snapshot']['normalized_unique_texts']==298"</automated>
  </verify>
  <done>The audit contains source-specific empirical evidence for at least 12 endpoints, does not inflate advisories/indicators into incidents, and identifies collectable adapters or an evidenced zero-result without invented data.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement the qualified scrape-only collectors with explicit provenance and safe deduplication</name>
  <files>src/data_pipeline/schemas.py, src/data_pipeline/scraper/real_sources.py, tests/data_pipeline/test_real_sources.py</files>
  <behavior>
    - Legacy four-field `SeedRecord` JSONL remains valid unchanged.
    - A provenance-rich real record serializes with `data_origin=real_public`, a precise record unit, source/canonical URLs, publisher/native ID when available, access and rights statuses, UTC retrieval time, stable content hash, and redaction state; `raw_label_hint` stays null.
    - NFC + case-fold + collapsed-whitespace exact matching, canonical-URL matching, and RapidFuzz near matching remove duplicates while preserving duplicate provenance/counts in the manifest.
    - Source adapters stop on an empty/repeated terminal page, restrict discovered links to the allowlisted host, enforce timeouts/response-size/page/record caps and the existing polite delay, and expose failures instead of silently returning success.
    - Blocked, prohibited, authentication-gated, or redistribution-unknown sources cannot emit a durable sample; mocked source layouts exercise every enabled adapter without network access.
  </behavior>
  <action>
Add a backward-compatible `ProvenancedSeedRecord` derived from `SeedRecord`; keep all new fields required on newly acquired rows while leaving legacy parsing intact. Use record-unit literals that preserve the distinction established in Task 1 and do not promote source categories into the project's four model labels.

Create `src.data_pipeline.scraper.real_sources` as a dedicated `python -m` command with `audit`, `collect`, and offline `verify` subcommands. Read the audited source entries, expose adapters only for sources marked collectible, reuse the existing normalizer/rate limiter/extraction helpers where their live layouts fit, and implement source-specific parsing for every additional viable source. Emit a JSON summary to stdout. The CLI must require explicit output paths, write atomically, refuse to overwrite unless `--replace` is passed, cap `--max-records-per-source`, and accept the retained seed path for cross-source deduplication. It must never continue into synthetic generation, judging, labeling, or split building.

Canonicalize URLs without fragments or tracking parameters, derive a stable provenance/content identifier, preserve all contributing URLs when duplicates collapse, and redact victim PII before persistence. Retain malicious URLs/domains only as inert text when the source and rights assessment permit it. Use existing dependencies only (`requests`, BeautifulSoup, Playwright when allowed, Pydantic, RapidFuzz); add no package installation. Tests must use mocked/captured structural fixtures, cover error/pagination/robots/rights gates and schema compatibility, and must not depend on the live sites being up.
  </action>
  <verify>
    <automated>python -m pytest tests/data_pipeline/test_real_sources.py tests/data_pipeline/test_scraper.py tests/data_pipeline/test_schemas.py tests/data_pipeline/test_normalizer.py tests/data_pipeline/test_dedup.py -x --tb=short -q</automated>
  </verify>
  <done>The repo has a tested scrape-only CLI that can reproducibly collect only qualified sources, emits explicit real-data provenance, preserves legacy seeds, and reports rather than hides access or extraction failures.</done>
</task>

<task type="auto">
  <name>Task 3: Run the bounded acquisition and freeze honest judge-facing evidence</name>
  <files>.planning/quick/260806-ubr-audit-and-acquire-crawlable-real-vietnam/260806-ubr-SOURCE-AUDIT.md, .planning/quick/260806-ubr-audit-and-acquire-crawlable-real-vietnam/260806-ubr-ACQUISITION-MANIFEST.jsonl, .planning/quick/260806-ubr-audit-and-acquire-crawlable-real-vietnam/260806-ubr-REAL-SAMPLE.jsonl</files>
  <action>
Run the new audit/collect commands against only the qualified live adapters, with a maximum of 50 retained rows per source and the project’s 2–5 second polite delay. Deduplicate within/across new sources and against `data/raw/seeds-2026-04-24.jsonl`. Record gross, normalized-unique, duplicate-existing, net-new, unique-source-URL, and record-unit counts per source, plus sample SHA-256/bytes/rows and the exact command. Also record hashes of `data/synthetic/recovered-balanced.jsonl` and the three `data/splits/recovered-balanced/*.jsonl` files before and after the run to prove this task did not alter training or evaluation lineage.

Persist `260806-ubr-REAL-SAMPLE.jsonl` only when at least one source has defensible redistribution permission and the selected rows are PII-redacted; otherwise omit the durable sample and record `sample_withheld` with the precise rights/privacy reason while keeping local ignored raw output only if collection itself is allowed. The manifest and audit must still represent a zero-row outcome truthfully. Never infer project labels from page category, never convert indicators/advisories into DatasetRecord rows, and never merge into `data/synthetic`, `data/processed`, or `data/splits`.

Finish `260806-ubr-SOURCE-AUDIT.md` with a compact judge-facing findings table and claim boundary: the April file contains 300 extracted advisory snippets from 67 unique pages (298 normalized-unique), not 300 independent incidents; report new net real rows separately by unit and source; state that the existing 3,000-row model corpus remains synthetic and unchanged; and state exactly what additional labeling, human review, seed-group isolation, and retraining would be required before acquired seeds could support training or independent evaluation. Include failed and prohibited sources, not only successes.
  </action>
  <verify>
    <automated>python -m src.data_pipeline.scraper.real_sources verify --manifest .planning/quick/260806-ubr-audit-and-acquire-crawlable-real-vietnam/260806-ubr-ACQUISITION-MANIFEST.jsonl --sample .planning/quick/260806-ubr-audit-and-acquire-crawlable-real-vietnam/260806-ubr-REAL-SAMPLE.jsonl --existing-seeds data/raw/seeds-2026-04-24.jsonl</automated>
  </verify>
  <done>The acquisition manifest verifies offline; any retained sample is real-public, permitted, redacted, schema-compatible, hashed, and net-new; otherwise the durable result is an evidenced zero/withheld outcome. Synthetic and split artifacts are byte-identical before and after.</done>
</task>

</tasks>

## Threat Model

### Trust Boundaries

| Boundary | Description |
|---|---|
| Public web → collector | Untrusted HTML/JSON, malicious links, oversized responses, redirects, and adversarial content enter local parsing. |
| Public reports → durable evidence | Public pages may still contain victim PII or lack redistribution/ML-use permission. |
| Real seed evidence → model corpus | Weak categories and advisory prose must not be mistaken for human-labeled training/evaluation examples. |

### STRIDE Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|---|---|---|---|---|---|
| T-UBR-01 | Spoofing | Source identity/provenance | medium | mitigate | Allowlist audited hosts, preserve canonical/native identifiers, timestamps, and content hashes. |
| T-UBR-02 | Tampering | Fetched content and manifest | high | mitigate | Atomic writes, SHA-256 evidence, deterministic normalization, and offline manifest verification. |
| T-UBR-03 | Information Disclosure | User-submitted reports/sample | high | mitigate | Exclude private/authenticated submissions, redact victim identifiers, and withhold durable content when redistribution is not defensible. |
| T-UBR-04 | Denial of Service | Remote sites and local collector | medium | mitigate | Polite delay, timeout, response-size/page/row caps, repeated-page detection, and no bypass of anti-bot controls. |
| T-UBR-05 | Elevation/SSRF | Discovered URLs and browser fallback | high | mitigate | Fixed source registry, HTTP(S)-only same-host link resolution, redirect validation, and no arbitrary-URL CLI fetch. |
| T-UBR-06 | Tampering | Real-to-synthetic lineage boundary | high | mitigate | Real records remain seed artifacts with null label hints; protected corpus hashes must remain unchanged. |
| T-UBR-SC | Tampering | Package supply chain | low | accept | No package installation is permitted; implementation uses dependencies already declared by the project. |

## Verification

- Focused scraper/schema/normalization/deduplication tests pass without live network access.
- The offline verifier reconciles source counts, record units, hashes, deduplication totals, sample policy, and protected corpus hashes.
- The audit states current live results with timestamps and distinguishes exact counts, lower bounds, and bounded estimates.
- A zero/withheld result is considered valid only when every candidate has a recorded access, policy, duplication, relevance, or privacy blocker.

## Source Coverage Audit

| Source | ID | Feature / Requirement | Task | Status | Notes |
|---|---|---|---|---|---|
| GOAL | Q-260806 | Audit broadly, quantify honestly, and acquire defensible real Vietnamese scam data where feasible | 1–3 | COVERED | Empirical audit, collector, bounded run, and evidence are all included. |
| REQ | — | No ROADMAP requirement IDs apply to this quick task | — | N/A | Quick mode is intentionally outside the completed milestone roadmap. |
| RESEARCH | EXEC-01 | Live source discovery and temporal probing | 1 | COVERED | No separate research artifact was requested; discovery is an explicit execution deliverable. |
| CONTEXT | — | No quick-task CONTEXT.md or D-XX decisions exist | — | N/A | The invoking task constraints are represented directly in objective, tasks, and must-haves. |

## Success Criteria

- At least 12 candidate endpoints across four source families have source-specific empirical evidence and rights/access status.
- Current Tín Nhiệm Mạng availability and count are re-measured; the retained 67-URL snapshot is never called 67 incident cases.
- Every eligible adapter is tested offline and every live failure remains visible in the audit.
- Net-new records, if any, validate as provenance-rich real seeds and are deduplicated against the retained snapshot.
- The 3,000-row synthetic corpus and its train/validation/test files remain unchanged and are still described as synthetic.
- If acquisition yields no defensible rows, the audit is still complete, quantitative, and explicit about why.

## Output

Create `.planning/quick/260806-ubr-audit-and-acquire-crawlable-real-vietnam/260806-ubr-SUMMARY.md` when execution completes.
