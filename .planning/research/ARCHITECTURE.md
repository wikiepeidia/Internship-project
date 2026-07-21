# Qwen vs. PhoBERT Comparison Research

> Note: this file replaces a prior milestone's demo-verification architecture note (v5.1), which is no longer relevant to the active v6.0 report-revision milestone. That content is preserved in git history if needed again.

**Purpose:** Supporting research for a new "why Qwen, not PhoBERT" subsection in the thesis Methodology chapter, addressing the defense question the student could not answer in writing (see `documents/Transcript defense.md`, line 72-74).
**Researched:** 2026-07-21
**Confidence:** MEDIUM-HIGH (claims below are cross-checked against multiple web sources including arXiv papers, the official PhoBERT repo/paper, and the Qwen3 technical report; no paywalled/curated docs source was used, so tier is capped at MEDIUM-HIGH rather than HIGH)

## PhoBERT Capabilities & Typical Use

PhoBERT (VinAI Research, EMNLP 2020 Findings) is the first large-scale monolingual Vietnamese language model, built on the **RoBERTa architecture** — i.e. it is a pure **Transformer encoder**, pretrained with masked-language-modeling on ~20GB of Vietnamese text. It ships in `base` and `large` sizes. Architecturally, PhoBERT has **no decoder and was never trained with a generative (autoregressive, next-token) objective**. It outputs contextual embeddings, not text.

Consequences of this for actual use:

- **Primary use pattern:** attach a small task-specific head on top of the pooled/`[CLS]` (or token-level) representation and fine-tune the whole stack. PhoBERT's own paper reports state-of-the-art results this way on POS tagging, dependency parsing, NER, and NLI. The standard downstream recipe in the wild (per the official VinAI repo and multiple community fine-tuning guides, e.g. the `phobert-text-classification` reference implementation) is: PhoBERT encoder -> dropout -> linear/softmax classification head -> single-label or multi-label output.
- **It is overwhelmingly used for single-label or token-level classification tasks**, not free-form generation: sentiment analysis (PhoBERT reaches ~94% accuracy / 83 F1 on UIT-VSFC sentiment; ~78 accuracy/F1 on ViNLI), hate-speech detection (PhoBERT-CNN hybrid ~67 macro-F1 on ViHSD), emotion classification (~65 macro-F1 on VSMEC), NER, and dependency parsing.
- Task-specific literature does extend PhoBERT past plain classification with **additional bolted-on components** — e.g. an LSTM/CNN-LSTM head instead of a plain linear layer, or a graph-attention layer for token-level tasks — but these are still discriminative heads (predicting a label per token/sequence), never generation.
- **PhoBERT cannot natively write free text.** It has no generation capability at all — no answer text, no explanation, no recommendation sentence. When the Vietnamese NLP community needs sequence-to-sequence generation (summarization, translation, free-text answers), they use a *different* model family entirely, **BARTpho** (also VinAI, encoder-decoder), not PhoBERT. This is a direct architectural admission from the same research group that PhoBERT and generation are separate problems requiring separate models.

**Bottom line on capability:** PhoBERT is a best-in-class Vietnamese *representation* model for classification and sequence-labeling. It is not, and was never designed to be, a generator of explanatory or evidentiary text.

## Task-Shape Comparison (structured multi-field output)

The thesis task is not plain single-label classification. Per `.planning/PROJECT.md`, each inference call must jointly produce, from one input message:
1. a risk tier (ordinal),
2. one-or-two labels from a 4-class threat taxonomy,
3. grounded evidence — exact quoted substrings copied from the input (extractive span grounding), and
4. a safe-action recommendation (free-form generated guidance text).

This is simultaneously a **classification problem**, an **extractive span-identification problem**, and a **conditional text-generation problem**, all conditioned on the same input and expected to be mutually consistent (the evidence must actually support the label; the recommendation must match the risk tier).

**Why an encoder-only model cannot do this in one architecture:**
- A classification head over PhoBERT can produce (1) and (2) — that part is well-precedented and PhoBERT would likely do it competently, possibly even more parameter-efficiently than a 4B decoder for the label alone.
- (3), extractive evidence-span grounding, is a *different* task type (token-span extraction, akin to extractive QA/SQuAD-style start/end-span prediction) and requires its own head and its own span-level training signal on top of the same encoder, or an entirely separate span-extraction model.
- (4), the recommendation text, requires generation, which PhoBERT's encoder-only architecture cannot produce at all — it would require bolting on a decoder (e.g., pairing PhoBERT-derived features with BARTpho, or a template-filling system) as a genuinely separate model.
- The rationalization/explainability literature confirms this is a known, still-unsolved architectural seam: work on "joint text classification and rationale extraction" (e.g. Unifying Model Explainability and Robustness for Joint Text Classification and Rationale Extraction, arXiv 2112.10424) and hybrid extractive+abstractive rationale systems like **RExC** explicitly combine an *extractive* encoder component with a *separate BART-based generator* to produce both a span rationale and free text — i.e., even the academic literature's answer to "classification + grounded evidence + generated explanation" is "use two coupled models," not "extend one encoder."
- Generative Information Extraction research frames this exact shift explicitly: tasks traditionally done as separate classification/span-extraction/pipeline stages are increasingly reformulated as a single conditional-generation problem with one autoregressive model, because constrained/structured decoding (schema-constrained JSON generation) can guarantee syntactic validity and unify what used to be 2-3 separate models into one forward pass.
- Countervailing honest point: single-pass generative structured output is not free of tradeoffs. Literature on generative pipelines (e.g. structured event/relation extraction) notes that models which correctly classify can still fail to *assemble* fully correct structured objects, because span-to-label linking is implicit in autoregressive decoding rather than explicit as in a dedicated span-extraction head — this is a real, documented weakness of the "one generator does everything" approach and should be named as a limitation, not hidden.

**Architectural complexity comparison, stated plainly:**
- **PhoBERT-based route for the full task:** encoder + classification head (labels/tier) + a separate span-extraction head or model (evidence) + a separate generation model (recommendation text), likely requiring 2-3 coupled models/heads trained and calibrated somewhat independently, with consistency between the three outputs not architecturally guaranteed.
- **Qwen (decoder-only, QLoRA-tuned) route:** one model, one forward pass, one JSON schema, trained end-to-end so label, evidence quoting, and recommendation are conditioned on each other and on the same hidden state — consistency between fields is learned jointly rather than reconciled post hoc across separate models.

This is the honest core of the "why QLoRA on a generative LLM" argument, and it is the same argument that should anchor the separate "why QLoRA instead of encoder+head" gap already flagged in PROJECT.md — the two revision items are really one architectural argument told twice.

## Multilingual Extension Argument

This is the argument the student gave live but never wrote down. It holds up, with appropriate hedging:

- **Qwen3 is trained on ~36 trillion tokens across 119 languages and dialects** (Qwen3 technical report / QwenLM GitHub), including English and Vietnamese in the same shared parameter space and shared tokenizer/vocabulary. Qwen2.5, the prior generation, explicitly lists Vietnamese among its 29+ supported languages.
- **PhoBERT is monolingual by construction** — its 20GB pretraining corpus, tokenizer, and word-segmentation preprocessing (it requires Vietnamese word-segmented input, via VnCoreNLP/RDRSegmenter) are Vietnamese-specific. It has no learned representations for English tokens/subwords beyond incidental overlap, and no code-switched (Vietnamese-English mixed) training signal comparable to a model natively pretrained on both languages jointly.
- General cross-lingual transfer literature on multilingual encoders (mBERT, XLM-R) supports the underlying mechanism the student invoked: multilingual pretraining creates a shared representation space that enables transferring a task learned in one language to another with little or no additional labeled data in the new language — this is precisely the "future extension to English-language scam text" scenario the student described.
- Important honest caveat found in the same literature: multilingual models are not a free lunch — cross-lingual transfer is "not consistently better" than a strong monolingual model for the *original* language, multilingual models can underperform monolingual ones on morphologically rich languages, and off-the-shelf multilingual models are "notably inferior" to monolingual ones specifically on *generation* tasks unless the multilingual model was purpose-built for generation (this caveat mainly threatens weaker multilingual encoders like mBERT, not decoder LLMs like Qwen that were pretrained on generation from the start).
- Precedent for the extension argument specifically: to add English-language scam detection to a PhoBERT-based system, the realistic path is training or swapping in a second, separate English-specific (or multilingual) encoder + head, and maintaining two parallel classification stacks — not extending PhoBERT itself. With Qwen, the same weights and same QLoRA adapter architecture could in principle be re-tuned or extended with additional multilingual training data without a wholesale architecture change, because the base model already has English (and 118 other languages) in its pretraining distribution.

**Assessment:** this is a legitimate, well-precedented reason grounded in real architectural differences (monolingual-only pretraining vs. massively multilingual pretraining), not a post-hoc excuse. It should be written up as a secondary/supporting reason, not the primary one — the primary reason is the task-shape argument above (structured multi-field generation), because that is the argument that holds even if English extension were never pursued.

## Honest Tradeoff Summary

State plainly in the thesis — do not oversell:

| Dimension | PhoBERT (encoder + head) | Qwen3-4B (decoder, QLoRA) |
|---|---|---|
| Single-label / risk-tier classification alone | Well-precedented, likely strong accuracy, smaller/cheaper model, faster inference | Also capable, but heavier for a task this narrow |
| Grounded evidence spans (exact input substrings) | Not natively supported; needs a second span-extraction head/model | Natively producible as part of one generation, though exact-quote fidelity must still be verified post-hoc (a real, separately-flagged risk, not unique to either architecture) |
| Free-form safe-action recommendation text | Not supported at all -- PhoBERT cannot generate; would need pairing with a generative Vietnamese model like BARTpho | Native capability, same forward pass |
| Producing all of the above jointly, consistently, in one artifact | Requires 2-3 coupled models/heads with no architectural guarantee of cross-field consistency | One model, one schema, fields conditioned on each other by construction -- though field *assembly* correctness (e.g., evidence-to-label linking) is implicit in decoding and must be evaluated explicitly, a documented weakness of generative structured output generally |
| Future extension to English or mixed-language input | Requires a new/second Vietnamese-specific-architecture stack; PhoBERT's tokenizer and pretraining are Vietnamese-only | Base model already multilingual (119 languages incl. English) from pretraining; extension is a data/fine-tuning problem, not an architecture-swap problem |
| Compute/footprint for the classification-only sub-task | Smaller, cheaper, likely faster | Larger footprint for what is, in isolation, an "easy" sub-task -- a genuine cost the thesis should acknowledge, not hide |

**The honest conclusion to write in the thesis:** PhoBERT would very plausibly have been the stronger, cheaper choice **if the task were single-label Vietnamese text classification alone** — this is well-established by benchmark results (UIT-VSFC, VSMEC, ViHSD, ViNLI) and is likely what the NLP-specialist judge was picturing when asking the question. It was not chosen because the actual task requires **jointly generating a classification decision, extractive evidence grounded in the input text, and free-form safe-action guidance in a single, internally-consistent output** — a combined classification + extraction + generation task shape that PhoBERT's encoder-only architecture cannot natively produce and that the rationalization/explainable-classification literature shows typically requires stitching together multiple separate models (an extractive component plus a generative one) to approximate. A single QLoRA-tuned generative decoder unifies that into one model and one forward pass, at the acknowledged cost of being a heavier tool than strictly necessary for the classification sub-task in isolation, and at the cost of needing explicit evaluation that the generated evidence spans are actually faithful quotes from the input (a known weakness class of generative structured output). The multilingual/future-extension reasoning the student gave live is a real, secondary, well-precedented advantage of the chosen architecture (Qwen's 119-language pretraining vs. PhoBERT's Vietnamese-only pretraining and tokenizer), but should be presented as a supporting point, not the load-bearing justification — the load-bearing justification is the task-shape/architecture argument above.

## Sources

- PhoBERT: Pre-trained language models for Vietnamese, EMNLP 2020 Findings -- https://aclanthology.org/2020.findings-emnlp.92/ and https://arxiv.org/abs/2003.00744 (HIGH confidence -- peer-reviewed, primary source)
- VinAIResearch/PhoBERT official repo -- https://github.com/VinAIResearch/PhoBERT (HIGH confidence -- primary source)
- BARTpho: Pre-trained Sequence-to-Sequence Models for Vietnamese -- https://arxiv.org/pdf/2109.09701 (HIGH confidence -- same research group, shows generation requires a separate model)
- SMTCE: A Social Media Text Classification Evaluation Benchmark and BERTology Models for Vietnamese -- https://arxiv.org/pdf/2209.10482 (MEDIUM-HIGH -- reports PhoBERT benchmark numbers)
- From Universal Language Model to Downstream Task: Improving RoBERTa-Based Vietnamese Hate Speech Detection -- https://arxiv.org/pdf/2102.12162 (MEDIUM-HIGH)
- Unveiling Sentiments in Vietnamese Education Texts: Could LLM GPT-3.5-turbo Beat PhoBERT? -- https://link.springer.com/chapter/10.1007/978-981-97-0669-3_12 (MEDIUM -- direct PhoBERT-vs-LLM comparison, but note the LLM side was zero/few-shot prompted, not fine-tuned, so it is not a like-for-like comparison with a QLoRA-tuned Qwen; cite with that caveat)
- Fine-Tuned 'Small' LLMs (Still) Significantly Outperform Zero-Shot Generative AI Models in Text Classification -- https://arxiv.org/pdf/2406.08660 (MEDIUM-HIGH -- supports the honest point that fine-tuned encoders can beat zero-shot LLMs; also supports that fine-tuned generative LLMs can beat BERT-class models when actually fine-tuned)
- Qwen3 Technical Report -- https://arxiv.org/pdf/2505.09388 and https://qwenlm.github.io/blog/qwen3/ (HIGH confidence -- primary source, confirms 119-language/36T-token pretraining)
- QwenLM/Qwen3 GitHub -- https://github.com/QwenLM/Qwen3 (HIGH confidence -- primary source)
- Unifying Model Explainability and Robustness for Joint Text Classification and Rationale Extraction -- https://arxiv.org/pdf/2112.10424 (MEDIUM -- supports "classification + grounded evidence needs coupled components" claim)
- From outputs to insights: a survey of rationalization approaches for explainable text classification (incl. RExC) -- https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2024.1363531/full and https://pmc.ncbi.nlm.nih.gov/articles/PMC11300430/ (MEDIUM-HIGH -- survey source, describes extractive-encoder + BART-generator pattern)
- Generative Information Extraction overview -- https://www.emergentmind.com/topics/generative-information-extraction (LOW-MEDIUM -- secondary/aggregator source, used only for framing, not for numeric claims)
- Cross-lingual transfer / multilingual model literature (mBERT/XLM-R general findings on transfer benefits and generation-task limitations) -- https://www.emergentmind.com/topics/multilingual-bert, https://arxiv.org/pdf/2409.10965 (LOW-MEDIUM -- secondary sourcing on general multilingual-transfer claims; used only to corroborate a widely-accepted mechanism, not for a Vietnamese-specific number)

**Confidence caveat for the downstream writer:** claims tagged HIGH/MEDIUM-HIGH above are safe to cite directly. The GPT-3.5-turbo vs PhoBERT comparison and the general cross-lingual-transfer claims are MEDIUM/LOW-MEDIUM tier -- use them as directionally-correct supporting color, not as precise numeric citations, and do not present the zero-shot-GPT-vs-PhoBERT result as evidence that "LLMs are worse than PhoBERT even when fine-tuned," since that specific comparison did not fine-tune the LLM side.
