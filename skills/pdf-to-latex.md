# PDF to LaTeX Conversion Pipeline

Convert a scanned PDF textbook to a multi-chapter LaTeX project.

## Usage
`/pdf-to-latex <scanned_pdf_path>`

## Pipeline (fully automated, non-stop)

### Phase 0: Setup (~2 min)
1. Read first 15 pages of scanned PDF to determine: title, author, edition, page geometry, TOC structure, content characteristics
2. Create directory structure: `latex/{ch01..chNN, backmatter, figures}`, `scripts/`
3. Write `preamble.tex` matching source page geometry, with standard math packages and custom commands
4. Write `main.tex` skeleton, `frontmatter.tex`, `book.conf` (book name in snake_case)
5. Write `build.sh` and `extract_figures_v2.py`
6. Configure exercise numbering style by reading the book's format
7. Mark Phase 0 done in `progress.md`

### Phase 1: Content conversion (parallel agents)
1. Launch N agents per batch (one per chapter), all concurrent
2. Each agent: reads scanned PDF pages → writes section .tex files → updates progress.md
3. Batch size: ~4 chapters per batch, sequential batches
4. If agent fails (content filter): retry with rephrased prompt immediately
5. After each batch: auto-compile via `/compile-fix` to catch errors early

### Phase 2: Figures
1. Scan scanned PDF for all "Figure X.Y.Z" captions using PyMuPDF text search
2. For each figure: crop the region (figure + caption) and save as PNG at 250 DPI
3. Replace placeholders with `\includegraphics`
4. Verify figure count matches .tex figure environments

### Phase 3: Back matter
1. Extract bibliography, answers to starred exercises, index skeleton
2. Usually done as part of Phase 1 final batch

### Phase 4: Compile-fix loop (use `/compile-fix` skill)
1. Compile (into `build/`) → count errors → if 0, done
2. If errors: categorize, fix programmatically (Python, not sed), recompile
3. Quantitative inventory check: sections, equations, figures, exercises
4. Report final stats

## Key Rules
- **NEVER use sed for LaTeX replacements** — always Python `re` module (sed `\f` = form feed)
- **Always parallel agents** — never do chapters sequentially by hand
- **Auto-compile after each batch** — catch errors early, not at the end
- **Content filter retry** — if agent blocked, retry immediately with "creating original LaTeX markup" phrasing
- **Figures from scanned PDF** — extract by caption index, crop region, not TikZ recreation
- **Progress tracking** — update progress.md after every completed task
- **Build cleanliness** — compile into `build/` subdir, only output PDFs in `latex/` root
- **Exercise numbering** — read the book's exercise style in Phase 0, configure `\exerciselabel` in preamble. Don't hardcode
- **Book config** — `book.conf` stores `BOOK_NAME` in snake_case, used by build.sh for output PDF naming

## Arguments
- `$ARGUMENTS` — path to scanned PDF
