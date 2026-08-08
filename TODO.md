Overall structure is right — dependency order (data → train → report → slides → code) makes sense, and a few of these ideas (real LoRA-vs-QLoRA comparison, real trained PhoBERT, dictated-tone report rewrite) are genuinely strong. But there are real gaps that will bite you if not nailed down before we start. Going through each:

1. Fix data — good instinct, too vague to execute on.
"If bad, kill it" needs a hard rule, or you'll spend a week eyeballing rows and still not know when you're done. The ChatGPT-side audit already gave concrete numbers: one seed = 758/3,000 rows (25%), top-4 seeds = 48.2%, one seed crosses all three splits, 131 rows have invalid evidence spans. That's your actual "bad" checklist — not a fresh read of all 3,000 rows. I'd set explicit acceptance gates (e.g. "no single seed >X% of corpus," "zero invalid spans," "zero seed crossing splits") so this phase has a clear finish line instead of running indefinitely. Also: some of these are fixable without deleting (131 bad spans might just need re-extraction, not row deletion) — "kill it" shouldn't be the default for everything.

2. LoRA → QLoRA → PhoBERT, all trained with graphs — this is the single best idea in the plan.
It directly manufactures hard evidence for the two most-repeated defense questions (why QLoRA not LoRA, why Qwen not PhoBERT) instead of arguing from literature. Two things to nail down before starting:

Compute fit. LoRA (no 4-bit quantization) needs meaningfully more VRAM than QLoRA. Fine on an H100, tight-to-impossible on a free-tier T4. Which Colab tier do you actually have right now?
Be ready for PhoBERT to win on raw accuracy. It's a specialized Vietnamese encoder on a classification-only task — it might score higher F1 than Qwen. That's fine, not a loss — the report already argues "PhoBERT would be the smaller, cheaper choice for single-label output," so a real number confirming that strengthens the existing argument. Don't let a good PhoBERT score feel like a setback; it's the point.
All three must train on the fixed corpus, or the comparison is meaningless. Data-fix has to actually finish first, not run in parallel.
3. Report overhaul via dictated tone — right idea, needs a safety rule.
Good mechanism (you produce real draft text, I clean grammar without changing structure/word choice). But: a full rewrite risks the opposite problem — chapters in your real voice sitting next to chapters from the old emergency-revision voice, and a judge comparing before/after noticing the seam. Since this is a retake with real runway, full rewrite is the right call, but do it chapter-by-chapter with a consistency pass at the end, not one-shot.

1. Slide overhaul (pipeline-stage structure + \pause reveals) — solid, no real issues. Just needs to happen after retrain numbers are final, since it's presenting results that don't exist yet.

2. Code clean as cheatsheet-building — good, correctly sequenced last, right before the retake so it's fresh for Q&A.

What's missing from the plan entirely:

Test-set discipline. The untouched 413-row reserved split should get used exactly once, at the very end, across all three trained models — not touched during data-fix iteration. Worth stating explicitly so nobody peeks at it while cleaning data.
Whether the HF real-data rows (44-711, pending human review) get folded into the retrain corpus, or stay evidence-only. Your plan doesn't say. That's a real decision, not a detail.
Plan is good to build a milestone on once these are pinned down. Want me to fold these into the actual milestone requirements now, or do you want to settle the Colab-tier and real-data-inclusion questions first?
Going through the rest:

1. Unused-row framing — agreed, don't narrate housekeeping. Salvage what's salvageable, quietly drop what isn't, don't create a "look, an unused row!" flag that wasn't a problem until you announced it.

2. A100 for LoRA/QLoRA + PhoBERT — good, removes the VRAM-fit risk I flagged. And yes: "we used heavier hardware to run the comparison experiment, but the deployed system is QLoRA+GGUF on a laptop" is a clean, defensible split — training location and inference location are different claims, and the report already frames it that way.

3. "Title isn't 'using Qwen for scam detection'" — correct, and worth stating explicitly in the report once you have the numbers: if PhoBERT or plain LoRA scores higher on raw classification, that's not a loss, it's confirmation of the tradeoff the report already argues (PhoBERT/head-based = cheaper for single-label output; this system needed the other two output fields too). Frame results as "here's what we measured" either way, not as a contest you need to win.

4. The "too clean" diagnosis — this is the sharpest point in your message, and I think you're right. And I can back it with something concrete: your project already has a real failure-and-recovery story, sitting in your own history, that was deliberately scrubbed from the report by an earlier guardrail rule.

task_scam originally had only 18 seed groups — badly underrepresented — and an early evaluation measured 0.44 recall on that class, a real release-blocking failure under your own recall-first gate. You root-caused it (too few real seeds → not enough synthetic diversity in that class), generated 400 additional targeted task_scam examples, re-evaluated, and recall rose to 0.871 — a documented, adapter-checkpointed, re-verified fix. That's a genuine "hit a wall, diagnosed it, fixed it, proved the fix" arc. It's real, it's yours, it's already evidenced (checkpoint task-scam-recovery-2026-05-28, saved eval snapshot) — it just isn't in the report, because an earlier revision explicitly decided to hide it ("no mention of 0.44 recall failure... or recovery iterations anywhere in report or slides").

That decision made sense in the moment (didn't want to look like you shipped something broken) but it's very plausibly part of why the report now reads as suspiciously frictionless. Putting this back — one paragraph in Data Construction or Evaluation, framed as normal iterative development, not confession — costs zero new work and adds exactly the texture you're describing. I'd prioritize this above almost everything else on the list, because it's free.

1. The t-test — real options, not an obvious call, want your read:

Cut it, replace with plain mean/pass-rate language a student would obviously compute themselves.
Keep it, reframe origin — "supervisor suggested checking whether the score difference was statistically meaningful" — getting stats guidance from a supervisor is normal, not suspicious, and explains the sophistication without hiding the number.
Keep as-is if you're actually comfortable explaining a one-sample t-test live (it's not hard to learn in 10 minutes if you don't already know it).
Which of these matches how you'd actually want to answer if asked "walk me through this test"?

1. Full LLM-judge re-pass on the fixed corpus — yes, needed, folds into the data-fix phase naturally (can't claim quality on rows you haven't re-checked post-fix).

Good plan overall. With the recovery-story restoration added and the t-test question settled, this is ready to become real milestone requirements. Want to lock the t-test decision now, or move to drafting requirements with it as an open item?

Manual-100 check → you, results handed to me ✓
Codex → interactive CLI review, batched, structured output ✓
Timeline → 1 month data+retrain (Codex window), 1 month report/slides/code, retake ~Oct 7 ✓
Reference report → pending, doesn't block starting (only blocks the report-overhaul phase specifically)
