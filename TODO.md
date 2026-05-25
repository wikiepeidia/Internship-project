Finish today

1. Refresh the Phase 5 snapshot on the repaired holdout:

```bash
python -m src.model_adaptation.cli evaluate-release-split \
 --split-path data/splits/recovered-balanced/val.jsonl \
 --snapshot-path .planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json \
 --run-id phase5-recovered-balanced-val \
 --progress-every 1 \
 --checkpoint-every 1
```

1. Build the new explanation review pack from that snapshot:

```bash
python -m src.model_adaptation.cli prepare-explanation-review \
 --snapshot-path .planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json \
 --output-path .planning/phases/05-recall-priority-evaluation-and-release-gates/05-explanation-review-pack.json
```

1. Manual step: review the regenerated `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-explanation-review-pack.json` and only mark it completed if the new snapshot is approved.

2. After the manual review is complete, synthesize the refreshed Phase 5 verdict and artifacts:

```bash
python -m src.model_adaptation.cli release-eval \
 --snapshot-path .planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json \
 --review-pack-path .planning/phases/05-recall-priority-evaluation-and-release-gates/05-explanation-review-pack.json \
 --report-dir .planning/phases/05-recall-priority-evaluation-and-release-gates \
 --manifest-dir data/manifests
```

Tomorrow: retrain only if needed

- Not needed just to finish Phase 5 paperwork today.
- Needed if you want a real updated adapter from the repaired `recovered-balanced` train/val split.
- The completed run today was only a smoke test (`smoke_test: true`, checkpoint-2), so it is not a meaningful full retrain.

1. Preflight the real training job:

```bash
python -m src.model_adaptation.cli doctor \
 --candidate baseline-winner \
 --train-split data/splits/recovered-balanced/train.jsonl \
 --val-split data/splits/recovered-balanced/val.jsonl \
 --output-root "D:/PROJEct/AI MODELS" \
 --registry-path "D:/PROJEct/AI MODELS/manifests/model-registry.json"
```

1. Run the real baseline retrain:

```bash
python -m src.model_adaptation.cli train \
 --candidate baseline-winner \
 --version-tag proposal-closeout-full-2026-05-26 \
 --train-split data/splits/recovered-balanced/train.jsonl \
 --val-split data/splits/recovered-balanced/val.jsonl \
 --output-root "D:/PROJEct/AI MODELS" \
 --registry-path "D:/PROJEct/AI MODELS/manifests/model-registry.json" \
 --device cuda \
 --full-precision
```

1. Optional after the retrain: convert the new baseline adapter to GGUF so the default GGUF runtime can use it.

```bash
python -m src.model_adaptation.cli convert \
 --candidate baseline-winner \
 --version-tag proposal-closeout-gguf-2026-05-26 \
 --output-root "D:/PROJEct/AI MODELS" \
 --registry-path "D:/PROJEct/AI MODELS/manifests/model-registry.json"
```
