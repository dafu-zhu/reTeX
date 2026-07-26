# reTeX

Convert scanned PDF textbooks into structured, multi-chapter LaTeX projects with proper equations, exercises, figures, and cross-references.

## Features

- **Parallel conversion** — multiple chapters converted simultaneously via AI agents
- **Figure extraction** — automatically finds figures by caption index, crops and imports as PNGs
- **Clean build system** — all auxiliary files in `build/`, only PDFs in project root
- **Compile-fix loop** — automated error detection and programmatic fixing
- **Quantitative verification** — counts sections, equations, figures, exercises to validate completeness

## Branch Structure

- **One branch: `master`.** Pipeline code, skills, scripts, and every converted book all live together — each book in its own `books/<book_name>/` directory.
- Per-book `output/*` branches are retired — they all claimed the same flat `latex/ch01/` paths, so they could never merge and the working tree mixed chapters from different books.

## Quick Start

```bash
# 1. Place your scanned PDF
cp your_textbook.pdf pdfs/scanned.pdf

# 2. Run the pipeline (in Claude Code)
/pdf-to-latex pdfs/scanned.pdf
# Creates books/<book_name>/ on the current branch — never a new branch

# 3. Build the PDF
./scripts/build.sh <book_name>          # Full book
./scripts/build.sh <book_name> 3        # Chapter 3 only
./scripts/build.sh <book_name> clean    # Remove build artifacts
```

## Project Structure

```
├── pdfs/
│   └── scanned.pdf              # Source PDF (user provides)
├── books/
│   └── <book_name>/
│       ├── book.conf            # Chapter page ranges
│       ├── progress.md          # Section-level progress tracker
│       ├── latex/
│       │   ├── main.tex         # Master document
│       │   ├── preamble.tex     # Packages, commands, geometry
│       │   ├── frontmatter.tex  # Title page (title, author, edition only)
│       │   ├── ch01/ ... chNN/  # One directory per chapter
│       │   ├── backmatter/      # Bibliography, answers, index
│       │   └── figures/         # Extracted figure PNGs
│       └── build/               # Auxiliary files (not committed)
├── scripts/
│   ├── build.sh                 # Build full book or single chapter
│   ├── pipeline.py              # Python-first pipeline orchestrator
│   ├── compile_fix.py           # Deterministic compile→fix→recompile loop
│   ├── extract_figures.py       # Extract figures from scanned PDF
│   ├── inventory_check.py       # Count sections/equations/figures/exercises
│   ├── check_repo_layout.py     # Validate books/ layout and copyright rules
│   ├── import_book.sh           # Import one book's LaTeX tree into books/<name>/
│   └── test_compile_fix.py      # Tests for compile_fix patterns
├── skills/                      # Claude Code skills (slash commands)
│   ├── pdf-to-latex.md          # /pdf-to-latex — full pipeline
│   ├── compile-fix.md           # /compile-fix — compile→fix loop
│   └── extract-figures.md       # /extract-figures — figure extraction
├── docs/
│   └── plan.md                  # Conversion plan template
└── .gitignore
```

## Build System

| Command | Output | Aux files |
|---------|--------|-----------|
| `./scripts/build.sh <book_name>` | `books/<book_name>/<book_name>.pdf` | `books/<book_name>/build/` |
| `./scripts/build.sh <book_name> N` | `books/<book_name>/<book_name>_chNN.pdf` | `books/<book_name>/build/` |
| `./scripts/build.sh <book_name> clean` | — | Removed |

## Skills

| Skill | Description |
|-------|-------------|
| `/pdf-to-latex` | Full pipeline: scanned PDF → LaTeX project |
| `/compile-fix` | Compile → diagnose → fix → recompile loop |
| `/extract-figures` | Extract figures from PDF by caption index |

## Python Pipeline

Most pipeline tasks run as pure Python — no AI needed:

```bash
# Full pipeline (AI only for content conversion)
python scripts/pipeline.py pdfs/scanned.pdf

# Skip AI — setup, figures, compile-fix, inventory only
python scripts/pipeline.py pdfs/scanned.pdf --skip-ai

# Individual phases
python scripts/pipeline.py pdfs/scanned.pdf --phase 0    # Setup
python scripts/pipeline.py pdfs/scanned.pdf --phase 2    # Figures
python scripts/pipeline.py pdfs/scanned.pdf --phase 4    # Verify

# Standalone compile-fix loop
python scripts/compile_fix.py --book <book_name>                  # Full book
python scripts/compile_fix.py --book <book_name> --chapter 3      # Single chapter
python scripts/compile_fix.py --book <book_name> --fix-only       # Apply fixes without compiling
python scripts/compile_fix.py --book <book_name> --compile-only   # Compile without fixing
```

| Phase | Task | Requires AI? |
|-------|------|-------------|
| 0 | Parse TOC, create structure, write templates | No — PyMuPDF + templates |
| 1 | Content conversion (scanned pages → LaTeX) | **Yes** — Claude sonnet |
| 2 | Figure extraction | No — PyMuPDF crop |
| 3 | Back matter skeleton | No — templates |
| 4 | Compile-fix + inventory | No — regex patterns |

## Dependencies

- **LaTeX**: pdflatex (amsmath, tikz, pgfplots, tcolorbox, enumitem, etc.)
- **Python 3**: PyMuPDF (`pip install pymupdf`) for figure extraction and TOC parsing
- **Claude Code** or **Anthropic API** (`pip install anthropic`): content conversion only (Phase 1)

## Roadmap

- [x] Claude Code pipeline
- [x] Scripted Python pattern matching for compile fixes (`scripts/compile_fix.py`)
- [x] Python-first pipeline — AI only for content conversion (`scripts/pipeline.py`)
- [ ] **Resolve Claude copyright output filter** — Claude refuses to output content it recognizes as copyrighted; see [research](docs/research.md)
- [ ] Per-chapter compilation instead of per-batch

## License

MIT. Converted content retains the original textbook's copyright.
