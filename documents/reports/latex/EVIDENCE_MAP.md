| Chapter | Primary evidence | Claim boundary |
|---|---|---|
| Introduction | `data/manifests/final-qlora-evidence-2026-06.json` | Local Vietnamese phishing prototype; no production or independent-test claim. |
| Background | Cited literature and NIST privacy principles | Literature motivates design; it does not prove implementation details or dataset novelty. |
| Methodology | `training-summary.json`, split hashes, `quality-stats.json`, implementation code | Pydantic validates structure; the LLM judge scores sampled semantics; seed overlap is disclosed. |
| Implementation | `src/data_pipeline`, `src/model_adaptation`, `src/runtime` | Text-only local runtime, QLoRA training, GGUF conversion, and structured result contract. |
| Evaluation | `baseline-eval-qwen3-4b.json`, `eval-results-qlora.json` | Same-model comparison on 254 validation rows; the 413-row test split was not evaluated. |
| Deployment | External registry plus final evidence manifest | Q8_0 GGUF path, byte size, SHA-256, doctor pass, and CLI demo pass. |
| Conclusion | Final evidence manifest and disclosed limitations | Reports internal development evidence; real-world, seed-disjoint testing remains future work. |
