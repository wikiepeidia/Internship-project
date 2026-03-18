# Technology Stack (2026): Vietnamese Offline XAI Phishing Text Detection

**Project:** Localized, offline-capable explainable AI for Vietnamese financial phishing/social engineering text detection  
**Date:** 2026-03-18  
**Scope guardrail:** Text-only pipeline (no OCR/image stack)

## Executive Recommendation

Build with a **Python-first training/evaluation stack** and a **GGUF + llama.cpp local inference runtime** for laptop deployment.

- Training/data: PyTorch + Transformers + PEFT + TRL, with QLoRA where GPU memory is limited.
- Runtime: quantized GGUF model served by `llama.cpp` (or embedded via `llama-cpp-python`) for CPU baseline, optional CUDA/Vulkan acceleration.
- Product layer: strict structured JSON outputs + deterministic rule checks for explainability and safety.

This is the most standard, maintainable 2026 path for small teams shipping domain LLMs to consumer devices.

## Recommended Stack (Prescriptive)

### 1. Core Platform

| Layer | Choice | Version family (2026) | Why this is the default | Confidence |
|---|---|---|---|---|
| Language/runtime | Python | 3.11-3.12 | Best library support for NLP fine-tuning and evaluation; stable packaging ecosystem | HIGH |
| DL framework | PyTorch | 2.10.x stable | Current stable baseline with broad ecosystem support and CUDA/CPU paths | HIGH |
| Model APIs | Hugging Face Transformers | 4.5x-5.x family | Standard model-definition layer and interoperability hub | HIGH |
| Data format | JSONL + Parquet | N/A | JSONL for training examples, Parquet for analytics and reproducibility | HIGH |

### 2. Scraping Pipeline (Vietnam threat seed collection)

| Component | Choice | Version family | Why | Confidence |
|---|---|---|---|---|
| Crawl framework | Scrapy | 2.13+ | Reliable, resumable, production-grade crawling | HIGH |
| JS rendering fallback | Playwright (Python) | 1.5x | Needed for dynamic anti-bot/dynamic pages | HIGH |
| Boilerplate extraction | Trafilatura | 2.x | Strong text extraction quality from news/advisory pages | MEDIUM |
| HTML parsing fast path | selectolax + lxml | selectolax 0.3x, lxml 5.x | Fast parsing and robust fallback selectors | MEDIUM |
| Scheduling | APScheduler or cron in CI runner | 3.10+ | Simple recurring pulls, easy offline-friendly operation | HIGH |

**Do not use (for this scope):**

- Selenium-first scraping stacks (heavier, slower, less maintainable than Scrapy+Playwright).
- Spark-based crawling ETL for this scale (2k-3k synthetic target; overkill).

### 3. Dataset Processing and Quality Layer

| Component | Choice | Version family | Why | Confidence |
|---|---|---|---|---|
| Table transforms | Polars (primary), pandas (interop) | Polars 1.x, pandas 2.2+ | Polars is faster for batch transformations; pandas compatibility remains useful | MEDIUM |
| Validation schema | Pydantic | 2.x | Strict schema checks for structured labels/explanations | HIGH |
| Dedup/similarity | RapidFuzz + MinHash/LSH (`datasketch`) | RapidFuzz 3.x, datasketch 1.x | Fast near-duplicate control for synthetic and scraped text | MEDIUM |
| Language normalization | underthesea + regex + Unicode normalization (`ftfy`) | underthesea 6.x, ftfy 6.x | Practical Vietnamese preprocessing and cleanup | MEDIUM |
| Data versioning | DVC | 3.x | Reproducible datasets/models without bloating git | HIGH |

**Do not use:**

- Pure manual spreadsheet curation as the source of truth.
- Aggressive stopword stripping/token surgery that destroys scam indicators (URLs, phone/account strings, urgency markers).

### 4. Fine-tuning Stack (LoRA / QLoRA)

| Component | Choice | Version family | Why | Confidence |
|---|---|---|---|---|
| Base model family | Open 7B-8B instruct model with good multilingual support (Qwen/Llama-class) | latest stable checkpoints | Best quality-to-local-runtime tradeoff for laptop target | MEDIUM |
| Training toolkit | Transformers + Accelerate + PEFT | Accelerate 1.x, PEFT 0.1x | De facto stack for LoRA/QLoRA fine-tuning | HIGH |
| Trainer | TRL `SFTTrainer` first; optional `DPOTrainer` later | TRL 0.2x | Fast path for domain SFT, upgrade path for preference optimization | HIGH |
| QLoRA kernel | bitsandbytes 4-bit NF4 + double quant | bitsandbytes 0.4x | Standard memory-efficient fine-tuning pattern | HIGH |
| Experiment tracking | MLflow or W&B (self-host/offline mode) | MLflow 2.x+ / W&B offline | Reproducibility and auditability for security-sensitive model changes | MEDIUM |

**Prescriptive training policy:**

- Start with **LoRA rank 16-64**, target key projection modules.
- Use **QLoRA** when GPU VRAM < 24 GB.
- Keep one immutable baseline checkpoint and evaluate every adapter against same holdout slices.

**Do not use:**

- Full-parameter fine-tuning for v1 (costly, slower iteration, poor fit for laptop deployment goals).
- RLHF/RL-heavy post-training before achieving stable high-recall SFT baseline.

### 5. Quantization and Local Inference (offline first)

| Component | Choice | Version family | Why | Confidence |
|---|---|---|---|---|
| Runtime | llama.cpp | rolling builds (pin tested build) | Most standard offline GGUF runtime for CPU and mixed hardware | HIGH |
| Python embedding | llama-cpp-python | 0.3x | Easy in-process integration for local app/service | HIGH |
| Model format | GGUF | current | Native for llama.cpp ecosystem | HIGH |
| Default quant | Q4_K_M (baseline), Q5_K_M (quality-first) | N/A | Good laptop latency/quality tradeoff | HIGH |
| Optional acceleration | CUDA/Vulkan backend in llama.cpp | current supported backend | Optional speed-up on prosumer GPU | HIGH |

**Laptop baseline target:**

- CPU-only: 7B-8B Q4_K_M with context tuned for short-message triage.
- Optional GPU: same model with larger context and faster throughput.

**Do not use:**

- vLLM/TensorRT-LLM as primary local runtime for consumer-laptop offline app (excellent server stacks, not best default for this edge target).
- Extremely aggressive quantization (e.g., 2-bit) for safety-critical phishing recall in v1.

### 6. Evaluation Stack (recall-prioritized)

| Component | Choice | Version family | Why | Confidence |
|---|---|---|---|---|
| Core metrics | scikit-learn metrics | 1.8.x | Standard precision/recall/F1/calibration tooling | HIGH |
| LLM eval harness | `evaluate` + custom rubric scripts | evaluate 0.4+ | Blend standard metrics and explanation-quality checks | MEDIUM |
| Test data slicing | stratified + adversarial slices | N/A | Required for scam variants, mixed-language, obfuscation patterns | HIGH |
| Regression suite | pytest + golden JSON outputs | pytest 8.x | Prevents silent behavior drift in explanation schema | HIGH |

**Release gate (recommended):**

- Recall-weighted acceptance with minimum floor for precision and explanation correctness.
- Keep latency checks for CPU baseline device class.

**Do not use:**

- Single aggregate F1 as sole ship criterion.
- Human-only manual spot checks without deterministic regression suite.

### 7. Safety Guardrails and Explainability Contract

| Component | Choice | Version family | Why | Confidence |
|---|---|---|---|---|
| Output contract | Pydantic JSON schema + strict parser retries | 2.x | Enforces stable explainable structure for UI and auditing | HIGH |
| Constrained generation | llama.cpp grammar / JSON schema-constrained outputs | current | Reduces malformed outputs, improves deterministic parsing | HIGH |
| Rule-based safety layer | Deterministic regex/heuristics over URLs, bank keywords, urgency/credential asks | N/A | Catches obvious high-risk patterns and supports explanation traceability | HIGH |
| Prompt-injection resistance | Input sanitization + instruction boundary templates + refusal policy for non-scope asks | N/A | Limits model drift and jailbreak behavior in a narrow domain app | MEDIUM |
| PII discipline | Local redaction utilities before logging | N/A | Privacy-by-default in local telemetry and debug traces | HIGH |

**Do not use:**

- Free-form prose-only outputs as the primary contract.
- Cloud moderation dependencies in the critical inference path (breaks offline/privacy goals).

### 8. Packaging and Deployment (consumer laptop baseline)

| Component | Choice | Version family | Why | Confidence |
|---|---|---|---|---|
| Local API service | FastAPI + Uvicorn around llama.cpp binding/server | FastAPI 0.11x, Uvicorn 0.3x | Clean local interface and easy testability | HIGH |
| Desktop app shell | Tauri 2 + TypeScript UI (optional) | Tauri 2.x | Lightweight cross-platform desktop packaging | MEDIUM |
| Env/package manager | uv + lockfile (or Poetry if team standardized) | uv 0.x | Fast reproducible environments | MEDIUM |
| Model artifact delivery | Versioned GGUF + adapter manifest + checksum | N/A | Safe local updates and rollback | HIGH |
| Windows distribution | MSIX/winget package + signed binaries | current tooling | Practical enterprise/consumer deployment path | MEDIUM |

**Do not use:**

- Docker as the only deployment strategy for non-technical consumer laptops.
- Remote-only inference fallback as primary mode.

## What Not To Use (Global)

1. OCR/image pipelines in v1 (out of scope, adds major complexity).
2. Giant 30B+ local models as baseline target (poor laptop UX and update footprint).
3. End-to-end agent frameworks for core classification loop (unnecessary latency and unpredictability).
4. Unversioned synthetic data generation without provenance metadata.

## Suggested Baseline Build Profiles

### Profile A: CPU-first (default)

- 7B-8B instruct model, LoRA-adapted for Vietnamese phishing domain.
- GGUF Q4_K_M.
- llama.cpp local server + FastAPI wrapper.
- Deterministic JSON output + rules overlay.

### Profile B: Optional GPU acceleration

- Same model family with Q5_K_M (or higher precision where memory allows).
- CUDA-enabled llama.cpp backend.
- Larger context window and stricter evaluation thresholds before promotion.

## Sources (verification basis)

- PyTorch local install/stable matrix: <https://pytorch.org/get-started/locally/>
- Hugging Face Transformers docs: <https://huggingface.co/docs/transformers/index>
- Hugging Face PEFT docs: <https://huggingface.co/docs/peft/index>
- Hugging Face TRL docs: <https://huggingface.co/docs/trl/index>
- llama.cpp repo/docs: <https://github.com/ggml-org/llama.cpp>
- ONNX Runtime docs (alternative runtime context): <https://onnxruntime.ai/docs/>
- scikit-learn release/news: <https://scikit-learn.org/stable/>
- LM Studio docs (local runtime ecosystem signal): <https://lmstudio.ai/docs>

## Confidence Notes

- **HIGH:** Widely adopted OSS stack components with active official docs and ecosystem momentum.
- **MEDIUM:** Exact 2026 minor versions and some Vietnam-specific preprocessing choices depend on local benchmark outcomes and data characteristics.
- **LOW:** None in final recommendations; uncertain options were excluded from prescriptive path.
