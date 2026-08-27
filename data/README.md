# Dataset artifact layout

This document describes the governed artifact flow without inspecting or changing
the sealed records.

```text
retained root seeds
  -> generated candidates
  -> schema and span validation
  -> lexical deduplication
  -> label + seed_id grouping
  -> whole-group train / validation / test assignment
  -> semantic cross-split cleanup
  -> class-coverage and concentration checks
  -> versioned SHA-256 manifest
```

## Leakage-control contract

- `seed_id` identifies one independent root scenario, not one generated row.
- Variants of the same root scenario retain the same `seed_id`.
- Every seed belongs to exactly one class, and its entire group is assigned to one
  split only.
- Within each class, seed groups are deterministically hash-ordered and allocated as
  whole groups toward the 80/10/10 train/validation/test targets.
- A class with fewer than three independent seed groups fails closed because it
  cannot populate all three splits without leakage.
- Post-split deduplication removes validation/test collisions before class coverage
  is checked again.

The terminal test split is a sealed evaluation authority. Routine cleanup,
documentation, training, and validation work must not enumerate or read its records.

## Promoted snapshot

These counts are copied from the final Phase 39 governance report; this documentation
pass did not reopen the split files.

| Class | Train | Validation | Terminal evaluation | Total |
| --- | ---: | ---: | ---: | ---: |
| Bank impersonation | 595 | 76 | 70 | 741 |
| Benign | 517 | 72 | 66 | 655 |
| Task scam | 306 | 49 | 49 | 404 |
| Zalo social engineering | 240 | 22 | 35 | 297 |
| **Total** | **1,658** | **219** | **220** | **2,097** |

Whole-seed split disjointness passed. The largest retained seed group contains 167
rows, or 7.9638% of the corpus, below the declared 8% concentration cap.
