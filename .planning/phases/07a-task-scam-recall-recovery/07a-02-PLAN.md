---
phase: 07a-task-scam-recall-recovery
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - notebooks/H100fixedv5.ipynb
autonomous: true
requirements:
  - EVAL-02

must_haves:
  truths:
    - "The notebook contains a clearly marked training section that can be run after the vLLM server is stopped"
    - "The training section installs all required Python packages before any training code runs"
    - "The training section loads the base model from HuggingFace (not from local disk)"
    - "The training section runs the existing src.model_adaptation.cli train command with the correct version tag"
    - "The training section zips the adapter directory and prints the path for download"
    - "The training section includes evaluation cells that run the adapter model on /content/val.jsonl and compute per-label recall without GGUF conversion"
    - "The evaluation cells write a snapshot JSON to /content/eval-snapshot-task-scam-recovery.json in the ReleaseEvaluationSnapshot-compatible format"
    - "The generation section still works unchanged (existing cells are not broken)"
  artifacts:
    - path: "notebooks/H100fixedv5.ipynb"
      provides: "H100 Colab notebook with vLLM generation section plus training and evaluation sections"
      contains: "task-scam-recovery-2026-05-28"
  key_links:
    - from: "Training section install cell"
      to: "Training section train cell"
      via: "peft transformers accelerate bitsandbytes datasets all installed before train CLI runs"
      pattern: "peft.*transformers.*accelerate"
    - from: "Training section train cell"
      to: "src.model_adaptation.cli train"
      via: "python -m src.model_adaptation.cli train --candidate baseline-winner --version-tag task-scam-recovery-2026-05-28"
      pattern: "task-scam-recovery-2026-05-28"
    - from: "Evaluation cell F"
      to: "eval-snapshot-task-scam-recovery.json"
      via: "PeftModel inference on val.jsonl → per-label recall → snapshot JSON"
      pattern: "eval-snapshot-task-scam-recovery"
---

<objective>
Add a self-contained training section to `notebooks/H100fixedv5.ipynb` that the operator runs after stopping the vLLM generation server. The new section installs training dependencies, clones or uploads the repo, runs the existing training CLI, and zips the adapter for download. The existing generation and judge sections are left completely intact.

Purpose: The H100 that serves vLLM for generation can retrain the 4B model after the server is stopped — the same session handles both roles per D-08. The training section must be ready before the operator starts the H100 session so no notebook editing is required mid-session.

Output: Updated `H100fixedv5.ipynb` with new training section cells appended after the existing "stop server" cell.
</objective>

<execution_context>
@C:/Users/wikiepeidia/OneDrive - caugiay.edu.vn/bài tập/usth/GEN14/INTERNSHIP/Internship-project/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/wikiepeidia/OneDrive - caugiay.edu.vn/bài tập/usth/GEN14/INTERNSHIP/Internship-project/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/07a-task-scam-recall-recovery/07a-CONTEXT.md
@.planning/phases/07-proposal-closeout-and-quantitative-validation/07-CONTEXT.md

<interfaces>
<!-- Existing notebook structure the executor must understand before editing. -->
<!--
The notebook H100fixedv5.ipynb has these cells in order:
  Cell "83777174" (markdown): Phase 7 H100 Colab Endpoint Notebook — intro and constraints
  Cell "5a04df79" (code):     %%capture — %pip -q install "vllm>=0.10.0" "pyngrok>=7.2.0"
  Cell "fd73909e" (code):     Imports, ACTIVE_ROLE, MODEL_PROFILES, WORKDIR setup
  Cell "5554e7b4" (code):     Helper functions: tail_log, stop_all_processes, start_vllm_server, wait_for_vllm_ready, start_*_tunnel
  Cell "e2e3d518" (code):     server_process = start_vllm_server()
  Cell "8c27feb8" (code):     wait_for_vllm_ready(...)
  Cell "930f199c" (code):     start_tunnel() — prints OPENAI_COMPATIBLE_* env and local CLI command
  Cell "b676efc2" (markdown): "How To Use This Notebook" — generator/judge instructions
  Cell "ca6822ab" (code):     stop_all_processes(kill_tunnel=True) — STOP SERVER CELL

New training cells must come AFTER cell "ca6822ab".
The training cells must be a new logical section with a markdown header cell first.
-->

From .planning/phases/07a-task-scam-recall-recovery/07a-CONTEXT.md D-09 and D-11-workflow:
- Install: peft transformers accelerate bitsandbytes datasets
- Clone/upload repo src/ tree to Colab
- Set MODEL_ARTIFACT_ROOT to a Colab path
- Load base model from HuggingFace: Qwen/Qwen3-4B-Instruct-2507 (or the locked 4B checkpoint ID)
- Run: python -m src.model_adaptation.cli train --candidate baseline-winner --version-tag task-scam-recovery-2026-05-28 ...
- Zip adapter directory for download

From .planning/phases/07-proposal-closeout-and-quantitative-validation/07-CONTEXT.md canonical train command:
python -m src.model_adaptation.cli train \
  --candidate baseline-winner \
  --version-tag proposal-closeout-full-2026-05-26 \
  --train-split data/splits/recovered-balanced/train.jsonl \
  --val-split data/splits/recovered-balanced/val.jsonl \
  --output-root "D:/PROJEct/AI MODELS" \
  --registry-path "D:/PROJEct/AI MODELS/manifests/model-registry.json" \
  --device cuda \
  --full-precision
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Append training section cells to H100fixedv5.ipynb</name>

  <read_first>
    - notebooks/H100fixedv5.ipynb (full file — understand existing cell structure, especially cell IDs and the stop_all_processes call at the end)
    - .planning/phases/07a-task-scam-recall-recovery/07a-CONTEXT.md (D-08, D-09, D-10, D-11-workflow — full training workflow requirements)
    - .planning/phases/07-proposal-closeout-and-quantitative-validation/07-CONTEXT.md (canonical train command flags)
  </read_first>

  <files>
    notebooks/H100fixedv5.ipynb
  </files>

  <action>
  Read the current notebook JSON. Append the following new cells to the `cells` array (after the existing last cell with `stop_all_processes`). Use unique cell IDs that do not collide with existing ones. The notebook format is `nbformat: 4`.

  **New cell 1 — Markdown section header:**
  ```
  ## Phase 7a: Training Section (run AFTER generation is complete and vLLM is stopped)

  This section retrains the `qwen3-4b-instruct-2507` baseline winner on the augmented splits that include the new task_scam rows generated above.

  **Prerequisites before running these cells:**
  1. Generation pass complete — new `task-scam-recovery-2026-05-28.jsonl` file exists locally.
  2. Splits rebuilt locally — `data/splits/recovered-balanced/train.jsonl` and `val.jsonl` updated.
  3. vLLM server stopped (run the cell above).
  4. GPU memory cleared — verify with `nvidia-smi` before proceeding.

  **Workflow:**
  - Cell A: Install training dependencies.
  - Cell B: Clone repo and upload augmented splits.
  - Cell C: Configure training paths.
  - Cell D: Run training CLI.
  - Cell E: Zip and download adapter.
  ```

  **New cell 2 (code) — Install training dependencies (%%capture to keep output quiet):**
  ```python
  %%capture
  import subprocess, sys

  # Install training stack. peft and bitsandbytes enable QLoRA on the H100.
  subprocess.run(
      [sys.executable, "-m", "pip", "install", "-q",
       "peft>=0.12.0",
       "transformers>=4.46.0",
       "accelerate>=1.0.0",
       "bitsandbytes>=0.44.0",
       "datasets>=3.0.0"],
      check=True,
  )
  print("Training dependencies installed.")
  ```

  **New cell 3 (code) — Clone repo and upload splits:**
  ```python
  import os
  import subprocess
  from pathlib import Path

  # --- CONFIGURE BEFORE RUNNING ---
  # Option A (recommended): clone the repo from GitHub.
  REPO_URL = "https://github.com/YOUR_ORG/YOUR_REPO.git"   # Replace with actual repo URL
  REPO_BRANCH = "main"
  COLAB_REPO_ROOT = Path("/content/vnphish-repo")

  # Option B: If the repo is private, upload a zip of the src/ tree manually to /content/
  # and set COLAB_REPO_ROOT to "/content/vnphish-repo" after unzipping.
  # Then skip the git clone block below.

  # --- Split upload path (upload these files from your local machine via Files panel) ---
  # Required uploads:
  #   /content/train.jsonl  (from data/splits/recovered-balanced/train.jsonl after local rebuild)
  #   /content/val.jsonl    (from data/splits/recovered-balanced/val.jsonl after local rebuild)
  COLAB_TRAIN_SPLIT = Path("/content/train.jsonl")
  COLAB_VAL_SPLIT   = Path("/content/val.jsonl")

  if not COLAB_REPO_ROOT.exists():
      print(f"Cloning repo from {REPO_URL} ...")
      result = subprocess.run(
          ["git", "clone", "--branch", REPO_BRANCH, "--depth", "1", REPO_URL, str(COLAB_REPO_ROOT)],
          capture_output=True, text=True,
      )
      if result.returncode != 0:
          print("git clone failed:")
          print(result.stderr[-3000:])
          raise RuntimeError("Repo clone failed. See error above.")
      print("Repo cloned.")
  else:
      print(f"Repo already exists at {COLAB_REPO_ROOT}, pulling latest...")
      subprocess.run(["git", "-C", str(COLAB_REPO_ROOT), "pull"], check=False)

  if not COLAB_TRAIN_SPLIT.exists():
      raise FileNotFoundError(
          f"Upload {COLAB_TRAIN_SPLIT} before running. "
          "Use the Colab Files panel or copy from /content/ after uploading."
      )
  if not COLAB_VAL_SPLIT.exists():
      raise FileNotFoundError(
          f"Upload {COLAB_VAL_SPLIT} before running. "
          "Use the Colab Files panel."
      )

  print("Repo and splits are ready.")
  print(f"  train split: {COLAB_TRAIN_SPLIT} ({COLAB_TRAIN_SPLIT.stat().st_size // 1024} KB)")
  print(f"  val split:   {COLAB_VAL_SPLIT} ({COLAB_VAL_SPLIT.stat().st_size // 1024} KB)")
  ```

  **New cell 4 (code) — Configure training paths and environment:**
  ```python
  import json, os
  from pathlib import Path

  # Training output will land here inside Colab's /content volume.
  # Zip and download the adapter sub-directory after training finishes.
  COLAB_MODEL_ARTIFACT_ROOT = Path("/content/model-artifacts")
  COLAB_REGISTRY_PATH = COLAB_MODEL_ARTIFACT_ROOT / "manifests" / "model-registry.json"
  COLAB_MODEL_ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
  COLAB_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)

  # Seed an empty registry if it does not exist yet (the train CLI will populate it).
  if not COLAB_REGISTRY_PATH.exists():
      COLAB_REGISTRY_PATH.write_text(
          json.dumps({}),
          encoding="utf-8",
      )

  # Set env vars so the train CLI resolves paths correctly inside Colab.
  os.environ["MODEL_ARTIFACT_ROOT"] = str(COLAB_MODEL_ARTIFACT_ROOT)
  os.environ["MODEL_REGISTRY_PATH"] = str(COLAB_REGISTRY_PATH)

  TRAIN_SPLIT = str(COLAB_TRAIN_SPLIT)
  VAL_SPLIT   = str(COLAB_VAL_SPLIT)
  VERSION_TAG = "task-scam-recovery-2026-05-28"       # D-10: locked version tag

  print("Training configuration:")
  print(json.dumps({
      "output_root":     str(COLAB_MODEL_ARTIFACT_ROOT),
      "registry_path":   str(COLAB_REGISTRY_PATH),
      "train_split":     TRAIN_SPLIT,
      "val_split":       VAL_SPLIT,
      "version_tag":     VERSION_TAG,
  }, indent=2))
  ```

  **New cell 4b (code) — Download base model from HuggingFace:**
  ```python
  from huggingface_hub import snapshot_download
  from pathlib import Path

  # D-08: HF model ID confirmed from catalog.py hf_source for qwen3-4b-instruct-2507 (baseline-winner)
  BASE_MODEL_ID = "Qwen/Qwen3-4B-Instruct-2507"
  BASE_MODEL_LOCAL = COLAB_MODEL_ARTIFACT_ROOT / "base" / "qwen3-4b-instruct-2507"
  BASE_MODEL_LOCAL.mkdir(parents=True, exist_ok=True)

  print(f"Downloading base model {BASE_MODEL_ID} to {BASE_MODEL_LOCAL} ...")
  snapshot_download(
      repo_id=BASE_MODEL_ID,
      local_dir=str(BASE_MODEL_LOCAL),
      ignore_patterns=["*.msgpack", "flax_model*", "tf_model*", "rust_model*"],
  )
  print(f"Base model downloaded. Size: {sum(f.stat().st_size for f in BASE_MODEL_LOCAL.rglob('*') if f.is_file()) // (1024*1024)} MB")
  ```

  **New cell 5 (code) — Run training CLI:**
  ```python
  import subprocess, sys, os
  from pathlib import Path

  # Run from inside the cloned repo so Python can find src/.
  train_cmd = [
      sys.executable, "-m", "src.model_adaptation.cli", "train",
      "--candidate",       "baseline-winner",
      "--version-tag",     VERSION_TAG,
      "--train-split",     TRAIN_SPLIT,
      "--val-split",       VAL_SPLIT,
      "--output-root",     str(COLAB_MODEL_ARTIFACT_ROOT),
      "--registry-path",   str(COLAB_REGISTRY_PATH),
      "--device",          "cuda",
      "--full-precision",
  ]

  print("Starting training. This may take 2-4 hours on H100 for the full augmented dataset.")
  print("Command:", " ".join(train_cmd))
  print()

  result = subprocess.run(
      train_cmd,
      cwd=str(COLAB_REPO_ROOT),
      env={**os.environ},
  )

  if result.returncode != 0:
      raise RuntimeError(f"Training failed with exit code {result.returncode}. Check output above.")
  print("Training complete.")
  ```

  **New cell 6 (code) — Zip adapter and print download path:**
  ```python
  import subprocess, shutil
  from pathlib import Path

  # Locate the adapter directory that the train CLI created.
  # The pattern is: {output_root}/{version_tag}/qwen3-4b-instruct-2507/adapter/
  adapter_dir = COLAB_MODEL_ARTIFACT_ROOT / VERSION_TAG / "qwen3-4b-instruct-2507" / "adapter"
  zip_output  = Path(f"/content/adapter-{VERSION_TAG}.zip")

  if not adapter_dir.exists():
      # Fallback: search for any adapter directory under the output root.
      candidates = list(COLAB_MODEL_ARTIFACT_ROOT.rglob("adapter"))
      if candidates:
          adapter_dir = candidates[-1]
          print(f"Using discovered adapter directory: {adapter_dir}")
      else:
          raise FileNotFoundError(
              f"No adapter directory found under {COLAB_MODEL_ARTIFACT_ROOT}. "
              "Check training output above."
          )

  print(f"Adapter directory: {adapter_dir}")
  print(f"Contents: {list(adapter_dir.iterdir())}")

  shutil.make_archive(
      base_name=str(zip_output.with_suffix("")),
      format="zip",
      root_dir=str(adapter_dir.parent),
      base_dir=adapter_dir.name,
  )

  print(f"\nAdapter zipped to: {zip_output}")
  print(f"Zip size: {zip_output.stat().st_size // 1024} KB")
  print()
  print("Download instructions:")
  print("  1. In the Colab Files panel, navigate to /content/")
  print(f"  2. Right-click {zip_output.name} and select 'Download'")
  print(f"  3. Extract locally and register the adapter path in your off-repo model registry")
  print(f"     (D:/PROJEct/AI MODELS/manifests/model-registry.json)")
  ```

  **New cell F (code) — Colab evaluation: inference on val split using adapter model:**
  ```python
  import json, sys, torch
  from pathlib import Path
  from transformers import AutoModelForCausalLM, AutoTokenizer
  from peft import PeftModel
  from collections import defaultdict

  sys.path.insert(0, str(COLAB_REPO_ROOT))

  # Load model + adapter for eval (base model is already on disk from cell 4b)
  print("Loading base model + adapter for evaluation...")
  eval_model = AutoModelForCausalLM.from_pretrained(
      str(BASE_MODEL_LOCAL), torch_dtype=torch.bfloat16, device_map="auto"
  )
  eval_model = PeftModel.from_pretrained(eval_model, str(adapter_dir))
  eval_tokenizer = AutoTokenizer.from_pretrained(str(BASE_MODEL_LOCAL))
  eval_model.eval()
  print("Model loaded.")

  LABELS = ["bank_impersonation", "zalo_social_engineering", "task_scam", "benign"]

  def classify_message(text: str) -> str:
      # Try to import the exact classify prompt from the cloned repo
      try:
          from src.model_adaptation.analyze import build_classify_prompt
          prompt = build_classify_prompt(text)
      except (ImportError, AttributeError):
          # Fallback: Qwen3 instruction format matching training data
          prompt = (
              "<|im_start|>system\nYou are an expert Vietnamese financial fraud detection system. "
              "Classify the message into exactly one of: bank_impersonation, zalo_social_engineering, "
              "task_scam, benign. Reply with only the label.<|im_end|>\n"
              f"<|im_start|>user\n{text}<|im_end|>\n"
              "<|im_start|>assistant\n"
          )
      inputs = eval_tokenizer(prompt, return_tensors="pt").to(eval_model.device)
      with torch.no_grad():
          out = eval_model.generate(**inputs, max_new_tokens=16, do_sample=False)
      raw = eval_tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip().lower()
      return next((lbl for lbl in LABELS if lbl in raw), "benign")

  val_rows = [json.loads(l) for l in open(COLAB_VAL_SPLIT, encoding="utf-8")]
  print(f"Running inference on {len(val_rows)} val rows...")
  results = []
  for i, row in enumerate(val_rows):
      pred = classify_message(row["text"])
      results.append({"true": row["label"], "pred": pred})
      if (i + 1) % 20 == 0:
          print(f"  {i+1}/{len(val_rows)}")
  print("Inference complete.")
  ```

  **New cell G (code) — Compute per-label metrics and write snapshot JSON:**
  ```python
  import json
  from pathlib import Path
  from collections import defaultdict

  FLOORS = {"bank_impersonation": 0.90, "zalo_social_engineering": 0.90, "task_scam": 0.80}

  tp = defaultdict(int); fp = defaultdict(int); fn = defaultdict(int)
  for r in results:
      if r["true"] == r["pred"]: tp[r["true"]] += 1
      else: fp[r["pred"]] += 1; fn[r["true"]] += 1

  per_label_metrics = []
  blocker_reasons = []
  print("\n=== Per-label Evaluation Results ===")
  for lbl in LABELS:
      support = sum(1 for r in results if r["true"] == lbl)
      prec = tp[lbl] / (tp[lbl] + fp[lbl]) if (tp[lbl] + fp[lbl]) > 0 else 0.0
      rec  = tp[lbl] / (tp[lbl] + fn[lbl]) if (tp[lbl] + fn[lbl]) > 0 else 0.0
      f1   = 2*prec*rec/(prec+rec) if (prec+rec) > 0 else 0.0
      floor = FLOORS.get(lbl)
      status = f"PASS ✓" if (not floor or rec >= floor) else f"FAIL ✗ (floor={floor})"
      if floor and rec < floor:
          blocker_reasons.append(f"{lbl} recall {rec:.4f} is below the required floor of {floor:.2f}")
      print(f"  {lbl:35s} recall={rec:.4f}  prec={prec:.4f}  f1={f1:.4f}  support={support}  {status}")
      per_label_metrics.append({"label": lbl, "recall": rec, "precision": prec, "f1": f1, "support": support, "recall_floor_applies": bool(floor)})

  correct = sum(1 for r in results if r["true"] == r["pred"])
  snapshot = {
      "run_id": f"colab-eval-{VERSION_TAG}",
      "evaluated_split_path": str(COLAB_VAL_SPLIT),
      "audit": {
          "risky_recall_floor": 0.90,
          "blocker_reasons": blocker_reasons,
          "ready": not blocker_reasons,
          "verdict": "PASS" if not blocker_reasons else "BLOCK",
      },
      "overall_metrics": {"accuracy": correct / len(results), "total": len(results), "correct": correct},
      "per_label_metrics": per_label_metrics,
      "rows": results,
  }

  SNAPSHOT_PATH = Path("/content/eval-snapshot-task-scam-recovery.json")
  SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")

  print(f"\nGate verdict: {snapshot['audit']['verdict']}")
  print(f"Snapshot written to {SNAPSHOT_PATH}")
  if blocker_reasons:
      print("BLOCKERS:", blocker_reasons)
      print("Do NOT proceed to release-eval — loop back to generate more data.")
  else:
      print("Download eval-snapshot-task-scam-recovery.json from the Files panel for local release-eval.")
      print("GGUF conversion is NOT required for the gate verdict — only needed for app deployment.")
  ```

  Write the updated notebook back to `notebooks/H100fixedv5.ipynb`. The existing cells must remain identical (same `cell_id`, same `source`). Only new cells are appended.
  </action>

  <verify>
    <automated>python -c "import json; nb = json.loads(open('notebooks/H100fixedv5.ipynb', encoding='utf-8').read()); sources = [c.get('source', '') if isinstance(c.get('source', ''), str) else ''.join(c.get('source', [])) for c in nb['cells']]; full = '\n'.join(sources); checks = ['task-scam-recovery-2026-05-28' in full, 'peft' in full, 'bitsandbytes' in full, 'src.model_adaptation.cli' in full, 'shutil.make_archive' in full, 'stop_all_processes' in full, 'eval-snapshot-task-scam-recovery' in full, 'PeftModel' in full]; print('Checks:', checks); assert all(checks), 'One or more required strings missing from notebook'; print('PASS')"</automated>
  </verify>

  <done>
    - Notebook has all eight new cells after the existing stop_all_processes cell (markdown header + A through G)
    - Markdown section header clearly labels the training section as "run AFTER generation is complete and vLLM is stopped"
    - Install cell uses %%capture and installs peft, transformers, accelerate, bitsandbytes, datasets
    - Clone/upload cell includes REPO_URL placeholder and clear instructions for both clone and manual upload paths
    - Config cell sets MODEL_ARTIFACT_ROOT and MODEL_REGISTRY_PATH env vars to Colab paths and seeds empty registry as `{}`
    - Cell 4b downloads Qwen/Qwen3-4B-Instruct-2507 base model via snapshot_download before training
    - Train cell runs `python -m src.model_adaptation.cli train --candidate baseline-winner --version-tag task-scam-recovery-2026-05-28 --device cuda --full-precision`
    - Zip cell uses shutil.make_archive and prints download instructions
    - Cell F loads base model + adapter via PeftModel, runs inference on /content/val.jsonl, computes per-label recall
    - Cell G writes /content/eval-snapshot-task-scam-recovery.json in ReleaseEvaluationSnapshot-compatible format; prints gate verdict and download instructions
    - Existing cells (generation section, vLLM startup, tunnel, stop server) are unchanged
    - Verification command prints PASS
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Colab filesystem → local machine | Adapter zip is downloaded manually from Colab Files panel; no automated transfer |
| REPO_URL placeholder → actual repo | Operator must replace placeholder before cloning; leaving it blank causes a clear error |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-7a02-01 | Tampering | Model registry seeded with empty JSON | accept | Registry is populated by train CLI during the run; the seed just prevents FileNotFoundError on first access |
| T-7a02-02 | Denial of Service | Long training run exhausts Colab session time limit | mitigate | Checkpoint resume is supported by src.model_adaptation.cli train (established in Phase 3); operator can restart and resume |
| T-7a02-03 | Information Disclosure | NGROK_AUTHTOKEN hardcoded in notebook | accept | Token already present in existing cells; training cells do not use tunnels |
</threat_model>

<verification>
After the task completes:

1. Notebook parses as valid JSON: `python -c "import json; json.loads(open('notebooks/H100fixedv5.ipynb', encoding='utf-8').read()); print('valid JSON')"` prints `valid JSON`.
2. Training section present: the verification command in the task prints `PASS`.
3. Existing cells intact: `python -c "import json; nb = json.loads(open('notebooks/H100fixedv5.ipynb', encoding='utf-8').read()); src = ''.join([''.join(c.get('source',[])) if isinstance(c.get('source',[]), list) else c.get('source','') for c in nb['cells']]); assert 'stop_all_processes' in src; assert 'ACTIVE_ROLE' in src; print('existing cells intact')"` prints `existing cells intact`.
</verification>

<success_criteria>
- Notebook has a new training section with six cells (1 markdown + 5 code)
- Training cell runs `src.model_adaptation.cli train` with `--version-tag task-scam-recovery-2026-05-28` and `--device cuda --full-precision`
- Zip cell produces `/content/adapter-task-scam-recovery-2026-05-28.zip` and prints clear download instructions
- All existing notebook cells are untouched
- Notebook is valid JSON and can be opened in Colab without errors
</success_criteria>

<output>
After completion, create `.planning/phases/07a-task-scam-recall-recovery/07a-02-SUMMARY.md` with:
- Number of cells added and their types
- Exact version tag string used in the training command
- Which existing cells were confirmed unchanged
- Output of the verification command
</output>
