---
name: compile-fix
description: "Automated LaTeX compile → diagnose → fix → recompile loop. Iterates until 0 errors or max 10 attempts. Use when LaTeX compilation fails, when the user says 'fix compilation', 'compile errors', 'make it build', or after any batch of LaTeX changes. Also trigger after /pdf-to-latex completes a batch."
---

# LaTeX Compile-Fix Loop

Compile a LaTeX project, diagnose errors, fix them programmatically, and recompile. Repeat until clean or max 10 iterations.

## Input
- Optional: path to latex directory (default: `latex/`)

## Output
- Compiled PDF at `latex/<book_name>.pdf`
- Inventory report (sections, equations, figures, exercises)

---

## Build Convention

All auxiliary files go in `latex/build/`. The `latex/` root stays clean.

```bash
cd latex/
export TEXINPUTS="$(pwd)//:build//:"
mkdir -p build
pdflatex -interaction=nonstopmode -file-line-error -output-directory=build main.tex
```

Read `BOOK_NAME` from `book.conf`. Copy `build/main.pdf` → `latex/<BOOK_NAME>.pdf`.

---

## Loop

```
REPEAT (max 10):
  1. Compile into build/
  2. Count errors (grep "^! " or file-line-error patterns)
  3. If 0 errors → copy PDF, run inventory check, DONE
  4. Categorize errors by file, then by type
  5. Fix highest-impact category first (errors cascade)
  6. Go to 1
```

---

## Error Categories and Fixes

Apply fixes using **Python `re` module only**. Never use `sed` — it interprets `\f` as form feed byte (0x0c), silently corrupting `\frac` and similar commands.

| Error Pattern | Root Cause | Fix |
|---------------|-----------|-----|
| `\begin{boxed}...\end{boxed}` | Invalid environment | → `\boxed{...}` |
| `\begin{defbox}` inside `equation` | tcolorbox can't nest in math | → `\boxed{...}` |
| `\boxed{$...$}` inside `\[...\]` | Double math mode | → `\fbox{\parbox{0.8\textwidth}{...}}` |
| `\boxed{\[...\]}` | Wrong nesting | → `\[\boxed{...}\]` |
| `\foreach` in PGFPlots domain with arithmetic | pgfplots can't evaluate `{\k+1}` | Expand to individual `\addplot` calls |
| `\frac{partial}{partial x}` | Missing backslash | → `\frac{\partial}{\partial x}` |
| Form feed bytes (0x0c) in .tex files | sed corruption artifact | Strip with `bytes.replace(b'\x0c', b'')` |
| `\fbox{\parbox{...}{` with premature `}}` | Script split content outside box | Move content inside, fix closing braces |

---

## Inventory Check

After clean compile, count per chapter:

```python
sections   = count(r'\\section\{')
equations  = count(r'\\begin\{(?:equation|align|gather|multline)\*?\}')
figures    = count(r'\\begin\{figure\}')
exercises  = count(r'\\item')
```

Report as table. Sections should match the book's TOC exactly.

---

## Rules

- Fix one category per iteration, recompile, verify before next category
- Fixing is sequential Ch 1 → Ch N when errors cascade (e.g., missing equation shifts all downstream numbering)
- If error count doesn't decrease after a fix, reassess — the fix may have introduced new issues
- After 10 iterations with remaining errors, report what's left and stop
