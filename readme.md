# VNPhish: local Vietnamese phishing detection

Bachelor internship project, University of Science and Technology of Hanoi
(USTH), 2026.

**Thesis:** Design and Development of a Localized LLM for Vietnamese Financial
Phishing Detection
**Author:** Phạm Thế Minh (23BI14279)
**Supervisors:** Nguyễn Việt Anh, Giang Anh Tuấn

The project is finished and archived. It is not maintained.

## What it does

VNPhish checks one pasted Vietnamese message (SMS, Zalo, chat) on the user's own
computer. Nothing is sent to a cloud API. Each message is sorted into one of four
classes: bank impersonation, Zalo social engineering, task scam, or benign.

Two models were trained on the same data and compared:

- **Qwen3-4B-Instruct-2507, fine-tuned with QLoRA** (4-bit NF4 base, LoRA
  r=16, alpha=32). It writes a JSON answer with the risk tier, the label, the
  phrases it reacted to, and safe next steps. The trained model was exported to a
  Q8_0 GGUF file that runs on a CPU through llama.cpp.
- **PhoBERT-base-v2, fully fine-tuned** as a four-class classifier. It returns
  the label only.

## Results

Final test: 220 messages set aside before training, each model run once.

| | Qwen QLoRA | PhoBERT |
| --- | ---: | ---: |
| Accuracy | 0.9818 | 0.9909 |
| Macro F1 | 0.9805 | 0.9909 |
| Weighted F1 | 0.9818 | 0.9909 |
| Unreadable answers | 0 | 0 |
| Scams called benign | 1 | 1 |

Each model was trained once (seed 42), so the gap describes this run, not a
proven difference between the models.

## Dataset

2,097 messages (1,658 train / 219 validation / 220 test), written by LLMs from
public scam warnings on tinnhiemmang.vn, then checked by a separate judge model
and by manual review. All messages from one source article stay in the same
split.

The dataset is on Hugging Face:
[wikiepeidia/vnphish-dataset](https://huggingface.co/datasets/wikiepeidia/vnphish-dataset).
Phone numbers and email addresses are masked in that public copy. The trained
model files are not published.

## Limitations

- The messages are generated, not collected from real victims.
- One training run per model.
- Qwen's written explanation was not evaluated on its own.
- This is a research prototype, not a production system.

## Repository map

- `src/data_pipeline/` — seed crawler, message generation, judge model, record
  schema, split by source article
- `src/model_adaptation/` — the training and evaluation code that produced the
  results above
- `src/modeling/` — training, inference and evaluation interfaces
- `src/runtime/` — the `vnphish` command, the local web demo, the model backend
  and the decision rules
- `tests/` — unit and architecture tests
- `scripts/`, `notebooks/` — run launchers, Colab training notebooks, the demo
  notebook
- `data/` — small evidence files from the final runs (metrics, manifests); no
  dataset or model weights
- `docs/architecture/` — architecture notes

## Running it

Needs Python 3.13 and the exported GGUF model file, which is not included.

```bash
python -m pip install -e .[dev,runtime]
vnphish analyze --text "<message>" --channel sms
vnphish demo
```

Set `MODEL_STORAGE_ROOT`, `MODEL_ARTIFACT_ROOT` and `MODEL_REGISTRY_PATH` to the
folder that holds the model file and its registry; `START_DEMO.bat` shows the
layout it expects. The app accepts pasted text only: no images, OCR or audio.
