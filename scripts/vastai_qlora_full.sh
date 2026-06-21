#!/bin/bash
# =============================================================
# Vast.ai H200/A100 — Full QLoRA + Baseline + GGUF (one shot)
# Paste this entire script into the Vast.ai terminal
# Total time: ~15-30 min on H200, ~45 min on A100
# =============================================================
set -Eeuo pipefail

echo "=== [1/8] Installing dependencies ==="
python3 -m pip install -q \
    "peft>=0.12.0" \
    "transformers>=4.46.0,<5" \
    "accelerate>=1.0.0" \
    "bitsandbytes>=0.44.0" \
    "datasets>=3.0.0" \
    huggingface_hub pydantic-settings python-dotenv

echo "=== [2/8] Cloning repo ==="
REPO=/workspace/vnphish
if [ ! -d "$REPO" ]; then
    git clone --depth 1 https://github.com/wikiepeidia/Internship-project.git "$REPO"
else
    cd "$REPO" && git pull && cd /workspace
fi

echo "=== [3/8] Upload check ==="
# You need to upload these two files to /workspace/ first:
#   train.jsonl  (from data/splits/recovered-balanced/train.jsonl)
#   val.jsonl    (from data/splits/recovered-balanced/val.jsonl)
#
# On Vast.ai: use the file manager in Jupyter, or:
#   scp -P <port> train.jsonl val.jsonl root@<host>:/workspace/
if [ ! -f /workspace/train.jsonl ] || [ ! -f /workspace/val.jsonl ]; then
    echo "ERROR: Upload train.jsonl and val.jsonl to /workspace/ first!"
    echo "Use Vast.ai file manager or: scp -P PORT train.jsonl val.jsonl root@HOST:/workspace/"
    exit 1
fi
echo "train.jsonl: $(wc -l < /workspace/train.jsonl) rows"
echo "val.jsonl: $(wc -l < /workspace/val.jsonl) rows"

echo "=== [4/8] Downloading base model ==="
MODEL_ROOT=/workspace/model-artifacts
BASE=$MODEL_ROOT/base/qwen3-4b-instruct-2507
REGISTRY=$MODEL_ROOT/manifests/model-registry.json
VERSION=qlora-final-2026-06
mkdir -p "$BASE" "$(dirname $REGISTRY)"

python3 -c "
from huggingface_hub import snapshot_download
snapshot_download('Qwen/Qwen3-4B-Instruct-2507', local_dir='$BASE',
    ignore_patterns=['*.msgpack','flax_model*','tf_model*'])
print('Model downloaded.')
"

# Bootstrap registry
cat > "$REGISTRY" << 'REGISTRY_EOF'
{
  "version_tag": "qlora-final-2026-06",
  "selection": {
    "baseline_winner_id": "qwen3-4b-instruct-2507",
    "runner_up_id": "qwen3.5-4b",
    "selection_notes": "QLoRA NF4 retrain on Vast.ai"
  },
  "scorecards": [],
  "artifacts": []
}
REGISTRY_EOF

export MODEL_ARTIFACT_ROOT=$MODEL_ROOT
export MODEL_REGISTRY_PATH=$REGISTRY

echo "=== [5/8] Baseline eval (zero-shot, no adapter) ==="
cd "$REPO"
python3 << 'BASELINE_EOF'
import json, re, torch
from pathlib import Path
from collections import defaultdict
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE = "/workspace/model-artifacts/base/qwen3-4b-instruct-2507"
VAL = "/workspace/val.jsonl"
LABELS = ["bank_impersonation", "zalo_social_engineering", "task_scam", "benign"]
ALIASES = {"bank impersonation":"bank_impersonation","zalo social engineering":"zalo_social_engineering",
           "social engineering":"zalo_social_engineering","task scam":"task_scam",
           "safe":"benign","legitimate":"benign","not phishing":"benign"}
PROMPT = """You are a Vietnamese financial phishing detector.
Classify the following message into exactly one category:
- bank_impersonation
- zalo_social_engineering
- task_scam
- benign
Reply with ONLY the category name."""

def extract(raw):
    t = re.sub(r"<think>.*?</think>","",raw,flags=re.DOTALL).strip().lower()
    for l in LABELS:
        if l in t: return l
    for a,c in sorted(ALIASES.items(),key=lambda x:-len(x[0])):
        if a in t: return c
    if any(w in t for w in ["bank","otp"]): return "bank_impersonation"
    if any(w in t for w in ["zalo","social"]): return "zalo_social_engineering"
    if any(w in t for w in ["task","job"]): return "task_scam"
    if any(w in t for w in ["safe","legit","normal"]): return "benign"
    return "unknown"

print("Loading base model...")
model = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.float16, device_map="auto")
tok = AutoTokenizer.from_pretrained(BASE)
model.eval()
rows = [json.loads(l) for l in open(VAL)]
print(f"Evaluating {len(rows)} rows (baseline)...")
results = []
for i,row in enumerate(rows):
    msgs = [{"role":"user","content":PROMPT+"\n\nMessage: "+row["text"]}]
    try: p = tok.apply_chat_template(msgs,tokenize=False,add_generation_prompt=True,enable_thinking=False)
    except: p = tok.apply_chat_template(msgs,tokenize=False,add_generation_prompt=True)
    inp = tok(p,return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inp,max_new_tokens=64,do_sample=False,pad_token_id=tok.eos_token_id)
    raw = tok.decode(out[0][inp["input_ids"].shape[1]:],skip_special_tokens=True)
    results.append({"true":row["label"],"pred":extract(raw)})
    if (i+1)%50==0: print(f"  {i+1}/{len(rows)}")

tp=defaultdict(int);fp=defaultdict(int);fn=defaultdict(int)
for r in results:
    if r["true"]==r["pred"]: tp[r["true"]]+=1
    else: fp[r["pred"]]+=1; fn[r["true"]]+=1
mf1 = sum(2*tp[l]/(2*tp[l]+fp[l]+fn[l]) if (2*tp[l]+fp[l]+fn[l])>0 else 0 for l in LABELS)/4
correct = sum(1 for r in results if r["true"]==r["pred"])
print(f"\nBaseline Macro F1: {mf1:.4f}  Acc: {correct}/{len(results)}")
out = {"base_model":"Qwen/Qwen3-4B-Instruct-2507","macro_f1":round(mf1,4),
       "accuracy":round(correct/len(results),4),"predictions":results}
Path("/workspace/baseline-eval-qwen3-4b.json").write_text(json.dumps(out,indent=2))
del model; torch.cuda.empty_cache()
print("Baseline done. GPU freed.")
BASELINE_EOF

echo "=== [6/8] QLoRA NF4 training ==="
python3 -m src.model_adaptation.cli train \
    --candidate baseline-winner \
    --version-tag "$VERSION" \
    --train-split /workspace/train.jsonl \
    --val-split /workspace/val.jsonl \
    --output-root "$MODEL_ROOT" \
    --registry-path "$REGISTRY" \
    --device cuda

# Verify it was QLoRA
ADAPTER=$MODEL_ROOT/$VERSION/qwen3-4b-instruct-2507/adapter
python3 -c "
import json
s = json.load(open('$ADAPTER/training-summary.json'))
print(f\"Mode: {s['quantization_mode']}\")
print(f\"Train: {s['train_examples']} Val: {s['val_examples']}\")
assert s['quantization_mode'] == '4bit-qlora', f\"WRONG: {s['quantization_mode']}\"
print('QLoRA NF4 confirmed!')
"

echo "=== [7/8] Fine-tuned eval ==="
python3 << 'EVAL_EOF'
import json, torch
from pathlib import Path
from collections import defaultdict
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

BASE = "/workspace/model-artifacts/base/qwen3-4b-instruct-2507"
ADAPTER = "/workspace/model-artifacts/qlora-final-2026-06/qwen3-4b-instruct-2507/adapter"
VAL = "/workspace/val.jsonl"
LABELS = ["bank_impersonation","zalo_social_engineering","task_scam","benign"]
CID = "Qwen/Qwen3-4B-Instruct-2507"
SCHEMA = json.dumps({"label":"bank_impersonation | zalo_social_engineering | task_scam | benign",
    "risk_tier":"benign | suspicious | high-risk","suspicious_spans":["exact suspicious substrings"],
    "xai_explanation":"localized explanation"},ensure_ascii=False)

print("Loading base + adapter...")
model = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.float16, device_map="auto")
model = PeftModel.from_pretrained(model, ADAPTER)
tok = AutoTokenizer.from_pretrained(BASE)
model.eval()

def classify(text):
    inst = f"Candidate: {CID}\nYou are fine-tuning a local Vietnamese phishing detector.\nAnalyze the following raw message text and produce a structured response.\nResponse schema: {SCHEMA}\nMessage text: {text}"
    full = f"### Instruction\n{inst}\n\n### Response\n"
    inp = tok(full, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inp, max_new_tokens=64, do_sample=False)
    raw = tok.decode(out[0][inp["input_ids"].shape[1]:], skip_special_tokens=True).strip().lower()
    return next((l for l in LABELS if l in raw), "benign")

rows = [json.loads(l) for l in open(VAL)]
print(f"Evaluating {len(rows)} rows (fine-tuned)...")
results = []
for i,row in enumerate(rows):
    results.append({"true":row["label"],"pred":classify(row["text"])})
    if (i+1)%50==0:
        acc = sum(1 for r in results if r["true"]==r["pred"])/len(results)
        print(f"  {i+1}/{len(rows)} acc={acc:.3f}")

tp=defaultdict(int);fp=defaultdict(int);fn=defaultdict(int)
for r in results:
    if r["true"]==r["pred"]: tp[r["true"]]+=1
    else: fp[r["pred"]]+=1; fn[r["true"]]+=1
for l in LABELS:
    s=sum(1 for r in results if r["true"]==l)
    p=tp[l]/(tp[l]+fp[l]) if tp[l]+fp[l]>0 else 0
    rc=tp[l]/(tp[l]+fn[l]) if tp[l]+fn[l]>0 else 0
    f=2*p*rc/(p+rc) if p+rc>0 else 0
    print(f"  {l:35s} P={p:.4f} R={rc:.4f} F1={f:.4f} n={s}")
mf1=sum(2*tp[l]/(2*tp[l]+fp[l]+fn[l]) if 2*tp[l]+fp[l]+fn[l]>0 else 0 for l in LABELS)/4
correct=sum(1 for r in results if r["true"]==r["pred"])
print(f"\nFine-tuned Macro F1: {mf1:.4f}  Acc: {correct}/{len(results)}")
out={"model":CID,"quantization":"4bit-qlora","macro_f1":round(mf1,4),
     "accuracy":round(correct/len(results),4),"predictions":results}
Path("/workspace/eval-results-qlora.json").write_text(json.dumps(out,indent=2))
del model; torch.cuda.empty_cache()
EVAL_EOF

echo "=== [8/8] GGUF Q8_0 export ==="
MERGED="$MODEL_ROOT/$VERSION/qwen3-4b-instruct-2507/merged" \
  bash "$REPO/scripts/vastai_gguf_export.sh"

echo ""
echo "============================================"
echo "  ALL DONE! Download these files:"
echo "============================================"
echo ""
cp "$ADAPTER/training-summary.json" /workspace/training-summary.json
ls -lh /workspace/baseline-eval-qwen3-4b.json
ls -lh /workspace/eval-results-qlora.json
ls -lh /workspace/training-summary.json
ls -lh /workspace/gguf-laptop.gguf 2>/dev/null || ls -lh "$MODEL_ROOT"/$VERSION/*/gguf*.gguf 2>/dev/null
echo ""
echo "Use Vast.ai file manager or:"
echo "  scp -P PORT root@HOST:/workspace/{baseline-eval-qwen3-4b.json,eval-results-qlora.json,training-summary.json,gguf-laptop.gguf} ."
