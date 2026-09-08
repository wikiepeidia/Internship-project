# Result and discussion
(ok  so this raise an issue, whether we did literally has 2 kind of Evaluation  one is 219 record and one "Held out message" lets say to you i dont understand wtf is 220 held out messages , this need to be clear, )
This chapter keeps four kinds of evidence apart because they answer differentquestions: howgoodthecorpusis,
how themodels scored onvalidation, whetherthehardwarecoulddothejob, andwhatthesinglefinalevaluation
showed. The separation matters: a high validation score does not prove the data is realistic, a hardware probe
says nothing about accuracy, and one final run cannot show how much the result would move on a second run. --> wtf is 4 kinds of "evidence" fix is: How good is the quality of dataset, how the model performed , whether the hardware is capabable of doing the job (wtf is Single final evaluation ) 

5.1 The Final dataset( not kidding but the whole 5.1 is the exact same as  some other chapters 3 or 4 )
either attempt to paraphrase it or SOMETHING? 
5.2 what the hardware staticstic showed

same issue but the graph , the prev graph i ask you to fix max ram is 6G or something, but this graph below showing 7.5G, inconsistent. 
also remove all kind of 00:54 UTC and date because it is displayed in graph

he conclusion is deliberately narrow. Ordinary LoRA was runnable but left almost no memory headroom and
implied a schedule that would not fit the deadline,  -->another chatgpt +drama

5.3 Validation Results on the Same 219 Messages 

oth passed their safety gates with zero invalid outputs and zero
cases of a risky message being called benign. -->remove Safety gates

Table 5.1(merge to 5.2 bar chart): Fresh development-validation results on the same 219 records. R. denotes recall. Both runs use one
seed, so the numerical differences have no variance or significance estimate --> Vadilation result between 2 models Qwen phobert, R stand for recall. Both use the same set 

I highly recomend merging table 5.1 to Figure 5.2 so we have a beautiful 5 stats Bar chart. 


once,sothesenumbers
justify accepting the selected checkpoints under the stated gates and nothing more.  --> Both model is run and evaluated only once. 

Timing and throughput
were left out of the comparison on purpose, because the two models produce output in different ways and their
execution paths are confounded by hardware. A qualitative queue of 52 full validation messages was also kept, 26 per model, and read by a Vietnamese
fluent reviewer with the model-run and validation-row identifiers fixed in advance. Of those, 46 were judged
supported, four unsupported, one raised a concern about the gold label, and one was ambiguous. This review
was qualitative only. Its publication path was checked to be byte-stable and it changed no label, prediction,
checkpoint choice, or metric.--> REMOVE ALL 

5.4 220 "held out"(need something equiv)

re-render the image Figure 5.3, remove ANY thing related to Termiunal cohort, terminal confusion ????

and jargons 
5.5 
t does not
claim that deployment fitting over all available data was finished. P-->fix this message development fittig wtf is this mean

5.6 NO FUCK ONEDRIVE NOO 

5.7: 

Bounded human corroboration. The 100-row stratified sample and the 324-candidate targeted triage
are real manual work, but neither is full-corpus annotation.  --> CRAZY jargons again. Fix and cross check

Judge-family overlap. The 296 reconstructed Zalo rows share a model family with the final judge, so
their verdicts are not independent of the generator family wtf is jUdje family i dont udnerstand this 

One seed and one terminal pass. Each model was run once with seed 42. There is no seed or epoch
sweep, no variance estimate, no significance test, and no basis for claiming a stable winner. PhoBERT’s
higher terminal numbers describe this cohort only-->Another goofy jargons


. Evaluation-file access disclosure. The models ran once, but automated integrity tests read the evaluation
file both before and after that run, as described above. This report therefore makes no absolute isolation
or zero-access claim.-->KICK it out

erminal policy. The terminal result was not used to retrain, repair, reselect a checkpoint, move a thresh
old, or trigger a contingency. Deployment fitting is still deferred, so there is no claim of a final all-data
fit. -->Change all to : the model was run Only once , was not rerun etc

 Artifact scope. The Qwen GGUF was built and shown to load, but PhoBERT was never converted to
GGUF and no comparative deployment latency was measured. -->Phobert was not converted to GGUF due to.... add in

. Open architecture review debt. The reorganised codebase still carries six critical and three warning
findings, covering filesystem andnativeguardcompleteness, command-routediscovery, loopbackrequest
security, terminal escaping, and test-runner controls. They do not change any frozen metric, but they do
rule out a production-readiness claim.
9. Operational generalization. Version 1 is text-only and Vietnamese-focused. How it holds up against
screenshots, voice calls, deliberately reworded scams, and real user traffic is untested. A dedicated human
review of explanation quality is also still to come  -->Change to only 1: Only text only (NO version1 GSD shit) no OCR, Voice support 


Within those limits, the project does show a complete chain of evidence: seed-governed data construction,
resource probes on the target laptop, two fully trained local models, training graphs derived mechanically from
the run logs, a verified Qwen GGUF export, one terminal evaluation on a shared cohort, and an explicit record
of the failures and corrections along the way.-->Despite the limit, the thesis show that the [something easier than "seed governed"] Dataset construction , run on the Laptop with 2 trained models, with proper logs, graphs, GGUF for Qwen 

