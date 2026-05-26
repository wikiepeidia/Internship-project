If you are doing the full retrain tonight

1. Start the full retrain now. This is the long run. Expect roughly 8 to 9 hours.

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

Tomorrow, after the full retrain finishes

1. Convert the new baseline adapter to GGUF so the runtime can actually use the freshly trained model.

```bash
GGUF_CONVERTER_SCRIPT="C:/Users/wikiepeidia/AppData/Local/Programs/Python/Python313/Lib/site-packages/bin/convert_hf_to_gguf.py" python -m src.model_adaptation.cli convert \
 --candidate baseline-winner \
 --version-tag proposal-closeout-gguf-2026-05-26 \
 --output-root "D:/PROJEct/AI MODELS" \
 --registry-path "D:/PROJEct/AI MODELS/manifests/model-registry.json" \
 --quantization-profile q8_0
```

1. Refresh the Phase 5 snapshot on the repaired holdout using the newly converted GGUF model.

```bash
python -m src.model_adaptation.cli evaluate-release-split \
 --split-path data/splits/recovered-balanced/val.jsonl \
 --snapshot-path .planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json \
 --run-id phase5-recovered-balanced-val \
 --progress-every 1 \
 --checkpoint-every 1
```

1. Build the new explanation review pack from that snapshot.

```bash
python -m src.model_adaptation.cli prepare-explanation-review \
 --snapshot-path .planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json \
 --output-path .planning/phases/05-recall-priority-evaluation-and-release-gates/05-explanation-review-pack.json
```

1. Manual step: review `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-explanation-review-pack.json` and mark it completed only if the new snapshot looks good.

2. After that manual review is complete, synthesize the final refreshed Phase 5 verdict and artifacts.

```bash
python -m src.model_adaptation.cli release-eval \
 --snapshot-path .planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json \
 --review-pack-path .planning/phases/05-recall-priority-evaluation-and-release-gates/05-explanation-review-pack.json \
 --report-dir .planning/phases/05-recall-priority-evaluation-and-release-gates \
 --manifest-dir data/manifests
```

Notes

- The ~20 minute run from today was only a smoke test: `smoke_test: true`, `checkpoint-2`, 2 steps total.
- The full retrain above is the real run.
- The convert step matters because Phase 5 evaluation uses the runtime model path, and the default runtime backend reads the GGUF artifact.
- On this machine, plain `q4_k_m` conversion failed because there is no `llama-quantize` binary available. The working overnight path used the installed Python 3.13 converter script with direct `q8_0` output.
