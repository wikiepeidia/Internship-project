# Model and Evidence Storage Retention

This is a documentation-only classification copied from the approved read-only
inventory. No D: location was rescanned to create this page. Every cleanup candidate
below is informational and not authorized for deletion. Any future action requires
separate exact-path user authorization and a fresh safety review.

## Four sealed model roots: retain exactly

These four roots total **10.170 GiB**. Files that look unnecessary may still
participate in the recorded tree identity, so each root is retained as a whole.

<!-- sealed-roots:start -->
| Role | Exact path | Recorded size | Tree SHA-256 |
| --- | --- | --- | --- |
| `Qwen QLoRA adapter` | `D:\PROJEct\AI MODELS\phase40-full-local-20260825\transfer-root-v3\data\models\phase40\full\qwen-qlora\adapter-or-model` | `0.139 GiB` | `466d107d7212fd9b65f19b36be5011e6043865bce4c937460145908d3847b7ec` |
| `Qwen base` | `D:\PROJEct\AI MODELS\phase40-full-local-20260825\transfer-root-v3\data\models\phase40\base\qwen3-4b-instruct-2507` | `7.507 GiB` | `bab9c18a02587fb842c9332848bdc4f1316bae7ee5bed3bb1d573dca2d64554c` |
| `PhoBERT inference bundle` | `D:\PROJEct\AI MODELS\phase40-full-local-20260825\phobert-release-v4\data\models\phase40\inference\phobert` | `1.513 GiB` | `649f566a6525833778fbc617261278ef53e4ecc6ab88ae54715f6aaf7b56bb7a` |
| `PhoBERT base` | `D:\PROJEct\AI MODELS\phase40-full-local-20260825\transfer-root-v5\data\models\phase40\base\phobert-base-v2` | `1.011 GiB` | `1708ec099dcc8385a88ab49d0bb7860e4ceb496fd08aa792b0ec95e2326d8d5f` |
<!-- sealed-roots:end -->

Also retain the compact `source-runtime-v3`, `source-runtime-v12`, and `controller`
evidence directories under the recorded experiment root until the report and defense are
finished.

## Optional deployment artifact

The following artifact was not used in the terminal evaluation. It is the convenient
local-demo/defense Qwen artifact, so it should remain unless a replacement is copied
elsewhere and independently verified against the recorded SHA-256 first.

<!-- optional-gguf:start -->
| Role | Exact path | GGUF plus manifest | GGUF SHA-256 |
| --- | --- | --- | --- |
| `Qwen Q8_0 GGUF and manifest` | `D:\PROJEct\AI MODELS\phase40-full-local-20260825\exports-v3\qwen-qlora-q8_0.gguf` | `3.986 GiB` | `457f6f92d36a7d54da9916fd80a4028dcd055a653a015c4877370a0fea4d18ab` |
<!-- optional-gguf:end -->

## Conservative candidates: information only

These trainer checkpoints, interrupted work, superseded releases, and comparison
staging roots occupy approximately **30.304 GiB** in the approved inventory. Their
classification is not an instruction to change them.

<!-- cleanup-candidates:start -->
| Exact path | Recorded size | Inventory rationale |
| --- | --- | --- |
| `D:\PROJEct\AI MODELS\phase40-full-local-20260825\phobert-work-v12` | `14.103 GiB` | `trainer checkpoints and final-model staging` |
| `D:\PROJEct\AI MODELS\phase40-full-local-20260825\work-v3` | `4.122 GiB` | `Qwen checkpoints and intermediate adapters` |
| `D:\PROJEct\AI MODELS\phase40-full-local-20260825\resume-work-v2` | `1.008 GiB` | `interrupted superseded Qwen attempt` |
| `D:\PROJEct\AI MODELS\phase40-full-local-20260825\phobert-release-v2` | `part of 6.058 GiB` | `superseded by v4` |
| `D:\PROJEct\AI MODELS\phase40-full-local-20260825\phobert-release-v3` | `part of 6.058 GiB` | `superseded by v4` |
| `D:\PROJEct\AI MODELS\phase40-full-local-20260825\comparison-root-v4` | `part of 5.013 GiB` | `comparison staging` |
| `D:\PROJEct\AI MODELS\phase40-full-local-20260825\comparison-root-v5` | `part of 5.013 GiB` | `comparison staging` |
| `D:\PROJEct\AI MODELS\phase40-full-local-20260825\comparison-root-v6` | `part of 5.013 GiB` | `comparison staging` |
<!-- cleanup-candidates:end -->

## Reviewed nested duplicates

The inventory identifies another **4.040 GiB** of nested duplicates. A parent may
also contain a sealed root, so no parent-level inference is safe.

<!-- nested-candidates:start -->
| Exact path | Recorded size |
| --- | --- |
| `D:\PROJEct\AI MODELS\phase40-full-local-20260825\transfer-root-v3\data\models\phase40\base\phobert-base-v2` | `1.011 GiB` |
| `D:\PROJEct\AI MODELS\phase40-full-local-20260825\transfer-root-v5\data\models\phase40\full\phobert` | `1.514 GiB` |
| `D:\PROJEct\AI MODELS\phase40-full-local-20260825\phobert-release-v4\data\models\phase40\full\phobert` | `1.514 GiB` |
<!-- nested-candidates:end -->

## Older bases needing a separate decision

These are outside the retained final system and may belong to unrelated work.

<!-- older-bases:start -->
| Exact path | Recorded size |
| --- | --- |
| `D:\PROJEct\AI MODELS\base\qwen2.5-7b-instruct` | `14.196 GiB` |
| `D:\PROJEct\AI MODELS\base\qwen3.5-4b` | `8.701 GiB` |
<!-- older-bases:end -->

## Hardlink and authorization boundary

Repeated Qwen base paths in older transfer roots are NTFS hardlinks to the same
physical shards. Removing a non-authoritative link may recover little space while
the retained link still exists. This document performs no deletion, move, trim,
relink, rescan, or authorization and provides no executable cleanup instruction.
