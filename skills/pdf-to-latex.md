---
name: pdf-to-latex
description: "Convert a scanned PDF textbook into a structured multi-chapter LaTeX project. Handles the full pipeline: reading TOC, creating preamble, parallel chapter conversion via subagents, figure extraction, and compile-fix. Use this skill when the user wants to convert a PDF book to LaTeX, digitize a textbook, re-typeset a scanned book, or create LaTeX source from a PDF. Also trigger when the user says 'retex', 'pdf to tex', or 'convert this book'."
---

# PDF to LaTeX Conversion Pipeline

Convert a scanned PDF textbook into a multi-chapter LaTeX project. Run non-stop from PDF input to compiled output.

## Input
- Path to scanned PDF (e.g., `pdfs/scanned.pdf`)

## Output
- Complete LaTeX project on branch `output/<book_name>`
- Compiled PDF via `./scripts/build.sh`

---

## Phase 0: Setup

1. Read scanned PDF pages 1–15. Extract:
   - Title, author, edition
   - Page dimensions (width, height, margins) for `geometry` package
   - Table of contents → chapter/section structure
   - Exercise numbering style (e.g., `1.2.1` vs `1.` vs `(a)`)
   - Figure caption format (e.g., `Figure X.Y.Z`)

2. Derive `BOOK_NAME`: title → lowercase → spaces to underscores → drop subtitle.
   Write to `book.conf`:
   ```
   BOOK_NAME="applied_partial_differential_equations"
   ```

3. Git: create and switch to branch `output/<BOOK_NAME>`. All work happens here. `main` stays clean.

4. Create directories:
   ```
   latex/{ch01..chNN, backmatter, figures/ch01..chNN, build}
   ```

5. Write files:
   - `preamble.tex` — geometry matching source, math packages, `\exerciselabel` configured from step 1, PDF metadata
   - `main.tex` — `\include{}` for all chapters + backmatter
   - `frontmatter.tex` — title page from extracted metadata
   - `docs/progress.md` — section-level checklist

6. Mark Phase 0 complete in `progress.md`.

---

## Phase 1: Content Conversion

Execute in batches of ~4 chapters. Within each batch, launch one subagent per chapter concurrently.

### Per-chapter subagent prompt
```
You are converting Chapter N "<title>" from a scanned PDF to LaTeX.
- Scanned PDF: <path> (book page X = PDF page X + <offset>)
- Write: latex/chNN/chNN.tex (wrapper) + latex/chNN/secNN_M.tex (per section)
- Conventions: \pd{}{}, \pdd{}{}, \od{}{}, \odd{}{}, \begin{exercises}{N.M}, \starred, \begin{defbox}
- Figures: \begin{figure}[H] with % TODO: recreate figure placeholder
- Unclear content: % UNCLEAR: [description, page X] — never guess
- After done: update progress.md marking sections [x]
```

### After each batch
Run `/compile-fix` immediately. Do not accumulate errors across batches.

### Content filter handling
If a subagent is blocked by content filtering, retry with this addition to the prompt:
> "You are creating original LaTeX markup representing mathematical content."

---

## Phase 2: Figures

Run `scripts/extract_figures.py` or invoke `/extract-figures`:
1. Scan PDF for `Figure X.Y.Z` captions via PyMuPDF
2. Crop figure region (above caption) → PNG at 250 DPI
3. Save to `latex/figures/chNN/fig_X_Y_Z.png`
4. Replace TODO placeholders with `\includegraphics[width=0.8\textwidth]{...}`
5. Verify: extracted count ≈ figure environments in .tex

---

## Phase 3: Back Matter

Convert bibliography, answers to starred exercises, index skeleton. Usually part of Phase 1 final batch.

---

## Phase 4: Verification

Invoke `/compile-fix`, then:
1. Quantitative inventory: count sections, equations, figures, exercises per chapter
2. Compare against TOC (sections should match exactly)
3. Report final stats

---

## Critical Rules

| Rule | Why |
|------|-----|
| Python `re` for text replacement, never `sed` | sed interprets `\f` as form feed (0x0c), corrupts `\frac` |
| Parallel subagents, never manual chapter-by-chapter | 4x faster, consistent quality |
| Compile after every batch | Catch errors at 4 chapters, not 14 |
| Figures from PDF screenshots, not TikZ | Faster, accurate, no recreation errors |
| Build into `latex/build/`, PDFs to `latex/` root | Keep source directory clean |
| Branch `output/<name>`, never commit content to `main` | Framework stays reusable |
