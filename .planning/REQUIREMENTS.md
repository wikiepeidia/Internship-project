# Requirements: Localized Explainable AI (XAI) Engine for Vietnamese Financial Phishing and Threat Detection

**Defined:** 2026-03-18
**Core Value:** Users can safely verify suspicious Vietnamese financial messages on-device with explainable, high-recall detection that minimizes dangerous misses.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data Pipeline

- [x] **DATA-01**: System can scrape seed Vietnamese financial threat examples from NCSC sources into normalized raw records.
- [x] **DATA-02**: System can generate a curated synthetic training dataset of 2,000-3,000 JSONL samples from seed data using a controlled LLM generation pipeline.
- [x] **DATA-03**: System can maintain reproducible dataset versions with split governance to reduce leakage and evaluation contamination.

### Ingestion

- [x] **ING-01**: User can paste raw text messages for analysis from channels such as SMS, Zalo, Messenger, Telegram, and Facebook.
- [x] **ING-02**: System can process Vietnamese and mixed Vietnamese-English text, including common code-switch patterns.

### Detection

- [ ] **DET-01**: System can classify each input message into risk tiers: benign, suspicious, or high-risk.
- [ ] **DET-02**: System can assign in-scope threat labels: bank impersonation, account takeover/social engineering, and light-work-high-pay task scam.

### Explainability

- [ ] **XAI-01**: User receives evidence-linked reasons tied to suspicious spans or cues from the input text.
- [ ] **XAI-02**: User receives actionable, safety-focused recommendations (for example: do not click links, verify identity via trusted voice call).

### Runtime and Deployment

- [x] **RUN-01**: User can run inference in local/offline mode without sending message content to cloud APIs in default operation.
- [x] **RUN-02**: System provides a GGUF quantized inference path that works on consumer laptop CPU/iGPU baseline.
- [x] **RUN-03**: System provides an optional accelerated inference path for prosumer GPU hardware.

### Model Adaptation

- [x] **MOD-01**: System supports LoRA-based fine-tuning of an open-source local model family using project dataset artifacts, with a 4B-primary path for 8GB VRAM and optional larger comparison candidates.

### Evaluation and Safety Gates

- [ ] **EVAL-01**: Offline evaluation reports include overall F1 score and per-class metrics on held-out data.
- [ ] **EVAL-02**: Release gating enforces recall-priority thresholds that minimize false negatives for high-harm scam classes.
- [ ] **EVAL-03**: Release gating includes explanation quality checks using a defined rubric for correctness, relevance, and actionability.

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Explainability Enhancements

- **XAI-03**: User receives calibrated confidence scores with uncertainty-aware wording.
- **XAI-04**: User receives risk decomposition dimensions (for example urgency pressure, spoofing likelihood, credential theft intent).

### Runtime Enhancements

- **RUN-04**: System meets explicit latency targets per hardware profile with automated benchmarking dashboards.

### Product and Channel Expansion

- **CHN-01**: System supports OCR/image-based text extraction from screenshots.
- **CHN-02**: System supports audio/voice scam analysis.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
| ------- | ------ |
| OCR and image understanding | Violates strict v1 text-only boundary and expands scope significantly |
| Voice/call analysis | Requires separate ASR/audio pipeline and is outside current objective |
| Cloud-default inference | Conflicts with privacy-first local/offline value proposition |
| Autonomous actions (auto-report/auto-block/auto-reply) | High harm risk from false positives in early versions |
| Broad generic cybersecurity assistant behavior | Dilutes focused financial scam detection mission |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
| ----------- | ----- | ------ |
| DATA-01 | Phase 1 | Complete |
| DATA-02 | Phase 1 | Complete |
| DATA-03 | Phase 1 | Complete |
| ING-01 | Phase 2 | Complete |
| ING-02 | Phase 2 | Complete |
| DET-01 | Phase 4 | Pending |
| DET-02 | Phase 4 | Pending |
| XAI-01 | Phase 4 | Pending |
| XAI-02 | Phase 4 | Pending |
| RUN-01 | Phase 2 | Complete |
| RUN-02 | Phase 3 | Complete |
| RUN-03 | Phase 3 | Complete |
| MOD-01 | Phase 3 | Complete |
| EVAL-01 | Phase 5 | Pending |
| EVAL-02 | Phase 5 | Pending |
| EVAL-03 | Phase 5 | Pending |

**Coverage:**

- v1 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0 ✅

---
*Requirements defined: 2026-03-18*
*Last updated: 2026-05-11 after Phase 3 completion*
