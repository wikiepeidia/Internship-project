# Phase 40 Fresh-Launch Readiness Result

**Checked:** 2026-08-25T12:22:11.641639Z

**Verdict:** PASS for the machine-bound fresh PhoBERT launch; automated resume excluded

**Checker:** `check_readiness.py --repo-root .`

The retained v8 run passed 20/20 blocking checks. It opened only the named Phase 40 request, amendment, PhoBERT configuration, controller/preflight/parse evidence, pinned telemetry script, source identities, and PhoBERT base-model provenance. The checker did not discover, stat, hash, or open the reserved evaluation split and did not start a GPU process.

Bound identities:

- run request: `2512dbe6d7c5b8c16141ebdbdc848382e56b3a5737e8aeea51d7fb89447c643a`
- two-model amendment: `9a19fdb0ac13855abe06d957129764651c4e49b8c75e44849c213475bbf5bbaa`
- comparison-finalizer source tree: `098d39b62867a017574f0e98a2768e85696741c3cf559e81ddcf2dd98522b026` (41 files)
- PhoBERT controls: `f6bedc5ddc04ca50ba5f737aaf1003b3e27dac676d8082eba33d6cecd97df629`
- source archive: `eae64f17383d749a7759391d766ad59b337d35155ae89744adeaba8631e71a66`
- source inventory: `5903dd5d68881916424e0b529760c3e8810b89a7c207aa714f13171fccf02a3d`
- PhoBERT provenance: `b94e490259cdb42f0fa6c177421519bb4a3944d2693e249bcf8e358cb92dc3f6`
- controller v8: `473fb1ae8c4ed154bbf918232ef79fbb04cb4cbeca9b2555fe7adb662812c9e4`
- armed source-preflight receipt: `5fe13c8c3ef3cd6ebb372d0c6e5616d7dfaee561c2ef1082918158723f99516d`
- PowerShell parse receipt: `2b4c9bba6c41471b4510567a53ba530de2e9910fa72c965ed4410d9fb5c068f5`
- pinned telemetry script: `1bc33f3726b57297a3cc5a69b36831bbd602edac680ba329224b14cf06231c70`

Exact live identities at the retained check were Qwen trainer PID 19772 / creation FILETIME `134321016774482304`, Qwen supervisor PID 1576 / `134321017671588653`, and chain controller PID 13180 / `134321337277925629`; each matched PID, creation time, and executable image. Controller v8 holds the fixed lease with `FileShare.None` (exclusive-open probe returned Windows sharing violation 32), binds a clean 28-file `source-runtime-v8`, proves its invocation-scoped bytecode-cache root absent, permits zero automated resume attempts, and has empty stdout/stderr captures.

The controller revalidates the full fresh-target set at arm time, after the Qwen wait before doctor, and again after doctor immediately before creating work. It fails on a nonzero training exit before evidence verification, and its terminal telemetry seal rejects missing coverage, gaps over 30 seconds, clock drift, malformed PID sets, early/nonzero exits, stderr, or an unverified summary.

This receipt is not proof that future training succeeds. It proves only that the fresh-launch chain was correctly armed at the recorded time. Any interrupted fresh PhoBERT run is terminal evidence and must be preserved and reported rather than silently resumed.
