# Source map

Use this page as the code-review entry point.

| Area | Responsibility |
| --- | --- |
| `runtime/` | Installed CLI, local demo, analyzers, rendering, and orchestration |
| `data_pipeline/core/` | Record contracts, text normalization, and group-safe splitting |
| `data_pipeline/workflows.py` | Optional collection, generation, and publication orchestration |
| `modeling/` | Maintained training, inference, evaluation, and evidence interfaces |
| `source_archiving/` | Provenance archive contracts and implementation |
| `model_adaptation/` | Retained experiment implementation and compatibility adapters |

The maintained training path is intentionally layered:

```text
src/modeling/training.py
  -> src/modeling/legacy_adapters.py
     -> retained src/model_adaptation implementation
```

Phase-numbered names under `model_adaptation/` preserve reproducibility and older
command contracts. New application code should depend on `runtime/`, `modeling/`, or
the data core instead of importing those historical implementations directly.

See [`docs/architecture/training-evaluation.md`](../docs/architecture/training-evaluation.md)
for the maintained-port, frozen-evidence, and terminal-evaluation boundaries.
