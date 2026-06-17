# Transcription Progress — A First Course in Monte Carlo Methods
# D. Sanz-Alonso & O. Al-Ghattas, University of Chicago
# Branch: output/a_first_course_in_monte_carlo_methods

## Phase 0: Setup
- [x] Branch created: `output/a_first_course_in_monte_carlo_methods`
- [x] Book identified: *A First Course in Monte Carlo Methods*, Sanz-Alonso & Al-Ghattas
- [x] Directory structure created: ch01–ch10, appendix, backmatter, figures, build
- [x] `preamble.tex` written (geometry, theorem environments, custom commands)
- [x] `main.tex` skeleton written (10 chapters + appendix + backmatter)
- [x] `frontmatter.tex` written (title page, LOF, LOA, preface, TOC)
- [x] `book.conf` updated (BOOK_NAME=a_first_course_in_monte_carlo_methods)
- [x] `build.sh` verified (existing, reads BOOK_NAME from book.conf)
- [x] `extract_figures_v2.py` written
- [x] Title page smoke test PASSED — clean render, matches source

## Phase 1: Content Conversion

| Chapter | Title | PDF Pages | Book Pages | Status |
|---------|-------|-----------|------------|--------|
| ch01 | Introduction | 14–21 | 1–8 | DONE |
| ch02 | Transformation and Accept/Reject Sampling | 22–35 | 9–22 | DONE |
| ch03 | Monte Carlo Integration and Importance Sampling | 36–49 | 23–36 | DONE |
| ch04 | Metropolis Hastings | 50–63 | 37–50 | DONE |
| ch05 | Gibbs Sampling | 64–77 | 51–64 | DONE |
| ch06 | Langevin Monte Carlo | 78–89 | 65–76 | DONE |
| ch07 | Annealing Strategies | 90–99 | 77–86 | DONE |
| ch08 | Hamiltonian Monte Carlo | 100–111 | 87–98 | DONE |
| ch09 | Sequential Monte Carlo | 112–125 | 99–112 | DONE |
| ch10 | Variational Inference and EM | 126–139 | 113–126 | DONE |
| appA | Markov Chain Theory | 140–151 | 127–138 | DONE |

## Phase 2: Figures
- [x] 21 PNG figures extracted (fig_01_1.png through fig_10_2.png + fig_07_3.png extra)
- All 21 LOF entries have matching PNG files in latex/figures/

## Phase 3: Back Matter
- [x] Bibliography (refs [16]–[242] transcribed; refs [1]–[15] are stubs — no chapters cite them)
- [x] Alphabetical Index (source pages 153–155, hardcoded with source page numbers)

## Phase 4: Compile-Fix Loop
- [x] Full compile: 245 pages, 0 hard errors, 0 undefined citations
- [x] Fixed: stale aux files from previous book (stale ch01–ch10 aux files)
- [x] Fixed: LOF populated (21 figures)
- [x] Fixed: named citation keys in sec3_4, sec5_4, sec9_4 → numeric
- [x] Fixed: cleardoublepage suppresses blank page header (preamble.tex)
- [x] Final PDF: latex/a_first_course_in_monte_carlo_methods.pdf (4.2 MB, 245 pages)

## Notes
- PDF page offset: book page N = PDF page N + 13
- Section format: "X.Y · Title" (titlesec with $\cdot$ separator)
- Theorem counter: single shared counter per chapter
- Algorithms: numbered by chapter (Algorithm 2.1, 2.2, ...)
- Figures: numbered by chapter (Figure 1.1, 2.1, ...)
- QED rule: proof environment auto-appends QED — never add manual \qed inside proof
- TOC depth: 2 (sections and subsections)
- 23 algorithms total across all chapters
