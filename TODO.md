[CRITICAL]: The thesis identifies Qwen3.5-4B as selected and fine-tuned, but the registry and final recovery run use Qwen3-4B-Instruct-2507. Consequently, the baseline comparison is between different base models, so the claimed +0.307 improvement cannot be attributed solely to fine-tuning.

[CRITICAL]: The reported QLoRA configuration is unsupported. The final run records full-precision LoRA, 2,333 training rows, 254 validation rows, one epoch, checkpoint 584, loss 0.5004, and 551 seconds. [Chapter 3 (line 54)](C:/Users/wikiepeidia/OneDrive - caugiay.edu.vn/bài tập/usth/GEN14/INTERNSHIP/Internship-project/documents/reports/latex/chapters/03_methodology_and_system_design.tex:54) instead reports NF4 QLoRA, 2,018/210 rows, three epochs, checkpoint 505, loss 0.4951, and 1,733 seconds.

[CRITICAL]: The final recovery adapter was never converted to GGUF. The registered gguf-laptop artifact predates recovery, while the reported 0.9553 result comes from Colab adapter inference. The report therefore combines final-model accuracy with latency and deployment evidence from an older model artifact.

[CRITICAL]: The 254 examples are val.jsonl, used during training and repeated recall-recovery decisions, not an untouched holdout. The actual test split contains 413 examples. Rename this result as validation performance or evaluate the 413-row test split once.

[CRITICAL]: The “seed-disjoint” claim is false for the current splits. Seed seed_1a4f7d4d7c53 appears in train, validation, and test, including 608 training and 75 validation rows. This creates a serious leakage challenge to the reported metrics.

[CRITICAL]: Dataset counts do not match the final pipeline. Current splits are 2,333 train, 254 validation, and 413 test, totaling 3,000; the report gives 2,018 train, 210 validation, 254 holdout, and 518 filtered.

[CRITICAL]: The quality review is misstated as manual review of 100 examples with 99 passes. [`quality-stats.json`](C:/Users/wikiepeidia/OneDrive - caugiay.edu.vn/bài tập/usth/GEN14/INTERNSHIP/Internship-project/data/processed/quality-stats.json) records 49/50, and the implementation is explicitly an LLM-as-judge. The reported \(t\)-statistics also appear calculated using the unsupported \(n=100\).

[CRITICAL]: Pydantic is overstated as a semantic quality judge. It constrains field types, label vocabularies, lengths, and score ranges; the external LLM assigns realism and correctness scores. Clearly separate “Pydantic schema validation” from “LLM-based semantic review.”

[CRITICAL]: The claimed explanation review covers 156 risky predictions from the older 210-row blocked run, not the final 254-row recovery evaluation. Thus “5/5 conditions met” and model-artifact currency are not demonstrated for one consistent run.

[CRITICAL]: The evaluation threshold evidence conflicts: the snapshot stores a 0.90 floor while passing task-scam recall 0.871; the graph shows one 0.80 line, although intended floors are 0.90/0.90/0.80 by class. State all per-class thresholds explicitly.

[CRITICAL]: The methodology omits the key bridge from synthetic records to model learning: instruction/response construction, tokenization, loss masking, label decoding, and conversion from multi-label runtime outputs to the single-label confusion matrix. This is the abrupt data-to-model transition most likely to attract jury questions.

[CRITICAL]: Appendix traceability is not reproducible from the public repository: final splits, final evaluation snapshot, baseline predictions, and model registry are ignored or off-repository, while the source column merely says “Evaluation results.”

[CRITICAL]: The system-overview graph does not map the final experiment. It shows QLoRA-to-GGUF-to-runtime as one path, although the final run was full-precision LoRA and has no corresponding GGUF. It also omits synthetic generation and the distinct Pydantic/LLM-judge gates.

[MINOR]: Replace internal engineering phrases such as “Operator Surface,” “artifact currency,” and “5/5 conditions met” with ordinary bachelor-thesis language.

[MINOR]: The title includes broad “financial fraud,” while the evaluated task is text-based phishing/scam classification. Narrow the title or explain the broader fraud boundary.

[MINOR]: The exact national statistics use weakly traceable references, particularly an NCA homepage. The “no public benchmark exists” novelty claim also needs a documented search boundary.

[MINOR]: NIST Privacy Framework citations do not support implementation facts such as backend dispatch or the text-only boundary. Cite them only for privacy principles.

[MINOR]: The abbreviation list omits recurring terms including CLI, RAM, URL, VND, LIME, SHAP, and IA3. Five bibliography entries are uncited, and BibTeX reports one unsupported @software type warning.

[MINOR]: [Chapter 5 (line 12)](C:/Users/wikiepeidia/OneDrive - caugiay.edu.vn/bài tập/usth/GEN14/INTERNSHIP/Internship-project/documents/reports/latex/chapters/05_evaluation_and_discussion.tex:12) contains an incomplete sentence beginning “To measure the effect...”.

[CLEAN]: The “API wrapper” test passes at the framing level. The abstract, objectives, and main chapters foreground dataset engineering, local adaptation, structured constraints, evaluation, and privacy rather than presenting a web application as the contribution.

[CLEAN]: The rendered thesis contains no GSD terminology or obvious AI meta-commentary. Its general tone is appropriate for a bachelor thesis.

[CLEAN]: The runtime contract diagram accurately represents the implemented CLI → service → backend → structured-result flow, and the confusion matrix exactly matches the saved 254-row prediction snapshot.

[CLEAN]: The PDF is mechanically sound: 33 pages, no undefined citations or references, and no compilation errors. The audit was read-only; the worktree remains unchanged.
What needs to happen (your call on scope):

Model name: Revert to qwen3-4b-instruct-2507 everywhere (that's what was actually trained/evaluated)
Quality n: Revert to n=50, 49 passed. Recalculate t-test with n=50
Split numbers: Update to 2,333/254/413 or explain which split version the numbers refer to
GGUF export: Need to run the GGUF conversion on Colab for the final adapter, OR acknowledge in report that the eval was done via adapter inference
Seed overlap + val-as-holdout: These are the hardest — fundamental design issues
Which of these do you want to tackle? Some are quick text fixes, others need Colab runs.
