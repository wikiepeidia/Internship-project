| Chapter | Primary evidence | Claim boundary |
|---|---|---|
| Introduction | `data/manifests/final-qlora-evidence-2026-06.json` | Local Vietnamese phishing prototype; no production or independent-test claim. |
| Background | Cited literature and NIST privacy principles | Literature motivates design; it does not prove implementation details or dataset novelty. |
| Methodology | Final judge/provenance artifacts, manifest-bound human sheet, split hashes, implementation code | Pydantic validates structure; joined Codex evidence covers 2,097 rows and the separate human sample covers 100. Final splits are seed-disjoint; 296 reconstructed Zalo rows share the judge family. |
| Implementation | `src/data_pipeline`, `src/model_adaptation`, `src/runtime` | Text-only local runtime, QLoRA training, GGUF conversion, and structured result contract. |
| Evaluation | `baseline-eval-qwen3-4b.json`, `eval-results-qlora.json` | Historical same-model comparison on 254 validation rows; 413 rows were then designated test. These metrics were not recomputed on the promoted corpus, whose current test split has 220 rows. |
| Deployment | External registry plus final evidence manifest | Q8_0 GGUF path, byte size, SHA-256, doctor pass, and CLI demo pass. |
| Conclusion | Final evidence manifest and disclosed limitations | Final corpus splits are seed-disjoint; model metrics remain historical internal-development evidence, and independent real-world testing remains future work. |
