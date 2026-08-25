# Phase 43 Source Audit

| Source | ID | Required outcome or constraint | Plan coverage | Status |
|---|---|---|---|---|
| GOAL | — | Rebuild the defense deck around the real get data -> train -> GGUF -> evaluate pipeline, using real evidence and progressive reveals while lifting the prior lock only for this milestone. | 43-01, 43-02 | COVERED |
| REQ | SLIDE-08 | Pipeline stages appear in the real execution order. | 43-01, 43-02 | COVERED |
| REQ | SLIDE-09 | Training and evaluation result frames use active `\pause` reveals. | 43-01, 43-02 | COVERED |
| REQ | SLIDE-10 | Only canonical Phase 40/41 graphs and values are rendered. | 43-01, 43-02 | COVERED |
| REQ | SLIDE-11 | The entire locked deck source closure is archived and hash-bound before any live edit. | 43-01, 43-02 | COVERED |
| HANDOFF | H-01 | No metric, graph, model conclusion, checkpoint identity, wall time, or GGUF claim is inserted until its canonical source verifies. | 43-01, 43-02 | COVERED |
| HANDOFF | H-02 | Archive `slides.tex`, the complete `slides/` tree, and resolved external figure dependencies rather than one entry file. | 43-01, 43-02 | COVERED |
| HANDOFF | H-03 | Bind all Phase 40/41 handoff slots: resource probe, both configurations and curves, validation, GGUF, qualitative review, held-out comparison, matrices, and terminal limitations. | 43-01, 43-02 | COVERED |
| HANDOFF | H-04 | Consume Phase 41 only as one complete frozen result transaction; never publish a partial comparison. | 43-01, 43-02 | COVERED |
| HANDOFF | H-05 | Deliberately include or explicitly exclude the currently orphaned `06_why_local.tex`, `09_confusion.tex`, and `12_future.tex`. | 43-01, 43-02 | COVERED |
| HANDOFF | H-06 | Compile twice with XeLaTeX, reject log errors and unresolved evidence tokens, and create new Phase 43 compile evidence. | 43-02 | COVERED |
| CONTEXT | D-01 | This planning task owns only `.planning/phases/43-evidence-bound-slide-rebuild/`. | planning output only | COVERED |
| CONTEXT | D-02 | Safe preparation is separate from evidence-gated live-deck execution. | Wave 1 versus Waves 2-3 | COVERED |
| CONTEXT | D-03 | Preparation and its tests do not open datasets, model bundles, D:, or the reserved split. | 43-01, 43-02 | COVERED |
| CONTEXT | D-04 | Real archive, graph insertion, live edits, and compilation wait for frozen Phase 40 and Phase 41 evidence. | 43-02 precondition | COVERED |

No Phase 43 `CONTEXT.md`, `RESEARCH.md`, or deferred-ideas section exists. The user instructions above are treated as locked decisions D-01 through D-04. No source item is missing.
