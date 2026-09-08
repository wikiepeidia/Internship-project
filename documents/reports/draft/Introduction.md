# introduction

...This
project-->change to This thesis or whatever sync with the rest, studies a local-first pipeline that fine-tunes a local LLM to detect those threats without sending the raw
content to a cloud service

1.1 Background

...Both halves are needed.-->Both Halves???  Private deployment alone
would not properly recognise Vietnamese-specific scams, and domain adaptation (dont understand this) alone would not protect the user’s data

fix that sentence only

Three constraints hold throughout (UHH change to something like Three Requirements ...): the pipeline is text-only, inference is offline or local by default, and detection
favours recall on the high-harm classes (the 3rd one strange, change to like: "the system must prioritize identifying high-risk content"). These narrow the scope compared with a full multimodal fraud assistant(multimodal?), but they keep the system realistic for consumer hardware and suited to private message analysis. They
also address a practical safety question: how to cut dangerous false negatives without relying on black-box
predictions.

1.2 problem
.....grounded guidance instead of
a vague alert (or something like cheap ML classification)..

....
The
output is one primary label (JSON? state it out full format ) from four mutually  exclusive (REMOVE this mutally thing)  classes — bank impersonation, Zalo social engineering, task scam, and benign — along with a derived(remmove this word) risk tier and the evidence spans supporting that label.

The explanation and recommendation outputs described further on are extra
structured fields produced alongside the classification, not a replacement for it (dont understand this thing too hard)

1.3 RQ

How well do the locally trained Qwen QLoRA and PhoBERT models classify the four Vietnamese
threat types, when both are given the same final test evaluation?

 Is parameter-efficient adaptation and local inference feasible on consumer laptop hardware, and
what resource trade-off motivates QLoRA over ordinary LoRA on an 8 GiB Video memory laptop GPU?

Can the detection pipeline return structured, evidence-grounded explanations — risk tier, threat
labels, suspicious cues drawn from the message text, and safe next-step recommendations — rather than
opaque confidence scores alone/cheap ML classification?

(also i wanna add something relating to Qlora and Phobert like i forgot to tell you: Whether a popular model versus a normal "Phobert" which is not even in Tensorflow or whatever has better Compatibility or something, else juror gotta say why u just not use ONE?Fix it in other chapter if you could  )

1.4 project contrinubtion
The work delivers more than a model checkpoint. It builds a 2,097-message dataset in which the training,
validation, and final-test groups are separated by which original article each message came from, rather than
message by message.  --> Hillariousass chatgpt-like sentence, change to something: The work delivers not only the finetuned model, but also built a 2097 dataset thingy.

It documents and repairs a systematic failure in the synthetic data: 240 retained Zalo
messages had been written as narration instead of direct messages, and rebuilding them offline kept the 60
original scenarios and wrote five versions of each, with no external API calls and no pretending the results
came from more sources than they did.  ---> During my triage, i found not only zalo but also TONS of message is generic , check triage again, even things like "fake-bank.com" things, also fix this sentence to be more natural

It trains Qwen QLoRA and PhoBERT locally on exactly the same
messages, keeps the raw training and validation evidence -->"evidence"-->LOG or seomthing easier to understand.
and verifies a Q8_0 GGUF export of the selected
Qwen checkpoint --> And exported a Q8 GGUF on Qwen model .
It records one final test-->Evaluation of both models on the same 220 messages, counting how many outputs
came back unreadable and how many dangerous messages were wrongly called safe

Finally, it separates the
maintained runtime, data, integrity, modelling, and evidence domains from the historical experiment machinery,
so the implementation can be explained and audited without crediting rewritten source with metrics it never
produced -->USELESSASS sentence or fix it.

1.5 scope
The
collection path targets retained alert pages from <https://tinnhiemmang.vn;> it does not ingest private user
conversations --> the dataset collection is came from Tinnhiemmang.vn , which does not ingest private conversation. (and also i remember at one point i had found a dataset in which the owner even stated that it is data leak made us choose tinnhiemmang as the main source , else juror gotta ask have you found datas? Check it)

The comparison uses one shared set of 220 messages
taken from the final dataset, and that set cannot be reused to fix data, retrain, change thresholds, or pick a
different checkpoint -->UHHHH is this message redundant like Train val test isnt it properly devided lmao, check.

Automated tests read the dataset files before the final test was run, so this report does not
describe that set as untouched; those reads displayed no row content to a human, invoked neither model, and
did not affect the final test result -->Lmao wtf is this sentence

1.6 methodology
The project runs in five connected stages. First,(Uhm i  thought the 1st is something crawling seeds...and also where we perform Labeling though ) retained Vietnamese cybercrime-alert roots are expanded into a
labelled dataset and then checked for correct structure and correctly highlighted spans, scored by a model judge,
reviewed by hand where it mattered, kept grouped by the article each message came from, and finally checked
for messages that were too close in meaning.

240 Zalo messages that had been written as narration; they were rebuilt offline from 60 preserved scenarios,
five versions each (60 preserved? wtf is 5 version, KICK if off, just said Revuilt offline)

...non-quantized sequence classifier on the same train and validation
identities (change to set or sth easier )

once independently, to confirm it really works; meanwhile the text-only runtime keeps returning its results in the
same fixed format -->UHH what wtf is this "meanwhile" should weridass,

 Fifth, both finished models are tested exactly once on the same 220 messages -->evaluated

The code was
reorganised afterwards to make it easier to read and to keep the old experiment code separate from the code that
is still maintained. That reorganisation produced none of the results and changed none of them, and there is still
security work left to do.  -->DELETE IMMEDEIETeLY

This chapter reviews existing work across seven areas that shape the system design:
Vietnamese phishing patterns, LLM-based threat detection, local inference for privacy, parameter-efficient finetuning, generative classification with decoder-only models, synthetic data generation, and explainable AI for

cybersecurity. The chapter closes with the research gap that motivates this project. -->Sound kinda weird when you say this in the Methdologu

1.7 vn phising issue
. These documented examples motivate the threat classes used in
this project without requiring a broader national prevalence claim --> requiring a bigger notice (or something EASIER this word i dont understand)

Diacritics carry meaning (e.g., ma vs mã vs mà),
and informal messages often drop or misplace them , add: in SMS they ususally dont bother to exist-i know it is did, but a lot of time it didnt (maybe add a cite here )

learning improves downstream (delete this word) social-media classification accuracy

 but their feature set was limited to bag-of-words
and n-grams (WTF is N-grams remove it and say something like dataset of smth even bags-of-words is very hgih end word)

Downstream words: too pain for me

This is a bounded literature finding rather than proof that no such dataset exists, so
two further checks were made to test that boundary directly rather than leave it as an assumption. -->UHH this looks clearly like chagtpt, change like The findings although didnt show that no such dataset exist, the quality are not quite viable for the project.

First, the seed source itself was quantified rather than assumed to be small (Uhm why the above was talking about the data issue, the below instancely say First the seed... also quantified nahh pain)

tinnhiemmang.vn’s live scamwarning listing was paginated to its terminal page and contains 74 advisory articles in total; this project’s retained
seed snapshot already traces to 67 of them. There is no large untapped reserve of real cases at this specific
source — synthetic expansion was necessary to reach a training-scale corpus from it, not a shortcut taken for
conveni--> tin nhiem mang live scam only has around 74 artical total, only 67 of them are used in this project, and there are no "real case" rather than just adversorial case like.... (check this)

Second, one recent candidate dataset was evaluated directly rather than cited on trus-->was evean evaluated directly by the owner of it.

found that 25.3% of the test set’s positive (phishing) rows are verbatim duplicates
of rows already present in the training set, which would inflate any classifier’s reported test performance on the
split as published.The dataset’s documentation was also revised four times within three days of upload without
the underlying data files changing  -->have a check on this because i remember at one point the owner even has a Git commit saying something about this, require proper cite (down to git commit)

Because of the confirmed train/test leakage, this dataset was not adopted
into this project’s corpus or evaluation; a usable subset would require independent re-labeling, re-splitting, and
its own authenticity review before any future use, not just a license check --> clearly chatgpt DNA here, change to Because of confirmed leakage, the dataset must be pre-processed , and re-labelling once again, hence we should go all the way from beginning (idk what to express here to say that why spend time fixing the broken dataset where we just spam from scratch)

1.8 LLM-based Phishing and Fraud Detection

with novel phishing patterns -->the fuck is Novel phising patterns , change to strange or sth (OH and also watch out informal words)

an approach close to the thesis

privacy-preserving alternatives to cloud APIs,-->provacy alternative

 system with an adversarial training loop that improves -->wtf is Adversarial training loop?

scam-detection system that keeps conversation content under federated rather than centralized processing -->FEDERATED, CENTRALIZED processing??? TOO pain word

but the shared privacy motivation is a direct precedent for treating
on-device or non-centralized processing as a requirement rather than an optimization-->their motivation is what smillar to training on device ...(this sentence is painful )

1.9
Suspicious financial messages contain names, phone numbers, OTP codes, and account details.  --> i remember adding scam message or any those link would immedietely trigger the AI filter safety, where to add  (maybe in other chaps or sth) it would be the best defense for "Privacy+Filter "

pruning -->PAIN , OUT.

1,10
QLoRA is selected
for this project’s adaptation because it combines the classification accuracy of LoRA with the memory savings
needed to fine-tune on consumer GPU hardware. -->I think we need a Qlora Literature here.

1.11 Generative Classification with Decoder-Only Models(this chapter basically make my brain stopped working  )
and the literature
offers two established routes -->no one said this clearly chatgpt,-->and the state or sthm offer 2 routes
(really this chapter is SO painful to read and understnad the whole whether is this neccessary or need a full rewrite)

1.12
For this, wonder if you could find a article said: Cheap generation, Expensive judge LLM better than Expensive LLM generate, Expensive LLM/Cheap to Judje data that would be good.
t few-shot generation with real examples outperforms zero-shot approaches for
classification tasks — consistent with the seed-based generation design used here -->the fuck was fewshot, zeroshot

the manifest-bound human sample, lineage governance, and explicit provenance fields (any other "goverance",Provenance TOO high wwords)-->the human manual verifcation

1.13

Explainability is treated as a core design requirement rather than a post-hoc addition -->heck is this sentence mean "post -hoc"
not to opaque confidence
scores -->generate vague confidence scroe ()
Sharma et al. [38] provided a taxonomy of (TAXONOMY???)
1.14:
dresses part of the problem space-->problems

1.15 Research Gap -->WHAT THE FUCK is this section even mean.
