# Plan: Convert Scanned Textbook PDF to LaTeX

## Overview
Convert a scanned textbook PDF into a multi-chapter LaTeX project with proper structure, equations, exercises, and figures extracted from the source.

## Source Material
- **Scanned PDF**: `pdfs/scanned.pdf` — the source of truth for all content

## Pipeline

### Phase 0: Setup
1. Read scanned PDF front matter to determine: title, author, edition, TOC structure, page geometry
2. Create directory structure: `latex/{ch01..chNN, backmatter, figures}`, `scripts/`
3. Write `preamble.tex` matching source page geometry
4. Write `main.tex` skeleton, `frontmatter.tex`, `book.conf`
5. Configure exercise numbering style in preamble (read from book)

### Phase 1: Content Conversion (Parallel Agents)
- Launch N agents per batch (one per chapter), concurrent within batch
- Each agent reads scanned PDF → writes section `.tex` files
- Batch size: ~4 chapters, sequential batches
- **Auto-compile after each batch** to catch errors early
- If agent blocked by content filter: retry with rephrased prompt

### Phase 2: Figures
- Scan PDF for "Figure X.Y.Z" captions using PyMuPDF
- Crop figure region (diagram + caption) at 250 DPI → PNG
- Save to `figures/chXX/fig_X_Y_Z.png`
- Update `.tex` with `\includegraphics`

### Phase 3: Back Matter
- Bibliography, Answers, Index skeleton

### Phase 4: Verification
1. Compile (into `build/` — keep `latex/` clean)
2. Fix errors programmatically (Python only, never sed)
3. Quantitative inventory: sections, equations, figures, exercises
4. Fixing is sequential Ch 1 → Ch N (errors cascade forward)

## Build Convention
- All `.aux/.log/.idx/.toc` in `latex/build/` — never pollute `latex/`
- Output PDF: `latex/<book_name>.pdf` (name from `book.conf`)
- Chapter PDF: `latex/<book_name>_chXX.pdf`
- Build command: `./scripts/build.sh [chapter_num|clean]`

## Key Rules
- **NEVER use sed** for LaTeX replacements — always Python `re` module
- **Always parallel agents** — never do chapters sequentially by hand
- **Figures from scanned PDF** — extract by caption index, crop, not TikZ
- **Exercise style** — configure `\exerciselabel` in preamble per book
- **Unclear content** → `% UNCLEAR: [description, page X]` placeholder, never guess

## Output Structure
```
project/
├── pdfs/
│   └── scanned.pdf
├── latex/
│   ├── main.tex
│   ├── preamble.tex
│   ├── frontmatter.tex
│   ├── ch01/ ... chNN/
│   │   ├── chXX.tex          (chapter wrapper)
│   │   └── secXX_Y.tex       (one per section)
│   ├── backmatter/
│   ├── figures/ch01/ ... chNN/
│   └── build/                (aux files, never committed)
├── scripts/
│   ├── build.sh
│   ├── extract_figures_v2.py
│   └── inventory_check.py
├── book.conf
├── plan.md
└── progress.md
```
