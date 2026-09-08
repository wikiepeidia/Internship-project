# chapter 3 draft 2 

- fix graph issue 

3.1 

The work has five  stages and one maintainability stage. (wtf is even Maintability stage, remove it ) 

The first builds the governed corpus -->dataset or equv easier to understand and
its seed-group split lineage (spilt or any thing easier to understand). The second measures ordinary-->measure training LoRA and QLoRA on the target laptop 

 The third  fully trains Qwen QLoRAandPhoBERTlocallyandverifiestheQwenGGUFexport.
The fourth delivers a text-only runtime with stable structured-output contracts(remove this word contracts)

 Thefifth 
evaluates them once on the  220-row Test dataset or eqv.
 Themaintainability stage then separates the active application
code from the historical experiment and evidence-producing source, without altering or regenerating any frozen
metric.DELETE


3.2 Building and Splitting the Dataset

( i think we are missing the Seed explaination here, jurors could ask where you even make the Seed ID and shits, we should add it in)
The dataset started from seed records collected by the tinnhiemmang.vn crawler and was expanded into a
controlled synthetic development corpus-->generation or eqv.

 After processing and quality repair ,  the final set  holds 2,097
rows across four classes: bank impersonation, Zalo social engineering, task scam, and benign.

 Every generated
record first passes a Pydantic which verify schema gate that checks types, required fields, permitted labels, score ranges,
and evidence-span structure. 

Further more(or smth eqv), the quality is assessed separately by a model-based judge (Section 3.2), and
Random set (or eqv or dont need this idk in this part) manual decisions are made by a Vietnamese  reviewer . 
Pydantic  validates structure only; and model judgments thought bulk automated, are not offered as human ground truth. Figure 3.2 shows the
pipeline, and two representative message forms follow.

Graph: fix whatever "Span dedup ,hillarious as fuck"

Figure 3.2: Dataset construction and final quality controlled pipeline. Human review detected cirtain narrative, generic fake links (and eqvs)and then pass schema pydantic, duplicate (WTF is even span , seed caps, Linage, spit Itegrity???) . HUman review fix and approve cirtain wrong label (please recheck this)

igure 3.4: One governed corpus row from the training split, showing all seven retained fields: message text,
four-class label, risk tier, literal suspicious spans, Vietnamese explanation, generator source, and the seed iden
tity used for group-disjoint splitting. --> One example of the dataset which has all 7 fields (be simple here)


Add: Two example of classification (High risk, no risk) before "bank impersonation" and Beigin example 

The corpus supports model development and internal validation. It is not a substitute for a real-world, human
labelled benchmark. Each build is tied to a versioned manifest, so any evaluation result can be traced back to
the exact dataset snapshot it came from -->The set has been built with proper vadilation but it wont be a subtitute for a real world human labelled benchmark 



Table 3.2:
Set during generation (just this

)

Source  tag from which API Provider (or eqv )

Seed id: Link back to the original seed from TInnhiemmang and eqv 

The label is set when the record is generated. The scheduler runs repeated class-conditioned batches in its
complex and bulk modes until every target count is filled. Each batch asks explicitly for one class, so each
record’s label starts out matching the class that was requested. This is the same label-conditioned generation
approach used for controllable dataset construction elsewhere [36]. The targeted review described below then
either drops a flagged record or approves a corrected label; it is not a claim that every row in the corpus was
annotated by hand. ---> Change to something that is fucking simpler like for bachelor, they mostly understand that generation can be done with a System Prompt which i am sure we did fucking have it.



Worked Example:

The example shows the record contract; it is not used to claim anything about which partition the
row belongs to --> WTF is this sentence evn mean

The label does different jobs at training time and at scoring time. For Qwen training it is part of the serialized
target, alongside the risk and evidence fields; for PhoBERT it is the target of the four-class head. At scoring time
the ground-truth label is withheld from the model input and joined back only after the prediction is made. That
is what lets the same row identities support a fair shared-cohort comparison even though one model generates
structured text and the other returns class logits. --> WHAT the fuck  so many jargon and hard to undertstand , cant it be simple as this Qwen: The label is bundled directly into the text prompt as part of the structured target (alongside risk and evidence fields).PhoBERT: The label acts as the direct target for a traditional 4-class classification head.


The final judge bundle covers all 2,097 records. It combines 1,561 verdicts carried over for byte-identical
records with 536 newly judged ones; the carries are reusable evidence, not a claim that every record was judged
again. Within the bundle, 1,395 records pass all five rubric dimensions, or 66.52%. The mean scores on the 1–5
scale are 4.020 for realism, 4.851 for label correctness, 4.672 for code-switch naturalness, 4.119 for risk-tier
correctness, and 4.745 for suspicious-span accuracy. Semantic convergence finished with no unresolved rows.
-->another nonsense crazy full of words jargons, like Byte identical, Reusable Evidence, "claim"write as simple like other characters 


These are descriptive quality results, not inferential claims -->Lmao sentence

An independent review after generation found systematic scenario-framing and narrative artifacts in the syn
thetic Zalo subset.-->Those 240 records were completely replaced 

 controlled offline
reconstruction used 60 preserved semantic roots and their seed lineages to write 300 new direct-message ver
sions.  -->more jargon Seed linage i dont understand , also wtf is this Offline reconstruction means we sdhould explain it or change the word


qnd the schema, span (Shit), label (just this), seed-disjointness(shit), duplicate, and seed-cap (shitt)gates are properly pass.

Four of the new rows were later quarantined on semantic grounds, leaving 296 in the final corpus --> HECK why quarantine if it is useless, kick this sentence 

The original first-pass generator and the final judge are different model families. The judge does share a family
with the 296 reconstructed rows, so for those rows its verdicts are not an independent opinion. The later repair
and gap-filling work went through the same provider interface as the judge, and this report does not claim to
have established, one way or the other, whether those repaired rows are family-independent of it either. --> Cite the MODELS not just "generic shit"also clearly chatgpt message 


A separate stratified (wtf is this word) human sample of 100 rows was drawn from the final snapshot, including 9 Zalo rows. The
Vietnamese reviewer  (AHH "fluent") marked 44 PASS and 56 FAIL, and reviewer and judge agreed on 87 of the 100.
This is partial corroboration: it describes the sampled rows and does not make the whole reconstructed Zalo
subset independent of the generator family.(Shitass sentence lmao) The sample covers all four labels, and their outcomes

The targeted triage went through 324 task-scam rows the judge had flagged. It produced 91 drops and 233
approved relabels: 48 bank impersonation, 177 Zalo social engineering, and 8 benign. Admitting them was
a separate decision. Only 57 relabels were admitted, and 176 human-approved Zalo semantics were excluded
purely because they shared one non-independent lineage, not because the reviewer judged them wrong. The
global seed cap had already removed 33 rows, and final semantic convergence quarantined 4 rows whose labels
could not be repaired and removed 2 more cap rows. What remains is the 2,097-record corpus: 1,658 training,
219 validation, and 220 test rows, made up of 741 bank-impersonation, 655 benign, 404 task-scam, and 297
Zalo-social-engineering records
-->101% this is chatgpt's own narrator message rather than someone write in report .. Fix it so like the 324 task row the Judje flagged , another human review bla bla and explain reason why only few rows is allowed , instead of goofyass "semantic converenge" , make it something like Spilt dataset 80 10 10 thing

The completed model runs use exactly those identities(KICK this word): 1,658 training rows and 219 validation rows, followed
by one terminal comparison -->Evaluation on the remaining 220. Results from earlier development snapshots are not the
evidence behind any conclusion in this thesis.(delete this sentence) Table 3.3 gives the split counts the completed runs are bound to. 

Table:
Partition-->Data spilt or SOMETHING eqv
Terminal eva-->Evaluation (train/val/test)

Promoted corpus-->Total 

Integrity control table thing-->fduck it nonsense

3.3 
Because of that, swapping the backend changes
neither the command-line interface nor the output format.  -->NOnsense sentence 

 The
version 1 boundary is strictly text-only: OCR, image, audio, and mobile input channels are all out of scope. -->Clearly GSD workflow message remove it.

A readiness check confirms the selected profile loaded before any analysis starts. If it did not, the system stops
with a diagnostic instead of quietly running under a configuration nobody asked for -->what the hell is this even means are we even has configuratin to run Model or sth lmao

3.4
The selection pilot screened three open-weight Qwen candidates [41] on 33 fixed balanced examples under
recall-first scoring: qwen3-4b-instruct-2507, qwen3.5-4b, and qwen2.5-7b-instruct. --> For Finding Qwen's best candidates, a quick 33 fixed example were tested on 3 different qwen's family models.....

 It used a three
tier outcome structure of benign, suspicious, and high-risk, and it ran on the target laptop so that hardware fit
was in scope from the beginning.-->Instead of using 4 risk tiers, it used 3 tiers .... and run on the same laptop (each time i hear "scope " i clearly know that is chatgpt +GSD)


Table 3.4

Note: This was a bounded pre-adaptation screen, not the final Qwen–PhoBERT experiment. All three candidates had overall
risky-class recall 0.50 across the combined suspicious and high-risk tiers. The selected 4B checkpoint matched the observed recall
while using less measured pilot VRAM and latency than the other 4B candidate. These small-sample measurements do not establish
general model-family speed or quality superiority -->Couldnt we remove this shit instead of putting a damn note

The pilot selected a feasible Qwen
checkpoint for later adaptation; it is not a terminal evaluation result. -->remvoe this sentence

Qwen3-4B-Instruct-2507 was chosen for the generative path because it met the pilot’s recall and hardware
constraints and could emit the whole structuredresponse. PhoBERT[7]wasthenaddedasaVietnameseencoder
baseline instead of adapting a second Qwen candidate. That makes for a more useful engineering comparison:
a generative 4B model that returns label, evidence, and guidance, against a compact four-class classifier tuned
for the label alone --> wait a sec so Phobert is just a fucking Baseline for Qwen or it is the model that can generate Explaination-->fix the remaining chapter 3.4 to finaly said that Qwen=both Classifcation&Explaination while Phobert only good at Clasifcation only yet outperform Qwen bla bla



3.4.1 Measured LoRA–QLoRA Decision -->Decision of Lora&Qlora
The adaptation choice came from bounded evidence measured on the same machine. An ordinary full-precision
LoRAprobekept31optimizer-stepevents,26ofthemmeasured. I-->In the same machine, a small run test btween Lora and Qlora has been tested. For Lora, there are 31 steps...Each steps's median took 53 second, which estimated to be around 18 hours training. Furthermore the video peaked at 7902MB (thats clearly not 9MB free lmao). Remove the "the run ended with controlled eror"...Although there is no OOM message, during 18 hours with that low amount of Video memory there will be no gurantee that the run would properly succeed (find citations about this if ytou could , thats the best i can say about why i would choose qlora)

A separately dated QLoRA probe turned on NF4 with double quantization, verified 252 four-bit linear modules,
froze the base model, and kept exactly five warm-up plus 40 measured steps. Its median step was 3.462389 sec
onds, giving a 72-minute-49.750-second projection for the optimizer schedule plus one validation and save.
Peak device memory was 7,516 of 8,151 MiB, with no out-of-memory error and no thermal stop. Because that
projection leaves out the full checkpoint and validation cadence, it is used only as feasibility evidence. These
measurements are what motivated the QLoRA route, without turning a resource comparison into an accuracy
claim

-->therefore another smoke run with Qlora (NF4) showing that each step costing only 3 second, with highest memory 7516MB, leaving a very decent headroom for training. Since (whatever article said Qlora get accurancy from lora you said above add it in) , it motivated the thesis to Qlora route .

3.4.2: PLEASE devide this : 
3.4.2--> The Training Qlora for Qwen 

deterministic structured-output parser. -->something simpler

it passed the declared safety gates. These are development-validation measurements used to pick a checkpoint,not the terminal comparison -->more useless security things , aint it pass something like pydanitc or whatever be better 

The two parts are serialized under Instruction and Response headings,
tokenized to a maximum length of 1,024, and trained with a causal language-model objective over the whole
sequence. At evaluation time the generated class value is decoded back to one of the four labels for the con
fusion matrix. The user-facing runtime may later present more than one threat label after applying its decision
contract, which is separate from the single-label experimental metric -->too many jargon again.


This was a deliberate architectural choice, and it is not the only way to get a classification decision out of a fine
tuned LLM. The alternative, also used in practice, is to attach a small classification head to the decoder’s final
hidden state and train that head directly, leaving generation out of it [32]. A head can reach a well-calibrated
label with fewer trainable parameters. What it has no native mechanism for is the other two fields this system
must produce: an evidence span copied out of the input text, and a short recommendation. Adding those would
mean training a second generation component beside the head and reconciling the two outputs afterwards. This
project instead trains the decoder to emit the label as part of one generated JSON object, together with the
evidence and recommendation, in a single forward pass. The label acts as a verbalizer [30]: a fixed, closed
vocabulary of literal strings (bank_impersonation, zalo_social_engineering, task_scam, benign)that
the model is trained to reproduce, following the classification-as-generation framing introduced with T5 [29].
QLoRA adds no classification-specific layers of its own; it adapts the existing attention and projection weights,
and the classification signal comes entirely from next-token training on the label field. Narang et al. report that
generating a label and its explanation together in one pass gives a more consistent relationship between them
than predicting the label first and explaining it afterwards [31], which is the same reasoning applied here. A
classification head is still the better choice when a single label is all that is needed; this project needed two more
fields, produced from the same generation context rather than stitched on later --> 1001% jargon, and i asked gemini to explain it as simple as this: The Traditional Approach (Classification Head): Attach a small scoring layer to the end of the model. This layer only outputs a label (e.g., task_scam or benign). It is highly accurate and uses very few parameters. -->The Problem: It cannot naturally generate text. Since our project requires three outputs—a Label, a Text Evidence, and a Recommendation—we would have to build a separate text generator and try to stitch the outputs together later.Therefore Our Approach (Classification-as-Generation): We treat classification as a text-generation task (pioneered by Google's T5 model). We train the model to output a single JSON object containing all three required fields in one go.-->All-in-One Output: The model generates the label, evidence, and recommendation together in a single step (forward pass). Better Consistency: Research (Narang et al.) shows that generating a label alongside its explanation at the same time makes the explanation match the label much better than doing them separately.Simpler Architecture: By using QLoRA to fine-tune the model's existing weights, we don't need to add any custom classification layers. The model simply learns to pick the correct label string from a fixed list of choices (bank_impersonation, zalo_social_engineering, etc.). That clearly what bachelor write 


Qwen training procedure: only the low-rank matrices A and B in Equation 3.1 were updated, while the
base weights W0 stayed frozen in 4-bit NF4. Each micro-batch held one serialized instruction–response pair,
and four micro-batches were accumulated per optimizer update, giving an effective batch size of 4. The causal
language-modelling cross-entropy covered the whole response, including the literal class label, so a wrong label
fed straight into the token loss. Validation predictions, checkpoint selection, raw events, resolved configura
tion, hardware identity, and graph inputs were all retained and verified. Table 3.5 summarises the frozen run
configuration --> another goofyass jargon,aay somthng like Tối ưu bộ nhớ (QLoRA): Toàn bộ trọng số gốc của mô hình (W₀) được "đóng băng" ở định dạng nén siêu nhỏ 4-bit NF4. Hệ thống chỉ cập nhật một lượng rất nhỏ các tham số bổ sung (gọi là ma trận LoRA A và B). Việc này giúp chạy được mô hình lớn trên phần cứng giới hạn.Quản lý Batch Size: Mô hình xử lý dữ liệu theo từng cặp (Câu lệnh – Phản hồi). Cứ sau 4 lượt xử lý nhỏ (micro-batches), máy tính mới cập nhật trọng số một lần, tạo ra một Batch Size hiệu dụng bằng 4.Cách mô hình học (Loss Function): Chúng tôi áp dụng hàm phạt lỗi (Cross-Entropy) lên toàn bộ văn bản phản hồi—bao gồm cả Nhãn phân loại (Label). Nghĩa là, nếu mô hình đoán sai Nhãn, hệ thống sẽ tính điểm phạt rất nặng và ép mô hình phải sửa đổi ngay lập tức , and remove whatever "Verified"shit

Table 3.5: 

Cirtain field are hillarious definetely GGUF SHA256 garbage


(remove all phobert shit)



After training, the Qwen adapter was merged into the base weights and exported with Q8_0 quantization to a
4,280,403,232-byte GGUF artifact, and both the original and an independent load smoke were verified. NF4
and Q8_0 do different jobs: NF4 cuts training memory for QLoRA, while Q8_0 is the portable llama.cpp [42]
inference artifact. That establishes a local runtime path; deployment fitting after the evaluation is still deferred -->Have an Explaination why NF4-->Q8 not Q4 if it is hanst, my supervisor used to ask me about this , check if it is because of Vietnamese diacritics /better CPU interference, or any article compare Q4 vs q8 on cpu etc and also remove VERIFIED

3.4.3 Phobert training Expeirment (cut out from qwen)

PhoBERT was trained separately as a full, non-quantized four-label sequence classifier on the same train and
validation identities. It completed 312 optimizer steps, and the selected step-100 checkpoint recorded validation
macro F1 0.984893 and accuracy 0.986301 with zero invalid outputs. No LoRA target, PEFT adapter, or GGUF
conversion is claimed-->exported for PhoBERT 
and add some stats for Phobert (PT files) if you could. make it simple


3.4.4 duplicated  (move those SHIT to eval or dont need.or make it simple ) 

Both frozen models were run once over the 220 evaluattion Json file and the statistic is described in Evlaution (link it)


3.5

This follows the principle that an explanation should rest -->should be given on
observable evidence rather than on a model confidence score alone 

Two rules govern that layer. -->jargon chatgpt 

the rest are another Jargon ass, fix it Cách Hệ Thống Xử Lý Lỗi Khi LLM Sinh Văn Bản Tự DoKhác với các mô hình phân loại truyền thống luôn trả về kết quả chuẩn chỉnh, một mô hình tạo sinh (LLM) xuất ra văn bản tự do và không có gì đảm bảo cấu trúc JSON của nó luôn hoàn hảo.Để giải quyết vấn đề này, hệ thống áp dụng quy trình xử lý gồm 2 bước nghiêm ngặt sau:Bước 1: Sửa lỗi cú pháp và Bóc tách JSONHệ thống không bao giờ tin tưởng tuyệt đối vào đầu ra của mô hình. Thay vào đó, nó sẽ:Quét toàn bộ văn bản thô để tìm tất cả các đoạn có thể là JSON.Dùng thuật toán (heuristics) để chấm điểm và chọn ra đoạn JSON tốt nhất (bất chấp việc mô hình có thể viết sai tên trường hoặc đặt cấu trúc lồng nhau sai cách).Nguyên tắc an toàn (Fail-Closed): Nếu không thể bóc tách được bất kỳ đoạn JSON hợp lệ nào, hệ thống sẽ báo lỗi ngay lập tức thay vì tự đoán bừa hoặc tự động gán nhãn an toàn (benign).Bước 2: Kiểm tra 4 quy tắc logic (Cross-Field Rules)Ngay cả khi JSON đúng cú pháp, nội dung bên trong vẫn có thể tự mâu thuẫn vì LLM viết từng từ một một cách mù quáng. Do đó, kết quả phải vượt qua 4 bộ lọc logic sau trước khi hiển thị cho người dùng:Nhãn an toàn (benign) không được xuất hiện chung với bất kỳ nhãn đe dọa nào khác.Nếu mức độ rủi ro là benign (an toàn) → nhãn bắt buộc phải là benign.Nếu mức độ rủi ro là nguy hiểm → nhãn KHÔNG ĐƯỢC phép là benign.Nếu rủi ro được đánh giá ở mức cao → danh sách bằng chứng (evidence) bắt buộc phải có ít nhất một mục, không được để trống.Kết luận: Nếu vi phạm bất kỳ quy tắc nào ở trên, kết quả sẽ bị hệ thống hủy bỏ ngay lập tức. Đây là điều mà các mô hình phân loại truyền thống không cần làm, vì chúng vốn dĩ chỉ xuất ra một nhãn duy nhất nên không thể tự mâu thuẫn với chính mình. (i think i did see this on the code that we normalize wrong class have a check and fix and also PLEASE wtf is "GGUF profile and LOCAL profile " USELESS ~)

3.6 is a jerkass useless DELETE or fix cuz no one care :
🛑 Tại sao đoạn này lại cực kỳ khó hiểu?Dùng quá nhiều từ trừu tượng chỉ cấu trúc code: Các cụm từ như "named runtime, integrity and artifact, data, modelling, and evidence domains" chỉ là cách gọi tên các thư mục trong dự án, nhưng viết thế này làm người đọc tưởng đó là các lý thuyết AI vĩ mô.Lẫn lộn giữa quá khứ và hiện tại: Tác giả cố giải thích cái nào là code cũ (dùng để đối chứng/lưu vết - provenance) và cái nào là code mới (hướng tới tương lai - forward-facing design) một cách rất loằng ngoằng."Khoe" nhưng lại "Khai" lỗi: Câu chuyện về "adversarial review" (đánh giá bảo mật kiểu tấn công thử nghiệm) vượt qua 128 bài test nhưng lại lòi ra 6 lỗi chí mạng (critical) và 3 cảnh báo (warning) được viết bằng cấu trúc câu rất phức tạp, dễ làm sinh viên bối rối không biết hệ thống này cuối cùng là tốt hay xấu.

3.7:All bullshit , i think it should be something like: Privacy fist, data is properly generated without "cooking again and again of one seed" , proper explaination, no false neg (important) and KICK my ass all of useless "Unsolved review findings "
