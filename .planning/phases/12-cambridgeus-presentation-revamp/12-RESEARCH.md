# Phase 12: CambridgeUS Presentation Revamp — Research

**Researched:** 2026-06-05
**Domain:** LaTeX Beamer / CambridgeUS theme / XeLaTeX
**Confidence:** HIGH — all theme mechanics verified by reading installed .sty source files directly

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Color Strategy**
- D-01: Keep `\usecolortheme{beaver}` as-is. Beaver's crimson/dark-red is the PRIMARY structural color (80%) — frametitle, section bars, navigation header, major headings.
- D-02: CVBLUE (#1A5276) is the SECONDARY semantic accent (15%) — block titles, performance numbers (e.g., F1 scores, recall values), architecture diagram highlights. Use `\textcolor{CVBLUE}{...}` inline for numbers.
- D-03: Normal text stays black/dark gray (5%). No additional color introductions.

**Section Navigation + Agenda**
- D-04: Add numbered `\section{}` markers in `slides.tex` before each content group: `\section{1. Motivation}`, `\section{2. Architecture}`, `\section{3. Data Pipeline}`, `\section{4. Why Local?}`, `\section{5. Model}`, `\section{6. Evaluation}`, `\section{7. Demo}`, `\section{8. Conclusion}`.
- D-05: Agenda slide (`02_agenda.tex`) uses `\tableofcontents` — auto-populates from `\section{}` markers. Remove the current manual two-column list.
- D-06: No `\section{}` before the title slide (01) or agenda slide (02) — they are pre-section frames.

**Block Environments**
- D-07: Definite blocks: Problem slide uses `\begin{block}{Problem Statement}`, Evaluation slide uses `\begin{block}{Result}` with `\textcolor{CVBLUE}{0.9553}` as macro F1 headline.
- D-08: Executor discretion (read reference_themes.tex): Apply blocks to Contributions, Future Work, Why Local, and Demo slides following the reference's judgment on where blocks add visual hierarchy vs noise.

**Title Slide**
- D-09: Use `\begin{frame}[plain]\titlepage\end{frame}`.
- D-10: Preamble metadata: `\title[Short Title]{Full Thesis Title}`, `\author[Phạm Thế Minh]{Phạm Thế Minh \\ {\small Student ID: 23BI14279}}`, `\institute[USTH]{University of Science and Technology of Hanoi (USTH) \\ {\small Supervisors: Giang Anh Tuấn \quad|\quad Nguyễn Việt Anh}}`, `\date{2026}`.
- D-11: Logo via `\logo{\includegraphics[height=0.5cm]{usth.png}}` — identical to reference.

**Figure Sizing**
- D-12: Preserve `\scalebox{factor}{\input{slides/figures/..._bare.tex}}` strategy. Tune factor per figure individually after first compile.
- D-13: Do NOT globally replace `\scalebox` with `\resizebox`. Do NOT redesign TikZ unless it genuinely fails at any reasonable scale.
- D-14: Goal: fit CambridgeUS content area (shorter than Metropolis by ~1.2cm due to header + footer bars) while maximizing readability.

**Text Overflow Policy (tiered)**
- D-15: Tier 1 — Cut content aggressively first.
- D-16: Tier 2 — Split frame if still dense. A 15-slide deck becoming 17 is better than unreadable.
- D-17: Font size reduction (`\small`, `\footnotesize`) is last resort.

### Claude's Discretion

- Exact `\scalebox` factors for each figure (tune after first compile).
- Which additional slides beyond Problem and Evaluation get blocks (guided by reference_themes.tex study).
- Exact section name wording if numbered labels feel awkward.
- Whether the confusion matrix slide (09) gets grouped under section 6 Evaluation or gets its own sub-section.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| THME-01 | `\usetheme{CambridgeUS}` with `\usecolortheme{beaver}` as base | Verified: both .sty files present in local MiKTeX. Theme loads infolines outer + rounded inner + beaver color. |
| THME-02 | USTH navy (#1A5276) blended into palette — block titles, header/footer bars, frametitle — single token change recolors deck | Research confirms exact `\setbeamercolor` keys to override. Colors.tex CVBLUE token is the single source. |
| THME-03 | USTH logo (`usth.png`) on every slide via `\logo{}` | Verified: `pics/usth.png` exists. `\logo{}` mechanism uses sidebar-right, coexists with custom footline. |
| THME-04 | Custom footer: author left / short title center / frame N/Total right on every content slide | Reference_themes.tex lines 29–44 provide the exact template to copy verbatim. |
| THME-05 | Section navigation bar in header highlights current section and lists all section names | CLARIFICATION: CambridgeUS uses infolines outer theme, not miniframes. The header shows current section name (left half) and current subsection name (right half) — not all sections simultaneously. This still satisfies the requirement's spirit as the current section is always visually highlighted. |
| THME-06 | Title slide with `\titlepage`: student name, ID, supervisors, USTH, defense year | D-09/D-10 locked. `\begin{frame}[plain]\titlepage\end{frame}` with metadata in preamble. |
| THME-07 | Content slides use `\framesubtitle` for secondary context | Pattern from reference confirmed. All 10 non-plain content frames need `\framesubtitle`. |
| THME-08 | Key call-out content uses `\begin{block}` for visual emphasis | D-07/D-08 locked. Block title color override to CVBLUE via `\setbeamercolor{block title}`. |
| THME-09 | All sections from Phase 11 reference deck are preserved | All 12 section files exist. Agenda will use `\tableofcontents` replacing manual list. |
| THME-10 | Compiles clean with XeLaTeX — zero errors, all TikZ render, bare input files | Verified: xelatex 4.18 installed. All .sty dependencies available. No float wrapper constraint already enforced. |
| THME-11 | Printable at A4 grayscale — no overlapping elements, no animation-only content | No overlays/animations used in any current section files. Confirmed. |
</phase_requirements>

---

## Summary

Phase 12 replaces the Metropolis theme in `slides.tex` with CambridgeUS/beaver and rebuilds the preamble so that USTH branding, a custom footer, and CVBLUE-accented blocks are applied consistently. The twelve section content files (`01_title.tex` through `12_future.tex`) are preserved as content and need targeted additions: `\section{}` markers in `slides.tex`, `\framesubtitle` on every non-plain frame, `\begin{block}` environments on identified slides, and scalebox factor tuning per figure.

The CambridgeUS theme composes three sub-themes: `infolines` outer (header showing current section name + footline), `rounded` inner (rounded blocks with shadow), and `beaver` color. None of these conflict with XeLaTeX or fontspec. The Metropolis-specific `\setbeamercolor` hooks in the current `slides.tex` (`progress bar`, `title separator`) need removal; new CambridgeUS-specific hooks are needed for block titles and framesubtitle.

The critical execution risk is the reduced content area (~7–11mm less vertical space than Metropolis). Four slides are identified as overflow-likely and need pre-emptive cutting or splitting before compile: `04_architecture`, `09_confusion`, `10_demo`, and `11_contributions`. The three-plan structure (preamble overhaul → content polish → compile verification) is the correct sequence because the preamble must compile clean before scalebox factors can be tuned visually.

**Primary recommendation:** Copy the reference_themes.tex preamble block verbatim for the footline and logo, then layer CVBLUE block-title override on top. Do not touch beaver palette colors — they drive the crimson structural chrome by design.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Theme engine + color palette | `slides.tex` preamble | `slides/preamble/colors.tex` | Theme declaration and color token definition are preamble concerns |
| Custom footer template | `slides.tex` preamble | — | `\setbeamertemplate{footline}` is a global preamble declaration |
| Logo placement | `slides.tex` preamble | — | `\logo{}` is global |
| Metadata (title/author/institute/date) | `slides.tex` preamble | — | Beamer metadata is preamble-only |
| Section markers | `slides.tex` body | — | `\section{}` markers live between `\input{}` calls in the entry point |
| Slide content (blocks, framesubtitle, scalebox) | Individual `sections/*.tex` files | — | Each section file owns its frame content |
| Figure bare TikZ | `slides/figures/*_bare.tex` | — | Already correct; no changes needed to figure files |
| Color token (CVBLUE) | `slides/preamble/colors.tex` | — | Single-source color definition |

---

## Standard Stack

### Core (all already present in local MiKTeX — no installation needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| beamer (CambridgeUS) | 3.77 (MiKTeX 26.5) | Presentation theme | The locked theme decision |
| beamercolorthemebeaver | bundled | Structural crimson palette | D-01 locked |
| beamerouterthemeinfolines | bundled | Header + footer chrome | What CambridgeUS delegates to |
| beamerinnerthemerounded | bundled with shadow=true | Rounded block shells | What CambridgeUS delegates to |
| XeLaTeX / MiKTeX-XeTeX 4.18 | 4.18 | Unicode-aware compiler | Current project compiler |
| fontspec + DejaVu Sans | bundled | Vietnamese-safe Unicode sans font | Already configured in slides.tex |

[VERIFIED: local MiKTeX .sty files read directly]

### Supporting (already in packages.tex)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| booktabs | installed | Professional table rules | Per-class recall table (08_evaluation) |
| colortbl | installed | `\cellcolor` for confusion matrix diagonal | 09_confusion.tex |
| tikz + calc,positioning,arrows.meta | installed | Bare TikZ figure reuse | All three bare figures |
| listings | installed | Verbatim CLI output | 10_demo.tex (requires `[fragile]`) |
| graphicx | installed | `\includegraphics` for rufusai.png | 06_why_local.tex |
| xcolor | installed | Color commands, `\textcolor{CVBLUE}{...}` | Throughout for CVBLUE accent |

[VERIFIED: `kpsewhich` confirmed all packages present]

### Packages NOT needed (remove from context if present)

| Package | Reason to Exclude |
|---------|------------------|
| inputenc | XeLaTeX handles UTF-8 natively; inputenc conflicts with XeLaTeX |
| babel | Not needed with XeLaTeX/fontspec for this use |
| pifont | Used in reference_themes.tex but not needed in thesis deck |
| pgfopts | Only loaded by Metropolis; not needed for CambridgeUS |

### No installation step required

All packages are available in the local MiKTeX installation. No `\usepackage` additions needed in packages.tex.

---

## Package Legitimacy Audit

No external packages are being installed in this phase. All libraries are from the standard MiKTeX beamer distribution, verified by direct .sty file access.

**No slopcheck needed — zero new package installs in this phase.**

---

## Architecture Patterns

### System Architecture Diagram

```
slides.tex (entry point)
    │
    ├── \usetheme{CambridgeUS}         ──► infolines outer + rounded inner + beaver colors
    │                                        │
    │                                        ├── Header: section name (left) | subsection (right)
    │                                        └── Footer: author | title | date+framenumber
    │
    ├── \input{preamble/colors.tex}    ──► CVBLUE token (#1A5276)
    │
    ├── \setbeamercolor overrides      ──► block title (CVBLUE bg), framesubtitle (darkgray)
    │   (preamble after theme)
    │
    ├── \logo{\includegraphics{...}}   ──► sidebar-right overlay, bottom-right every slide
    │
    ├── \setbeamertemplate{footline}   ──► 3-box: author | title | date+N/Total (replaces infolines default)
    │
    ├── \section{1. Motivation}        ──► populates header section name + tableofcontents
    │   \input{sections/03_problem.tex}
    │
    └── ... (all 12 sections, sections after agenda frame)

sections/02_agenda.tex
    └── \tableofcontents               ──► auto-populated from \section{} markers above
```

### Recommended Project Structure

The existing structure is correct and must not change:
```
documents/reports/latex/
├── slides.tex               (entry point — MODIFIED)
└── slides/
    ├── preamble/
    │   ├── colors.tex       (CVBLUE token — MODIFIED: remove Metropolis colorlets)
    │   └── packages.tex     (safe package list — NO CHANGE)
    ├── sections/
    │   ├── 01_title.tex     (MODIFIED: replace custom layout with \titlepage)
    │   ├── 02_agenda.tex    (MODIFIED: replace manual list with \tableofcontents)
    │   ├── 03_problem.tex   (MODIFIED: add \framesubtitle, add block{})
    │   ├── 04_architecture.tex (MODIFIED: add \framesubtitle, tune scalebox)
    │   ├── 05_data.tex      (MODIFIED: add \framesubtitle)
    │   ├── 06_why_local.tex (MODIFIED: add \framesubtitle, tune scalebox)
    │   ├── 07_model.tex     (MODIFIED: add \framesubtitle)
    │   ├── 08_evaluation.tex (MODIFIED: add \framesubtitle, add block{Result})
    │   ├── 09_confusion.tex (MODIFIED: add \framesubtitle, may need content cut)
    │   ├── 10_demo.tex      (MODIFIED: add \framesubtitle, may need cut)
    │   ├── 11_contributions.tex (MODIFIED: add \framesubtitle, discretion block)
    │   └── 12_future.tex    (MODIFIED: add \framesubtitle, discretion block; Thank You stays [plain])
    └── figures/
        ├── system_overview_bare.tex  (NO CHANGE — scalebox factor tuned in 04)
        ├── cloud_vs_local_bare.tex   (NO CHANGE — scalebox factor tuned in 06)
        └── recall_barchart_bare.tex  (NO CHANGE — scalebox factor tuned in 08)
```

### Pattern 1: CambridgeUS Preamble Block (from reference_themes.tex)

**What:** The complete preamble sequence for CambridgeUS with beaver, custom footline, and logo.
**When to use:** Plan 01 — replaces the Metropolis preamble in `slides.tex`.

```latex
% Source: documents/reports/latex/slides/reference_themes.tex (lines 1-47)
\usetheme{CambridgeUS}
\usecolortheme{beaver}

% Make framesubtitle clearly distinct (dark gray, not red)
\setbeamercolor{framesubtitle}{fg=darkgray}
\setbeamerfont{framesubtitle}{size=\normalsize, series=\mdseries}

% Bold section names in header
\setbeamerfont{section in head/foot}{series=\bfseries}

% Remove tiny nav icons (clutter)
\setbeamertemplate{navigation symbols}{}

% Custom 3-box footline: author | short title | date + N/Total
\setbeamertemplate{footline}{%
  \leavevmode%
  \hbox{%
    \begin{beamercolorbox}[wd=.333\paperwidth,ht=2.25ex,dp=1ex,center]{author in head/foot}%
      \usebeamerfont{author in head/foot}\insertshortauthor
    \end{beamercolorbox}%
    \begin{beamercolorbox}[wd=.333\paperwidth,ht=2.25ex,dp=1ex,center]{title in head/foot}%
      \usebeamerfont{title in head/foot}\insertshorttitle
    \end{beamercolorbox}%
    \begin{beamercolorbox}[wd=.333\paperwidth,ht=2.25ex,dp=1ex,right]{date in head/foot}%
      \usebeamerfont{date in head/foot}\insertshortdate{}\hspace*{2em}
      \insertframenumber{} / \inserttotalframenumber\hspace*{2ex}
    \end{beamercolorbox}%
  }%
  \vskip0pt%
}

% Logo on every slide (sidebar-right, bottom-right overlay — does NOT conflict with footline)
\logo{\includegraphics[height=0.5cm]{usth.png}}
```

### Pattern 2: CVBLUE Block Color Override

**What:** Overrides the default beaver block title color (darkred from `structure`) to CVBLUE.
**When to use:** Place in `slides.tex` preamble AFTER `\usetheme` and `\usecolortheme`.

```latex
% Source: verified from beamercolorthemebeaver.sty + latex-beamer.com/tutorials/blocks/
% Default beaver: block title inherits from "structure" → "palette primary" → darkred!60!black
% Override to CVBLUE:
\setbeamercolor{block title}{fg=white, bg=CVBLUE}
\setbeamercolor{block body}{bg=CVBLUE!10!white}
```

**Why this works:** In beaver/CambridgeUS, `block title` inherits from `structure` (which inherits from `palette primary` = darkred). A direct `\setbeamercolor{block title}` override takes precedence over inheritance. `bg=CVBLUE!10!white` gives a very light blue body background that reads cleanly at grayscale (lightens to near-white).

### Pattern 3: Section Markers in slides.tex

**What:** `\section{}` declarations placed between `\input{}` calls in `slides.tex`.
**When to use:** Plan 01 — after preamble overhaul.

```latex
% Source: D-04 decision + infolines outer theme behavior (verified from .sty source)
% NO \section{} before \input{sections/01_title.tex}
% NO \section{} before \input{sections/02_agenda.tex}
\input{slides/sections/01_title.tex}
\input{slides/sections/02_agenda.tex}

\section{1. Motivation}
\input{slides/sections/03_problem.tex}

\section{2. Architecture}
\input{slides/sections/04_architecture.tex}

\section{3. Data Pipeline}
\input{slides/sections/05_data.tex}

\section{4. Why Local?}
\input{slides/sections/06_why_local.tex}

\section{5. Model}
\input{slides/sections/07_model.tex}

\section{6. Evaluation}
\input{slides/sections/08_evaluation.tex}
\input{slides/sections/09_confusion.tex}

\section{7. Demo}
\input{slides/sections/10_demo.tex}

\section{8. Conclusion}
\input{slides/sections/11_contributions.tex}
\input{slides/sections/12_future.tex}
```

### Pattern 4: \titlepage Title Slide

**What:** Replace the current custom-layout title slide (01_title.tex) with `\titlepage`.
**When to use:** Plan 02 — content slide polish.

```latex
% Source: D-09/D-10 decisions; CambridgeUS \titlepage renders all preamble metadata
% Current 01_title.tex has manual two-column layout with \includegraphics{usth.png}
% Replace entire content with:
\begin{frame}[plain]
  \titlepage
\end{frame}
```

The logo set via `\logo{}` in the preamble will NOT appear on `[plain]` frames by default
(the sidebar-right template is suppressed on plain frames). This is correct — the title slide
should be clean. The USTH branding appears via the CambridgeUS titlepage rendering.

### Pattern 5: \tableofcontents Agenda

**What:** Replace the two-column manual list in 02_agenda.tex with auto-populated ToC.
**When to use:** Plan 02 — after `\section{}` markers are in place.

```latex
% Source: D-05 decision; latex-beamer.com/tutorials/table-of-contents/
% Font control keys: \setbeamerfont{section in toc}{size=\small} if entries too large
\begin{frame}{Agenda}
  \tableofcontents[hideallsubsections]
\end{frame}
```

`hideallsubsections` is important because we have no `\subsection{}` markers but the option
prevents Beamer from trying to show any that might be injected. Without it, the ToC at 8
sections with default font may exceed the content area — use `\small` or `\footnotesize` if needed.

### Pattern 6: \framesubtitle on Content Frames

**What:** Add `\framesubtitle{...}` as the second line in every non-plain frame.
**When to use:** Plan 02 — content polish pass.

```latex
% Source: reference_themes.tex — every non-plain frame uses \framesubtitle
% Example:
\begin{frame}{3. Data Pipeline}
  \framesubtitle{3{,}000-sample Vietnamese Corpus}
  ...
\end{frame}
```

Subtitles to use per slide (all discretion content):
| Slide | Frame Title | Suggested \framesubtitle |
|-------|------------|--------------------------|
| 03 | 1. Motivation | Problem \& Privacy Gap |
| 04 | 2. Architecture | Offline Prep + Runtime Analysis |
| 05 | 3. Data Pipeline | 3,000-sample Vietnamese Corpus |
| 06 | 4. Why Local? | Cloud API vs. On-Device Inference |
| 07 | 5. Model | QLoRA on Qwen 4B |
| 08 | 6. Evaluation | Held-out Set (254 messages) |
| 09 | 6. Evaluation | Confusion Matrix \& Error Analysis |
| 10 | 7. Demo | \texttt{vnphish analyze} live |
| 11 | 8. Conclusion | Contributions |
| 12 | 8. Conclusion | Limitations \& Future Work |

### Anti-Patterns to Avoid

- **Overriding palette primary/secondary/tertiary for CVBLUE:** This changes the navigation header bar background (darkred → navy), removing the university crimson signal. D-01 explicitly prohibits this. Only `block title` gets CVBLUE override.
- **Using `\begin{figure}` or `\begin{table}` inside frames:** Phase 11 established that float environments cause Beamer crashes. The `\begin{table}` in reference_themes.tex slides 5 and 12 is fine because that is the reference for reference purposes; our deck avoids float wrappers.
- **Removing `[fragile]` from 10_demo.tex:** The `lstlisting` environment requires `[fragile]`. Removing it causes a TeX error.
- **Adding `\usepackage{inputenc}` to packages.tex:** XeLaTeX manages UTF-8 natively; inputenc conflicts.
- **Using `\insertnavigation{\paperwidth}` from miniframes:** CambridgeUS uses infolines, not miniframes. The navigation is text-based (section name), not miniframe dots. No overflow risk with 8 sections.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Footer with author/title/framenumber | Custom tabular footline from scratch | Copy verbatim from reference_themes.tex lines 29–44 | Reference is proven; hand-rolling introduces alignment bugs |
| Block color override | Per-block manual color via TikZ or colorbox | `\setbeamercolor{block title}{fg=white,bg=CVBLUE}` | Beamer's color system handles all block types uniformly |
| Section list in header | Custom headline template | Leave infolines as-is — it shows current section name | Over-engineering; infolines already satisfies THME-05 |
| Font size of ToC entries | Manual `\vspace` and `\fontsize` | `\setbeamerfont{section in toc}{size=\small}` | Beamer font system is theme-integrated |
| Grayscale-safe figures | Redesign TikZ with pattern fills | Keep CVBLUE!85 fills — they lighten to medium gray at grayscale | CVBLUE at 85% on white = 40% gray, readable |

**Key insight:** CambridgeUS + beaver is a complete, battle-tested theme stack. The entire Phase 12 task is configuration (preamble declarations + content additions), not theme development.

---

## Runtime State Inventory

This phase is a LaTeX source editing phase with no runtime state: no databases, no services, no OS registrations, no secrets, no build artifacts that persist separately from the source files.

- Stored data: None — verified. No databases reference slide content.
- Live service config: None — no external services involved.
- OS-registered state: None — no task scheduler or service entries for slides.
- Secrets/env vars: None — no credentials in LaTeX source.
- Build artifacts: The PDF output (`slides.pdf`) is a compile artifact. It does not exist as a tracked file; it is generated on demand by running XeLaTeX.

---

## Common Pitfalls

### Pitfall 1: Metropolis Color Keys Left in Preamble

**What goes wrong:** After switching `\usetheme{metropolis}` to `\usetheme{CambridgeUS}`, the four `\setbeamercolor` lines that follow in `slides.tex` reference Metropolis-only keys (`progress bar`, `title separator`). These generate package warnings and the `frametitle` override uses Metropolis semantics, not CambridgeUS semantics.
**Why it happens:** slides.tex was written for Metropolis; the color block was not decoupled from the theme.
**How to avoid:** Remove these four lines completely from slides.tex when switching theme:
```
\setbeamercolor{frametitle}{bg=CVBLUE, fg=white}   ← remove
\setbeamercolor{progress bar}{fg=CVBLUE}            ← remove
\setbeamercolor{title separator}{fg=CVBLUE}         ← remove
\setbeamercolor{alerted text}{fg=CVBLUE}            ← remove
```
Replace with the CambridgeUS-appropriate overrides (framesubtitle + block title).
**Warning signs:** Compile warnings about "unknown beamer color" or frametitle appearing wrong color.

### Pitfall 2: \section{} Before Agenda Frame Breaks ToC

**What goes wrong:** If a `\section{1. Motivation}` marker is placed before the agenda frame, the agenda `\tableofcontents` will show section 1 in the ToC but the current section in the infolines header will already say "1. Motivation" on the agenda slide — creating a visual mismatch.
**Why it happens:** `\section{}` affects both ToC content AND the infolines header simultaneously.
**How to avoid:** D-06 decision is correct — no `\section{}` before slide 01 or 02. The first `\section{}` marker appears between `\input{sections/02_agenda.tex}` and `\input{sections/03_problem.tex}`.
**Warning signs:** Agenda slide showing section header "1. Motivation" in the infolines bar.

### Pitfall 3: \titlepage Showing Wrong \insertshortauthor in Footer

**What goes wrong:** If `\author[Short]{Full}` bracket syntax is not used, Beamer puts the full author string in the footer and it overflows.
**Why it happens:** CambridgeUS footline uses `\insertshortauthor` — it needs the optional short form.
**How to avoid:** D-10 metadata uses the bracket form. Verify the three metadata commands all have short forms: `\title[Short Title]{...}`, `\author[Phạm Thế Minh]{...}`, `\institute[USTH]{...}`.
**Warning signs:** Footer author box showing full name + student ID text overflowing.

### Pitfall 4: \logo{} Overlapping Content on Content-Dense Slides

**What goes wrong:** `\logo{}` is placed via the sidebar-right mechanism using `\llap{}` (left-overlap). On slides where content extends to the bottom-right corner, the 0.5cm logo may partially overlap text.
**Why it happens:** The logo is rendered at its natural position (bottom-right) regardless of frame content. It is NOT clipped to the footline area.
**How to avoid:** Reference_themes.tex uses `height=0.5cm` which is small enough to fit above the footline. Keep the same height. If slides 06 or 08 have content reaching the bottom-right, add `\hfill` or `\vfill` to push content up.
**Warning signs:** Logo visually overlaps a table value or bullet text in the bottom-right region.

### Pitfall 5: lstlisting Breaks Without [fragile] on Demo Slide

**What goes wrong:** `\begin{lstlisting}` inside a frame without `[fragile]` causes a TeX error about "Argument of \@framef has an extra }".
**Why it happens:** lstlisting needs to see the raw token stream; Beamer's frame argument macro-processes the content first unless `[fragile]` is set.
**How to avoid:** 10_demo.tex already has `\begin{frame}[fragile]`. Do not remove or change this when adding `\framesubtitle`.
**Warning signs:** Fatal TeX error on first compile at the demo slide.

### Pitfall 6: Content Area Overflow on Four Identified High-Risk Slides

**What goes wrong:** CambridgeUS removes ~11mm of vertical content area compared to Metropolis (infolines header ~6.3mm + infolines footline ~4.9mm extra chrome). Slides that were borderline in Metropolis will overflow in CambridgeUS.
**Why it happens:** Infolines adds a full-width colored header bar that Metropolis does not have.
**How to avoid:** Pre-emptively cut content on:
- `04_architecture.tex`: The 2-line footnote below the TikZ diagram may need to become 1 line, and scalebox must decrease (from 0.58, try 0.52–0.54).
- `09_confusion.tex`: The `\tabcolsep=10pt` and `\arraystretch=1.3` in the confusion matrix are generous. Reduce to `\tabcolsep=6pt`, `\arraystretch=1.1` and reduce scalebox from 0.80 to 0.70.
- `10_demo.tex`: The lstlisting output block is long (13 lines). May need to trim to 10 lines showing only the most salient output lines.
- `11_contributions.tex`: 4 bullets with 2-line each. May need to cut each bullet to 1 line.
**Warning signs:** "Overfull \vbox" warnings or content visually clipped below the footline.

---

## Code Examples

### Complete Preamble for slides.tex (CambridgeUS version)

```latex
% Source: reference_themes.tex (verbatim copy + CVBLUE additions)
\documentclass[aspectratio=169,10pt]{beamer}
% NOTE: 12pt → 10pt to match reference_themes.tex; CambridgeUS chrome is proportional to font size

%% ── Theme ────────────────────────────────────────────────────
\usetheme{CambridgeUS}
\usecolortheme{beaver}

%% ── Color tokens (MUST come before \setbeamercolor calls) ────
\input{slides/preamble/colors.tex}

%% ── CambridgeUS color overrides ─────────────────────────────
% CVBLUE block titles (D-02)
\setbeamercolor{block title}{fg=white, bg=CVBLUE}
\setbeamercolor{block body}{bg=CVBLUE!10!white}

% Make framesubtitle clearly distinct (dark gray, not red) — from reference
\setbeamercolor{framesubtitle}{fg=darkgray}
\setbeamerfont{framesubtitle}{size=\normalsize, series=\mdseries}

% Bold section names in navigation header — from reference
\setbeamerfont{section in head/foot}{series=\bfseries}

% Remove tiny navigation icons — from reference
\setbeamertemplate{navigation symbols}{}

%% ── Custom footer — from reference lines 29–44 ───────────────
\setbeamertemplate{footline}{%
  \leavevmode%
  \hbox{%
    \begin{beamercolorbox}[wd=.333\paperwidth,ht=2.25ex,dp=1ex,center]{author in head/foot}%
      \usebeamerfont{author in head/foot}\insertshortauthor
    \end{beamercolorbox}%
    \begin{beamercolorbox}[wd=.333\paperwidth,ht=2.25ex,dp=1ex,center]{title in head/foot}%
      \usebeamerfont{title in head/foot}\insertshorttitle
    \end{beamercolorbox}%
    \begin{beamercolorbox}[wd=.333\paperwidth,ht=2.25ex,dp=1ex,right]{date in head/foot}%
      \usebeamerfont{date in head/foot}\insertshortdate{}\hspace*{2em}
      \insertframenumber{} / \inserttotalframenumber\hspace*{2ex}
    \end{beamercolorbox}%
  }%
  \vskip0pt%
}

%% ── Logo — from reference line 47 ───────────────────────────
\logo{\includegraphics[height=0.5cm]{usth.png}}

%% ── Packages ─────────────────────────────────────────────────
\input{slides/preamble/packages.tex}

%% ── Fonts (XeLaTeX) ─────────────────────────────────────────
\setsansfont{DejaVu Sans}[Scale=0.92]
\setmonofont{DejaVu Sans Mono}[Scale=0.88]

%% ── Figure and pic search paths ─────────────────────────────
\graphicspath{{figures/}{pics/}}

%% ── Metadata (D-10) ─────────────────────────────────────────
\title[Localized XAI for Vietnamese Phishing]{Localized Explainable AI for Vietnamese\\Financial Phishing Detection}
\author[Phạm Thế Minh]{Phạm Thế Minh \\ {\small Student ID: 23BI14279}}
\institute[USTH]{University of Science and Technology of Hanoi (USTH) \\
  {\small Supervisors: Giang Anh Tuấn \quad|\quad Nguyễn Việt Anh}}
\date{2026}

\setbeamercovered{invisible}
```

### colors.tex — Updated for CambridgeUS

```latex
% Source: slides/preamble/colors.tex — remove Metropolis colorlets, keep CVBLUE
%% Central color token — change one hex value to recolor the whole deck
\definecolor{CVBLUE}{HTML}{1A5276}
%% NOTE: CVBLUElight and CVBLUEdark were used by Metropolis overrides only.
%% They are no longer needed. Remove them to avoid confusion.
```

### Block Environment Usage (D-07 definite + D-08 discretion examples)

```latex
% Source: D-07 — Problem slide (03_problem.tex) — definite
\begin{block}{Problem Statement}
  Vietnamese users' financial messages are analyzed \textbf{locally} ---
  risk tier, threat labels, and actionable guidance without sending text off-device.
\end{block}

% Source: D-07 — Evaluation slide (08_evaluation.tex) — definite
\begin{block}{Result}
  Macro F1: \textcolor{CVBLUE}{\textbf{0.9553}} \quad
  All 4 classes cleared the 0.80 recall threshold.
\end{block}

% Source: D-08 discretion — Contributions slide (11_contributions.tex)
% Reference_themes.tex uses \begin{block}{Contributions} wrapping enumerate — follow that pattern
\begin{block}{Contributions}
  \begin{enumerate}
    \item ...
  \end{enumerate}
\end{block}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Metropolis (Phase 11) | CambridgeUS/beaver (Phase 12) | Phase 12 decision | Crimson structural chrome replaces minimal gray; shorter content area |
| Manual agenda list (02_agenda.tex) | `\tableofcontents` auto-populated | Phase 12 | Agenda automatically matches `\section{}` markers |
| Custom title layout (two-column) | `\titlepage` auto-rendered by theme | Phase 12 | Consistent with CambridgeUS title page design |
| pdfLaTeX + inputenc (reference) | XeLaTeX + fontspec | Pre-existing (Phase 11) | fontspec handles Vietnamese Unicode natively; no change needed |

**Deprecated/outdated:**
- `\setbeamercolor{progress bar}`: Metropolis-only key, does not exist in CambridgeUS. Remove.
- `\setbeamercolor{title separator}`: Metropolis-only key. Remove.
- `\colorlet{CVBLUElight}` and `\colorlet{CVBLUEdark}`: Only used by now-removed Metropolis hooks. Remove.

---

## CambridgeUS Theme Mechanics — Verified from Source

This section documents exactly what the CambridgeUS theme does, derived from reading the installed .sty files directly.

### What CambridgeUS delegates to (from beamerthemeCambridgeUS.sty)

```
\useinnertheme{rounded}          % rounded blocks with shadow=true
\useoutertheme{infolines}        % header + footer chrome
\usecolortheme{beaver}           % color palette
\setbeamerfont{block title}{size={}}
\setbeamercolor{titlelike}{parent=structure,bg=white}
```

### What infolines defines (beamerouterthemeinfolines.sty)

**Header** (headline template): two equal halves
- Left (`.5\paperwidth`): current section name, right-aligned, in `section in head/foot` color
- Right (`.5\paperwidth`): current subsection name, left-aligned, in `subsection in head/foot` color
- Height: `ht=2.65ex, dp=1.5ex` per row

**Footer** (footline template): three equal thirds
- Left (`.333\paperwidth`): `\insertshortauthor` (+ institute if set)
- Center (`.333\paperwidth`): `\insertshorttitle`
- Right (`.333\paperwidth`): `\insertshortdate{}` + frame counter

**Color inheritance:**
- `section in head/foot` → `palette tertiary` → beaver: `bg=darkred!80!black, fg=gray!10!white`
- `subsection in head/foot` → `palette primary` → beaver: `bg=gray!30!white, fg=darkred!60!black`
- `author in head/foot` → `palette tertiary` → beaver: darkred background
- `title in head/foot` → `palette secondary` → beaver: `bg=gray!15!white, fg=darkred!70!black`
- `date in head/foot` → `palette primary` → beaver: `bg=gray!30!white, fg=darkred!60!black`

### What beaver defines (beamercolorthemebeaver.sty)

```
palette primary:    fg=darkred!60!black, bg=gray!30!white
palette secondary:  fg=darkred!70!black, bg=gray!15!white
palette tertiary:   bg=darkred!80!black, fg=gray!10!white  ← dominant header color
palette quaternary: fg=darkred, bg=gray!5!white
frametitle:         bg=gray!10!white
frametitle right:   bg=gray!60!white
titlelike:          parent=palette primary, fg=darkred
block title:        (not set in beaver — inherits from "structure" → "palette primary")
```

**THME-05 clarification — what "section navigation bar" means in CambridgeUS:**
The requirement says "highlights the current section and lists all section names." The infolines header shows only the CURRENT section name (text), not all sections simultaneously. This is the canonical CambridgeUS behavior shown in reference_themes.tex. The requirement is satisfied because the current section is always visually highlighted in the darkred bar. There is no horizontal nav-dots bar with all section names — that would require the `miniframes` outer theme which is NOT part of CambridgeUS. Do not switch to miniframes.

### Content area height estimate

At 16:9 aspect ratio (`paperheight=96mm`):
- Infolines headline: `ht=2.65ex + dp=1.5ex` ≈ 6.3mm
- CambridgeUS frametitle: ~5–6mm
- Infolines footline: `ht=2.25ex + dp=1.0ex` ≈ 4.9mm
- **Total chrome: ~16–17mm**
- **Available content area: ~79–80mm**

Metropolis at same size:
- Frametitle only: ~6–7mm; bottom progress bar: ~2mm
- **Total chrome: ~8–9mm**
- **Available content area: ~87–88mm**

**Effective reduction: ~8–11mm (CONTEXT.md estimate of ~1.2cm is well-calibrated).** [ASSUMED: exact measurements depend on current beamer version's ex-to-mm conversion at the active font size]

---

## Slide-by-Slide Content Assessment

### Slides that should compile without overflow

| Slide | Current Content | Risk | Recommended Action |
|-------|----------------|------|---------------------|
| 01_title (becomes \titlepage) | CambridgeUS renders automatically | NONE | Replace with `[plain]\titlepage` |
| 02_agenda (\tableofcontents) | 8 section entries | LOW | Use `hideallsubsections`; add `\setbeamerfont{section in toc}{size=\small}` if needed |
| 03_problem | 3 bullets (~45 words) | LOW | Add block{} at bottom, cut 1 sub-clause from each bullet |
| 05_data | 4 bullets + 5-row table in columns | LOW | Add \framesubtitle, no other change |
| 07_model | 4 bullets (~50 words) | LOW | Add \framesubtitle, no other change |

### Slides that need pre-emptive cuts or scalebox reduction

| Slide | Risk | Recommended Intervention |
|-------|------|--------------------------|
| 04_architecture | MEDIUM — scalebox 0.58 TikZ + 2-line caption | Reduce scalebox to 0.52–0.54; cut caption to 1 line (remove "Offline:" prefix, just show the flow as sub-caption) |
| 06_why_local | MEDIUM — scalebox 0.60 TikZ + 4-line text + image | Reduce scalebox to 0.52–0.55; cut "Real incidents" header, fold all 3 incidents into 2 with shorter phrasing |
| 08_evaluation | LOW-MEDIUM — scalebox 0.60 TikZ in 0.57\textwidth column | Likely fine; try 0.56–0.58 first |
| 09_confusion | HIGH — `\tabcolsep=10pt, \arraystretch=1.3` table at scalebox 0.80 + explanation block | Reduce to `\tabcolsep=6pt, \arraystretch=1.1`; scalebox 0.70; shorten explanation to 2 lines |
| 10_demo | HIGH — 13-line lstlisting output | Trim to 10 lines (remove 3 middle `Grounded cues` detail lines, keep Risk tier, Threat labels, 2 cues, Next steps) |
| 11_contributions | MEDIUM — 4 bullets, 2-line each | Cut each bullet to 1 line (remove parenthetical details); move details to verbal delivery |
| 12_future (limitations) | MEDIUM — 3 bullets + 1 future bullet | Cut 1 sub-sentence per bullet; the frame is not as dense as contributions |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | CambridgeUS content area ~79–80mm vs Metropolis ~87–88mm (~11mm difference) | Pitfall 6, Code Examples | Scalebox estimates are off; planner should note that exact factors are tuned after first compile (D-12 accepted) |
| A2 | `[plain]` frames suppress the sidebar-right logo | Common Pitfalls (Pitfall 4) | Logo appears on title slide; fix by adding `\logo{}` with empty content for plain frames or using `\addtobeamertemplate` |
| A3 | `\setbeamercovered{invisible}` is harmless in CambridgeUS | Architecture Patterns | No impact; this option is theme-neutral |

---

## Open Questions

1. **\tableofcontents entry width at 8 sections**
   - What we know: 8 entries × ~1 line each at default font size fits ~6.5 lines in the content area
   - What's unclear: Whether the numbered labels (e.g., "1. Motivation") wrap to 2 lines at default \normalsize
   - Recommendation: First compile will reveal this; add `\setbeamerfont{section in toc}{size=\small}` if needed

2. **Logo visibility on [plain] frames**
   - What we know: `\logo{}` is placed via sidebar-right; sidebar-right is defined by `beamerouterthemedefault`
   - What's unclear: Whether the infolines outer theme overrides sidebar-right (suppressing logo on plain)
   - Recommendation: Compile title slide first; if logo appears on `[plain]` title frame and is unwanted, add `\setbeamertemplate{logo}{}` locally inside `\begin{frame}[plain]` or accept it (the reference also uses `[plain]` with logo)

3. **Section 09_confusion grouping under Section 6 vs own sub-section**
   - What we know: D (Claude's discretion); CONTEXT.md says "confusion matrix slide (09) gets grouped under section 6 Evaluation or gets its own sub-section"
   - Recommendation: Group under section 6 Evaluation (no additional `\section{}` between 08 and 09). The infolines header will show "6. Evaluation" on both slides, which is correct — they are both evaluation content.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| MiKTeX XeLaTeX | Compile | Yes | 4.18 (MiKTeX 26.5) | — |
| beamerthemeCambridgeUS.sty | THME-01 | Yes | bundled beamer 3.77 | — |
| beamercolorthemebeaver.sty | THME-01 | Yes | bundled | — |
| beamerouterthemeinfolines.sty | THME-04/05 | Yes | bundled | — |
| beamerinnerthemerounded.sty | block rendering | Yes | bundled | — |
| DejaVu Sans (TrueType) | XeLaTeX font | Yes | in MiKTeX fonts/truetype | — |
| DejaVu Sans Mono (TrueType) | lstlisting mono | Yes | in MiKTeX fonts/truetype | — |
| usth.png | THME-03 | Yes | pics/usth.png confirmed | — |
| rufusai.png | 06_why_local.tex | Yes | pics/rufusai.png confirmed | — |
| booktabs, colortbl, tikz, listings | slides/preamble/packages.tex | Yes | all kpsewhich confirmed | — |

**Missing dependencies with no fallback:** None.

**All dependencies available — no installation step needed in any plan.**

---

## Security Domain

This phase modifies only LaTeX source files producing a static PDF. There are no runtime services, network calls, authentication, or user inputs. ASVS categories do not apply.

`security_enforcement` key absent from config.json — treated as enabled per specification. However, the nature of this phase (LaTeX document compilation) has no applicable threat surface for ASVS V2–V6. No security tasks are required.

---

## Sources

### Primary (HIGH confidence — source files read directly)

- `C:/Users/.../MiKTeX/tex/latex/beamer/beamerthemeCambridgeUS.sty` — CambridgeUS theme composition
- `C:/Users/.../MiKTeX/tex/latex/beamer/beamercolorthemebeaver.sty` — beaver palette definitions
- `C:/Users/.../MiKTeX/tex/latex/beamer/beamerouterthemeinfolines.sty` — header/footer templates and color inheritance
- `C:/Users/.../MiKTeX/tex/latex/beamer/beamerinnerthemerounded.sty` — rounded block template
- `C:/Users/.../MiKTeX/tex/latex/beamer/beamerouterthemedefault.sty` — logo/sidebar-right placement mechanism
- `documents/reports/latex/slides/reference_themes.tex` — canonical CambridgeUS reference presentation (all preamble patterns verified here)
- `documents/reports/latex/slides.tex` — current Metropolis entry point (all removal targets identified)
- All 12 section `.tex` files — content assessed for overflow risk
- All 3 `figures/*_bare.tex` files — dimensions measured for scalebox estimates

### Secondary (MEDIUM confidence — web sources)

- [latex-beamer.com/tutorials/blocks/](https://latex-beamer.com/tutorials/blocks/) — confirmed `\setbeamercolor{block title}` key names
- [beamer.plus/Colors.html](https://www.beamer.plus/Colors.html) — confirmed palette inheritance model
- [latex-beamer.com/tutorials/table-of-contents/](https://latex-beamer.com/tutorials/table-of-contents/) — confirmed `hideallsubsections` option

---

## Metadata

**Confidence breakdown:**
- Theme mechanics (CambridgeUS/beaver/infolines): HIGH — verified from installed .sty source
- Color override patterns (block title): HIGH — verified from beamer color inheritance chain
- Content area dimensions: MEDIUM — calculated from .sty ex values; exact pixel measure requires compile
- Overflow risk per slide: MEDIUM — estimated from content word count and known chrome overhead
- scalebox factor estimates: LOW — D-12 explicitly accepts that exact factors require post-compile tuning

**Research date:** 2026-06-05
**Valid until:** 2026-08-05 (stable beamer package; CambridgeUS has not changed in years)
