# LaTeX Compile-Fix Loop

Automated compile → diagnose → fix → recompile cycle until 0 errors.

## Usage
`/compile-fix [latex_dir]`

Default: current project's `latex/` directory.

## Build Convention
- All auxiliary files (.aux, .log, .idx, .toc, .out) go in `latex/build/` — never pollute `latex/`
- Output PDF goes to `latex/` root with clean name: `book_name_in_snake_case.pdf`
- Chapter PDFs: `book_name_in_snake_case_chXX.pdf`
- Set `TEXINPUTS` so pdflatex resolves inputs from `latex/` while writing to `build/`

### Compile command
```bash
cd latex/
export TEXINPUTS="$(pwd)//:build//:"
mkdir -p build
pdflatex -interaction=nonstopmode -file-line-error -output-directory=build main.tex
# Copy result to root
cp build/main.pdf ./book_name.pdf
```

## Process (fully automated, iterate until clean)

### Step 1: Compile (into build/)
```bash
export TEXINPUTS="$LATEX_DIR//:$LATEX_DIR/build//:"
pdflatex -interaction=nonstopmode -file-line-error -output-directory="$LATEX_DIR/build" main.tex
```

### Step 2: If 0 errors → copy PDF to latex/ root with clean name → report success → DONE

### Step 3: Categorize errors
Group by file, then by error type:
- `Undefined control sequence` → missing package or typo
- `Missing $ inserted` → math outside math mode
- `Argument of \X has extra }` → brace mismatch, often `\left/\right` inside macro args
- `Bad math environment delimiter` → `\boxed{\[...\]}` or similar nesting
- `Something's wrong--perhaps a missing \item` → enumerate outside list context
- `Paragraph ended before \X` → unclosed braces across paragraphs

### Step 4: Fix programmatically
**CRITICAL: Use Python only, NEVER sed** (sed interprets `\f` as form feed, corrupts `\frac`)

Common fixes (apply in order):
1. `\begin{boxed}...\end{boxed}` → `\boxed{...}` (invalid environment)
2. `\begin{defbox}...\end{defbox}` inside equation → `\boxed{...}` (can't nest tcolorbox in equation)
3. `\boxed{$...$...}` inside `\[...\]` → `\fbox{\parbox{}{...}}` (double math mode)
4. `\boxed{\[...\]}` → `\[\boxed{...}\]` (wrong nesting)
5. `\foreach` in PGFPlots with variable arithmetic in domain → expand manually
6. `\frac{partial}{partial x}` → `\frac{\partial}{\partial x}` (missing backslashes)
7. Form feed bytes (0x0c) → strip with Python `bytes.replace(b'\x0c', b'')`
8. `\fbox{\parbox{...}{` with premature `}}` → move content inside

### Step 5: Recompile (into build/) → go to Step 2

### Step 6: After clean compile, run inventory check
Count per chapter: sections, equations, figures, exercises. Report totals.

## Rules
- Max 10 iterations. If still errors after 10, report remaining and stop.
- Fix one error category at a time (most impactful first — errors cascade)
- After fixing, always recompile to verify fix didn't break other things
- ALL build artifacts stay in `build/` — latex/ root stays clean
- Output PDF naming: all lowercase, underscores for spaces, e.g. `applied_partial_differential_equations.pdf`

## Arguments
- `$ARGUMENTS` — optional path to latex directory
