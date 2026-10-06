# Training and evaluation boundaries

This page separates the maintained application interfaces from the retained code
that produced the frozen experiment artifacts.

## Maintained call surface

```text
src/modeling/training.py
  -> src/modeling/legacy_adapters.py
     -> retained Qwen and PhoBERT training implementations

src/modeling/evaluation.py
  -> src/modeling/legacy_adapters.py
     -> retained evaluation implementation

src/modeling/evidence.py
  -> read-only result and provenance contracts
```

New application code should call the `src.modeling` services. The
`src.model_adaptation` package preserves experiment-era implementations and command
compatibility; its phase-numbered names are reproducibility labels, not the current
domain vocabulary.

## Model roles

- Qwen3-4B-Instruct-2507 was adapted with NF4 QLoRA and emits the richer structured
  response contract. Its selected adapter was merged and packaged as a Q8_0 GGUF
  artifact for the local runtime.
- PhoBERT was trained as a full four-logit classification-head model. It is a native
  classifier bundle, not a GGUF artifact, and it does not natively generate Qwen's
  evidence and recommendation fields.

## Evaluation authority

Development validation used the 219-row validation partition for checkpoint selection
and descriptive comparison. Both frozen models were then evaluated in one terminal
model-evaluation pass over the same 220-row cohort. That terminal result did not cause
retraining, repair, threshold changes, checkpoint reselection, or a retry.

The terminal files are sealed from routine work. Historical integrity regressions did
parse, stat, and hash them before the model run, so project prose must not say that the
partition was literally untouched or had zero prior filesystem access. Those checks
did not display rows to a human, invoke a model or external service, or influence a
model action.

## Claim boundary

The runs use one training seed. Reported differences are descriptive: no variance
estimate, t-test, statistical-significance claim, cross-family speed ranking, or
stable-winner claim is supported. Deployment fitting was deliberately deferred.
The later source refactor preserved interfaces and provenance; it did not generate or
change the frozen metrics.
