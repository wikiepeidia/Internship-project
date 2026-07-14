# Defense Walkthrough — Numbered Story Order

This folder exists for one reason: so you can navigate the codebase live, in front of judges, **by opening files in order by name** — no full-text search, no grep. See `documents/reports/supervisor/defense_code_navigation.md` for the full rationale (a different team got destroyed in defense over exactly this).

**These are not a second implementation.** Each file is a byte-for-byte copy of the real source, with one header comment block added on top pointing back to the canonical `src/...` path it came from. If a judge asks "is this the real code," open the header — it says exactly where the original lives, and you can open that file too to show they match.

**This is a snapshot**, taken on this branch (`defense-walkthrough`) on 2026-07-14. It will not auto-update if the real `src/` files change later. If you edit real code after this branch was made, treat this folder as historical reference only — the `src/` tree is always the source of truth.

## The story, in order

| # | File | What happens here |
|---|------|--------------------|
| 1 | `1_scrape_seeds.py` | Fetch real scam-message text from NCSC/tinnhiemmang.vn |
| 2 | `2_generate_synthetic_data.py` | Generate synthetic variations from those seeds via LLM |
| 3 | `3_quality_judge.py` | A different model scores and filters the generated data |
| 4 | `4_split_dataset.py` | Deterministic, seed-aware train/val/test split assignment |
| 5 | `5_train_qlora.py` | QLoRA fine-tuning — all real hyperparameters live here |
| 6 | `6_convert_to_gguf.py` | Merge adapter into base model, export to GGUF Q8_0 |
| 7 | `7_analyze_entrypoint.py` | Where a live message enters the system (`vnphish analyze`) |
| 8 | `8_runtime_service.py` | Orchestrator: normalize, boundary-check, dispatch to backend |
| 9 | `9_prompt_and_grounding.py` | **Start here for "how does it actually work" questions.** Prompt building + the evidence-grounding algorithm (`cue_span_is_grounded`) |
| 10 | `10_gguf_model_backend.py` | Loads the `.gguf` file and calls the model |

Files 1-4 are the data pipeline. Files 5-6 are training. Files 7-10 are the runtime — read these four together to answer "walk me through what happens when I submit a message."

## How to use this during the defense

Open by filename (`Ctrl+P` in VS Code, type e.g. `9_prompt`), not by searching for a keyword. If a judge wants to see the *real* location, the header comment at the top of every file names it exactly.

## Companion documents

- `documents/reports/supervisor/defense_code_navigation.md` — the drilling guide: the four question types that sank a different team's defense, mapped to this project's real answers.
- `documents/reports/supervisor/defense_qa_preparation.md` — full Q&A prep, numbers, and design rationale.
- `documents/reports/supervisor/defense_speaking_script.md` — slide-by-slide talking points.
