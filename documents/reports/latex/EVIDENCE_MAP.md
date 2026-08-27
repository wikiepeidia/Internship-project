# Report Evidence Map

**Editorial status:** evidence-enriched review draft. The technical claims below are mapped to retained sources, but student voice/style approval and comparison against a real passed-student reference remain pending. This status must not be mistaken for technical evidence or for final authorship approval.

## Claim-boundary legend

- **Verified:** a retained verifier or closeout record passed against the named artifacts.
- **Frozen:** immutable result evidence; reporting may summarize it but must not rerun, repair, or rewrite it.
- **Descriptive:** a count, score, or bounded review result with no inferential claim.
- **Historical background:** preserved for chronology only; not current corpus or model authority.
- **Open debt:** an unresolved review finding that must remain visible.

## Chapter-level authority

| Chapter / section | Primary retained evidence | Report-safe claim | Required boundary |
|---|---|---|---|
| Introduction | `readme.md`; `docs/architecture/overview.md`; `data/manifests/manifest.json` | Local, text-only Vietnamese phishing-detection prototype with a governed four-label corpus and local runtime. | No production-readiness or real-world generalization claim. |
| Background | Cited literature and NIST privacy principles | Literature motivates phishing detection, privacy, local inference, and model choices. | Literature does not prove this implementation, corpus novelty, or measured performance. |
| Methodology: corpus | `data/manifests/manifest.json`; `data/processed/judge-summary.json`; `.planning/phases/39-independent-quality-re-judge/39-REPORT-NOTE.md` | Final governed corpus: 2,097 rows; 1,658/219/220 partition identities; schema/span, duplicate, seed-cap, all-label, and group-disjointness checks passed. | Synthetic/model-assisted content; 296 reconstructed Zalo rows share the final judge's model family. |
| Methodology: human evidence | `.planning/phases/39-independent-quality-re-judge/39-final-manual-review-sheet.md`; `39-REPORT-NOTE.md` in the same directory | Stratified sample: 44/100 PASS, 56/100 FAIL, 87/100 judge-human agreement. | **44/100 is stratified corroboration, not a random population estimate or a corpus failure rate.** One reviewer is not a multi-annotator reliability study. |
| Implementation: model training | `.planning/phases/40-multi-model-training-evidence/40-VERIFICATION.md`; `40-VALIDATION-COMPARISON.md` | Two fresh local full models: genuine Qwen NF4 QLoRA and non-quantized PhoBERT classification head, both seed 42. | One seed; no variance, confidence interval, significance, t-test, or stable-winner claim. |
| Implementation: runtime | `src/runtime`; `docs/architecture/cli-contracts.md`; `data/models/phase40/qwen-gguf-verification-receipt.json` | Installed `vnphish` commands and verified Qwen Q8_0 materialization/load path. | Qwen GGUF only; no PhoBERT GGUF and no completed deployment fit. |
| Validation comparison | `.planning/phases/40-multi-model-training-evidence/40-VALIDATION-COMPARISON.md`; `40-VERIFICATION.md` | On 219 aligned validation rows: Qwen macro F1 0.9885153110; PhoBERT 0.9848929140; both zero invalid outputs. | Development validation only. Qwen's generative path and PhoBERT's classifier path make speed/throughput comparison inadmissible. |
| Terminal model evaluation | `.planning/phases/41-one-shot-two-model-evaluation/41-VERIFICATION.md`; `.planning/phases/41-one-shot-two-model-evaluation/41-REVIEW-RESOLUTION.md` | One terminal N=220 shared-cohort pass. Qwen: accuracy 0.981818, macro F1 0.980493, weighted F1 0.981848. PhoBERT: 0.990909, 0.990892, 0.990925. Both: zero invalid outputs and one risky-to-benign error. | Frozen terminal result; no retry, repair, retraining, thresholding, model selection, or contingency activation. PhoBERT's measured advantage is not stable superiority. |
| Terminal access disclosure | `data/models/phase41/phase41-provenance-erratum.json`; `.planning/phases/41-one-shot-two-model-evaluation/41-REVIEW-RESOLUTION.md` | Exactly one terminal model-evaluation pass; prior automated integrity reads did not perform model inference or influence selection/training/repair. | Never say “untouched” or “zero prior filesystem access.” The erratum is mandatory with the frozen export. |
| Architecture | `architecture/module-boundaries.json`; `docs/architecture/overview.md`; `.planning/phases/41.1-codebase-architecture-overhaul/41.1-REPORT-HANDOFF.md` | Maintained code now has domain-oriented boundaries, a 232-line model CLI facade, a 160-line archive facade, and a checked 29-module/83-edge active graph. | The refactor did not produce or replace frozen metrics. |
| Architecture limitations | `.planning/phases/41.1-codebase-architecture-overhaul/41.1-REVIEW.md` | The latest review records six critical and three warning findings. | Open debt: do not claim the architecture is fully secure, closed, or production-ready. |
| Conclusion | All rows above; `chapters/06_conclusion_and_future_work.tex`; `chapters/appendices.tex` | Final corpus, two local model families, Qwen GGUF verification, validation comparison, one terminal N=220 pass, local runtime, and maintainability refactor were completed. | Real-world generalization and deployment fitting remain unverified/deferred. |

## Current numerical authority

| Quantity | Value | Authority and interpretation |
|---|---:|---|
| Final corpus | 2,097 | Current governed corpus. |
| Training / validation / terminal evaluation | 1,658 / 219 / 220 | Final partition identities; seed groups are disjoint. |
| Joined quality-judge coverage | 2,097 / 2,097 | 1,395 passes (66.52%); descriptive automated quality evidence. |
| Human sample | 44 PASS / 56 FAIL | Stratified 100-row review; not a corpus prevalence estimate. |
| Judge-human agreement | 87 / 100 | Consistency on the bounded sample; not model accuracy. |
| Qwen validation macro F1 | 0.9885153110 | One seed, 219 rows, selected step 200. |
| PhoBERT validation macro F1 | 0.9848929140 | One seed, 219 rows, selected step 100. |
| Qwen terminal macro F1 | 0.980493 | Frozen N=220 terminal pass. |
| PhoBERT terminal macro F1 | 0.990892 | Frozen N=220 terminal pass; measured higher value, not stable superiority. |
| Qwen GGUF | 4,280,403,232 bytes | Q8_0; SHA-256 `457f6f92d36a7d54da9916fd80a4028dcd055a653a015c4877370a0fea4d18ab`. |
| Architecture review debt | 6 critical / 3 warning | Current unresolved review status. |

## Failure-and-recovery sources

| Event | Evidence path | Defensible statement |
|---|---|---|
| Zalo narrator/scenario framing | `.planning/phases/39-independent-quality-re-judge/39-REPORT-NOTE.md` | 240 retained rows were replaced through 60 preserved roots; 296 reconstructed rows survive. Synthetic and same-family limitations remain. |
| Ordinary LoRA bounded probe | `.planning/phases/40-multi-model-training-evidence/40-LOCAL-PROBE-REPORT.md` | 31 observed/26 retained measured-window steps; no OOM; 7,902/8,151 MiB peak VRAM use; 18.42--18.88 h incomplete-window compute ETA; resource evidence only. |
| Genuine QLoRA probe | Same probe report | Exact 5+40-step target; 3.462389 s median measured step; 72m49.750s limited projection; disposable runtime removed. |
| Qwen first full attempt | `.planning/phases/40-multi-model-training-evidence/40-LOCAL-FULL-QLORA-REPORT.md` | Interrupted after run-root and canonical-JSON operator defects; preserved, not relabelled as success. Clean step-zero run supplied final evidence. |
| Two completed local models | `.planning/phases/40-multi-model-training-evidence/40-VERIFICATION.md` | Accepted Qwen run completed 1,245 steps; accepted PhoBERT run completed 312 steps. |
| Five pre-claim launcher failures | `.planning/phases/41-one-shot-two-model-evaluation/41-VERIFICATION.md` | Each failed before its invocation-local claim/access boundary; together they are not a machine-wide access audit. |
| Prior-access correction | `data/models/phase41/phase41-provenance-erratum.json` | Frozen result unchanged; global zero-access wording retracted. |
| Refactor review debt | `.planning/phases/41.1-codebase-architecture-overhaul/41.1-REVIEW.md` | Six critical and three warning findings remain reportable limitations. |

## Historical evidence kept only for background

The 2,333-training / 254-validation Qwen study and its macro F1 0.9625 belong to an earlier snapshot. The 254-row class table may remain in the appendix only when labelled historical. It must not be used as authority for the final 2,097-row corpus, the 219-row validation comparison, or the terminal N=220 evaluation.

## Prohibited report claims

- No t-test, statistical-significance, confidence-interval, stable-winner, or run-to-run variance claim.
- No “untouched test,” “zero prior filesystem access,” or machine-wide audit claim.
- No ordinary-LoRA OOM or completed full-LoRA accuracy claim.
- No PhoBERT GGUF claim.
- No completed deployment fitting or inherited unbiased score after a future fit.
- No fair Qwen-versus-PhoBERT speed comparison.
- No claim that the architecture refactor generated the frozen results.
- No claim that the current architecture is fully secure or review-closed.
- No interpretation of 44/100 as the complete corpus pass rate or 56/100 as the complete corpus failure rate.
