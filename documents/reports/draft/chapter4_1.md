# chapter 4 Implementation

(in this chapter i fucking found cirtain part literally exist in chapter Methdology, so WHICH belongs to which, please reimplement and port  chapter 3-4 to sync properly to each other lmao)
and also something like the Exported artifact or sth should be moved to chapter 5 and giggles because it is Result , 3 chapters are deadass overlapping lowkey 




hree constraints shaped it: seed-level data integrity, an 8 GiB laptop GPU, and
evidence that could still be checked after each long experiment finished. The repository was reorganised after
the terminal evaluation, so the frozen experiment bundle remains the authority for every reported metric while
the reorganised tree is the code that is maintained going forward. -->delete all of this shit or just say laptop 8gb Video memory GPU

4.1 Implemented System  (wtf is even Boundary)
The model could be started with command is vnphish analyze (both 2 others are Internal commands even the demo , the most important must be 1st)

the Project structure many things that is shit and cirtain are very ass like somewhere we have `+--` but somewhere we have ``(2 of `) --` like "Safe write" , Profile selction, seed-safe, review oneoff (wtf is the folder named Migrations and those NONSENSE  immutable source-closure operations retained experiment compatibility layer)

DELETE goofyass 2 next passage until figure 4.1
The active...............code easier to navigate and defend (AHHH clearly shit here)

Figure 4.1 is technically same of my ass  to Figure 3,1 and it is so broken(text overlaps etc) kick it off

4.2 Sussy sameass/ so many dup to chaptee 3 , persumably port chapter 3's content to here or something 

4.3: Sussy has so many dup to chapter 3, persumably merge chapter 3 to here

Combining that median with one observed validation pass and one
observed checkpoint save gives a projected 4,369.750-second schedule (72 minutes 49.750 seconds). That
is an extrapolation from a short probe, not the wall clock later observed for full training.-->we do full Qlora , so get the fuck some like "observed chcekpoint bla bla no need"



22,136,381,440 bytes of peak system RAM.  -->REMOVE!

probe-->Training or smoke test smoke run or somthing i dont understand this word much

Figure 4.2: Bounded RTX 5050 resource probes. Step time and optimizer-schedule duration use separate visual
scales; the duration values are projections, not observed end-to-end runtimes. Neither probe produced an out
of-memory event. --> Estimation of LORA and Qlora smoke run  statistics. 

Figure 4.3  console output from the 45-step NF4 QLoRA, taking only 3.4 seconds in Median and the smoke run for around 3 minute.

(also i have to edit this image as it is having some numbers in it )

4.4 the Full Qlora (PORT some from chapter 3 down to here)


eed 42,wtf is seed 42 no lol

n the same 1,658-row training and 219-row
validation identities.  -->really wonder what is "the same"-->kick "the same", Identities=dataset

4.4.1:
(clealry duplicated from chapter 3's board thing tabler 3.5)
 Checkpoints were chosen against a safety gate declared in advance, never against terminal
evaluation performance. Checkpoint 200 was kept, -->i am wonderig why Checkpoint 200 was kept  and shit 

An earlier attempt at the full run got as far as useful intermediate evidence but exposed two defects: the mutable
output root left out the run-ID segment, and a validation object was compared against canonical JSON in the
wrongrepresentation. That attempt was deliberately interrupted and kept as failure evidence, and no checkpoint
from it seeded the final run. After the fixes, a clean request restarted from step zero and completed all 1,245
steps. The restart matters: quietly continuing from a structurally ambiguous work root would have left the final
lineage much harder to defend.
 --> literally nonsense+chatgpt+ "harder to defend" 

 igure 4.4  Qwen QLoRA training and validation loss across the completed 1,245-step run plotted (just this)

 That run took 14.87 hours end to end, and it is worth saying where the time went. The 1,245 optimizer steps
account for only 1.36 hours of it. The remaining time is the validation cadence: at each of the 25 checkpoints
the model generated a full structured answer for all 219 validation rows, which is 5,475 generations on a laptop
GPU. --> CLEARLY chatgpt change to: THe run took 14.87 hours , however most of them came from Validation. The optimizer steps only takes 1.36 hours. The figure 4.5 show it. 

Figure 4,5: why the fuck Peak allocated Vram in figure 4.5 is only 5.73GB and not 7G like we stated above, inconsisetent.

Need to regenerate figure 4.5 or fix stats

4.4.2: seems to be dupass on chapter 3 have a porting.

plotted from the run’s
own retained event log rather than drawn by hand -->KICK THAT

The dip at Qwen step 150 is
the recorded value, not a smoothing artifact. -->remove this 



4.5 
he selected Qwen adapter was merged with the pinned-->remove this word  base model and converted through llama.cpp [42]
into a single Q8_0 GGUF file.  

 Both the original conversion envi
ronment and an independent CPU load test accepted the file before its receipt was registered.  -->HECK this sentence no

At runtime, analyze and demo both use AnalysisRequest and AnalysisResult as the public contract. The
service normalises the text, picks an explicit local profile, dispatches to the heuristic, GGUF, or accelerated-local
analyzer, and returns a risk tier, threat labels, grounded cues, and safety recommendations. vnphish doctor
checks profile and artifact readiness through DoctorStatus before any analysis runs. The offline runtime
needs no provider credential of any kind. -->if we fix "profile" shitass we have to fi this sentence at all and also wtf Provider credential, crap so many jargon again in here


4.6 vidence and Failure-Recovery Design

this is where any failure should be in, but honestly tere are a few failure: 
API during claude generation-->propose Checkpoint to avoid losing data 
Narrative in dataset-->fix 
Lora has controller error+consuming so much vram-->Qlora  (that is what i remember during my work fr) 
revamp this chapter with the graph and nuke jargons

4.7 is an ultimate fucking jargon+ useless CYBERSECURITY  again KICK!


