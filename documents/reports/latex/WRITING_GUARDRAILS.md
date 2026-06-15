# Writing Guardrails

## Working template rule

- The current `documents/reports/latex/main.tex` structure is the working thesis template.
- Phase 8 does not create a parallel manuscript tree.
- Later supervisor formatting changes may adjust layout, but they should not reopen the chapter architecture.

## Evidence boundary for Chapter 5

- Chapter 5 must stay grounded in tracked manifests, saved evaluation artifacts, and repo-visible closeout notes.
- Off-repo training logs or hardware screenshots are appendix-only evidence unless they are copied into a tracked local note first.
- In paragraphs, describe the final result as not release-ready under the project's safety gate.
- Keep the literal `BLOCK` label for tables, appendix notes, or file names rather than ordinary thesis prose.

## Tone rules

- Prefer short declarative sentences.
- Prefer measured verbs such as `shows`, `indicates`, `suggests`, `records`, and `supports`.
- Avoid AI-like stock phrasing and generic transition filler.
- Avoid inflated claims unless the evidence directly supports them.
- Do not write `state-of-the-art`, `rapidly evolving landscape`, `revolutionary`, or similar promotional language without direct proof.

## Process-language filter

- Do not mention GSD, roadmap language, internal phases, `STATE.md`, or UAT inside the thesis prose.
- Replace internal process wording with thesis-facing wording such as `closeout evidence`, `saved evaluation artifact`, `implementation record`, or `user-facing validation`.
- Do not describe the thesis as a report draft, current report, or next writing pass.

## Claim discipline

- Every strong claim should point to one named manifest, document, table, command output, or verified external source.
- Keep class-level evaluation claims tied to the actual support counts.
- If a result is mixed, say so directly.
- If a limit is central to the final outcome, name it explicitly.

## Citation boundary

- Phase 8 seeds citation targets and starter BibTeX entries only.
- In-text citation insertion is deferred to Phase 9.
- Final bibliography rendering is deferred to Phase 9.
- Do not imply that the citation pass is already finished.

## Terminology replacements

- `repository` -> `implemented system` or `project codebase`
- `project state file` -> `closeout record` or `saved artifact`
- `planning artifacts` -> `tracked records` or `saved documents`
- `internal workflow` -> `implementation workflow`
- `blocked verdict` -> `not release-ready` in prose, with the literal label kept outside ordinary paragraphs
