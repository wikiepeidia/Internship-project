# Spoken Script — matches `slides/main.tex` (Sept 28 build, slides I–XVII)

Read this out loud a few times, then stop reading it and just talk from memory
using the slide as your only prompt. If your own words drift from this, that's
fine and expected — the script is a starting point, not a thing to recite.

Total spoken time below is about **11 minutes**, not counting the live demo.
If you need to land at 10, the three easiest cuts are marked **[CUT]**.

---

**Title (0:15)**
"Good morning. My project is Design and Development of a Localized LLM for
Vietnamese Financial Phishing Detection. I'll walk through it in the order I
actually built it."

**Contents (0:15)**
"Here's the order: the problem, the pipeline, the data, training both models,
two evaluations, and the conclusion."

**I. Problem (0:50)**
"Vietnamese financial scams arrive by SMS and Zalo, and the messages people
most want checked are exactly the ones carrying bank details, phone numbers,
and OTP codes. If I send that message to a cloud API to get it checked, I'm
uploading exactly what needs protecting. So the check has to run on the
user's own device. Underneath, this is supervised classification into four
classes: bank impersonation, Zalo social engineering, task scam, and
benign."

**II. Research Questions (0:35)**
"Three questions drove every decision after this. RQ1: how well do the two
models I trained locally classify the four threat types on the same final
test. RQ2: is fine-tuning practical on a consumer laptop, and why QLoRA
instead of ordinary LoRA. RQ3: can the system explain its answer, not just
give a score. I'll answer all three at the end."

**III. Pipeline (0:45)**
"This is the whole system in one picture. The top row is offline work, done
once: collect and generate messages, check and review them, split them by
source article, train both models, package the result. The bottom row is
what happens every time a user checks a message: text goes in, a structured
answer comes out — risk, label, cues, advice. The only thing crossing
between the two is the trained model file."

**IV. Seed Crawl (0:35)**
"Everything starts with tinnhiemmang.vn, a site that publishes public scam
warnings. A crawler collected those articles. Each article becomes a seed
with its own ID. A seed describes a scam — it is not a scam message itself,
so it can't be training data as it is."

**V. Data Generation (0:45)**
"From each seed I generate several messages, one class at a time. The
prompt names the target class and the exact fields to return. Every message
is checked the moment it's produced and saved after each batch, so if a
provider rate-limits me mid-run, I resume instead of losing the batch. One
review found 240 Zalo messages written as narration instead of real chat
messages. I rebuilt those offline from 60 preserved scenarios."

**VI. How the Label Is Set (0:50)** — point at the table
"Here's one real record from the training set. This is the label field:
bank impersonation. The label is set when the message is written, not added
afterward — the prompt names the class, so every message in that batch
starts with it. Qwen writes the label as text in its answer. PhoBERT trains
on it as a class number. When either model is scored, it only ever sees the
text, never the label."

**VII. Checking the Labels (0:50)**
"Structural checks can't tell if a message is realistic or correctly
labeled, so I added two more layers. A judge model scored every message on
five dimensions; 1,395 of 2,097 passed. I reviewed 100 messages by hand and
agreed with the judge on 87 of them. I also reviewed 324 flagged labels —
233 of those I agreed needed a change, but I only applied 57, because the
other 176 all traced back to one source article."

**VIII. Splitting the Data (0:35)**
"Messages from the same article look alike, so I split by article, never by
message. An article and all its messages go into exactly one split — no
article appears in two. The largest one holds under 8 percent of the data.
That gives 1,658 training, 219 validation, 220 final-test messages."

**IX. Model and Training Choosing (0:50)**
"I picked the base model by measuring, not by reputation. Three Qwen models
were tried on the same 33 messages, and Qwen3-4B-Instruct fit the laptop
best. Then I measured ordinary LoRA against QLoRA on the actual 8-gigabyte
card. LoRA didn't crash, but it left only 9 megabytes free and would have
needed about 18 hours. QLoRA fit comfortably, so that's what I trained
with."

**X. Training Qwen (0:40)**
"Qwen trained with QLoRA for 3 epochs, 1,245 steps, the same seed as
PhoBERT. Loss falls fast, then flattens. I checked validation every 50
steps, and the best checkpoint was step 200. The whole run took 14.87
hours, mostly because Qwen writes a full answer for every validation
message at each check." **[CUT the "mostly because..." clause if short on time]**

**XI. Training PhoBERT (0:35)**
"PhoBERT is a different design: every weight is trained, plus a four-way
classification head — not LoRA, not QLoRA. Same 3 epochs, 312 steps, same
seed. Best checkpoint was step 100."

**XII. Eval 1: Best Checkpoint (0:40)**
"Both models were checked on the same 219 validation messages to pick their
checkpoints. Qwen: step 200, macro F1 0.9885. PhoBERT: step 100, macro F1
0.9849. The rule was: first enough recall on the risky classes and no
unreadable answers, then the best macro F1."

**XIII. Eval 2: Final Test (0:40)**
"Then, once, I ran both finished models on 220 messages neither model had
ever seen. PhoBERT scored 0.991, Qwen scored 0.980 macro F1. That's one run
each, so I'm calling this a comparison, not a ranking."

**XIV. Where It Went Wrong (0:35)**
"On those same 220 messages, Qwen made 4 mistakes, PhoBERT made 2. And this
is the number that matters most: each model called exactly one dangerous
message safe. On the metric that actually matters for a phishing tool, they
tied."

**XV. Conclusion (0:45)**
"Back to the three questions. RQ1: PhoBERT scored a bit higher, but with one
run each I won't claim more than this specific comparison. RQ2: yes — QLoRA
trained on the 8-gigabyte laptop where ordinary LoRA left almost nothing
free, and the exported model runs without a discrete GPU. RQ3: yes — every
answer came back in the structured format, risk tier, label, quoted
phrases, advice, and none of them were unreadable."

**XVI. Limitations (0:40)**
"I'd rather say these myself. The messages are generated, not collected
from real victims. Everything ran once, with one seed. The judge isn't
independent for the rebuilt Zalo class. Genuine messages that ask someone
to log in get over-flagged. My manual check covered a sample, not the whole
set. And a code review left six critical findings open — this is a
prototype, not something ready for real use." **[CUT to 3 bullets if short on time — keep "generated", "one seed", "six critical findings"]**

**XVII. Future Work (0:30)**
"Three things I'd do next: review the whole dataset by hand, not a sample;
use both models together — PhoBERT for the label, Qwen for the explanation;
and add OCR, so someone can point this at a screenshot instead of copying
text out of a suspicious message."

**Demo (0:15 lead-in, then live)**
"Let me show this running locally." — switch to the browser demo, paste one
message, wait for the answer (about 30 seconds on CPU). Narrate the wait:
"It's running fully offline on this laptop, no network call."

**Thank You (0:10)**
"Thank you. I'm happy to take questions."

---

## If a check goes wrong live

- **Demo won't start / shows an error:** say "let me start the local demo" and
  double-click `START_DEMO.bat` at the project root — don't try to debug it
  live. If it still fails, fall back to slide XIII's screenshot and say the
  live copy is unavailable right now, the recorded results stand.
- **Someone asks you to run `doctor` or `analyze` in a terminal:** both work
  now (fixed Sept 28). `doctor` will still print NOT READY — that's correct,
  it's reporting release-shippability, not analysis readiness. Say so plainly
  if asked; see `STUDY_GUIDE_7_DAYS.md`, Day 0.
