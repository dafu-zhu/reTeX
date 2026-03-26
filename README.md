# reTeX

Convert scanned PDF textbooks into structured, multi-chapter LaTeX projects with proper equations, exercises, figures, and cross-references.

## Features

- **Parallel conversion** — multiple chapters converted simultaneously via AI agents
- **Figure extraction** — automatically finds figures by caption index, crops and imports as PNGs
- **Clean build system** — all auxiliary files in `build/`, only PDFs in project root
- **Compile-fix loop** — automated error detection and programmatic fixing
- **Quantitative verification** — counts sections, equations, figures, exercises to validate completeness

## Quick Start

```bash
# 1. Place your scanned PDF
cp your_textbook.pdf pdfs/scanned.pdf

# 2. Run the pipeline (in Claude Code)
/pdf-to-latex pdfs/scanned.pdf

# 3. Build the PDF
./scripts/build.sh              # Full book
./scripts/build.sh 3            # Chapter 3 only
./scripts/build.sh clean        # Remove build artifacts
```

## Project Structure

```
├── pdfs/
│   └── scanned.pdf              # Source PDF (user provides)
├── latex/
│   ├── main.tex                 # Master document
│   ├── preamble.tex             # Packages, commands, geometry
│   ├── frontmatter.tex          # Title page, copyright
│   ├── ch01/ ... chNN/          # One directory per chapter
│   │   ├── chXX.tex             # Chapter wrapper
│   │   └── secXX_Y.tex          # One file per section
│   ├── backmatter/              # Bibliography, answers, index
│   ├── figures/ch01/ ... chNN/  # Extracted figure PNGs
│   └── build/                   # Auxiliary files (not committed)
├── scripts/
│   ├── build.sh                 # Build full book or single chapter
│   ├── extract_figures.py       # Extract figures from scanned PDF
│   └── inventory_check.py       # Count sections/equations/figures/exercises
├── skills/                      # Claude Code skills (slash commands)
│   ├── pdf-to-latex.md          # /pdf-to-latex — full pipeline
│   ├── compile-fix.md           # /compile-fix — compile→fix loop
│   └── extract-figures.md       # /extract-figures — figure extraction
├── docs/
│   ├── plan.md                  # Conversion plan template
│   └── progress.md              # Section-level progress tracker
├── book.conf                    # Book name (auto-generated)
└── .gitignore
```

## Build System

| Command | Output | Aux files |
|---------|--------|-----------|
| `./scripts/build.sh` | `latex/<book_name>.pdf` | `latex/build/` |
| `./scripts/build.sh N` | `latex/<book_name>_chNN.pdf` | `latex/build/` |
| `./scripts/build.sh clean` | — | Removed |

## Skills

| Skill | Description |
|-------|-------------|
| `/pdf-to-latex` | Full pipeline: scanned PDF → LaTeX project |
| `/compile-fix` | Compile → diagnose → fix → recompile loop |
| `/extract-figures` | Extract figures from PDF by caption index |

## Dependencies

- **LaTeX**: pdflatex (amsmath, tikz, pgfplots, tcolorbox, enumitem, etc.)
- **Python 3**: PyMuPDF (`pip install pymupdf`) for figure extraction
- **Claude Code**: AI-powered content conversion

## Roadmap

- [x] v0.1 — Claude-only pipeline (works, but expensive)
- [ ] Delegate bulk OCR→LaTeX to cheaper vision models (Gemini Flash / GPT-4o-mini)
- [ ] Replace LLM-based compile fixes with scripted Python pattern matching
- [ ] Compile after each chapter instead of each batch for faster error detection
- [ ] Standalone CLI (`retex convert book.pdf`) without Claude Code dependency
- [ ] Plugin system for swappable OCR backends

## License

MIT. Converted content retains the original textbook's copyright.
