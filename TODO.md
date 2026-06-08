Update Todos

Review slide 5 (Data Pipeline) — TikZ flow layout, JSONL snippet, bottom columns spacing

Review slide 7 (Model Adaptation) — 2-column block layout, text fit, no overflow

Review thesis Ch. 3 — tinnhiemmang.vn paragraph, QLoRA table placement and formatting

Report any visual bugs so they can be fixed
Review checklist written. Check in this order:

Slide 5 — TikZ 4-step flow visible and non-overlapping; JSONL snippet left, split stats right; no overflow
Slide 7 — 2-column blocks fit cleanly; r=16 α=32 NF4 in left block; GGUF/13s in right block
Thesis Ch. 3 p.7 — tinnhiemmang.vn in first data sentence; QLoRA table appears after the training paragraph
Report back with any visual bugs
code written

bugs
thesis:
Require making this map bigger (like slide so the arrows be better)

```text
) Offline Preparation
(2) Runtime Analysis
Data
Collection
Quality
Review
Versioned
Splits
QLoRA
Training
GGUF
Export
model artifacts
Text Input
(local)
Runtime
Interface
Local Model
Backend
Decision
Layer
RiskꞏLabels
CuesꞏGuidanc 
```

Privacy is treated as a first-class design requirement. By default, raw message text does not leave the local
device. The version 1 boundary is strictly text-only; OCR, image, audio, and mobile input channels are explicitly

out of scope [? ] the ? means something not right with Bibilographies

slide
map is overlapped (expecially the texts on the arrow)

```text

tinnhiemmang.vn
Seeds
claude-3-5-haiku
Generation
Pydantic Judge
Quality Gate
JSONL Output
3,000 rows
seed reco
```

this map could be extended in terms of length to make it better seeing in projector

```text
(A) Cloud API path (B) Local inference path
User
Message
Cloud API
(3rd-party)
Data stored
on remote servers
raw upload
logs 30+ days
User
Message
Local GGUF
(on-device)
Grounded
Output
```

revamp slide Model Adaptation — QLoRA on Qwen 4B

Apply the following structural, aesthetic, and textual updates to the slide code:

1. ARCHITECTURAL LAYOUT & SPACING:

- Use a strict, top-aligned two-column layout using `\begin{columns}[t]` and `\begin{column}{0.48\textwidth}`.
- Place the "QLoRA Configuration" and "Training Results" blocks in the left column.
- Place the "Why QLoRA?" and "CPU Deployment" blocks in the right column.
- Ensure all blocks use standard Beamer `block` environments cleanly.

1. DATA ALIGNMENT (LEFT COLUMN):

- Do not use raw spaces or tabs for data alignment inside the blocks.
- Wrap the configuration and results data inside a clean, borderless `tabular` environment: `\begin{tabular}{ll}` or `\begin{tabular}{p{2.2cm}l}`.
- Use `\renewcommand{\arraystretch}{1.1}` inside the tables to give the metrics subtle breathing room.

1. TEXTUAL REFINEMENTS & TONE CORRECTIONS:

- In "Why QLoRA?", change "fits Colab or consumer GPU" to: "— fits target laptop hardware (RTX 5050)"
- In "QLoRA Configuration", change "4-bit NF4 + double quant" to professional terminology: "4-bit NF4 + Nested Quantization"
- In "CPU Deployment", change the first bullet to: "Exported to GGUF Q8_0 — offline inference without GPU"

1. MATHEMATICAL ANCHORING:

- To anchor the technical depth, inject the Low-Rank forward pass equation cleanly centered between the two blocks in the left column, or positioned beautifully inside the QLoRA Configuration block using:
  $$h = W_0 x + \frac{\alpha}{r} B A x$$
(can add the eqn to report)
