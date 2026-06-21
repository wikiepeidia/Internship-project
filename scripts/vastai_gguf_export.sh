#!/usr/bin/env bash

# Resume-safe GGUF export for the Vast.ai training workflow.
# This script never trains or evaluates. If a merged HF model already exists,
# it only repairs the converter environment and writes the GGUF artifact.

set -Eeuo pipefail

BASE="${BASE:-/workspace/model-artifacts/base/qwen3-4b-instruct-2507}"
ADAPTER="${ADAPTER:-/workspace/model-artifacts/qlora-final-2026-06/qwen3-4b-instruct-2507/adapter}"
MERGED="${MERGED:-/workspace/merged-model}"
GGUF_OUT="${GGUF_OUT:-/workspace/gguf-laptop.gguf}"
LLAMA_CPP="${LLAMA_CPP:-/workspace/llama.cpp}"
PYTHON="${PYTHON:-python3}"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

if [[ ! -f "$MERGED/config.json" ]]; then
  [[ -f "$BASE/config.json" ]] || die "Base model is missing: $BASE"
  [[ -f "$ADAPTER/adapter_config.json" ]] || die "Adapter config is missing: $ADAPTER"
  [[ -f "$ADAPTER/adapter_model.safetensors" || -f "$ADAPTER/adapter_model.bin" ]] || \
    die "Adapter weights are missing under $ADAPTER"

  echo "[1/4] Merging QLoRA adapter into the BF16 base model..."
  BASE="$BASE" ADAPTER="$ADAPTER" MERGED="$MERGED" "$PYTHON" <<'PY'
import os
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

base_path = os.environ["BASE"]
adapter_path = os.environ["ADAPTER"]
merged_path = os.environ["MERGED"]

base = AutoModelForCausalLM.from_pretrained(
    base_path,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    low_cpu_mem_usage=True,
)
merged = PeftModel.from_pretrained(base, adapter_path).merge_and_unload()
Path(merged_path).mkdir(parents=True, exist_ok=True)
merged.save_pretrained(merged_path, safe_serialization=True)
AutoTokenizer.from_pretrained(base_path).save_pretrained(merged_path)
print(f"Merged model written to {merged_path}")
PY
else
  echo "[1/4] Reusing existing merged model: $MERGED"
fi

[[ -f "$MERGED/tokenizer.json" || -f "$MERGED/tokenizer.model" ]] || \
  die "Merged model has no tokenizer.json or tokenizer.model: $MERGED"

# Some Qwen snapshots serialize `extra_special_tokens` as a list. Recent
# Transformers releases reserve that field for a name-to-token mapping, while
# the same list is valid as `additional_special_tokens`.
MERGED="$MERGED" "$PYTHON" <<'PY'
import json
import os
from pathlib import Path

config_path = Path(os.environ["MERGED"]) / "tokenizer_config.json"
if config_path.exists():
    config = json.loads(config_path.read_text(encoding="utf-8"))
    extra = config.get("extra_special_tokens")
    if isinstance(extra, list):
        current = config.get("additional_special_tokens") or []
        config.pop("extra_special_tokens", None)
        config["additional_special_tokens"] = list(dict.fromkeys([*current, *extra]))
        config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Normalized {len(extra)} tokenizer special tokens")
PY

echo "[2/4] Preparing the official llama.cpp converter..."
if [[ ! -f "$LLAMA_CPP/convert_hf_to_gguf.py" ]]; then
  rm -rf "$LLAMA_CPP"
  git clone --depth 1 https://github.com/ggerganov/llama.cpp.git "$LLAMA_CPP"
fi

# A PyPI package named `conversion` shadows llama.cpp's own conversion package.
"$PYTHON" -m pip uninstall -y conversion >/dev/null 2>&1 || true
"$PYTHON" -m pip install -q sentencepiece protobuf safetensors

echo "[3/4] Validating the tokenizer environment..."
if ! MERGED="$MERGED" "$PYTHON" <<'PY'
import os
import transformers
from transformers import AutoTokenizer
from transformers.generation import GenerationMixin

AutoTokenizer.from_pretrained(os.environ["MERGED"])
print(f"Tokenizer OK (transformers {transformers.__version__})")
PY
then
  echo "Repairing the mixed transformers/tokenizers installation..."
  "$PYTHON" -m pip uninstall -y transformers tokenizers >/dev/null 2>&1 || true
  "$PYTHON" -m pip install -q --no-cache-dir --force-reinstall \
    "transformers==4.57.1" sentencepiece protobuf safetensors
  MERGED="$MERGED" "$PYTHON" <<'PY'
import os
import transformers
from transformers import AutoTokenizer
from transformers.generation import GenerationMixin

AutoTokenizer.from_pretrained(os.environ["MERGED"])
print(f"Tokenizer repaired (transformers {transformers.__version__})")
PY
fi

echo "[4/4] Converting merged model to GGUF Q8_0..."
rm -f "$GGUF_OUT"
(
  cd "$LLAMA_CPP"
  "$PYTHON" convert_hf_to_gguf.py "$MERGED" \
    --outfile "$GGUF_OUT" \
    --outtype q8_0
)

[[ -s "$GGUF_OUT" ]] || die "Converter did not produce $GGUF_OUT"
size_bytes=$(wc -c < "$GGUF_OUT")
(( size_bytes > 1000000000 )) || die "GGUF is unexpectedly small: ${size_bytes} bytes"

echo "GGUF READY"
ls -lh "$GGUF_OUT"
