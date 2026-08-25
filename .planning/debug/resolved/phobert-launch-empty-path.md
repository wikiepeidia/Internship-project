---
status: resolved
trigger: "Controller v9 passed Qwen evidence, GGUF, VRAM, and PhoBERT doctor gates, started PhoBERT telemetry, then failed before trainer launch because GetFullPath received an empty path. Recover without reusing or overwriting a partial PhoBERT run."
created: 2026-08-26
updated: 2026-08-26
---

# PhoBERT Launch Empty Path

## Symptoms

- **Expected:** Frozen controller v9 starts exactly one fresh PhoBERT trainer after verified Qwen/GGUF evidence, three safe low-VRAM samples, and a passing PhoBERT doctor; telemetry and trainer are then supervised to immutable run evidence.
- **Actual:** Controller v9 passed every upstream gate and started PhoBERT telemetry PID 15308, but no PhoBERT trainer was launched. It recorded a terminal failure immediately after telemetry startup.
- **Error messages:** `Exception calling "GetFullPath" with "1" argument(s): "The path is empty. (Parameter 'path')"`
- **Timeline:** First observed at 2026-08-26 01:20:45 +07:00. This frozen fresh-only controller had never previously reached the PhoBERT launch boundary.
- **Reproduction:** Let controller v9 observe Qwen supervisor exit after verified QLoRA and Q8_0 GGUF, pass its independent evidence/GGUF checks, collect three GPU-memory samples at or below 2048 MiB, pass `phobert-doctor`, and start telemetry. The failure occurs before the trainer process is created.

## Current Focus

hypothesis: "Confirmed and self-verified: v12 training/run/graphs are complete, and the missing telemetry seal is truthfully recovered by distinct v13 artifacts that preserve the forced-timeout shutdown and legacy locale encoding."
test: "Await human confirmation that the recovered PhoBERT evidence is acceptable in the real workflow; all executable local and production-like checks are complete."
expecting: "User confirms the completed v12 run plus v13 repair artifacts satisfy the original workflow without retraining."
next_action: "On human confirmation, archive this debug session and commit only explicitly coordinated code/test/planning files; preserve the unrelated `.gitignore` change."
bug_class: "heisenbug-mandelbug (telemetry cancellation); deterministic locale-contract defect"
reasoning_checkpoint:
  hypothesis: "v12 cannot seal otherwise complete telemetry because its unconditional infinite sampler has no cooperative stop token and the real asynchronous Stop() missed the 30-second deadline; independently, every producer-localized comma-decimal elapsed value is rejected by v12's InvariantCulture parser."
  confirming_evidence:
    - "Frozen telemetry source has `while ($true)` and no StopPath; v12 wrapper's only normal termination is `$engine.Stop()`."
    - "Real v12 wrote the correct stop receipt, continued sampling for 19.716 seconds, timed out at 30.099 seconds, and its controller force-stopped the exact PID."
    - "All 21 CSV rows encode elapsed_seconds with a comma decimal, while v12 parses that field only with InvariantCulture/Float; the parser rejects all 21."
    - "A fixed comma-decimal parser matches timestamp-minus-start with maximum error 0.001692 seconds; timestamps are strictly increasing with maximum gap 11.708 seconds, and coverage spans the complete verified run."
  falsification_test: "The repair hypothesis is wrong if any raw CSV hash/header/timestamp/numeric/PID/coverage check fails, if fixed comma elapsed disagrees with timestamp-derived elapsed by more than 5 seconds, or if the run/controller/stop hashes and terminal log do not match the frozen v12 identities."
  fix_rationale: "A distinct offline v13 seal preserves every failed-v12 byte, records the forced-after-timeout termination honestly, and verifies the locale encoding against independent timestamps; it fills only the missing summary/receipt and cannot rerun or mutate the already verified model run."
  blind_spots: "The exact internal scheduling point that delayed the one real PowerShell.Stop() is timing-dependent and did not reproduce in short isolated runs; the repair therefore does not claim clean shutdown, and the future sampler still needs cooperative-stop design before reuse."
  candidate_causes:
    - "code: unconditional infinite sampler plus cancellation-only wrapper (confirmed by source and real timeout)"
    - "environment/serialization: current culture emitted comma-decimal elapsed values (confirmed in all rows)"
    - "contract/config: v12 verifier requires invariant decimals, clean exit=0, and samples not more than 5 seconds after stop (confirmed by source)"
  and_gate: "yes for successful sealing: even if cancellation had succeeded, the invariant parser would reject all rows; after the observed timeout, both the non-clean exit and post-stop samples also violate v12. The repair must address all contradictions without falsifying or rewriting evidence."
tdd_checkpoint:
  test_file: "tests/model_adaptation/test_phase40_phobert.py"
  test_name: "test_training_arguments_omit_removed_transformers_v5_keyword"
  status: "green"
  failure_output: "TypeError: StrictTransformers5TrainingArguments.__init__() got an unexpected keyword argument 'save_safetensors'"

## Evidence

- timestamp: 2026-08-25T18:20:45Z
  observation: "Controller log shows Qwen evidence verify exit 0, GGUF verify exit 0, three safe GPU samples at 0 MiB, PhoBERT doctor exit 0, fresh-target verification, and telemetry PID 15308 startup before the empty-path terminal failure."
  significance: "The fault is isolated to the post-doctor, post-telemetry, pre-trainer boundary; no duplicate PhoBERT training exists."

- timestamp: 2026-08-25T18:18:16Z
  observation: "Qwen supervisor sealed status complete after 5,097 telemetry samples; Q8_0 GGUF export and verification both exited 0."
  significance: "Recovery must reuse the verified Qwen/GGUF authorities and must not rerun Qwen."

- timestamp: 2026-08-26
  observation: "No repository-local .codex/skills or .agents/skills directory exists, and gsd-debugger has no configured injected agent skills. Targeted discovery found the frozen v9 controller and model-adaptation launcher tests without entering data/."
  significance: "No additional project skill rules constrain the investigation; the controller and its targeted test surface are the authoritative code paths."

- timestamp: 2026-08-26
  observation: "Git status contains a pre-existing modified .gitignore and this untracked debug session file."
  significance: "Any fix must preserve the unrelated .gitignore change and stage exact files only if a later commit is authorized."

- timestamp: 2026-08-26
  observation: "The v9 controller logs telemetry startup at line 1185 and immediately calls Invoke-PhoBertTraining at line 1187 before any trainer-success log."
  significance: "Working backwards localizes the thrown GetFullPath exception to Invoke-PhoBertTraining or code it synchronously calls before Start-Process returns."

- timestamp: 2026-08-26
  observation: "The debug knowledge base is absent; there is no prior pattern entry to test. SBFL is skipped because no failing automated test with per-test coverage exists for this controller launch boundary yet."
  significance: "Fault localization proceeds by deterministic working-backwards and exact call-site inspection, with a new regression needed to establish the failing spectrum."

- timestamp: 2026-08-26
  observation: "The production controller contains only two GetFullPath call sites: a separate path-containment helper at line 262 and ResumeFromCheckpoint normalization at line 481. The fresh call at line 1187 supplies no ResumeFromCheckpoint argument."
  significance: "Line 481 is the uniquely plausible empty-path sink at the failing boundary; the next test is whether its presence guard admits an omitted parameter."

- timestamp: 2026-08-26
  observation: "Invoke-PhoBertTraining declares [string] ResumeFromCheckpoint = $null (line 463), checks only $null -ne ResumeFromCheckpoint (line 479), then calls GetFullPath (line 481) before calling Invoke-PythonCaptured (line 483)."
  significance: "The source mechanism predicts that PowerShell string coercion turns the omitted fresh-only argument into an empty string, admits it through the guard, and throws before any trainer process can be launched."

- timestamp: 2026-08-26
  observation: "An isolated function with the identical typed default and null-only guard reported IsNull=false, Length=0, NullOnlyGuardEnters=true, then reproduced exactly: Exception calling GetFullPath with 1 argument: The path is empty."
  significance: "This directly confirms the typed-string coercion mechanism independently of Qwen, telemetry, GPU state, data, and child-process creation."

- timestamp: 2026-08-26
  observation: "Complete controller reading confirms the fresh call intentionally omits ResumeFromCheckpoint, while the only resume call supplies Checkpoint.Path after exact verification. Complete harness reading shows an AST-extraction seam that can execute selected controller functions with a stubbed Python launcher."
  significance: "No config, environment, or data condition is needed for the failure; a CPU-only differential regression can exercise v9 and v10 without top-level controller operations or child processes."

- timestamp: 2026-08-26
  observation: "Recovery ownership requires the frozen v9 source to remain byte-identical as failed-controller evidence; process cleanup and recovery launch are reserved for the parent controller after safety verification."
  significance: "The fix must be a new v10 immutable controller plus regression, not an in-place v9 mutation; this investigator will not stop telemetry or launch recovery."

- timestamp: 2026-08-26
  observation: "v10 controller and differential-test paths are absent. Frozen v9 SHA-256 is 63f47598fe81749b961ca7c5f056fe4e63925f2ad93f94f9beabafd047246b26. Its v9-specific literals separate into shared source-runtime-v9, new-attempt work/telemetry/log/cache paths, and a version-neutral exclusive lease."
  significance: "A new v10 can preserve source/Qwen authorities and cross-version duplicate exclusion while avoiding every failed-attempt output target; v9 identity can be asserted by regression."

- timestamp: 2026-08-26
  observation: "The new CPU-only differential test first verified the frozen v9 SHA and exact v9 empty-path failure, then failed on the inherited v10 guard with the same GetFullPath path-is-empty exception before the stub Python launcher."
  significance: "The regression is RED at the confirmed fix site and requires no trainer, child process, external config, or data access."

- timestamp: 2026-08-26
  observation: "After changing only v10's guard to IsNullOrEmpty, the unchanged differential test passed all three CPU-only scenarios: frozen v9 failure, v10 fresh launch arguments, and v10 non-empty resume canonicalization."
  significance: "The fix directly changes the causal branch and preserves adjacent resume behavior without launching any process."

- timestamp: 2026-08-26
  observation: "Fix-acceptance target regression passed 10 consecutive runs (30 scenario executions total); the new test and both controller sources parse with zero errors."
  significance: "The deterministic fix is stable in the CPU-only harness and the new sources are syntactically valid."

- timestamp: 2026-08-26
  observation: "Adjacent v9 CPU-only harness passed all 9 scenarios. Frozen v9 SHA-256 remains 63f47598fe81749b961ca7c5f056fe4e63925f2ad93f94f9beabafd047246b26; v10 SHA-256 is 547ea544907f3cc0b2219daff90e51e276827c2dc165bfecc6b9e4af2fa65289."
  significance: "The regression addition did not break the existing harness and the failed v9 evidence source was not mutated."

- timestamp: 2026-08-26
  observation: "The v9-to-v10 diff contains only attempt-specific v10 path substitutions and the IsNullOrEmpty guard. v10 retains exactly one v9 literal, source-runtime-v9, and retains the version-neutral shared FileShare.None controller lease."
  significance: "The fix is not behavior-deleting and isolates fresh recovery artifacts while preserving immutable source authority and cross-version duplicate exclusion."

- timestamp: 2026-08-26
  observation: "Stryker is not installed/configured (no command, package manifest, or mutation-tool reference), so the mutation signal is explicitly skipped. The recorded inherited-v10 RED followed by one-line-fix GREEN proves revert-and-reconfirm at the exact predicate."
  significance: "All applicable guardrail signals pass; the unavailable mutation framework is documented rather than assumed."

- timestamp: 2026-08-26
  observation: "Human-action checkpoint response authorizes the minimum fresh-only recovery after all process, lease, target, source, Qwen/GGUF reuse, and no-trainer gates pass; v9 evidence must remain immutable and only a conclusively identified v9 orphan telemetry process may be stopped."
  significance: "Recovery verification may now proceed, but process mutation and the single v10 launch remain gated on direct read-only identity evidence."

- timestamp: 2026-08-26
  observation: "Exact PID 15308 is absent; no live process command line matches Phase 40, PhoBERT, qwen-to-phobert, or system telemetry. The shared lease receipt exists, records failed v9 controller PID 20064 and SHA-256 63f47598..., and a read-only FileStream probe opens it successfully."
  significance: "There is no orphan telemetry process to stop, no duplicate controller/trainer, and no live FileShare.None lease owner; the stale lease is preserved as failed-v9 evidence."

- timestamp: 2026-08-26
  observation: "All 12 explicitly named v10 work/run/telemetry/log/preflight targets are absent; non-recursive *v10* scans of package and controller roots both return zero."
  significance: "No prior v10 attempt exists and the shared final PhoBERT run root is unused, satisfying the fresh-only target gate."

- timestamp: 2026-08-26
  observation: "Current request/source archive/source manifest/telemetry script hashes exactly match v10 constants (2512dbe6..., eae64f17..., 5903dd5d..., 1bc33f37...). Qwen summary remains status=complete with 5,097 samples and the GGUF manifest remains status=complete."
  significance: "v10 will reuse the same immutable source and completed Qwen/GGUF authorities; Qwen need not and must not be rerun."

- timestamp: 2026-08-26
  observation: "v9 evidence hashes were baselined read-only. Its log records the exact empty-path failure, then a 30-second controlled-stop timeout for PID 15308 and lease release; the cleanup implementation force-stops only the same creation-identity process before throwing. Telemetry CSV/stdout/stderr/stop receipt exist, while summary/verification files are absent because no StopReceipt was returned after the timeout."
  significance: "PID 15308 was already terminated by the identity-checked v9 cleanup, not left orphaned; no process mutation is needed and the incomplete failed telemetry artifacts must remain preserved."

- timestamp: 2026-08-26
  observation: "All named input archive/root, PhoBERT base model/manifest, Python, PowerShell, and source-runtime-v9 dependencies exist. All 28 non-reserved manifest entries in source-runtime-v9 match recorded byte sizes and SHA-256 values."
  significance: "The frozen source and runtime dependency gates pass without accessing or enumerating any reserved split."

- timestamp: 2026-08-26
  observation: "The Qwen GGUF manifest is status=complete, outtype=q8_0, load_smoke.passed=true, output bytes=4,280,403,232, output SHA-256=457f6f92..., and source run-evidence SHA-256=ce493f05...."
  significance: "The manifest provides exact current identities to verify before reusing Qwen/GGUF evidence; no Qwen execution is required."

- timestamp: 2026-08-26
  observation: "Current Qwen run-evidence SHA-256 is ce493f0596ce232b4afac193dea1dea36e4826ae1c57a2470cbe8e40a433f9da; current GGUF bytes are 4,280,403,232 and SHA-256 is 457f6f92d36a7d54da9916fd80a4028dcd055a653a015c4877370a0fea4d18ab, all exact manifest matches."
  significance: "The completed Qwen/GGUF authorities are byte-identical and safe to reuse without rerunning Qwen."

- timestamp: 2026-08-26
  observation: "Three 15-second-spaced GPU samples at 18:33:37Z, 18:33:54Z, and 18:34:10Z each reported 0 MiB used and zero related controller/trainer processes."
  significance: "The no-trainer and low-VRAM gates pass immediately before the authorized single v10 launch."

- timestamp: 2026-08-26
  observation: "After an atomic repeat of old-PID absence, zero related processes, v9/v10 source hashes, all fresh targets, unlocked lease, and 0 MiB GPU, exactly one hidden v10 controller was launched as PID 12664 at 2026-08-25T18:35:12.6220146Z (FILETIME 134321565126220146)."
  significance: "The authorized fresh recovery has begun exactly once; controller identity is bound to v10 SHA-256 547ea544... and unique v10 stdout/stderr captures."

- timestamp: 2026-08-26
  observation: "Immediate CIM/Get-Process verification confirms PID 12664 is pwsh.exe with creation FILETIME 134321565126220146. Reading the lease receipt is blocked while live because v10 holds it with FileShare.None."
  significance: "The read failure is expected exclusive-lock evidence rather than a controller failure; live identity must be correlated through the chain log until the lease is released."

- timestamp: 2026-08-26
  observation: "Lock-only probe returns sharing violation 32. The v10 chain log binds PID 12664/FILETIME 134321565126220146 to controller SHA-256 547ea544..., records fresh targets verified, and records verify-qwen-before-phobert exit=0 plus verify-qwen-gguf-before-phobert exit=0."
  significance: "One exclusively owned v10 controller is live and has reused, not rerun, completed Qwen/GGUF authorities successfully without a terminal failure."

- timestamp: 2026-08-26
  observation: "The bounded monitor recorded Qwen GPU release at 0 MiB with three safe samples, phobert-doctor exit=0, telemetry PID 27392 startup, and phobert-train-fresh Python PID 20412 launch at 18:36:37Z. Trainer PID 20412 has parent PID 12664 and creation FILETIME 134321565975430833."
  significance: "The real v10 recovery crossed the exact original failure boundary and created one fresh trainer without the GetFullPath empty-path exception."

- timestamp: 2026-08-26
  observation: "The first post-launch supervision check found controller PID 12664 no longer live shortly after trainer PID 20412 was logged."
  significance: "The original empty-path defect is fixed, but the recovery is not yet verified as a live supervised training run; a new post-launch terminal condition must be diagnosed from preserved v10 evidence."

- timestamp: 2026-08-26
  observation: "v10 chain log records phobert-train-fresh exit=1 and terminal failure. Trainer stderr shows successful PhoBERT weight loading followed by: TrainingArguments.__init__() got an unexpected keyword argument 'save_safetensors'. Controller cleanup then identity-stopped telemetry PID 27392 after a 30-second controlled-stop timeout and released the lease."
  significance: "The empty-path root cause is fixed and trainer creation occurred, but a new post-launch Transformers API failure prevents training. All v10 PIDs are absent and its used targets must be preserved rather than reused."

- timestamp: 2026-08-26
  observation: "Both repo and frozen source-runtime-v9 call transformers.TrainingArguments(..., save_safetensors=True) directly in phobert_training.py. Installed Transformers is 5.9.0 and its 113-parameter TrainingArguments signature has no save_safetensors parameter; pyproject declares only transformers>=4.45."
  significance: "The failure is an allowed dependency-major API mismatch, not corrupt data or launch state."

- timestamp: 2026-08-26
  observation: "The generic training.py path already builds a kwargs dictionary and filters it by inspect.signature(TrainingArguments) before construction; the PhoBERT path does not."
  significance: "A project-native compatibility pattern exists and provides a falsifiable minimal fix direction without pinning or mutating the installed environment."

- timestamp: 2026-08-26
  observation: "All 31 existing PhoBERT tests pass because their FakeTrainingArguments constructor accepts **kwargs, so it cannot reject a keyword removed from a strict upstream API."
  significance: "A strict-v5 constructor regression is required to reproduce the production incompatibility; a neighboring **kwargs regression is also required to prevent over-filtering permissive factories."

- timestamp: 2026-08-26
  observation: "The new injected strict Transformers-5-shaped constructor failed RED at phobert_training.py:2801 with the exact production-class error: unexpected keyword argument save_safetensors."
  significance: "The post-launch failure is now deterministically reproduced in a CPU-only integration test without any trainer process, source bundle, or reserved-split access; the fix site is confirmed."

- timestamp: 2026-08-26
  observation: "After adding the signature-aware construction seam, the strict-v5 regression and explicit **kwargs-neighbor regression both pass (2 passed in 2.04s). The strict factory omits removed save_safetensors, while the permissive factory captures save_safetensors=True."
  significance: "The minimal fix handles the installed v5 API without downgrading and preserves the prior behavior for factories that explicitly accept arbitrary keyword options."

- timestamp: 2026-08-26
  observation: "The complete PhoBERT module passes 33 tests in 5.89s and both changed Python files compile successfully. Ruff is not installed in the active environment, so its signal is unavailable rather than passed."
  significance: "All executable adjacent PhoBERT behavior remains green; the remaining local acceptance signal is targeted mutation/revert-and-reconfirm."

- timestamp: 2026-08-26
  observation: "A one-line pass-all-kwargs mutant made the strict-v5 regression fail with the exact original save_safetensors TypeError; after restoring `if key in parameters`, the strict-v5 and **kwargs-neighbor tests passed again (2 passed in 1.89s)."
  significance: "The regression kills the causal mutant and the restored source is reconfirmed; local API fix acceptance passes before any v11 packaging."

- timestamp: 2026-08-26
  observation: "The request schema fixes three repository-relative run roots and exactly three runs, so the partially used v10 canonical PhoBERT root in transfer-root-v3 cannot be reused or renamed in place. A new transfer-root-v4 gives v11 a fresh absolute canonical root while preserving every v10 artifact."
  significance: "v11 must use a separate transfer root with a new source bundle/request identity; completed Qwen run evidence and GGUF can remain byte-for-byte in v3 and be verified there without rerunning Qwen."

- timestamp: 2026-08-26
  observation: "The source bundle is a deterministic 28-file code allowlist. A v11 bundle can copy the 27 unchanged frozen runtime files and replace only phobert_training.py with the tested repo source; the input authority contains only the existing train/validation archive and can be copied opaquely to v4."
  significance: "The packaging plan requires no access, stat, hash, open, or enumeration of any reserved split and keeps v9/v10 runtime/bundle bytes immutable."

- timestamp: 2026-08-26
  observation: "The explicit prebuild gate found source-runtime-v11, transfer-root-v4, phobert-work-v11, the v11 controller, and its packager all absent before creation; no related process was live and the shared lease opened exclusively. Frozen v9/v10 hashes still match 63f47598... and 547ea544...."
  significance: "The fresh v11 artifact namespace is unused and there is no duplicate controller/trainer or lease owner; packaging may proceed without process mutation."

- timestamp: 2026-08-26
  observation: "The staging-first packager validated and atomically published source-runtime-v11 and transfer-root-v4. Request SHA-256 is 1521917a..., source archive 0e76ee9f..., inventory f6181c8f..., with 28 files and runtime PhoBERT SHA-256 3b41b29e... exactly matching tested repo source."
  significance: "v11 has a new immutable request/source authority and fresh absolute canonical run namespace while v9/v10 and transfer-root-v3 remain untouched."

- timestamp: 2026-08-26
  observation: "The new v11 controller parses with zero errors (6,688 tokens) and SHA-256 bd48a7e3.... Its diff from v10 contains only v11 attempt identities, v4 request/source/input/final-root paths, v3 completed Qwen/GGUF/base reuse paths, and the new request/source hashes; the shared lease path is unchanged."
  significance: "Controller construction preserves the established safety/supervision logic while separating every v11 mutable artifact and keeping v9/v10 byte-identical."

- timestamp: 2026-08-26
  observation: "The v11 CPU-only controller harness passes all three scenarios: frozen v9 exact failure, v11 fresh stub launch with v4 request/input, v11 work root and v3 base snapshot, and non-empty resume canonicalization. The unchanged v10 harness also remains green."
  significance: "Attempt-path substitutions and the original empty-path fix are regression-proven without launching a trainer or child process."

- timestamp: 2026-08-26
  observation: "The complete non-GPU prelaunch gate passed: read-only controller SHA bd48a7e3..., request 1521917a..., archive 0e76ee9f..., manifest f6181c8f..., input 12136f9a..., Qwen evidence ce493f05..., and GGUF 457f6f92... all match. All 28 runtime files match and are read-only; Qwen remains complete with 5,097 samples; v11 work/final/controller/cache targets are absent; no related/prior process is live; the shared lease is unlocked."
  significance: "Every source, reuse, duplicate-exclusion, and fresh-target gate passes immediately before the final spaced GPU gate."

- timestamp: 2026-08-26
  observation: "The first 30-second bounded sampling command returned after the three-sample window but its buffered JSON was not captured; an exact command-line identity check confirms no sampling process remains live."
  significance: "No launch is authorized from unrecorded evidence; the same read-only sampling gate must be repeated in a pollable session and captured explicitly."

- timestamp: 2026-08-26
  observation: "The repeated pollable GPU gate captured samples at 18:53:01Z, 18:53:18Z, and 18:53:34Z; each reported 0 MiB compute memory and zero related processes."
  significance: "The final spaced no-trainer/low-VRAM gate passes and authorizes the exactly-once v11 controller launch, subject to one atomic immediate recheck."

- timestamp: 2026-08-26
  observation: "An atomic immediate recheck found controller SHA/read-only state unchanged, all v11 mutable targets still absent, zero related processes, unlocked lease, and 0 MiB GPU; exactly one hidden v11 controller was launched as PID 26652 at 18:54:08Z (FILETIME 134321576483363104)."
  significance: "The authorized fresh recovery has started exactly once with unique outer captures and is bound to controller SHA bd48a7e3...."

- timestamp: 2026-08-26
  observation: "CIM and Get-Process confirm PID 26652 is the v11 pwsh command with exact creation FILETIME 134321576483363104. The shared lease now returns sharing violation, and the chain log binds that identity to controller SHA bd48a7e3..., verifies 28 runtime files/fresh targets, and records Qwen run-evidence verification exit 0 before starting GGUF verification."
  significance: "Exactly one correctly identified v11 controller owns the lease and has begun reuse-only upstream verification; there is no launch ambiguity or duplicate controller."

- timestamp: 2026-08-26
  observation: "The live controller recorded verify-qwen-gguf-before-phobert exit 0 at 18:54:35Z; its only persistent direct child is conhost and outer stderr remains empty."
  significance: "Both completed Qwen run evidence and GGUF were reused and independently verified; the controller is now in its internal GPU-release sampling gate, not rerunning Qwen."

- timestamp: 2026-08-26
  observation: "v11 passed its internal three 0-MiB GPU samples and repeated source/fresh-target gates, but phobert-doctor PID 28044 exited 1 with exact stderr: `--base-model-path is not the canonical request-bound snapshot path`. The controller released the lease; no telemetry, work root, final root, or trainer was created."
  significance: "The v11 source/API fix was never exercised by a trainer. The new failure is isolated to prelaunch request-bound path validation: v4 repo root plus v3 base authority is invalid by contract. v11 artifacts must remain frozen and a fresh namespace is required."

- timestamp: 2026-08-26
  observation: "Before v12 creation, source-runtime-v12, transfer-root-v5, phobert-work-v12, packager, controller, and harness were all absent; no related process was live, the shared lease was unlocked, and v11 controller/request hashes remained bd48a7e3.../1521917a...."
  significance: "The v12 namespace is fresh and v11 evidence remains immutable. The v12 packager can stage a physical base copy and compute provenance for its final v5 path before atomic publication."

- timestamp: 2026-08-26
  observation: "The v12 packager validated and published source-runtime-v12 plus transfer-root-v5. Request SHA-256 is f95f20a4..., source archive/inventory remain 0e76ee9f.../f6181c8f... with 28 files, and runtime PhoBERT remains tested SHA 3b41b29e.... The physical canonical v5 base copy has content SHA 7f841230..., final-path SHA 500361fa..., and newly sealed manifest SHA da2fbf3a...."
  significance: "The v12 request, source, input, base path, and provenance now form one validated repo-root authority; completed v3 bytes are reused by physical copy without changing v3 or failed v11."

- timestamp: 2026-08-26
  observation: "The v12 controller parses with zero errors and SHA-256 809e987c.... Its CPU-only harness passes frozen v9 failure, v12 fresh arguments, and resume canonicalization; it explicitly requires request/input/base all under transfer-root-v5 and rejects a v3 base argument."
  significance: "The controller-level recurrence guard prevents the exact cross-root v11 path configuration before any process launch."

- timestamp: 2026-08-26
  observation: "An independent source-runtime-v12 doctor using only transfer-root-v5 paths exited 0. It verified request, input, base content SHA 7f841230..., and base manifest SHA da2fbf3a..., reported CUDA available with Transformers 5.9.0, and explicitly reported model_acquisition_performed=false and training_performed=false."
  significance: "The exact v11 doctor failure is eliminated before controller launch, without network/model acquisition, Qwen execution, telemetry, or training."

- timestamp: 2026-08-26
  observation: "The v12 non-GPU prelaunch gate passed: read-only controller 809e987c..., request f95f20a4..., source 0e76ee9f.../f6181c8f..., input 12136f9a..., base manifest da2fbf3a... with expected content/path hashes, Qwen evidence ce493f05..., and GGUF 457f6f92... all match. All 28 runtime files match/read-only; v12 work/final/controller/cache targets are absent; no related/prior PID is live; lease is unlocked."
  significance: "Every non-GPU v12 safety and authority gate passes after the independent doctor; only the spaced GPU samples remain before launch."

- timestamp: 2026-08-26
  observation: "Three v12 GPU/process samples at 19:01:53Z, 19:02:10Z, and 19:02:26Z each reported 0 MiB and zero related processes."
  significance: "The final spaced low-VRAM/no-trainer gate passes and authorizes exactly one v12 launch, subject to one immediate atomic repeat."

- timestamp: 2026-08-26
  observation: "The immediate atomic recheck found v12 controller hash/read-only state unchanged, every v12 mutable target absent, zero related processes, unlocked lease, and 0 MiB GPU; exactly one hidden v12 controller launched as PID 22176 at 19:02:50Z (FILETIME 134321581708874442)."
  significance: "The second recovery is fresh, exactly-once, and bound to controller SHA 809e987c... after an independently passing doctor."

- timestamp: 2026-08-26
  observation: "The v12 controller identity/lease were confirmed. It passed Qwen/GGUF, its internal three 0-MiB samples, repeated fresh/runtime gates, and phobert-doctor exit 0. It then started telemetry PID 20940 and exactly one fresh trainer PID 6212 as a direct child with v5 request/input/base plus v12 run/work arguments; trainer stderr was empty at first poll."
  significance: "v12 has crossed the v11 canonical-base failure and the original v9 empty-path boundary. The live trainer creation also reaches the tested source where TrainingArguments compatibility is applied; continued progress must prove it survives construction."

- timestamp: 2026-08-26
  observation: "Telemetry PID 20940 is bound to creation FILETIME 134321582524721564 and trainer PID 6212 to FILETIME 134321582555173654 with parent PID 22176. Append-only v12 events reached optimizer step 150 with train logs and evaluation; peak allocated/reserved GPU bytes are 3,005,169,152/3,609,198,592, and the prior save_safetensors exception is absent."
  significance: "The signature-aware TrainingArguments fix is exercised successfully in the real Transformers 5.9.0 GPU runtime, not merely unit-tested; training has completed nearly half its controlled steps."

- timestamp: 2026-08-26
  observation: "The v12 run reached optimizer step 312/312, safety gate passed with macro-F1 0.9815140779573065, emitted terminal run_end completed=true, and the trainer exited 0. The first independent run-evidence verification also exited 0; controller PID 22176 and telemetry PID 20940 remain correctly identified while render-phobert-graphs runs."
  significance: "The production GPU path has now passed both the Transformers 5.9.0 TrainingArguments boundary and controlled training completion. Only controller-owned graph/telemetry sealing and final process/lease cleanup remain."

- timestamp: 2026-08-26
  observation: "render-phobert-graphs exited 0, the controller's second post-render run-evidence verification exited 0, and it logged that Qwen evidence/GGUF and full local PhoBERT evidence are verified. Trainer/render/verifier children are gone; only the exact controller PID 22176 and its telemetry child PID 20940 remain during cleanup."
  significance: "All model artifacts and graphs are independently verified. The only remaining acceptance boundary is the controller's controlled telemetry shutdown/seal and terminal lease/process cleanup."

- timestamp: 2026-08-26
  observation: "At 19:08:01Z the v12 controller recorded `PhoBERT telemetry process failed controlled stop within 30 seconds: pid=20940`, terminal_status=failed, and released its lease. A subsequent exact PID check found controller 22176, telemetry 20940, and trainer 6212 all absent and the lease unlocked, but no telemetry summary or verification receipt exists."
  significance: "Model training, artifact verification, and graphs succeeded; the remaining defect is isolated to telemetry controlled-stop/sealing. The telemetry process exited after the controller's timeout without external intervention, so v12 must stay preserved and the stop handshake must be diagnosed before any fresh recovery."

- timestamp: 2026-08-26
  observation: "Frozen v12 writes and flushes exactly `telemetry-phobert-v12.stop.json`, the same path UTF-8/Base64-embedded into its wrapper. The durable receipt was created at 19:07:31.479Z, but the telemetry CSV continued receiving 10-second samples through 19:07:51 while stdout/stderr stayed empty; at 30 seconds the controller's own timeout branch force-stopped the still-identical PID."
  significance: "A controller/wrapper path mismatch is contradicted by construction and durable evidence. The remaining falsifiable mechanism is that the wrapper reached or attempted synchronous pipeline cancellation but did not complete; an instrumented isolated wrapper can distinguish stop-file observation from Stop() blocking."

- timestamp: 2026-08-26
  observation: "The preserved v12 CSV SHA-256 is 9fa8ffcf..., 4,383 bytes, with 21 rows and the exact 15 expected headers. Fixed comma-decimal parsing yields strictly increasing timestamps, maximum adjacent gap 11.707361 seconds, maximum elapsed-vs-timestamp delta 0.001692 seconds, sampler/first-sample startup delays 0.333459/1.678768 seconds, two nonempty Python-PID samples, and peak VRAM 3,666 MiB."
  significance: "Raw telemetry coverage is internally consistent and complete enough to seal without resampling. It can be recovered byte-for-byte by an explicit legacy decoder rather than rewriting the CSV."

- timestamp: 2026-08-26
  observation: "Every elapsed_seconds value is producer-localized with a comma decimal (`1,347` through `218,388`); v12's InvariantCulture/Float parser rejects all 21. The last sample is 19.715961 seconds after the durable stop request but 10.382922 seconds before the logged force-timeout failure."
  significance: "Even a clean cancellation would have reached a deterministic seal-parser failure. After the actual timeout, v12's clean-exit and no-post-stop-sample rules also cannot truthfully be satisfied; a fresh repair schema must preserve and label both facts."

- timestamp: 2026-08-26
  observation: "Frozen terminal identities are controller 809e987c..., chain log a9fdc09d..., CSV 9fa8ffcf..., stop receipt c2d35497..., empty stderr e3b0c442..., run evidence 48907892..., request f95f20a4..., and base manifest da2fbf3a.... Run evidence status is complete, selected checkpoint step 100 passed safety, and its graph artifacts are included."
  significance: "A seal-only v13 can bind all model/graph/telemetry/controller authorities without accessing any reserved split or launching any process."

- timestamp: 2026-08-26
  observation: "The v13 seal-only regression reached RED because its target `seal-phase40-phobert-v12-telemetry-v13.ps1` does not exist. The fixture already contains legacy comma decimals, bounded post-stop samples, verified model/graph log lines, exact hashes, absent PIDs, and an unlockable lease."
  significance: "The regression is positioned before implementation and will exercise the intended recovery contract rather than any trainer or telemetry launch path."

- timestamp: 2026-08-26
  observation: "After implementation and two test-harness false-positive corrections, the v13 seal-only regression passes check-only, fresh seal/readback, existing-target rejection, mixed-decimal rejection, wrong-hash rejection, and static no-process-launch/no-split-boundary scenarios. The production repair parses with zero errors."
  significance: "The repair accepts only the explicitly modeled legacy/forced-timeout evidence class and cannot invoke a trainer, telemetry sampler, Qwen, or Python. Causal source mutation remains before production check-only."

- timestamp: 2026-08-26
  observation: "Two source mutants are killed: removing the comma-to-dot legacy decode fails at row 0 with elapsed delta 999 seconds, and changing the summary to claim telemetry exit-code verification fails summary readback. The unmodified baseline passes all six scenarios again."
  significance: "The regression is causally sensitive to both evidence decoding and the requirement not to invent a clean telemetry exit; production check-only can proceed after source sealing and exact gates."

- timestamp: 2026-08-26
  observation: "The tested v13 repair source is read-only with SHA-256 70d165f0.... Both distinct production outputs remain absent and controller/telemetry/trainer PIDs 22176/20940/6212 are absent. Production check-only passed all internal hash, identity, process, lease, chain-log, run-evidence, and telemetry checks with 21 samples."
  significance: "The exact production evidence matches the synthetic acceptance class without writing anything. One fresh seal-only invocation is now authorized by the existing recovery scope."

- timestamp: 2026-08-26
  observation: "After an immediate repeat of source/fresh-target/PID gates, the repair ran exactly once and sealed `system-telemetry-summary-phobert-v12-repair-v13.json` SHA-256 8063eedc... plus its verification receipt SHA-256 65e09763..., reporting 21 samples and repair source SHA-256 70d165f0...."
  significance: "The missing telemetry evidence is now represented by distinct v13 artifacts without modifying v12 inputs or launching any process. Independent readback and regression reconfirmation remain before acceptance."

- timestamp: 2026-08-26
  observation: "Independent readback verified both v13 hashes/read-only attributes and every truth field: run/coverage complete, shutdown forced_after_controller_timeout, clean exit not claimed, 21 samples, maximum gap 11.707361 seconds, elapsed delta 0.001692 seconds, final sample 19.715961 seconds after stop. All v9-v12 controller/raw/run hashes remain exact; related PIDs are absent and lease is unlocked."
  significance: "The production seal is internally and externally verified while the failed v12 summary path remains absent. Only post-production regression reconfirmation remains before the guardrail verdict."

- timestamp: 2026-08-26
  observation: "Post-production verification passes: both v13 source mutants remain killed and baseline is GREEN; the complete PhoBERT module passes 33 tests in 5.97 seconds; both changed Python files compile; and the v12 CPU-only controller harness passes all three scenarios."
  significance: "Targeted, adjacent, mutation, syntax, controller, real-Transformers, and immutable-artifact signals all accept the combined fix/recovery."

- timestamp: 2026-08-26
  observation: "Git status shows the pre-existing `.gitignore` modification still present and untouched, the two intended tracked Python changes, and exact untracked v10-v13 recovery/debug artifacts. No commit has been created."
  significance: "A later commit must stage explicit coordinated paths only and exclude `.gitignore`; human verification is the remaining workflow checkpoint."

## Eliminated

- hypothesis: "Synchronous System.Management.Automation.PowerShell.Stop() inherently blocks for an asynchronously invoked infinite sampler."
  evidence: "The isolated instrumented wrapper observed its stop file, returned from Stop(), wrote the post-Stop marker, and exited cleanly after one sample; the diagnostic intentionally failed because the predicted block did not occur."
  timestamp: 2026-08-26

- hypothesis: "A Phase-40-specific native/CIM operation deterministically prevents PowerShell.Stop() from cancelling the frozen telemetry script."
  evidence: "With corrected path quoting, the byte-identical frozen sampler produced two real samples, observed the stop marker, returned from Stop(), wrote the post-Stop marker, and exited cleanly in the bounded isolated test. The v12 failure is therefore timing/runtime-dependent rather than an always-failing sampler operation."
  timestamp: 2026-08-26

## Resolution

root_cause:
  - "PowerShell coerces omitted `[string] ResumeFromCheckpoint = $null` to an empty string; v9's null-only guard therefore called `GetFullPath('')` before starting a fresh trainer."
  - "After that guard was fixed, PhoBERT passed removed `save_safetensors` directly to installed Transformers 5.9.0; unlike the generic training path, this constructor call had no signature-aware compatibility seam."
  - "v11 declared transfer-root-v4 as the request repo but passed a transfer-root-v3 base snapshot; request-bound canonical-path validation correctly rejected the cross-root base."
  - "v12 training completed, but its telemetry sampler was an unconditional infinite loop terminated only by timing-dependent asynchronous `PowerShell.Stop()`; the real stop missed 30 seconds and was force-terminated. Independently, the producer serialized all elapsed values with comma decimals while the v12 seal parser required invariant decimals, so v12 could never seal those rows truthfully."
fix:
  - "Preserved v9 byte-for-byte and created fresh v10 with an `IsNullOrEmpty` checkpoint guard and attempt-specific paths."
  - "Added `_build_phobert_training_arguments`, which signature-filters strict factories while preserving all options for `**kwargs` factories; retained Transformers 5.9.0."
  - "Created fresh v12 request/runtime/controller authority with a physical canonical base copy and path-bound resealed provenance under transfer-root-v5; preserved v10/v11 evidence."
  - "Completed the exactly-once v12 GPU run (312/312) and created a distinct no-launch v13 seal-only repair. It preserves the raw CSV, validates fixed comma-decimal elapsed values against independent timestamps, records the forced timeout without inventing exit code 0, and emits read-only summary/verification artifacts."
oracle_type: "derived: controller/request/process/telemetry contracts plus immutable hash and timestamp relations"
verification:
  original_reproduction:
    result: pass
    evidence: "Frozen v9 CPU harness reproduces the exact empty GetFullPath call; strict Transformers-5 test reproduces the exact save_safetensors TypeError."
  target_tests:
    result: pass
    suites:
      - "v12 CPU-only controller harness: 3/3 scenarios"
      - "v13 seal-only regression: 6/6 positive/negative scenarios"
  mutation_check:
    result: pass
    mutants_killed:
      - "TrainingArguments pass-all-kwargs mutant: exact save_safetensors TypeError"
      - "v13 comma-decoder mutant: elapsed delta 999 seconds"
      - "v13 false-clean-exit mutant: summary readback mismatch"
  no_op_deletion:
    result: pass
    deletion_justified_by_rca: false
    note: "Fixes are additive/fresh-only; no failed evidence was deleted or overwritten."
  adjacent_tests:
    result: pass
    suites:
      - "tests/model_adaptation/test_phase40_phobert.py: 33 passed in 5.97s"
      - "changed Python files compile"
  real_environment:
    result: pass
    evidence: "Installed Transformers 5.9.0 real GPU run completed 312/312, selected safety-passing step 100, trainer/run verification/graph rendering all exited 0."
  telemetry_repair:
    result: pass
    repair_source_sha256: "70d165f02e192db9b874ce69afd3f0a3c4b3eef2edc357495fe7a889cb09f8f7"
    summary_sha256: "8063eedc43ad0ce0663394dab09dfbfbced3206e2426e43766e2fdb6c4b08adf"
    verification_receipt_sha256: "65e09763d182565c9e32d8020110056bdc5a633e0b944b82567fcbc209f1591d"
    truth: "run/coverage complete; shutdown forced_after_controller_timeout; clean exit not claimed"
  process_safety:
    result: pass
    evidence: "Controller/telemetry/trainer and related processes absent; shared lease unlocked; no Qwen or trainer rerun; v13 launched no process."
  preservation:
    result: pass
    v9_sha256: "63f47598fe81749b961ca7c5f056fe4e63925f2ad93f94f9beabafd047246b26"
    v10_sha256: "547ea544907f3cc0b2219daff90e51e276827c2dc165bfecc6b9e4af2fa65289"
    v11_sha256: "bd48a7e3300f427270e9058bc9003a186f36fe2a9c92a2cd4d84708a83fc9b01"
    v12_sha256: "809e987c61bb7fd20f6ca4cbab62dccb4c470b5a052776fef0ec8c6d0df23dde"
    unrelated_gitignore_untouched: true
  guardrail_verdict: accepted
files_changed:
  - "src/model_adaptation/phobert_training.py"
  - "tests/model_adaptation/test_phase40_phobert.py"
  - ".planning/spikes/001-training-window-readiness/phase40-qwen-to-phobert-chain-v10.ps1"
  - ".planning/spikes/001-training-window-readiness/test-phase40-qwen-to-phobert-chain-v10.ps1"
  - ".planning/spikes/001-training-window-readiness/prepare-phase40-phobert-v11.py"
  - ".planning/spikes/001-training-window-readiness/phase40-qwen-to-phobert-chain-v11.ps1"
  - ".planning/spikes/001-training-window-readiness/test-phase40-qwen-to-phobert-chain-v11.ps1"
  - ".planning/spikes/001-training-window-readiness/prepare-phase40-phobert-v12.py"
  - ".planning/spikes/001-training-window-readiness/phase40-qwen-to-phobert-chain-v12.ps1"
  - ".planning/spikes/001-training-window-readiness/test-phase40-qwen-to-phobert-chain-v12.ps1"
  - ".planning/spikes/001-training-window-readiness/test-phase40-telemetry-stop-blocking-repro.ps1"
  - ".planning/spikes/001-training-window-readiness/seal-phase40-phobert-v12-telemetry-v13.ps1"
  - ".planning/spikes/001-training-window-readiness/test-seal-phase40-phobert-v12-telemetry-v13.ps1"
  - ".planning/spikes/001-training-window-readiness/test-seal-phase40-phobert-v12-telemetry-v13-mutations.ps1"
  - ".planning/debug/phobert-launch-empty-path.md"

## Prevention

why_not_caught: "No end-to-end prelaunch gate exercised PowerShell's omitted typed-string coercion, the installed Transformers 5 constructor signature, request/base canonical-root binding, and locale-dependent telemetry serialization as one chain. Unit fakes accepted arbitrary TrainingArguments keywords, while telemetry shutdown/sealing was only exercised in short synthetic runs."
recurrence_guard: "`tests/model_adaptation/test_phase40_phobert.py::test_training_arguments_omit_removed_transformers_v5_keyword` and its kwargs neighbor protect the API seam; v10/v12 CPU controller harnesses protect empty checkpoint and canonical base arguments; `test-seal-phase40-phobert-v12-telemetry-v13.ps1` plus its mutation harness protect legacy locale decoding, forced-timeout truth, fresh outputs, exact hashes, and the no-launch boundary."
semantic_index: "skipped because project config has MemPalace disabled; `.planning/debug/knowledge-base.md` is the durable fallback"

five_whys:
  code_branch:
    - "The fresh launch failed because an omitted typed PowerShell string became empty rather than null."
    - "The controller checked only null before canonicalizing the path."
    - "The harness had not covered the exact omitted-parameter binding behavior at that call boundary."
    - "After launch, PhoBERT also passed a version-removed TrainingArguments keyword directly."
    - "The PhoBERT path lacked the signature-aware compatibility seam already used by generic training."
  config_contract_branch:
    - "v11 failed because its request repo and base snapshot came from different roots."
    - "Base provenance binds both bytes and the absolute canonical location."
    - "The first recovery package reused valid bytes but did not reproduce the request-bound path authority."
    - "v12 corrected this with a physical canonical copy and newly sealed path provenance."
  environment_serialization_branch:
    - "v12 telemetry could not seal after training because shutdown depended on timing-sensitive cancellation of an unconditional infinite sampler."
    - "The real cancellation exceeded 30 seconds, so the controller force-stopped it."
    - "Even with a clean stop, the producer's current culture wrote comma-decimal elapsed values while the verifier required invariant decimals."
    - "The v13 repair preserves the raw bytes, validates those values against independent timestamps, and explicitly records that a clean exit was not observed."
