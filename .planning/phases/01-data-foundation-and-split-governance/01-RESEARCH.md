# Phase 1: Data Foundation and Split Governance - Research

**Researched:** 2026-04-10
**Domain:** Vietnamese phishing text dataset pipeline -- scraping, synthetic generation, JSONL schema, versioning, split governance
**Confidence:** HIGH

## Summary

Phase 1 builds a reproducible Vietnamese financial phishing dataset from scratch: scrape 100-300 seed threat examples from Vietnam NCSC (khonggianmang.vn / canhbao.ncsc.gov.vn), expand to 2,000-3,000 synthetic JSONL samples via tiered LLM generation (Claude API for complex examples, DeepSeek/OpenRouter for bulk), enforce XAI-optimized schema with rich metadata fields, and lock down train/val/test splits with seed-level governance and semantic deduplication.

The core technical risks are: (1) NCSC site scraping reliability -- the site may use JavaScript rendering and its DOM structure must be discovered at implementation time, (2) synthetic data mode collapse producing repetitive templates rather than linguistically diverse Vietnamese phishing examples, and (3) data leakage through near-duplicate synthetic variants crossing split boundaries. All three have well-established mitigation strategies documented below.

**Primary recommendation:** Build the pipeline as a sequential Python CLI with four stages (scrape, generate, validate, split+version), each producing JSONL artifacts tracked by SHA256 manifests in git. Use Pydantic for schema enforcement at every stage boundary.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Python-based scraper using BeautifulSoup or Playwright targeting khonggianmang.vn threat advisories. Must parse DOM to extract actual raw phishing text payloads (SMS/Zalo scripts) embedded within articles, not just alert titles.
- D-02: Implement polite scraping with randomized delays to respect NCSC rate limits and avoid IP blocks.
- D-03: Target 100-300 usable seed examples from NCSC.
- D-04: NCSC is the primary seed source. Fall back to other Vietnamese sources (forums, news) only if NCSC yields insufficient seeds.
- D-05: Output language is Vietnamese with natural code-switching -- English fintech loanwords and teencode/SMS shorthand must be preserved, not normalized away.
- D-06: Tiered generation approach -- Claude API for high-quality complex examples; cheaper models (DeepSeek via Colab, OpenRouter) for bulk simple variations.
- D-07: User has Claude API access. Does NOT have OpenAI API key. Budget-conscious.
- D-08: Generation prompts must explicitly instruct the LLM to naturally code-switch and use common abbreviations.
- D-09: Quality validation: LLM-as-judge + manual spot-check of 5-10% subset.
- D-10: Balanced class distribution across all threat classes plus robust benign class.
- D-11: Rich XAI-optimized JSONL schema: text, label, risk_tier, suspicious_spans, xai_explanation, source.
- D-12: Risk tier is contextual and must be an explicit field, not a static label-to-tier lookup.
- D-13: Store JSONL files directly in Git repository (dataset is <10MB at 3K records). No DVC, no HuggingFace Hub.
- D-14: Version via git commit tags + SHA256 hash manifests.
- D-15: Default split ratio 80/10/10 (train/validation/test).
- D-16: Seed-level splitting is MANDATORY -- all synthetic variants of a seed must stay in the same split.
- D-17: Semantic similarity check across splits after seed-level splitting.

### Claude's Discretion
- Specific scraping library choice (BeautifulSoup vs Playwright) based on NCSC site structure
- Exact LLM-as-judge prompt design for quality validation
- Choice of lightweight embedding model for cross-split dedup
- Threshold tuning for semantic similarity dedup

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | System can scrape seed Vietnamese financial threat examples from NCSC sources into normalized raw records | NCSC scraping architecture (BS4 + Playwright fallback), Pydantic schema validation, polite scraping patterns |
| DATA-02 | System can generate a curated synthetic training dataset of 2,000-3,000 JSONL samples from seed data using a controlled LLM generation pipeline | Tiered Claude/DeepSeek/OpenRouter generation architecture, LLM-as-judge quality gate, diversity metrics |
| DATA-03 | System can maintain reproducible dataset versions with split governance to reduce leakage and evaluation contamination | Git + SHA256 manifests, seed-level splitting algorithm, sentence-transformers semantic dedup, manifest schema |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Conventional Commits format** required for all git operations in this phase
- **No hardcoded secrets** -- API keys (Claude, DeepSeek, OpenRouter) must come from environment variables or .env files (excluded from git)
- **Run tests before marking implementation tasks complete**
- **Update docs/ files** after significant changes
- **TypeScript strict mode** is the project default but Phase 1 is Python-only data pipeline -- Python code style should follow equivalent discipline (type hints, no console debug in committed code)
- **PRD.md is read-only** unless human explicitly approves edits

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12.10 | Runtime | Already installed, latest stable, full type hint support |
| beautifulsoup4 | 4.14.3 | HTML parsing for NCSC advisory pages | Already installed, lightweight, sufficient for server-rendered HTML |
| playwright | 1.58.0 | JS-rendered page fallback scraper | Latest, handles dynamic content NCSC may use; install from PyPI |
| requests | 2.31.0 | HTTP client for static page fetching | Already installed, simple GET requests |
| pydantic | 2.12.5 | JSONL schema validation at every pipeline stage | Already installed, enforces D-11 schema contract |
| polars | 1.39.3 | DataFrame operations for dataset analysis and split computation | Near-latest installed; fast for batch transforms |
| anthropic | 0.93.0 | Claude API client for complex synthetic generation | Already installed, official SDK |
| httpx | 0.28.1 | HTTP client for OpenRouter/DeepSeek API calls | Already installed, async-capable |
| sentence-transformers | 5.4.0 | Multilingual embeddings for semantic dedup across splits | 5.2.3 installed, upgrade to 5.4.0 for latest |
| rapidfuzz | 3.14.5 | Fast fuzzy string matching for lexical dedup | Latest available |
| datasketch | 1.9.0 | MinHash/LSH for scalable near-duplicate detection | Latest available |
| underthesea | 9.2.11 | Vietnamese NLP toolkit (word segmentation, normalization) | Latest, specialized for Vietnamese text |
| pytest | 9.0.2 | Test framework | Already installed |
| scikit-learn | 1.8.0 | Stratified splitting utilities, metrics | Already installed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ftfy | 6.x | Unicode text cleanup and normalization | Fix mojibake/encoding issues in scraped Vietnamese text |
| hashlib (stdlib) | N/A | SHA256 hash computation for manifests | Every dataset build step |
| json (stdlib) | N/A | JSONL read/write | Core data format |
| pathlib (stdlib) | N/A | Cross-platform file path handling | All file operations |
| random/secrets (stdlib) | N/A | Randomized scraping delays, reproducible seeds | Polite scraping (D-02), split reproducibility |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| beautifulsoup4 | Scrapy | Scrapy is production-grade crawl framework but overkill for single-site advisory scraping; BS4 + requests simpler for 100-300 pages |
| polars | pandas | pandas works but Polars is faster; both are fine at this scale, Polars already installed |
| sentence-transformers | PhoBERT + custom SBERT | dangvantuan/vietnamese-embedding is Vietnamese-specific and achieves Pearson 84.87 on STS; paraphrase-multilingual-MiniLM-L12-v2 covers Vietnamese in 50+ languages and is lighter. Start with multilingual MiniLM, switch to Vietnamese-specific if dedup quality is poor |
| datasketch MinHash | Pure cosine similarity matrix | Cosine matrix is O(n^2) which is fine at 3K records; MinHash scales better if dataset grows. Use cosine for cross-split check (small N), MinHash for intra-split dedup (larger N) |

**Installation:**
```bash
pip install beautifulsoup4 playwright pydantic polars anthropic httpx sentence-transformers rapidfuzz datasketch underthesea ftfy scikit-learn pytest
playwright install chromium
```

**Version verification:** All core packages verified against PyPI registry on 2026-04-10. Most are already installed on this system.

## Architecture Patterns

### Recommended Project Structure
```
src/
  data_pipeline/
    __init__.py
    schemas.py            # Pydantic models for seed, synthetic, and dataset records
    scraper/
      __init__.py
      ncsc_scraper.py     # NCSC advisory page scraper (BS4 + Playwright fallback)
      extractors.py       # Phishing payload extraction from advisory HTML
      rate_limiter.py     # Polite scraping with randomized delays
    generation/
      __init__.py
      generator.py        # Tiered LLM generation orchestrator
      prompts.py          # Generation prompt templates (code-switch, threat classes)
      quality_judge.py    # LLM-as-judge validation pipeline
    processing/
      __init__.py
      dedup.py            # Lexical + semantic deduplication
      normalizer.py       # Vietnamese text normalization (preserving code-switch)
      splitter.py         # Seed-level splitting + semantic cross-split check
    versioning/
      __init__.py
      manifest.py         # SHA256 manifest generation and verification
      build.py            # Full pipeline orchestration (scrape -> generate -> split -> version)
  config/
    __init__.py
    settings.py           # Environment-based configuration (API keys, paths, thresholds)
data/
  raw/                    # Scraped NCSC seed records (JSONL)
  synthetic/              # Generated synthetic records (JSONL)
  processed/              # Final validated dataset (JSONL)
  splits/                 # train.jsonl, val.jsonl, test.jsonl
  manifests/              # SHA256 manifest files per build
tests/
  data_pipeline/
    test_schemas.py       # Schema validation tests
    test_scraper.py       # Scraper unit tests (mocked HTML)
    test_generation.py    # Generation pipeline tests (mocked API)
    test_dedup.py         # Deduplication tests
    test_splitter.py      # Seed-level splitting correctness tests
    test_manifest.py      # Manifest integrity tests
```

### Pattern 1: Stage-Based Pipeline with JSONL Intermediates

**What:** Each pipeline stage (scrape, generate, validate, split, version) reads JSONL input, produces JSONL output, and validates schema at boundaries using Pydantic.
**When to use:** Every pipeline execution.
**Example:**
```python
# schemas.py
from pydantic import BaseModel, Field
from typing import Literal

class SeedRecord(BaseModel):
    text: str = Field(min_length=10)
    source_url: str
    scrape_timestamp: str
    raw_label_hint: str | None = None

class DatasetRecord(BaseModel):
    text: str = Field(min_length=10)
    label: Literal[
        "bank_impersonation",
        "zalo_social_engineering",
        "task_scam",
        "benign"
    ]
    risk_tier: Literal["benign", "suspicious", "high-risk"]
    suspicious_spans: list[str] = Field(default_factory=list)
    xai_explanation: str = Field(min_length=20)
    source: Literal["ncsc_seed", "synthetic_claude", "synthetic_deepseek", "synthetic_openrouter"]
    seed_id: str  # Links synthetic variants back to originating seed

# Every stage boundary:
# record = DatasetRecord.model_validate_json(line)
```

### Pattern 2: Seed-Level Split Governance

**What:** Assign each seed a deterministic split assignment. All synthetic variants inherit their parent seed's split.
**When to use:** Split computation step.
**Example:**
```python
import hashlib

def assign_seed_split(
    seed_id: str,
    split_ratios: tuple[float, float, float] = (0.8, 0.1, 0.1),
    salt: str = "v1.0"
) -> str:
    """Deterministic, reproducible split assignment based on seed_id hash."""
    h = hashlib.sha256(f"{salt}:{seed_id}".encode()).hexdigest()
    bucket = int(h[:8], 16) / 0xFFFFFFFF
    if bucket < split_ratios[0]:
        return "train"
    elif bucket < split_ratios[0] + split_ratios[1]:
        return "val"
    else:
        return "test"

# All synthetic records with the same seed_id get the same split
```

### Pattern 3: SHA256 Manifest for Versioning

**What:** After each dataset build, compute SHA256 of every output file and record in a manifest alongside git commit hash and build metadata.
**When to use:** Every dataset build completion.
**Example:**
```python
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

def build_manifest(data_dir: Path, version_tag: str) -> dict:
    manifest = {
        "version": version_tag,
        "build_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": None,  # Filled by build script from `git rev-parse HEAD`
        "files": {}
    }
    for jsonl_file in sorted(data_dir.rglob("*.jsonl")):
        sha = hashlib.sha256(jsonl_file.read_bytes()).hexdigest()
        manifest["files"][str(jsonl_file.relative_to(data_dir))] = {
            "sha256": sha,
            "records": sum(1 for _ in jsonl_file.open()),
            "bytes": jsonl_file.stat().st_size
        }
    return manifest
```

### Anti-Patterns to Avoid

- **Normalizing away code-switch tokens:** Do NOT strip English loanwords (OTP, link, Smart OTP, Internet Banking) or teencode from Vietnamese text. These are signal, not noise. Normalization should fix encoding issues only.
- **Global random split without seed grouping:** Random shuffled split will scatter synthetic variants of the same seed across train/eval/test, inflating metrics via near-duplicate leakage.
- **Single LLM temperature for all generation:** Using one temperature produces either all-conservative or all-creative outputs. Use lower temperature for complex Teacher-quality examples (Claude) and higher temperature for bulk diversity (DeepSeek).
- **Validating schema only at final output:** Validate at every stage boundary. A malformed record from the scraper will cascade errors through generation and splitting.
- **Storing API keys in code or config files committed to git:** Use environment variables or .env (gitignored).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vietnamese word segmentation | Custom regex tokenizer | underthesea.word_tokenize | Handles Vietnamese compound words, diacritics, and edge cases correctly |
| Near-duplicate text detection | Custom edit-distance loops | rapidfuzz + datasketch MinHash/LSH | O(n log n) vs O(n^2), handles Unicode correctly |
| Semantic similarity for cross-split dedup | Train custom embeddings | sentence-transformers with paraphrase-multilingual-MiniLM-L12-v2 | Pre-trained, supports Vietnamese, runs on CPU |
| JSONL schema validation | Manual dict key checks | Pydantic BaseModel with Field constraints | Type safety, automatic error messages, serialization |
| Stratified splitting | Manual bucket counting | scikit-learn StratifiedGroupKFold or custom hash-based | Handles class balance + group constraints |
| Unicode normalization | Manual character replacement | ftfy + unicodedata.normalize("NFC", text) | Handles mojibake, combining characters, fullwidth chars |
| SHA256 hashing | Custom checksum code | hashlib.sha256 (stdlib) | Standard, auditable, no dependencies |

**Key insight:** The dataset is small (3K records, <10MB) so performance is not the bottleneck. Correctness and reproducibility are. Every "don't hand-roll" item above exists because the edge cases in Vietnamese text, Unicode handling, and near-duplicate detection are subtle and well-solved by existing libraries.

## Common Pitfalls

### Pitfall 1: NCSC Site Structure Unknown Until Runtime

**What goes wrong:** The scraper is designed around assumed HTML structure, but khonggianmang.vn or canhbao.ncsc.gov.vn may use JavaScript-rendered content, pagination via AJAX, or anti-bot measures.
**Why it happens:** NCSC sites are government portals that may change structure without notice. Both khonggianmang.vn and canhbao.ncsc.gov.vn were unreachable from this research environment, so DOM structure cannot be pre-verified.
**How to avoid:** Implement a two-phase scraper: (1) attempt static HTML fetch with requests + BS4, (2) if content is empty or minimal, fall back to Playwright headless browser. The very first task must be manual site reconnaissance to document the actual DOM structure before writing extraction logic.
**Warning signs:** Empty or truncated responses from requests.get(), missing article content despite visible page titles.

### Pitfall 2: Synthetic Data Mode Collapse

**What goes wrong:** LLM generates variations that are superficially different but share the same template skeleton, vocabulary, and sentence structure. The 2K-3K dataset looks large but contains only 10-20 unique patterns.
**Why it happens:** LLMs trained on English-dominant data may fall back to repetitive Vietnamese phrasing patterns, especially at lower temperatures.
**How to avoid:**
- Use explicit diversity instructions in prompts: vary sentence length, register (formal/informal), channel context (SMS vs Zalo vs email), urgency level.
- Track distinct n-gram ratio and template entropy after each generation batch.
- Generate in small batches (50-100), review diversity metrics, adjust prompts before next batch.
- Use different seed examples as anchors for each batch to force structural variation.
**Warning signs:** Distinct 4-gram ratio below 0.3, multiple samples starting with identical phrases.

### Pitfall 3: Seed-Split Leakage Through Metadata

**What goes wrong:** Seed-level splitting is correctly implemented for text content, but metadata fields (URLs, phone numbers, domain patterns) leak across splits because synthetic variants reuse the same phishing infrastructure details.
**Why it happens:** Generation prompts may not instruct the LLM to vary metadata fields like URLs and phone numbers alongside text content.
**How to avoid:** Generation prompts must explicitly instruct variation of ALL fields including fake URLs, phone numbers, and entity names. Post-generation semantic dedup (D-17) catches remaining leaks.
**Warning signs:** Cross-split cosine similarity above threshold on suspicious_spans field specifically.

### Pitfall 4: Vietnamese Encoding Corruption

**What goes wrong:** Scraped Vietnamese text contains mojibake, broken diacritics, or mixed encoding (UTF-8 vs Windows-1252 legacy).
**Why it happens:** Government websites sometimes serve mixed encodings or have copy-paste artifacts from Word documents.
**How to avoid:** Apply ftfy.fix_text() + unicodedata.normalize("NFC") as the very first processing step on all scraped text. Validate that all Vietnamese diacritics are present and correct.
**Warning signs:** Characters like "Ä" appearing where Vietnamese diacritics should be, missing tone marks.

### Pitfall 5: Unbalanced Class Distribution Despite D-10

**What goes wrong:** Generation produces roughly equal counts per class label, but the benign class is linguistically impoverished compared to threat classes (all benign examples sound like "Your account is fine" variations).
**Why it happens:** Benign financial messages are harder to make diverse because they lack the creative manipulation tactics that make phishing text varied.
**How to avoid:** Invest equal prompt engineering effort in benign class diversity: bank notifications, transaction confirmations, service updates, marketing offers, OTP confirmations, account statements. Source benign seed text from real Vietnamese banking communications (with PII removed).
**Warning signs:** Benign class has lowest distinct n-gram ratio despite equal record count.

### Pitfall 6: LLM-as-Judge Agrees with LLM-as-Generator

**What goes wrong:** Using the same model family for generation and quality judgment creates confirmation bias. The judge rates its own generation style as high quality.
**Why it happens:** Same model biases in both generation and evaluation.
**How to avoid:** Use a different model for judging than for generation. If Claude generates, use DeepSeek or a different Claude model tier as judge. Cross-validate with human spot-check (D-09 mandates 5-10%).
**Warning signs:** LLM judge passes >95% of samples with minimal differentiation in scores.

## Code Examples

### NCSC Scraper Pattern (BS4 + Playwright Fallback)
```python
# Source: Project-specific pattern combining BS4 and Playwright
import requests
from bs4 import BeautifulSoup
from typing import Optional
import time
import random

class NCSCScraper:
    BASE_URL = "https://khonggianmang.vn"  # Or canhbao.ncsc.gov.vn
    
    def __init__(self, use_playwright: bool = False):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (research-project; contact@example.com)"
        })
        self.use_playwright = use_playwright
    
    def _polite_delay(self):
        """D-02: Randomized delay between 2-5 seconds."""
        time.sleep(random.uniform(2.0, 5.0))
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch with static HTML first, Playwright fallback."""
        self._polite_delay()
        
        if not self.use_playwright:
            resp = self.session.get(url, timeout=30)
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")
            # Check if content is actually rendered
            if self._has_content(soup):
                return soup
            # Fall back to Playwright
        
        return self._fetch_with_playwright(url)
    
    def _has_content(self, soup: BeautifulSoup) -> bool:
        """Check if page has actual article content (not just shell)."""
        # This selector must be determined during site reconnaissance
        articles = soup.select("article, .post-content, .article-body")
        return len(articles) > 0
    
    def _fetch_with_playwright(self, url: str) -> Optional[BeautifulSoup]:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle")
            html = page.content()
            browser.close()
        return BeautifulSoup(html, "html.parser")
```

### Tiered LLM Generation
```python
# Source: Project-specific pattern based on D-06, D-07, D-08
import anthropic
import httpx
import json
import os

class TieredGenerator:
    def __init__(self):
        self.claude_client = anthropic.Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"]
        )
        self.openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        self.deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    
    def generate_complex(self, seed: dict, threat_class: str) -> list[dict]:
        """Use Claude for complex, high-quality examples."""
        prompt = self._build_complex_prompt(seed, threat_class)
        response = self.claude_client.messages.create(
            model="claude-sonnet-4-20250514",  # Cost-effective for generation
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        return self._parse_generation_response(response.content[0].text)
    
    def generate_bulk(self, seed: dict, threat_class: str, count: int = 10) -> list[dict]:
        """Use DeepSeek/OpenRouter for bulk simple variations."""
        prompt = self._build_bulk_prompt(seed, threat_class, count)
        
        if self.deepseek_key:
            return self._call_deepseek(prompt)
        elif self.openrouter_key:
            return self._call_openrouter(prompt)
        else:
            raise ValueError("No bulk generation API key configured")
    
    def _build_complex_prompt(self, seed: dict, threat_class: str) -> str:
        return f"""Generate 3 realistic Vietnamese financial phishing message variants.

SEED EXAMPLE: {seed['text']}
THREAT CLASS: {threat_class}

CRITICAL REQUIREMENTS:
- Write in Vietnamese with NATURAL code-switching: use English fintech terms 
  (OTP, Internet Banking, Smart OTP, link, login, app, account) where real 
  Vietnamese scammers would use them
- Include Vietnamese teencode/SMS shorthand (k, ko, dc, nha, ak, vs...)
- VARY the following across variants:
  * Message length (short SMS vs longer Zalo message)
  * Urgency level (immediate vs gentle pressure)  
  * Fake URLs/phone numbers (DIFFERENT from seed)
  * Sender persona (bank staff, friend, system notification)
- For each variant, provide:
  * text: The raw message
  * label: "{threat_class}"
  * risk_tier: contextual severity (suspicious or high-risk)
  * suspicious_spans: array of exact substrings that are red flags
  * xai_explanation: 2-3 sentences explaining WHY this is phishing

Return as JSON array."""
    
    def _call_deepseek(self, prompt: str) -> list[dict]:
        """DeepSeek API: $0.28/M input, $0.42/M output tokens."""
        response = httpx.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {self.deepseek_key}"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.9,  # Higher for diversity
                "max_tokens": 4000
            },
            timeout=60
        )
        return json.loads(response.json()["choices"][0]["message"]["content"])
```

### Semantic Dedup Across Splits
```python
# Source: sentence-transformers docs + project D-17 requirement
from sentence_transformers import SentenceTransformer
import numpy as np

def cross_split_dedup(
    train_records: list[dict],
    val_records: list[dict], 
    test_records: list[dict],
    threshold: float = 0.85
) -> dict[str, list[str]]:
    """Find semantically similar records across splits. Returns IDs to remove."""
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    
    # Encode all texts
    train_texts = [r["text"] for r in train_records]
    val_texts = [r["text"] for r in val_records]
    test_texts = [r["text"] for r in test_records]
    
    train_embs = model.encode(train_texts, normalize_embeddings=True)
    val_embs = model.encode(val_texts, normalize_embeddings=True)
    test_embs = model.encode(test_texts, normalize_embeddings=True)
    
    removals = {"val": [], "test": []}
    
    # Check val against train
    sim_matrix = val_embs @ train_embs.T
    for i, row in enumerate(sim_matrix):
        if row.max() > threshold:
            removals["val"].append(val_records[i].get("id", str(i)))
    
    # Check test against train + val
    combined = np.vstack([train_embs, val_embs])
    sim_matrix = test_embs @ combined.T
    for i, row in enumerate(sim_matrix):
        if row.max() > threshold:
            removals["test"].append(test_records[i].get("id", str(i)))
    
    return removals
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| DVC for dataset versioning | Git-native for small datasets (<100MB) + SHA256 manifests | 2024-2025 | DVC overhead not justified for <10MB JSONL; git tags + manifests simpler |
| Random train/test split | Group-aware splitting (seed-level, entity-level) | 2023-2024 | Prevents synthetic-variant leakage that inflates metrics by 5-15% |
| Single-model generation | Tiered multi-model generation (quality + bulk) | 2025-2026 | Claude/GPT for quality, DeepSeek/open models for volume -- 10-50x cost reduction |
| English-only embedding models | Multilingual sentence-transformers (50+ languages) | 2023+ | paraphrase-multilingual-MiniLM-L12-v2 supports Vietnamese semantic similarity out of the box |
| Manual data validation | LLM-as-judge + programmatic checks | 2024-2025 | Scales quality assessment to thousands of records while maintaining spot-check |

**Deprecated/outdated:**
- Scrapy for single-site advisory scraping (overkill; BS4+requests is sufficient for <500 pages)
- DVC for this project (user decision D-13 explicitly excludes it -- dataset fits in git)
- pandas as sole DataFrame tool (Polars is faster and cleaner for batch operations)

## Open Questions

1. **NCSC Site DOM Structure**
   - What we know: khonggianmang.vn and canhbao.ncsc.gov.vn are official NCSC advisory portals. They publish fraud warnings with embedded phishing text examples.
   - What's unclear: Exact HTML selectors for advisory listings, pagination mechanism, whether content is server-rendered or JS-rendered, whether the site has API endpoints.
   - Recommendation: First task in implementation must be manual site reconnaissance. Developer opens the site in browser, inspects DOM with DevTools, documents selectors, tests static vs dynamic rendering. This determines BS4 vs Playwright choice (Claude's discretion area).

2. **Semantic Dedup Threshold for Vietnamese**
   - What we know: Cosine similarity threshold of 0.85 is standard for English near-duplicate detection with multilingual sentence-transformers.
   - What's unclear: Whether 0.85 is appropriate for Vietnamese text which has different token density and code-switching patterns.
   - Recommendation: Start at 0.85, manually review flagged pairs in first batch, adjust threshold up (stricter) or down (more permissive) based on false positive/negative rate. This is a Claude's discretion area.

3. **DeepSeek Free Tier Sufficiency**
   - What we know: DeepSeek gives 5M free tokens to new users (30-day expiry). Pricing is $0.28/M input, $0.42/M output for cache misses.
   - What's unclear: Whether 5M free tokens is sufficient for bulk generation of 1,500-2,000 synthetic examples, or if paid credits will be needed.
   - Recommendation: Estimate ~500 tokens per generated example * 2000 examples = ~1M output tokens. At $0.42/M this is ~$0.42 if free tier exhausted. Budget is minimal. OpenRouter free models are viable zero-cost fallback.

4. **Benign Class Seed Sources**
   - What we know: NCSC primarily publishes threat advisories, not examples of benign financial messages.
   - What's unclear: Where to source diverse, realistic benign Vietnamese financial messages for the benign class.
   - Recommendation: Generate benign examples synthetically using Claude/DeepSeek with prompts covering real banking notification patterns (transaction alerts, OTP messages, balance updates, marketing offers). Supplement with manually written examples. Mark source as "synthetic_claude" or "synthetic_deepseek".

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All pipeline code | Yes | 3.12.10 | -- |
| pip | Package management | Yes | 26.0.1 | -- |
| beautifulsoup4 | NCSC scraping | Yes | 4.14.3 | -- |
| playwright | JS fallback scraping | No (not installed, available on PyPI) | 1.58.0 (PyPI) | Install: `pip install playwright && playwright install chromium` |
| pydantic | Schema validation | Yes | 2.12.5 | -- |
| polars | DataFrame ops | Yes | 1.38.1 (1.39.3 latest) | Works as-is |
| anthropic | Claude API | Yes | 0.93.0 | -- |
| httpx | DeepSeek/OpenRouter API | Yes | 0.28.1 | -- |
| sentence-transformers | Semantic dedup | Yes | 5.2.3 (5.4.0 latest) | Works as-is, upgrade optional |
| rapidfuzz | Fuzzy matching | No (available on PyPI) | 3.14.5 (PyPI) | Install: `pip install rapidfuzz` |
| datasketch | MinHash LSH | No (available on PyPI) | 1.9.0 (PyPI) | Install: `pip install datasketch` |
| underthesea | Vietnamese NLP | No (available on PyPI) | 9.2.11 (PyPI) | Install: `pip install underthesea` |
| scikit-learn | Splitting, metrics | Yes | 1.8.0 | -- |
| pytest | Testing | Yes | 9.0.2 | -- |
| git | Version control | Yes | -- | -- |
| ANTHROPIC_API_KEY | Claude generation | Unknown | -- | Must be set as env var |
| DEEPSEEK_API_KEY | Bulk generation | Unknown | -- | OpenRouter as fallback |
| OPENROUTER_API_KEY | Bulk generation fallback | Unknown | -- | DeepSeek as fallback |

**Missing dependencies with no fallback:**
- None -- all missing packages are installable from PyPI

**Missing dependencies with fallback:**
- playwright: Install on demand if NCSC site requires JS rendering; BS4+requests is the primary path
- rapidfuzz, datasketch, underthesea: Standard pip install, no system dependencies

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | None -- Wave 0 must create pytest.ini or pyproject.toml [tool.pytest] |
| Quick run command | `pytest tests/data_pipeline/ -x --tb=short` |
| Full suite command | `pytest tests/ -v --tb=long` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | Scraper produces normalized seed JSONL from NCSC HTML | unit (mocked HTML) | `pytest tests/data_pipeline/test_scraper.py -x` | Wave 0 |
| DATA-01 | Seed records pass Pydantic SeedRecord schema | unit | `pytest tests/data_pipeline/test_schemas.py::test_seed_record -x` | Wave 0 |
| DATA-02 | Generation pipeline produces valid DatasetRecord JSONL | unit (mocked API) | `pytest tests/data_pipeline/test_generation.py -x` | Wave 0 |
| DATA-02 | Generated records have balanced class distribution | unit | `pytest tests/data_pipeline/test_generation.py::test_class_balance -x` | Wave 0 |
| DATA-02 | LLM-as-judge rejects low-quality samples | unit (mocked) | `pytest tests/data_pipeline/test_generation.py::test_quality_judge -x` | Wave 0 |
| DATA-03 | Seed-level splitting keeps all variants in same split | unit | `pytest tests/data_pipeline/test_splitter.py::test_seed_grouping -x` | Wave 0 |
| DATA-03 | Cross-split semantic similarity below threshold | unit | `pytest tests/data_pipeline/test_dedup.py::test_cross_split_dedup -x` | Wave 0 |
| DATA-03 | SHA256 manifest matches actual file hashes | unit | `pytest tests/data_pipeline/test_manifest.py -x` | Wave 0 |
| DATA-03 | Split ratios match 80/10/10 within tolerance | unit | `pytest tests/data_pipeline/test_splitter.py::test_split_ratios -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/data_pipeline/ -x --tb=short`
- **Per wave merge:** `pytest tests/ -v --tb=long`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `pyproject.toml` or `pytest.ini` -- pytest configuration (test paths, markers)
- [ ] `tests/data_pipeline/conftest.py` -- shared fixtures (sample NCSC HTML, mock API responses, sample JSONL records)
- [ ] `tests/data_pipeline/test_schemas.py` -- Pydantic schema validation
- [ ] `tests/data_pipeline/test_scraper.py` -- scraper with mocked HTML
- [ ] `tests/data_pipeline/test_generation.py` -- generation with mocked API
- [ ] `tests/data_pipeline/test_dedup.py` -- deduplication correctness
- [ ] `tests/data_pipeline/test_splitter.py` -- seed-level splitting
- [ ] `tests/data_pipeline/test_manifest.py` -- SHA256 manifest integrity
- [ ] Package install: `pip install rapidfuzz datasketch underthesea ftfy`
- [ ] Playwright install: `pip install playwright && playwright install chromium` (only if needed)

## LLM Cost Estimation

### Claude API (Complex Generation)
- Model: claude-sonnet-4-20250514 (cost-effective for generation)
- Pricing: ~$3/M input, ~$15/M output tokens
- Estimate: ~100 complex examples * ~800 output tokens each = ~80K output tokens = ~$1.20
- With Batch API (50% discount): ~$0.60

### DeepSeek API (Bulk Generation)
- Model: deepseek-chat
- Pricing: $0.28/M input (cache miss), $0.42/M output tokens
- Estimate: ~2000 bulk examples * ~500 output tokens each = ~1M output tokens = ~$0.42
- Free tier: 5M tokens (likely sufficient for entire bulk generation)

### OpenRouter (Fallback)
- Free models available (20 req/min, 200 req/day limits)
- Paid models: DeepSeek V3.2 available at same pricing as direct API
- Total estimated cost: $0-$2 for entire Phase 1 generation

## NCSC Scraping Strategy

### Primary Target: khonggianmang.vn
- NCSC's national cybersecurity awareness portal
- Publishes threat advisories about phishing/scam campaigns
- Has a dedicated fraud alert system at canhbao.ncsc.gov.vn (or canhbao.khonggianmang.vn)

### Secondary Target: canhbao.ncsc.gov.vn
- Dedicated scam reporting and alert portal
- Likely contains more structured fraud case reports

### Scraping Approach
1. **Reconnaissance first:** Manually inspect both sites in browser, document DOM structure
2. **Start with requests + BS4** for static HTML extraction
3. **Fall back to Playwright** only if JavaScript rendering is required
4. **Extract phishing payloads** embedded in advisory articles (the actual SMS/Zalo text, not the article title)
5. **Polite scraping:** 2-5 second randomized delays between requests, identify via User-Agent
6. **Pagination:** Crawl advisory listing pages, follow links to individual advisory detail pages
7. **Error handling:** Retry with exponential backoff on 429/5xx, log and skip permanent failures

### Fallback Sources (D-04: only if NCSC yields <100 seeds)
- Vietnamese news articles reporting specific phishing campaigns (vnexpress.net, vietnamnet.vn)
- Vietnamese cybersecurity community forums
- Publicly shared scam text collections

## Sources

### Primary (HIGH confidence)
- PyPI package registry -- verified versions for all recommended packages (2026-04-10)
- Local environment audit -- confirmed installed packages and versions
- CONTEXT.md decisions (D-01 through D-17) -- locked user decisions constraining all recommendations
- Project STACK.md research -- prior technology decisions

### Secondary (MEDIUM confidence)
- [NCSC Vietnam portal structure](https://khonggianmang.vn) -- confirmed as official NCSC site via multiple Vietnamese government sources
- [sentence-transformers pretrained models](https://sbert.net/docs/sentence_transformer/pretrained_models.html) -- paraphrase-multilingual-MiniLM-L12-v2 supports Vietnamese
- [dangvantuan/vietnamese-embedding](https://huggingface.co/dangvantuan/vietnamese-embedding) -- Vietnamese-specific SBERT achieving 84.87 Pearson on STS
- [DeepSeek API pricing](https://api-docs.deepseek.com/quick_start/pricing/) -- $0.28/$0.42 per M tokens, 5M free tokens for new users
- [OpenRouter free models](https://openrouter.ai/collections/free-models) -- zero-cost models available with rate limits
- [Claude API pricing](https://platform.claude.com/docs/en/about-claude/pricing) -- Sonnet $3/$15 per M tokens, 50% batch discount
- [Vietnamese SMS spam detection with PhoBERT](https://link.springer.com/chapter/10.1007/978-3-031-77731-8_24) -- PhoBERT achieves 93.56% recall on Vietnamese spam
- [Synthetic data generation with multi-LLM pipeline](https://arxiv.org/html/2503.14023v1) -- tiered generation + SLM-as-judge validated approach

### Tertiary (LOW confidence)
- NCSC site DOM structure -- both khonggianmang.vn and canhbao.ncsc.gov.vn were unreachable from research environment; actual HTML selectors MUST be verified during implementation reconnaissance
- Vietnamese-specific embedding quality for semantic dedup -- threshold of 0.85 is extrapolated from English benchmarks; needs empirical validation on Vietnamese phishing text

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all packages verified on PyPI, most already installed locally
- Architecture: HIGH -- pipeline patterns well-established, Pydantic + JSONL + git versioning is standard
- NCSC scraping: MEDIUM -- site exists and is confirmed official, but DOM structure unknown
- Synthetic generation: HIGH -- Claude/DeepSeek/OpenRouter APIs are production-grade, pricing verified
- Split governance: HIGH -- seed-level splitting and semantic dedup are well-documented patterns
- Pitfalls: HIGH -- based on documented project risks + domain experience in synthetic data pipelines

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (stable domain, no fast-moving dependencies)
