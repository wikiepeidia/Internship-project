# Chapter 5 — draft

> Your original notes are kept at the bottom. Two of your questions are answered there,
> and one of your sentences is **factually backwards** — read that part first.

---

## 5.1 Main findings from the dataset

*(this is my suggestion in your voice — edit anything that doesn't sound like you)*

The final dataset has 2097 messages in 4 labels: bank impersonation, Zalo social
engineering, task scam, and benign. I split them into 1658 for training, 219 for
validation, and 220 that I kept aside for the final test.

Every message was generated from an original warning article, and messages made from the
same article share an ID. When I split the data, I made sure all messages with the same ID
went into the same group. This matters because it stops the model from seeing a reworded
version during training of something it gets tested on later. No ID appears in two groups.
I also set a rule before splitting that no single article could make up more than 8% of the
dataset. The biggest one ended up at 7.9638%.

To check quality I used a second model as a judge. It scored every message on five things:
how realistic it looks, whether the label is right, whether the Vietnamese-English mixing
sounds natural, whether the risk level is right, and whether the highlighted suspicious
parts are correct. A message only passes if it scores at least 3 out of 5 on all five.
1395 of 2097 messages passed, which is 66.52%. The average scores were 4.020 for realism,
4.851 for label correctness, 4.672 for the Vietnamese-English mixing, 4.119 for risk level,
and 4.745 for the suspicious parts.

I also checked 100 messages by hand. I picked them evenly across all four labels and across
both judge results, so the sample was not just the easy ones. I passed 44 and failed 56, and
my decision matched the judge on 87 out of 100. This is a check on the judge, not a
replacement for it — 100 messages is not the whole dataset.

Separately I went through all 324 task scam messages the judge had flagged as possibly
having the wrong label. I dropped 91 and approved 233 label corrections. But only 57 of
those corrections actually went into the dataset. I threw out the other 176 because they all
came from the same original article, so they were not really independent examples. That
decision cost me real work I had already done, but keeping them would have made the dataset
look more varied than it actually was.

One limitation I have to state here. The Zalo messages were rebuilt using a model from the
same family as the judge that scored them, so for those 296 messages the judge is not a
fully independent opinion. They still passed all the automatic checks, but an automatic
check cannot turn a generated message into a real one.

---

## Answers to the questions in your notes

### "check this for me" — the PhoBERT vs Qwen sentence

**Half right, and the second half is backwards.** Do not write it as you had it.

- PhoBERT **is** better overall: accuracy 0.990909 vs 0.981818, macro F1 0.990892 vs 0.980493.
- But **"lower false positive rates" is wrong — it's the opposite.** A false positive here
  means a safe message wrongly flagged as a scam. Look at the confusion matrix figure in your
  own report:
  - **Qwen: all 66 safe messages correctly called safe. Zero false alarms.**
  - **PhoBERT: 65 of 66. One safe message wrongly flagged as Zalo social engineering.**

  So Qwen raised fewer false alarms, not more. A juror can check this in ten seconds from
  the figure that is already printed in your report.

**Also**: you wrote "Qwen GGUF Q8.0" as the thing that was tested. It wasn't. The final test
ran the **trained Qwen checkpoint** (the one from step 200). The GGUF is a separate export
you made afterwards so the model can run through llama.cpp. Two different artifacts. Keep
them apart or a juror will pull the thread.

Safe version you can defend:

> PhoBERT scored higher overall. But on false alarms Qwen was better: it never flagged a
> safe message, while PhoBERT flagged one. And both models made exactly one dangerous
> mistake — one scam message called safe. Since I only ran one seed, I cannot say one model
> is truly better than the other.

### "please recheck" — the 3000 number

Close but not exact. The real numbers: **3413 candidate rows were pooled at the start**, and
after all the cleaning **2097** remained. Along the way: 371 removed as duplicates, 94
removed by the 8% rule, 825 old Zalo rows removed and 300 rebuilt ones added, 95 rows had
their highlighted spans repaired, 2 dropped because the spans could not be fixed.

So write "3413", not "3000".

### "need to find a way to describe this without trigger Synthetics"

I'm not going to help you hide this one, and you don't want me to.

Undisclosed generated data is part of what got you the F. If a juror finds it themselves
after you avoided the word, that is fatal. If you state it plainly first, it's just a
methodology choice with a reason — and you have a genuinely good reason.

You don't need a euphemism. You need the sentence that comes *after* it:

> The messages are generated, not collected from real victims. I could not use real ones:
> Tin Nhiem Mang's terms forbid redistribution, and real scam messages contain victims'
> personal data. So I generated messages from 3413 real public warning articles, then
> checked them with a second model and by hand. That is a real limitation on how far my
> results generalise, and I state it rather than hide it.

That paragraph is *stronger* than pretending. It shows you understood the legal and privacy
constraint, which is exactly the kind of judgement a jury gives marks for. You already did
the source audit that proves you looked for real data — it's in your appendix.

---

## Vocabulary: what I'm removing from your report

You said "terminal evaluation" and "disjoint" mean nothing to you. You're right to flag it —
if you can't say it, it can't be in there. Replacements:

| Was in the report | Now says | Why |
|---|---|---|
| terminal evaluation | **the final test** | "terminal" only meant "run once, never repeated" |
| terminal cohort | **the 220 messages I kept aside** | |
| seed-disjoint / disjoint splits | **no article appears in two groups** | |
| promoted corpus | **the final dataset** | |
| cohort / partition | **group** or **set** | |
| stratified sample | **picked evenly across all four labels** | |
| corroboration | **a double-check** | |
| rubric dimensions | **the five things the judge scored** | |
| lineage governance | **the rule about messages from the same article** | |
| provenance | **where it came from** | |

A sweep is running across all seven chapters right now to catch the rest. I'll bring you the
full list.

**What I am NOT removing:** accuracy, F1, epoch, checkpoint, training/validation set,
fine-tuning, QLoRA, quantization. An ICT juror expects a bachelor student to know those, and
stripping them would make the report look dumbed down. If any of *those* are shaky, tell me
and I'll explain them until you can say them cold — that's a different fix from removing them.

---

## Your original notes (kept)

# conclusion

This thesis built and evaluated a local, text-only system for detecting Vietnamese financial phishing. What was made was a 4 labelled dataset, 2 trained models including a Qwen  GGUF Q8.0 and  a fine tuned Pho bert. Moreover the system was evaluated properly and  The results showed that the fine-tuned PhoBERT model perform better the Qwen GGUF Q8.0 model in terms of overall performance, particularly in detecting phishing attempts with higher accuracy and lower false positive rates.(check this for me). However due to the dataset being relatively small, plus being generated (need to find a way to describe this without trigger Synthetics), the result may not be fully representative of real-world scenarios in Vietnamese scam traffic detection

## 5.1 Main Findings

- the final dataset after cleaning out of 3000 (please recheck), consist of 2097 messages, 1658 for train, 219 Validation, and 220 evaluation. Though the dataset is still model assisted, the data preprocessing (or whatever stuff ) including human review .

---

## One structural note

What you wrote under "# conclusion" is Chapter **6** material, not Chapter 5. Chapter 5 is
where the numbers and evidence live; Chapter 6 is the short "what I built, what it showed,
what's next" wrap-up. Your paragraph is a good Chapter 6 opening — I'll move it there when
you're happy with it.
