# Repo Consolidation: One Branch, One Folder Per Book

**Date:** 2026-07-25
**Status:** Approved

## Problem

Each book conversion lived on its own `output/<book_name>` branch, all writing to the
same flat paths (`latex/ch01/`, `latex/main.tex`, `latex/frontmatter.tex`, repo-root
`book.conf`, `docs/progress.md`). Two consequences:

1. **Branches cannot be merged.** Five branches claim identical paths, and three of
   them forked from an older `master`, so a merge conflicts on book content *and* on
   framework files (`scripts/`, `skills/`, `README.md`).
2. **Working tree mixes books.** Right now `latex/ch01–ch10` is Monte Carlo while
   `latex/ch11–ch25` is Option Volatility Pricing — the same `latex/ch01/` directory
   has held chapter 1 of several different books.

The root cause is the `.gitignore` block excluding `latex/ch*/`, `latex/backmatter/`,
`latex/frontmatter.tex`, and `latex/figures/**/*.png`. Book output was invisible to git
on `master`, which forced the `output/*` branch workaround (and a counter-`latex/.gitignore`
on `econometrics_hayashi` to undo it). It also caused real data loss: the Option
Volatility Pricing sources were never committed anywhere and ch01–ch10 were overwritten.

## Decisions

| Question | Decision |
|---|---|
| Layout | `books/<name>/` self-contained; framework shared at repo root |
| Branches with no committed source | Drop both — no salvage |
| Opus cross-check | Separate verify pass over every page, after Sonnet transcription |
| Other Opus phases | Phase 0 setup/preamble, Phase 4 final verification |
| Public repo + copyrighted content | Stay public, `books/` tracked |
| Copyright metadata | Strip — title, author, edition only |

## Target Structure

```
reTeX/
├── README.md  .gitignore
├── docs/          framework docs only (plan.md, research.md, superpowers/specs/)
├── scripts/       build.sh, compile_fix.py, extract_figures*.py, ocr_extract.py, pipeline.py
├── skills/        pdf-to-latex.md, compile-fix.md, extract-figures.md
├── pdfs/          source PDFs (gitignored)
└── books/
    └── <book_name>/
        ├── book.conf     page ranges, chapter count  (was repo-root book.conf)
        ├── progress.md   per-book tracker            (was docs/progress.md)
        ├── latex/        main.tex, preamble.tex, frontmatter.tex, chNN/, backmatter/, figures/
        └── build/        (gitignored)
```

Repo-root `book.conf` and `docs/progress.md` are deleted. They were the global
singletons that made two books unable to coexist.

## Migration: Import, Not Merge

Merging is rejected for the reasons in **Problem**. Instead each branch's `latex/` tree
is read directly into a disjoint path on `master`, giving zero conflicts and a
deterministic result.

Per book, on `master`:

```bash
mkdir -p books/<name>/latex
git archive <branch>:latex | tar -x -C books/<name>/latex
git show <branch>:book.conf > books/<name>/book.conf
# progress.md — source varies per branch, see table below
rm -f books/<name>/latex/.gitignore books/<name>/latex/book.conf
```

One commit per book: `refactor: import <name> conversion into books/`.

### Per-branch source of `progress.md`

`docs/progress.md` is a **stale shared template** on two branches — byte-identical
between `econometrics_hayashi` and `asymptotic_theory_white`. On those, the real
per-book tracker is the repo-root `progress.md`.

| Book | progress.md source | Extra cleanup |
|---|---|---|
| `econometrics_hayashi` | root `progress.md` | drop `latex/.gitignore`; scrub Publisher line |
| `asymptotic_theory_white` | root `progress.md` | drop duplicate `latex/book.conf` (identical to root) |
| `applied_partial_differential_equations` | `docs/progress.md` | — |
| `div_grad_curl_and_all_that` | `docs/progress.md` | — |
| `a_first_course_in_monte_carlo_methods` | `docs/progress.md` | — |

### Framework salvage

Committed on `div_grad_curl_and_all_that` but absent from `master` — import into `scripts/`:
`extract_figures_ocr.py`, `extract_figures_roman.py`, `ocr_extract.py`

Untracked in the working tree, never committed anywhere — commit into `scripts/`:
`extract_figures_v2.py`, `check_clean_textbook.py`, `codex_rewrite_chapter.ps1`

### Discarded

- `latex/ch11–ch25` — Option Volatility Pricing leftovers; ch01–ch10 already overwritten
- `latex/ai_ch02/`, `latex/ai_clean_ch03/`, `latex/ai_probe_ch02_page*.tex` — scratch
- `ocr_output/` (245 MB), `ocr_output_previous_20260602_170150/` (65 MB) — gitignored and
  left on disk for manual deletion; regenerable from the source PDF

## Branch Disposition

Tag every tip as `archive/<name>` before deleting, so no commit becomes unreachable.
Then delete local and remote.

| Branch | Disposition |
|---|---|
| `master` | **the only surviving branch** |
| `output/econometrics_hayashi` | import → tag → delete |
| `output/applied_partial_differential_equations` | import → tag → delete |
| `output/asymptotic_theory_white` | import → tag → delete |
| `output/div_grad_curl_and_all_that` | import → tag → delete |
| `output/a_first_course_in_monte_carlo_methods` | import → tag → delete |
| `output/option_volatility_pricing` | delete — tip identical to `master`, no output |
| `output/applied_pde_solutions_manual` | delete — no chapter sources committed |
| `dev` | delete — 0 commits ahead of `master` |
| `origin/fix/content-filter-phase0-subagent` | delete — already squash-merged as `49bfd36` |

## Copyright Scrub

Applied **at import time**, so the clean version is what lands on `master`.

`\bookpublisher` described in the skill was never implemented; preambles carry only
`pdftitle`/`pdfauthor`. `book.conf` files hold no metadata fields. The exposure is three
`frontmatter.tex` files and one `progress.md` line.

| Book | Removed | Kept |
|---|---|---|
| `applied_partial_differential_equations` | copyright page (`\textcopyright{} 2004, 1998, 1987, 1983 Pearson Education`, "All rights reserved", "Printed in the United States", `ISBN 0-13-065243-1`); `PEARSON / Prentice Hall / Upper Saddle River, New Jersey 07458` from title page | title, *Fourth Edition*, Richard Haberman, SMU |
| `asymptotic_theory_white` | copyright page (cover-photo ©, `Copyright © 2001, 1984 by Academic Press`, "All Rights Reserved", both publisher addresses, `Library of Congress Catalog Card Number: 00-107735`, `ISBN 0-12-746652-5`, "PRINTED IN THE UNITED STATES OF AMERICA"); `Academic Press / A Harcourt Science and Technology Company` imprint | title, *Revised Edition*, Halbert White, UCSD |
| `econometrics_hayashi` | `Princeton University Press \\ Princeton and Oxford` imprint; `- **Publisher**: Princeton University Press` from progress.md | title, Fumio Hayashi, University of Tokyo |
| `div_grad_curl_and_all_that` | — already clean | — |
| `a_first_course_in_monte_carlo_methods` | — already clean | — |

Edition is **kept**: it identifies which edition a transcription matches and carries no
copyright risk.

Also `README.md:50`: `frontmatter.tex  # Title page, copyright` → `# Title page`.

The `README.md` MIT disclaimer and `docs/research.md` analysis of the API content filter
are the project's own writing about copyright, not reproduced notices. They stay.

## .gitignore

Delete the block ignoring `latex/ch*/`, `latex/backmatter/`, `latex/frontmatter.tex`,
`latex/figures/**/*.png`. Book content becomes tracked on `master` — this is the change
that makes a single branch work.

```gitignore
books/*/build/
books/*/*.pdf
pdfs/*.pdf
ocr_output*/
*.aux *.log *.toc *.out *.idx *.ilg *.ind *.fls *.fdb_latexmk *.synctex.gz
.DS_Store  Thumbs.db  scripts/__pycache__/

.claude/
!.claude/CLAUDE.md
```

`.claude/` is currently ignored wholesale, so `.claude/CLAUDE.md` — which duplicates the
skill's LaTeX/build/branch conventions — is untracked and exists only on one machine. It
gets un-ignored so the project rules are versioned alongside `skills/`, while session
state and `settings.local.json` stay ignored.

The 626 committed figure crops stay tracked on public `master`, per decision.

## build.sh

```
./scripts/build.sh <book_name> [chapter|clean]
```

Sources `books/<name>/book.conf`; aux files → `books/<name>/build/`; output →
`books/<name>/<name>.pdf`. Bare invocation lists available books and exits non-zero.
The current behaviour of reading `BOOK_NAME` from a repo-root `book.conf` is removed.

## Skill Rule Updates

Applies to `skills/pdf-to-latex.md` and the LaTeX/Build/Branches sections of
`.claude/CLAUDE.md` (which becomes tracked — see **.gitignore**).

1. **Paths** — all output goes to `books/<BOOK_NAME>/latex/…`; `book.conf` and
   `progress.md` live in the book folder.
2. **Branching** — Phase 0 no longer creates `output/<name>`. The Critical Rules row
   *"Branch `output/<name>`, never commit content to main"* is replaced by a
   single-branch rule.
3. **Copyright** — Phase 0 extracts `Title, author, edition` (publisher dropped).
   New Critical Rule: never typeset the copyright page — no ©, ISBN, Library of
   Congress number, "all rights reserved", publisher name, imprint, or address.
   Phase 1: if a chunk's page range covers the copyright page, skip that page.
   Note in the skill that this *reduces* the content-filter pressure the skill spends
   ~60 lines mitigating — publisher and copyright text is exactly the recognizable
   metadata that trips it.
4. **Model tiering** — new table, and each phase's subagent prompt states its model.

| Phase | Model | Why |
|---|---|---|
| 0 Setup / preamble | **Opus** | One call, but theorem-counter, geometry and exercise-style choices cascade into every chapter |
| 1a Transcription, 5–8 pg chunks | **Sonnet** | Highest volume, tightly specified, tedious |
| 1b Notation cross-check | **Opus** | The step OCR structurally cannot do |
| 2 Figures | script; Sonnet for placeholder swap | Deterministic |
| 3 Back matter | **Sonnet** | Repetitive reference formatting |
| compile-fix loop | **Sonnet** | Mechanical error → fix |
| 4 Final verification vs TOC | **Opus** | Real omission vs renamed section is a judgment call |

### New Phase 1b: Notation Cross-Check

The rationale for the whole tiering scheme. Deterministic OCR classifies each glyph in
isolation; an agent can read the surrounding mathematics and infer which glyph was
*meant*. A subscript rendered `o` is almost always `0` when the neighbouring terms are
indexed `x_1, x_2`; `ν` and `v` are indistinguishable in scanned serif type but decided
by whether the symbol appears elsewhere as a frequency or a velocity.

The Opus agent receives:
- the scanned page images for the chunk
- the `.tex` Sonnet produced for those pages
- the chapter's symbol inventory established so far

It corrects **only** glyph and notation errors that mathematical context resolves:
`0/o/O`, `1/l/I`, `ν/v`, `ρ/p`, `κ/k`, `×/x`, `∈/e`, sub- vs superscript placement,
dropped hats/bars/primes, misread summation and product bounds.

Constraints: never restyle prose, never rewrite correct-but-differently-phrased text,
never resolve genuine ambiguity by guessing — emit `% UNCLEAR:` instead. Inherits the
QED and shared-theorem-counter rules. Each edit carries a one-line rationale.

## Verification

1. `git branch -a` shows only `master` plus `archive/*` tags
2. Every book directory contains `book.conf`, `progress.md`, `latex/main.tex`,
   `latex/preamble.tex`, and its full chapter set
3. Chapter counts match: hayashi 10, applied_pde 14, white 8, div_grad_curl 4,
   monte_carlo 10 + appendix
4. Figure counts match: applied_pde 391, div_grad_curl 205, hayashi 30
5. `git grep -iE "ISBN|all rights reserved|library of congress|\\\\textcopyright"` over
   `books/` returns nothing
6. `./scripts/build.sh <name>` compiles all five books; the three scrubbed books are
   rebuilt so their PDFs match the cleaned source
