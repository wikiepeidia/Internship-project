# Real Vietnamese scam-data source audit

Probe window: **2026-08-06 15:04–15:31 UTC**. The machine-checkable evidence is
[260806-ubr-ACQUISITION-MANIFEST.jsonl](./260806-ubr-ACQUISITION-MANIFEST.jsonl).

## Quantitative answer

There is no defensible public source containing 3,000 independently verified
Vietnamese scam messages or incidents among the endpoints audited. The original
Tín Nhiệm Mạng source is genuinely small: its live scam-warning category has
**74 editorial advisories** (pages 1–14 × 5, page 15 × 4, page 16 empty). The
April seed snapshot contains **300 extracted snippets, 298 normalized-unique
texts, from 67 of those advisory URLs**. Those are neither 300 independent
incidents nor uniformly verbatim scam messages.

Two open-license datasets are useful, but their units and limitations matter:

- [Vietnamese SMS Phishing Dataset](https://huggingface.co/datasets/trannguyenthaituan/vietnamese_sms_phishing_dataset)
  declares CC BY 4.0 and contains 2,991 rows: 798 publisher-labeled phishing
  rows, of which 711 are normalized-unique. Its card says the messages were
  contributed by people and anonymized, but the dataset was uploaded only on
  2026-08-03; no independent paper or IRB record was located, 394 normalized
  duplicates exist overall, and 29 normalized texts cross its published
  train/test boundary. Treat it as **publisher-asserted real message data with
  medium provenance confidence**, not an independent benchmark.
- [PhishVN v2](https://data.mendeley.com/datasets/b97hxbxtpd/2) declares CC BY
  4.0 and contains 51,362 unique URL rows, including 36,871 labeled phishing
  indicators. These are **threat indicators, not messages or incident cases**.
  Its upstream sources include Chống Lừa Đảo, Tín Nhiệm Mạng, OpenPhish, and
  Tranco, so source overlap must be preserved rather than presented as
  independent victim reports.

The bounded acquisition selected at most 50 rows per qualified source. It
retained **94 net-new, unlabeled provenance records** after collapsing six
within-sample duplicates and finding zero duplicates against the retained 300
seeds:

| Source | Retained unit | Gross selected | Duplicate within | Duplicate vs. retained seeds | Net |
|---|---:|---:|---:|---:|---:|
| Vietnamese SMS Phishing Dataset | verbatim-message example (publisher asserted) | 50 | 6 | 0 | **44** |
| PhishVN v2 | threat indicator | 50 | 0 | 0 | **50** |

The sample is [260806-ubr-REAL-SAMPLE.jsonl](./260806-ubr-REAL-SAMPLE.jsonl):
94 rows, 100,437 bytes, SHA-256
`9ce84faded30c8091dd67af361be0d4db5dfbe5808c3d56eecb73c041e424da1`.
It contains no project label or risk tier and was not merged into training,
processed data, or evaluation splits.

## Endpoint evidence

Counts below are kept in their native units. “0 eligible” can mean unavailable,
not relevant as real data, prohibited, privacy-risky, or lacking redistribution
permission; public visibility alone is not a reuse license.

| Endpoint | Unit | Empirical count | Access / reuse result | Eligible in bounded sample |
|---|---|---:|---|---:|
| [Tín Nhiệm Mạng warnings](https://tinnhiemmang.vn/canh-bao-lua-dao) | editorial advisory | **74 exact** | Pagination query is disallowed by robots; Content-Signal says AI training no; no redistribution license | 0 |
| [Tín Nhiệm Mạng blacklist](https://tinnhiemmang.vn/website-lua-dao) | threat indicator | **125,608 exact displayed** (125,169 websites + 439 social) | Same robots/reuse blocker; not crawled into a local dataset | 0 |
| [SCAM.VN reports](https://scam.vn/danh-sach) | incident report | **13,412 displayed; ≥32 unique inspected** | Terms prohibit reproduction/distribution/derivatives; high PII and accusation risk | 0 |
| [SCAM.VN articles](https://scam.vn/bai-viet) | editorial advisory | **970 exact** | Same express terms restriction | 0 |
| [Chống Lừa Đảo denylist](https://chongluadao.vn/database/denylist) | threat indicator | **≥50** visible rotating sample | Complete feed is contact-gated; no downstream data license | 0 |
| [Chống Lừa Đảo dashboard](https://chongluadao.vn/database/dashboard) | aggregate indicator metric | **17,851,045 displayed global total** | Aggregate only, not downloadable Vietnamese case rows | 0 |
| [Chống Lừa Đảo posts feed](https://feeds.chongluadao.vn/posts) | editorial advisory | **48 exact** | Public feed, but no downstream content/data license | 0 |
| [Chống Lừa Đảo WordPress API](https://chongluadao.vn/blog/wp-json/wp/v2/posts) | editorial advisory | **113 exact** from `X-WP-Total` | Editorial content, no downstream license | 0 |
| [Retired Chống Lừa Đảo API](https://api.chongluadao.vn/v2/blacklistdomains) | threat indicator | **0 accessible** | Endpoint retired/unavailable | 0 |
| [Bộ Công an crime warnings](https://bocongan.gov.vn/chuyen-muc/canh-bao-toi-pham-1750063351) | editorial advisory | **≥10** first-page articles | Robots permits the page, but no dataset/ML reuse license | 0 |
| [MST/NCSC tag page](https://mst.gov.vn/trung-tam-giam-sat-an-toan-khong-gian-mang-quoc-gia-ncsc.html) | editorial advisory | **0 extracted** | HTTP 200 shell with no article rows; derivative permission unclear | 0 |
| [Legacy khônggianmang warning host](https://canhbao.khonggianmang.vn/) | editorial advisory | **0** | DNS NXDOMAIN | 0 |
| [NCSC warning subdomain](https://canhbao.ncsc.gov.vn/) | editorial advisory | **0** | Timed out | 0 |
| [khonggianmang.vn](https://khonggianmang.vn/) | editorial advisory | **0** | DNS resolution failed | 0 |
| [AIS](https://ais.gov.vn/) | editorial advisory | **0** | DNS NXDOMAIN | 0 |
| [pth1993 SMS sample](https://github.com/pth1993/vie-spam-sms-filtering) | verbatim-message example | **10 exact** exposed; paper reports 6,599 | No LICENSE; 4/10 sample rows contain phone-like identifiers; full data absent | 0 |
| [ankhanh Vietnamese spam repository](https://github.com/ankhanhtran02/Vietnamese-Spam-Detection) | dataset row | **5,692 exact; 5,687 unique** | 122 unique spam rows observed, but no license, unclear provenance, and 52 phone-like rows | 0 |
| [PTIT SMS paper](https://jstic.ptit.edu.vn/jstic-ptit/files/journals/1/articles/484/submission/484-1-1821-1-2-20211031.pdf) | paper-reported dataset row | **5,113 reported** | No downloadable artifact or data license | 0 |
| [Vietnamese SMS Phishing Dataset](https://huggingface.co/datasets/trannguyenthaituan/vietnamese_sms_phishing_dataset) | verbatim-message example | **2,991 exact; 798 phishing; 711 unique phishing** | CC BY 4.0; revision and download bytes/hash pinned; provenance caveats above | **44** |
| [Companion SMS sample](https://huggingface.co/datasets/trannguyenthaituan/vietnamese_sms_phishing_sample) | verbatim-message example | **300 exact; 207 unique** | 190 rows overlap the full dataset; excluded as non-independent | 0 |
| [Vietnamese Scam Conversation](https://huggingface.co/datasets/hoang2501/Vietnamese_Scam_Conversation) | dataset row | **0** | Apache metadata, but repository contains no data file | 0 |
| [scam_dialogues](https://huggingface.co/datasets/adamtc/scam_dialogues) | dataset row | **3,840 exact** | Explicitly synthetic, so rejected as real evidence | 0 |
| [PhishVN v2](https://data.mendeley.com/datasets/b97hxbxtpd/2) | threat indicator | **51,362 exact unique; 36,871 phishing** | CC BY 4.0; ZIP bytes/hash and member pinned | **50** |

## Collection and safety notes

The collector uses fixed source/redirect host allowlists, timeouts, response-size
and per-source record caps, a 2–5 second delay, exact archive byte/hash pins,
atomic output, PII redaction, canonical URLs, and SHA-256 content identifiers.
Mendeley returned a visible Cloudflare challenge to Python Requests. A normal
`curl` request to the public file URL returned the repository’s HTTP 302 to a
fixed public S3 object; the collector used that exact redirect target with the
repository-declared 5,324,815-byte size and SHA-256
`ab1afd858c3822f3bf5cb70d5898e0e9692918579e24585a67648d5b691c7b1f`.
No login, CAPTCHA solving, cookie replay, report submission, or access-control
bypass was used.

The durable rows all carry `data_origin=real_public`, their precise record
unit, canonical/native identifiers, publisher, rights URL/status, UTC retrieval
time, normalized-content hash, redaction state, and contributing URLs.
`raw_label_hint` remains null. Source labels were used only to select a
bounded candidate subset; they were not copied into the project’s four-class
schema.

## Claim boundary for the report and judges

The defensible statement is:

> We verified that the original public advisory source contains 74 current
> advisory pages and that the retained April seed file has 300 extracted
> snippets from 67 pages (298 normalized-unique). Because open Vietnamese
> incident/message data are scarce and reuse rights are often absent, the
> existing 3,000-row model corpus is synthetic. A separate audit found and
> froze 44 CC BY publisher-asserted message examples plus 50 CC BY threat
> indicators as provenance evidence; these were not used for training or
> independent evaluation.

Do not say “3,000 real cases,” “300 real incidents,” or “94 verified scam
cases.” The 44 message examples still require human authenticity and language
review. The 50 PhishVN rows are URLs, not conversation text. Neither source is
currently an independent evaluation set.

Before any acquired row enters modeling:

1. Have at least two Vietnamese reviewers confirm message authenticity,
   remove residual identifiers, and independently assign the project label and
   risk tier with adjudication.
2. Preserve source-native IDs and group by original message/indicator,
   normalized near-duplicate cluster, and upstream source before splitting.
3. Keep all variants of one seed or indicator in one split; do not let the
   companion dataset or PhishVN upstream mirrors cross splits.
4. Reserve an independently sourced, human-adjudicated real test set. If that
   is unavailable, describe evaluation as synthetic/weak-source validation.
5. Rebuild manifests, retrain, and rerun leakage, calibration, class-balance,
   and subgroup checks. This audit intentionally performs none of those steps.

## Lineage integrity

Before and after acquisition, the protected artifacts were byte-identical:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `data/synthetic/recovered-balanced.jsonl` | 2,347,367 | `009af0d2b298c25705e26830a5a7abb9e4aad34e69b1ab84a363d97030beafad` |
| `data/splits/recovered-balanced/train.jsonl` | 1,758,973 | `8714fe483265aeec01379f17dbf49177009744cdc2bbdd11583d4a7898317cb5` |
| `data/splits/recovered-balanced/val.jsonl` | 183,895 | `4e3f10bd565cce005a219452ff68a3180ab0e1125108a2ba205090dc71f57d57` |
| `data/splits/recovered-balanced/test.jsonl` | 404,499 | `371ac104ab6910d5e37db994672c1b6fcd9879317cb260ced7f3332b0d24a94e` |
