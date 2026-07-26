# reTeX Project Rules

## LaTeX Conventions

### Theorem Numbering
Most math textbooks use a **single shared counter** for all theorem-like environments within each chapter. Check the source PDF in Phase 0:
- If Definition 2.1, Example 2.2, Proposition 2.3 are sequential → shared counter
- Use `\newtheorem{definition}[theorem]{Definition}` (shares `theorem` counter)
- **Never** use `\newtheorem{definition}{Definition}[chapter]` (creates a separate counter) unless the source explicitly uses separate numbering

### QED Symbols
- The `proof` environment auto-appends `\qedsymbol` — **never** add manual `\qed`, `\blacksquare`, or `\hfill$\blacksquare$` inside `\begin{proof}...\end{proof}`
- Use `\qedhere` only when the proof ends with a displayed equation or list (places QED on the equation line instead of a separate line)
- Subagent prompts MUST include the QED rule explicitly — agents default to adding manual QED markers

### Preamble
- Define **all** bold vector/matrix macros the book uses (e.g., `\bfX`, `\bfbeta`, `\bfOmega`) — agents will use them; undefined macros cause cascading errors
- Include both `\Var` and `\var` if agents might use either case
- Equation numbering: `\numberwithin{equation}{chapter}` for most books

### Copyright
- Title page carries **title, author, edition only**
- Never typeset the copyright page: no ©, ISBN, Library of Congress number,
  "all rights reserved", publisher name, imprint, or address

## Build
- `scripts/build.sh <book_name>` reads `books/<book_name>/book.conf`
- All aux files → `books/<name>/build/`, PDF → `books/<name>/<name>.pdf`
- **Never use `sed`** for LaTeX replacements — use Python `re` module

## Branches
- **One branch: `master`.** Each book lives in `books/<book_name_snake_case>/`
- Per-book `output/*` branches are retired — they all claimed the same `latex/ch01/`
  paths, so they could never merge and the working tree mixed chapters from different books
- Feature work on the framework uses `feature/`, `fix/`, `docs/`, `refactor/`
