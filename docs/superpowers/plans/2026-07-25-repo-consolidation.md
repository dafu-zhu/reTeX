# Repo Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse five `output/*` branches into a single `master` where each book lives in its own `books/<name>/` folder, scrub reproduced copyright pages, and rewrite the conversion skill to assign Sonnet to bulk transcription and Opus to context-dependent judgment.

**Architecture:** Book content is imported from each branch's `latex/` tree into a disjoint `books/<name>/` path via `git archive`, never via `git merge` — the branches all claim identical paths and would conflict on content and framework alike. A layout validator is written first (Task 1) and acts as the gate after every subsequent task. Branch deletion happens last, after all content is verified present and building.

**Tech Stack:** git, bash (Git Bash on Windows), Python 3 + pytest, pdflatex

## Global Constraints

- Repo root: `D:\GitHub\reTeX`. Shell for git/bash steps: Git Bash (POSIX). Never `cmd.exe` syntax.
- **Never use `sed` for LaTeX replacements** — `sed` interprets `\f` as form feed (0x0c) and corrupts `\frac`. Use Python `re` exclusively.
- Archive tags are created **locally only and never pushed** — pushing republishes the pre-scrub copyright pages.
- Branch deletion (Task 12) happens only after Task 11 verification passes. Nothing is deleted before its content is confirmed imported.
- Copyright scrub keeps title, author, and edition. It removes ©, ISBN, Library of Congress numbers, "all rights reserved", publisher names, imprints, and addresses.
- The five book slugs, used verbatim as `books/` directory names:
  `econometrics_hayashi`, `applied_partial_differential_equations`, `asymptotic_theory_white`, `div_grad_curl_and_all_that`, `a_first_course_in_monte_carlo_methods`
- Expected content, asserted in Task 11: chapter counts 10 / 14 / 8 / 4 / 10+appendix; figure counts 30 / 391 / 205 / 0 / 0 in the same order.
- Commit style: `type: description` (feat/fix/docs/refactor).

---

### Task 0: Create the working branch and carry the design docs over

The session that produced this plan ran on `output/a_first_course_in_monte_carlo_methods`, which Task 12 deletes. Tasks 0–11 run on `refactor/consolidate-books`, cut from `master`; Task 12 merges it to `master` and then deletes the old branches.

**Files:**
- Create on `refactor/consolidate-books`: `docs/superpowers/specs/2026-07-25-repo-consolidation-design.md`, `docs/superpowers/plans/2026-07-25-repo-consolidation.md`

**Interfaces:**
- Consumes: nothing
- Produces: `refactor/consolidate-books` checked out from `master`, with both design documents committed. Every later task through Task 11 assumes it is the current branch.

- [ ] **Step 1: Record the two design-doc commit SHAs**

Both documents are already committed on the current branch. Run:

```bash
git branch --show-current
git log --oneline -2 -- docs/superpowers/
```
Expected: `output/a_first_course_in_monte_carlo_methods`, and two commits — `docs: repo consolidation design …` and `docs: repo consolidation implementation plan`. Note both SHAs, oldest first: `<SPEC_SHA>` then `<PLAN_SHA>`.

- [ ] **Step 2: Cut the working branch from master and replay both commits**

```bash
git checkout master
git checkout -b refactor/consolidate-books
git cherry-pick <SPEC_SHA> <PLAN_SHA>
```

Both files are new on `master`, so a conflict is unexpected. If one occurs, resolve by taking the incoming version in full.

- [ ] **Step 3: Verify both documents are on the working branch**

Run:
```bash
git branch --show-current
ls docs/superpowers/specs/ docs/superpowers/plans/
git status --porcelain | grep -v '^??' || echo "clean"
```
Expected: `refactor/consolidate-books`, both `.md` files listed, and `clean`.

---

### Task 1: Layout validator

Written first so every later task has an executable gate. Replaces the discarded one-off `check_clean_textbook.py`.

**Files:**
- Create: `scripts/check_repo_layout.py`
- Test: `scripts/test_check_repo_layout.py`

**Interfaces:**
- Consumes: nothing
- Produces: `check_layout(root: pathlib.Path) -> list[str]` returning a list of human-readable violation strings, empty when clean. CLI entry point exits 1 if the list is non-empty. Tasks 4, 5, 7, 9, 11 call `python scripts/check_repo_layout.py`.

- [ ] **Step 1: Write the failing test**

Create `scripts/test_check_repo_layout.py`:

```python
import pathlib
import pytest
from check_repo_layout import check_layout

REQUIRED = ["book.conf", "progress.md", "latex/main.tex", "latex/preamble.tex"]


def make_book(root: pathlib.Path, name: str) -> pathlib.Path:
    book = root / "books" / name
    (book / "latex").mkdir(parents=True)
    for rel in REQUIRED:
        path = book / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("placeholder\n", encoding="utf-8")
    return book


def test_clean_repo_has_no_violations(tmp_path):
    make_book(tmp_path, "some_book")
    assert check_layout(tmp_path) == []


def test_missing_required_file_is_reported(tmp_path):
    book = make_book(tmp_path, "some_book")
    (book / "book.conf").unlink()
    violations = check_layout(tmp_path)
    assert len(violations) == 1
    assert "book.conf" in violations[0]
    assert "some_book" in violations[0]


def test_isbn_is_reported(tmp_path):
    book = make_book(tmp_path, "some_book")
    (book / "latex" / "frontmatter.tex").write_text(
        "ISBN 0-13-065243-1\n", encoding="utf-8"
    )
    violations = check_layout(tmp_path)
    assert any("ISBN" in v for v in violations)


@pytest.mark.parametrize(
    "text",
    [
        "All rights reserved.",
        "Library of Congress Catalog Card Number: 00-107735",
        r"\textcopyright{} 2004 Pearson Education, Inc.",
        r"Copyright \copyright\ 2001 by Academic Press",
    ],
)
def test_copyright_markers_are_reported(tmp_path, text):
    book = make_book(tmp_path, "some_book")
    (book / "latex" / "frontmatter.tex").write_text(text + "\n", encoding="utf-8")
    assert check_layout(tmp_path) != []


def test_edition_and_author_are_allowed(tmp_path):
    book = make_book(tmp_path, "some_book")
    (book / "latex" / "frontmatter.tex").write_text(
        "{\\Large Fourth Edition}\\\\[3cm]\n{\\Large Richard Haberman}\n",
        encoding="utf-8",
    )
    assert check_layout(tmp_path) == []


def test_legacy_paths_are_reported(tmp_path):
    make_book(tmp_path, "some_book")
    (tmp_path / "book.conf").write_text("BOOK_NAME=x\n", encoding="utf-8")
    (tmp_path / "latex" / "ch01").mkdir(parents=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "progress.md").write_text("# p\n", encoding="utf-8")
    violations = check_layout(tmp_path)
    assert any("book.conf" in v for v in violations)
    assert any("latex/ch01" in v for v in violations)
    assert any("docs/progress.md" in v for v in violations)


def test_binary_files_do_not_crash_the_scan(tmp_path):
    book = make_book(tmp_path, "some_book")
    (book / "latex" / "figures").mkdir()
    (book / "latex" / "figures" / "fig.png").write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe")
    assert check_layout(tmp_path) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest scripts/test_check_repo_layout.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'check_repo_layout'`

- [ ] **Step 3: Write minimal implementation**

Create `scripts/check_repo_layout.py`:

```python
"""Validate the books/ layout invariants and the absence of copyright notices.

Usage:
    python scripts/check_repo_layout.py [--root PATH]

Exits 1 and prints one line per violation when the layout is wrong.
"""
import argparse
import pathlib
import re
import sys

REQUIRED_FILES = ("book.conf", "progress.md", "latex/main.tex", "latex/preamble.tex")

# Reproduced-copyright markers. Deliberately does NOT include the bare word
# "copyright" — README.md and docs/research.md legitimately discuss copyright,
# and this scan is scoped to books/ anyway.
FORBIDDEN = (
    re.compile(r"\bISBN\b", re.IGNORECASE),
    re.compile(r"all rights reserved", re.IGNORECASE),
    re.compile(r"library of congress", re.IGNORECASE),
    re.compile(r"\\textcopyright", re.IGNORECASE),
    re.compile(r"\\copyright", re.IGNORECASE),
)

TEXT_SUFFIXES = {".tex", ".md", ".conf", ".txt", ".bib"}


def check_layout(root: pathlib.Path) -> list[str]:
    violations: list[str] = []
    books = root / "books"

    if not books.is_dir():
        return [f"missing books/ directory at {books}"]

    for book in sorted(p for p in books.iterdir() if p.is_dir()):
        for rel in REQUIRED_FILES:
            if not (book / rel).is_file():
                violations.append(f"{book.name}: missing {rel}")

        for path in sorted(book.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for pattern in FORBIDDEN:
                if pattern.search(text):
                    rel_path = path.relative_to(root).as_posix()
                    violations.append(
                        f"{rel_path}: contains forbidden marker {pattern.pattern}"
                    )

    if (root / "book.conf").is_file():
        violations.append("legacy repo-root book.conf still present")
    if (root / "docs" / "progress.md").is_file():
        violations.append("legacy docs/progress.md still present")
    for legacy in sorted((root / "latex").glob("ch*")):
        if legacy.is_dir():
            violations.append(f"legacy latex/{legacy.name} still present")

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parents[1],
        help="Repository root (default: parent of scripts/)",
    )
    args = parser.parse_args()

    violations = check_layout(args.root)
    for violation in violations:
        print(f"FAIL: {violation}")
    if violations:
        print(f"\n{len(violations)} layout violation(s)")
        return 1
    print("Layout OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest scripts/test_check_repo_layout.py -v`
Expected: PASS, 10 passed (the parametrized case counts as 4)

Note: the tests import `check_repo_layout` as a top-level module, which works because pytest inserts the test file's directory (`scripts/`) into `sys.path` under rootdir-based collection. If the import fails, run from the repo root as `python -m pytest scripts/test_check_repo_layout.py` rather than `pytest scripts/...`.

- [ ] **Step 5: Commit**

```bash
git add scripts/check_repo_layout.py scripts/test_check_repo_layout.py
git commit -m "feat: add books/ layout and copyright validator"
```

---

### Task 2: Local archive tags and baseline inventory

**Files:**
- Create: `docs/superpowers/plans/2026-07-25-baseline-inventory.txt` (evidence, committed)

**Interfaces:**
- Consumes: nothing
- Produces: local tags `archive/<branch-slug>` for all seven `output/*` branches plus `dev`; a baseline inventory file that Task 11 diffs against.

- [ ] **Step 0: Confirm you are on the working branch**

Run: `git branch --show-current`
Expected: `refactor/consolidate-books`. If not, Task 0 did not complete — go back and finish it. Committing any later task to an `output/*` branch means Task 12 deletes the work.

- [ ] **Step 1: Confirm the working tree is clean enough to proceed**

Run:
```bash
git status --porcelain | grep -v '^??' || echo "no tracked modifications"
```
Expected: `no tracked modifications`. Untracked (`??`) entries are expected and handled in Task 10. If tracked modifications exist, stop and report — do not stash.

- [ ] **Step 2: Create local archive tags**

```bash
for b in econometrics_hayashi applied_partial_differential_equations \
         asymptotic_theory_white div_grad_curl_and_all_that \
         a_first_course_in_monte_carlo_methods \
         option_volatility_pricing applied_pde_solutions_manual; do
    git tag "archive/$b" "output/$b"
done
git tag archive/dev dev
```

- [ ] **Step 3: Verify tags exist locally and are absent from the remote**

Run:
```bash
git tag -l 'archive/*'
git ls-remote --tags origin 'refs/tags/archive/*'
```
Expected: eight local tags listed; the `ls-remote` output is **empty**. If `ls-remote` prints anything, a tag was pushed — delete it with `git push origin :refs/tags/<name>` before continuing.

- [ ] **Step 4: Capture the baseline inventory**

```bash
{
  echo "# Baseline inventory captured before consolidation"
  echo
  for b in econometrics_hayashi applied_partial_differential_equations \
           asymptotic_theory_white div_grad_curl_and_all_that \
           a_first_course_in_monte_carlo_methods; do
      tex=$(git ls-tree -r --name-only "output/$b" latex/ | grep -c '\.tex$')
      png=$(git ls-tree -r --name-only "output/$b" latex/figures/ | grep -c '\.png$')
      ch=$(git ls-tree --name-only "output/$b" latex/ | grep -c '^latex/ch[0-9]')
      echo "$b: chapters=$ch tex=$tex png=$png"
  done
} > docs/superpowers/plans/2026-07-25-baseline-inventory.txt
cat docs/superpowers/plans/2026-07-25-baseline-inventory.txt
```

Expected output shape (exact `tex` counts are whatever the repo holds; `ch` and `png` must match the Global Constraints):

```
econometrics_hayashi: chapters=10 tex=... png=30
applied_partial_differential_equations: chapters=14 tex=... png=391
asymptotic_theory_white: chapters=8 tex=... png=0
div_grad_curl_and_all_that: chapters=4 tex=... png=205
a_first_course_in_monte_carlo_methods: chapters=10 tex=... png=0
```

Note: `div_grad_curl` shows 205 PNGs but only 4 chapter directories — that book uses roman-numeral chapters with many figures each. `asymptotic_theory_white` has 0 committed figures. Both are expected.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/2026-07-25-baseline-inventory.txt
git commit -m "docs: capture pre-consolidation baseline inventory"
```

---

### Task 3: Book import script

**Files:**
- Create: `scripts/import_book.sh`

**Interfaces:**
- Consumes: `scripts/check_repo_layout.py` (not called directly; run separately in Task 4)
- Produces: `scripts/import_book.sh <branch> <book_name> <progress_source>` where `<progress_source>` is either `docs` or `root`. Imports into the working tree and stages nothing — Task 4 commits.

- [ ] **Step 1: Write the script**

Create `scripts/import_book.sh`:

```bash
#!/bin/bash
# Import one book's LaTeX tree from an output/* branch into books/<name>/.
#
# Usage:
#   ./scripts/import_book.sh <branch> <book_name> <docs|root>
#
# The third argument selects the progress.md source: on some branches
# docs/progress.md is a stale shared template and the real per-book tracker
# is the repo-root progress.md.
#
# Imports into the working tree without staging. Caller commits.

set -euo pipefail

BRANCH="$1"
NAME="$2"
PROGRESS_SOURCE="$3"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$SCRIPT_DIR/.."
DEST="$ROOT/books/$NAME"

if ! git -C "$ROOT" rev-parse --verify "$BRANCH" >/dev/null 2>&1; then
    echo "Error: branch $BRANCH not found" >&2
    exit 1
fi

if [ -e "$DEST" ]; then
    echo "Error: $DEST already exists — refusing to overwrite" >&2
    exit 1
fi

mkdir -p "$DEST/latex"

# Book content
git -C "$ROOT" archive "$BRANCH:latex" | tar -x -C "$DEST/latex"

# book.conf always comes from the repo root of the source branch
git -C "$ROOT" show "$BRANCH:book.conf" > "$DEST/book.conf"

# progress.md source varies per branch
case "$PROGRESS_SOURCE" in
    docs) git -C "$ROOT" show "$BRANCH:docs/progress.md" > "$DEST/progress.md" ;;
    root) git -C "$ROOT" show "$BRANCH:progress.md"      > "$DEST/progress.md" ;;
    *) echo "Error: progress source must be 'docs' or 'root'" >&2; exit 1 ;;
esac

# Drop artifacts of the old per-branch layout
rm -f "$DEST/latex/.gitignore" "$DEST/latex/book.conf"

# Drop build artifacts that may have been committed
find "$DEST/latex" -type f \
    \( -name '*.aux' -o -name '*.log' -o -name '*.toc' -o -name '*.out' \
       -o -name '*.idx' -o -name '*.ilg' -o -name '*.ind' \) -delete
rm -rf "$DEST/latex/build"

echo "Imported $NAME:"
echo "  chapters: $(find "$DEST/latex" -maxdepth 1 -type d -name 'ch*' | wc -l)"
echo "  tex:      $(find "$DEST/latex" -name '*.tex' | wc -l)"
echo "  png:      $(find "$DEST/latex" -name '*.png' | wc -l)"
```

- [ ] **Step 2: Make it executable and verify the guard rails**

Run:
```bash
chmod +x scripts/import_book.sh
./scripts/import_book.sh no/such/branch test_book docs; echo "exit=$?"
```
Expected: `Error: branch no/such/branch not found` and `exit=1`

Run:
```bash
./scripts/import_book.sh output/asymptotic_theory_white test_book bogus; echo "exit=$?"
```
Expected: the import runs, then `Error: progress source must be 'docs' or 'root'` and `exit=1`.

- [ ] **Step 3: Clean up the test artifact**

```bash
rm -rf books/test_book
ls books/ 2>/dev/null || echo "books/ does not exist yet — correct"
```

- [ ] **Step 4: Commit**

```bash
git add scripts/import_book.sh
git commit -m "feat: add per-book import script for branch consolidation"
```

---

### Task 4: Import all five books

**Files:**
- Create: `books/econometrics_hayashi/`, `books/applied_partial_differential_equations/`, `books/asymptotic_theory_white/`, `books/div_grad_curl_and_all_that/`, `books/a_first_course_in_monte_carlo_methods/`

**Interfaces:**
- Consumes: `scripts/import_book.sh <branch> <book_name> <docs|root>` from Task 3
- Produces: five populated `books/<name>/` directories in the working tree, **not yet committed** — the copyright scrub in Task 5 must land before the first commit so the pre-scrub tree never enters `master`'s history.

- [ ] **Step 1: Run the five imports**

```bash
./scripts/import_book.sh output/econometrics_hayashi                   econometrics_hayashi                   root
./scripts/import_book.sh output/asymptotic_theory_white                asymptotic_theory_white                root
./scripts/import_book.sh output/applied_partial_differential_equations applied_partial_differential_equations docs
./scripts/import_book.sh output/div_grad_curl_and_all_that             div_grad_curl_and_all_that             docs
./scripts/import_book.sh output/a_first_course_in_monte_carlo_methods  a_first_course_in_monte_carlo_methods  docs
```

The `root` / `docs` argument is not interchangeable: on `econometrics_hayashi` and `asymptotic_theory_white`, `docs/progress.md` is a byte-identical stale template shared between them, and the real tracker is the repo-root `progress.md`.

- [ ] **Step 2: Verify counts against the baseline**

Run:
```bash
for n in econometrics_hayashi applied_partial_differential_equations \
         asymptotic_theory_white div_grad_curl_and_all_that \
         a_first_course_in_monte_carlo_methods; do
    printf "%s: chapters=%s png=%s\n" "$n" \
      "$(find books/$n/latex -maxdepth 1 -type d -name 'ch*' | wc -l)" \
      "$(find books/$n/latex -name '*.png' | wc -l)"
done
diff <(sed 's/ tex=[0-9]*//' docs/superpowers/plans/2026-07-25-baseline-inventory.txt | grep ':') \
     <(for n in econometrics_hayashi applied_partial_differential_equations \
                asymptotic_theory_white div_grad_curl_and_all_that \
                a_first_course_in_monte_carlo_methods; do
         printf "%s: chapters=%s png=%s\n" "$n" \
           "$(find books/$n/latex -maxdepth 1 -type d -name 'ch*' | wc -l)" \
           "$(find books/$n/latex -name '*.png' | wc -l)"
       done) && echo "MATCHES BASELINE"
```
Expected: `MATCHES BASELINE`. If the diff is non-empty, an import lost content — stop and report.

- [ ] **Step 3: Verify the progress.md selection took the real tracker**

Run:
```bash
head -1 books/econometrics_hayashi/progress.md
head -1 books/asymptotic_theory_white/progress.md
```
Expected: book-specific titles (e.g. `# Econometrics (Hayashi) — Conversion Progress`), **not** the generic `# Progress Tracker`. Seeing `# Progress Tracker` means the stale template was imported — rerun that import with `root`.

- [ ] **Step 4: Confirm the validator currently fails on copyright**

Run: `python scripts/check_repo_layout.py`
Expected: FAIL, listing `ISBN` / `all rights reserved` / `library of congress` / `\textcopyright` hits in `applied_partial_differential_equations` and `asymptotic_theory_white` frontmatter, plus legacy-path violations. This confirms the validator detects what Task 5 removes. Do not commit yet.

---

### Task 5: Copyright scrub

**Files:**
- Modify: `books/applied_partial_differential_equations/latex/frontmatter.tex`
- Modify: `books/asymptotic_theory_white/latex/frontmatter.tex`
- Modify: `books/econometrics_hayashi/latex/frontmatter.tex`
- Modify: `books/econometrics_hayashi/progress.md`
- Create: `scripts/scrub_copyright.py`

**Interfaces:**
- Consumes: the imported trees from Task 4
- Produces: frontmatter free of copyright pages and publisher imprints. `python scripts/check_repo_layout.py` passes its copyright checks afterward.

Python `re` only — `sed` corrupts `\frac` by interpreting `\f` as a form feed.

- [ ] **Step 1: Write the scrub script**

Create `scripts/scrub_copyright.py`:

```python
"""Remove reproduced copyright pages and publisher imprints from imported books.

Idempotent: re-running on already-scrubbed files is a no-op.

Usage:
    python scripts/scrub_copyright.py [--root PATH]
"""
import argparse
import pathlib
import re
import sys

BOOKS = "books"


def scrub_applied_pde(text: str) -> str:
    # Publisher imprint block on the title page
    text = re.sub(
        r"\{\\large PEARSON.*?\{\\normalsize Upper Saddle River, New Jersey 07458\}\n",
        "",
        text,
        flags=re.DOTALL,
    )
    # The whole copyright page, from its comment marker to the following \cleardoublepage
    text = re.sub(
        r"% Copyright page\n.*?\\cleardoublepage\n",
        "",
        text,
        flags=re.DOTALL,
    )
    return text


def scrub_asymptotic(text: str) -> str:
    # Publisher imprint block on the title page
    text = re.sub(
        r"\{\\large Academic Press\}.*?London \\quad Sydney \\quad Tokyo \\quad Toronto\}\n",
        "",
        text,
        flags=re.DOTALL,
    )
    # Copyright page: from the cover-photo credit through the closing \clearpage
    text = re.sub(
        r"\\thispagestyle\{empty\}\n\\vspace\*\{\\fill\}\n"
        r"\\noindent\\textit\{Cover photo credit:\}.*?\\clearpage\n",
        "",
        text,
        flags=re.DOTALL,
    )
    return text


def scrub_hayashi_frontmatter(text: str) -> str:
    text = re.sub(
        r"\\vfill\n\{\\normalsize Princeton University Press\\\\Princeton and Oxford\}\n",
        r"\\vfill\n",
        text,
    )
    return text


def scrub_hayashi_progress(text: str) -> str:
    return re.sub(r"^- \*\*Publisher\*\*:.*\n", "", text, flags=re.MULTILINE)


TARGETS = [
    ("applied_partial_differential_equations/latex/frontmatter.tex", scrub_applied_pde),
    ("asymptotic_theory_white/latex/frontmatter.tex", scrub_asymptotic),
    ("econometrics_hayashi/latex/frontmatter.tex", scrub_hayashi_frontmatter),
    ("econometrics_hayashi/progress.md", scrub_hayashi_progress),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()

    for rel, scrubber in TARGETS:
        path = args.root / BOOKS / rel
        if not path.is_file():
            print(f"SKIP (absent): {rel}")
            continue
        original = path.read_text(encoding="utf-8")
        scrubbed = scrubber(original)
        if scrubbed == original:
            print(f"unchanged: {rel}")
            continue
        path.write_text(scrubbed, encoding="utf-8")
        removed = len(original) - len(scrubbed)
        print(f"scrubbed:  {rel} (-{removed} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the scrub**

Run: `python scripts/scrub_copyright.py`
Expected: four `scrubbed:` lines with non-zero byte reductions. Any `unchanged:` line means a regex missed — inspect that file and fix the pattern before continuing.

- [ ] **Step 3: Verify idempotency**

Run: `python scripts/scrub_copyright.py`
Expected: four `unchanged:` lines.

- [ ] **Step 4: Verify the kept metadata survived**

Run:
```bash
grep -c "Richard Haberman\|Fourth Edition" books/applied_partial_differential_equations/latex/frontmatter.tex
grep -c "Halbert White\|Revised Edition"  books/asymptotic_theory_white/latex/frontmatter.tex
grep -c "Fumio Hayashi"                   books/econometrics_hayashi/latex/frontmatter.tex
```
Expected: each prints a count of at least 1. A zero means the scrub was too aggressive — restore from `archive/<name>` and narrow the regex.

- [ ] **Step 5: Verify the copyright checks now pass**

Run: `python scripts/check_repo_layout.py`
Expected: no `contains forbidden marker` lines remain. Legacy-path violations (repo-root `book.conf`, `docs/progress.md`, `latex/ch*`) are still expected — Task 10 removes those.

- [ ] **Step 6: Commit the imports and the scrub together**

The pre-scrub tree must never enter `master`'s history, so this is the first commit containing book content.

```bash
git add books/ scripts/scrub_copyright.py
git commit -m "refactor: import five book conversions into books/, scrubbed of copyright pages"
```

Note: if `git add books/` stages nothing, the old `.gitignore` is still masking the content. That is expected only for paths matching `latex/ch*/` at the repo root — `books/*/latex/ch*/` is not matched because the pattern is anchored. If content is genuinely missing from the commit, do Task 6 first, then redo this step.

---

### Task 6: .gitignore inversion

**Files:**
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nothing
- Produces: a `.gitignore` that tracks book content under `books/` and versions `.claude/CLAUDE.md`.

- [ ] **Step 1: Rewrite .gitignore**

Replace the entire contents of `.gitignore` with:

```gitignore
# Build artifacts
books/*/build/
*.aux
*.log
*.toc
*.out
*.idx
*.ilg
*.ind
*.fls
*.fdb_latexmk
*.synctex.gz

# Compiled book PDFs
books/*/*.pdf

# Source PDFs (user provides)
pdfs/*.pdf

# OCR intermediates (regenerable from source PDF)
ocr_output*/

# OS
.DS_Store
Thumbs.db

# Claude — session state stays local, project rules are versioned
.claude/
!.claude/CLAUDE.md

scripts/__pycache__/
.pytest_cache/
```

The removed block was `latex/ch*/`, `latex/backmatter/`, `latex/frontmatter.tex`, `latex/figures/**/*.png`, and `latex/*.pdf`. Those ignores are what forced the `output/*` branch workaround and lost the Option Volatility Pricing sources.

- [ ] **Step 2: Verify book content is no longer ignored**

Run:
```bash
git check-ignore -v books/econometrics_hayashi/latex/ch01/ch01.tex || echo "NOT IGNORED - correct"
git check-ignore -v books/econometrics_hayashi/latex/figures/ch01/*.png 2>/dev/null || echo "figures NOT IGNORED - correct"
```
Expected: both print the `NOT IGNORED - correct` message.

- [ ] **Step 3: Verify .claude/CLAUDE.md is now trackable**

Run: `git check-ignore -v .claude/CLAUDE.md || echo "NOT IGNORED - correct"`
Expected: `NOT IGNORED - correct`

Run: `git check-ignore -v .claude/settings.local.json && echo "still ignored - correct"`
Expected: `still ignored - correct` (if the file does not exist, `git check-ignore` prints nothing and returns 1 — that is acceptable).

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "fix: track book content under books/, stop ignoring conversion output"
```

---

### Task 7: build.sh takes a book argument

**Files:**
- Modify: `scripts/build.sh` (full rewrite)

**Interfaces:**
- Consumes: `books/<name>/book.conf`
- Produces: `./scripts/build.sh <book_name> [chapter|clean]`. Aux files land in `books/<name>/build/`; the PDF lands at `books/<name>/<name>.pdf`. Bare invocation lists books and exits 1. Task 11 calls this for all five books.

- [ ] **Step 1: Rewrite the script**

Replace the entire contents of `scripts/build.sh` with:

```bash
#!/bin/bash
# LaTeX textbook build script — one book per books/<name>/ directory.
#
# Usage:
#   ./scripts/build.sh <book_name>          # Build full book
#   ./scripts/build.sh <book_name> 3        # Build chapter 3 only
#   ./scripts/build.sh <book_name> clean    # Remove build artifacts
#   ./scripts/build.sh                      # List available books
#
# Output:
#   books/<name>/<name>.pdf          (full book)
#   books/<name>/<name>_ch03.pdf     (single chapter)
#   books/<name>/build/              (all aux/log/idx/toc)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."
BOOKS_DIR="$PROJECT_DIR/books"

list_books() {
    echo "Available books:"
    for d in "$BOOKS_DIR"/*/; do
        [ -d "$d" ] && echo "  $(basename "$d")"
    done
}

if [ -z "$1" ]; then
    echo "Error: no book specified."
    echo
    list_books
    echo
    echo "Usage: ./scripts/build.sh <book_name> [chapter|clean]"
    exit 1
fi

BOOK_NAME="$1"
BOOK_DIR="$BOOKS_DIR/$BOOK_NAME"
LATEX_DIR="$BOOK_DIR/latex"
BUILD_DIR="$BOOK_DIR/build"

if [ ! -d "$LATEX_DIR" ]; then
    echo "Error: no book named '$BOOK_NAME' (expected $LATEX_DIR)"
    echo
    list_books
    exit 1
fi

# book.conf is optional metadata; the directory name is authoritative
if [ -f "$BOOK_DIR/book.conf" ]; then
    # shellcheck disable=SC1090
    source "$BOOK_DIR/book.conf"
fi

mkdir -p "$BUILD_DIR"

if [ "$2" = "clean" ]; then
    rm -rf "${BUILD_DIR:?}"/*
    rm -f "$BOOK_DIR/$BOOK_NAME"*.pdf
    echo "Cleaned build artifacts for $BOOK_NAME."
    exit 0
fi

compile() {
    local TEX_FILE="$1"
    local OUTPUT_NAME="$2"
    local BASENAME
    BASENAME=$(basename "$TEX_FILE" .tex)

    echo "Building $OUTPUT_NAME.pdf ..."

    export TEXINPUTS="$LATEX_DIR//:$BUILD_DIR//:"
    cd "$LATEX_DIR"

    # Two passes for cross-references
    pdflatex -interaction=nonstopmode \
             -output-directory="$BUILD_DIR" \
             "$TEX_FILE" > /dev/null 2>&1 || true

    pdflatex -interaction=nonstopmode \
             -output-directory="$BUILD_DIR" \
             "$TEX_FILE" > /dev/null 2>&1 || true

    if [ -f "$BUILD_DIR/$BASENAME.pdf" ]; then
        cp "$BUILD_DIR/$BASENAME.pdf" "$BOOK_DIR/$OUTPUT_NAME.pdf"
        SIZE=$(ls -lh "$BOOK_DIR/$OUTPUT_NAME.pdf" | awk '{print $5}')
        echo "  Done: $OUTPUT_NAME.pdf ($SIZE)"
    else
        echo "  Failed. Check $BUILD_DIR/$BASENAME.log"
        exit 1
    fi
}

if [ -z "$2" ]; then
    compile "$LATEX_DIR/main.tex" "$BOOK_NAME"
else
    CH_NUM=$(printf "%02d" "$2")
    CH_DIR="ch${CH_NUM}"

    if [ ! -d "$LATEX_DIR/$CH_DIR" ]; then
        echo "Error: $CH_DIR not found in $BOOK_NAME"
        exit 1
    fi

    WRAPPER="$BUILD_DIR/ch${CH_NUM}_standalone.tex"
    cat > "$WRAPPER" << WRAPEOF
\\input{preamble}
\\begin{document}
\\include{${CH_DIR}/${CH_DIR}}
\\end{document}
WRAPEOF

    compile "$WRAPPER" "${BOOK_NAME}_ch${CH_NUM}"
fi
```

- [ ] **Step 2: Verify the no-argument and bad-argument paths**

Run: `./scripts/build.sh; echo "exit=$?"`
Expected: `Error: no book specified.`, the five book names listed, `exit=1`

Run: `./scripts/build.sh not_a_book; echo "exit=$?"`
Expected: `Error: no book named 'not_a_book'`, the list, `exit=1`

- [ ] **Step 3: Build one book end to end**

Run: `./scripts/build.sh asymptotic_theory_white`
Expected: `Done: asymptotic_theory_white.pdf (<size>)`

Run: `ls books/asymptotic_theory_white/asymptotic_theory_white.pdf books/asymptotic_theory_white/build/ | head`
Expected: the PDF exists at the book root; aux/log files are inside `build/`.

- [ ] **Step 4: Verify the PDF is not staged**

Run: `git status --porcelain books/asymptotic_theory_white/ | grep -E '\.pdf|build/' || echo "correctly ignored"`
Expected: `correctly ignored`

- [ ] **Step 5: Commit**

```bash
git add scripts/build.sh
git commit -m "refactor: build.sh takes a book name argument"
```

---

### Task 8: Python scripts take a book argument

**Files:**
- Modify: `scripts/inventory_check.py:6`
- Modify: `scripts/compile_fix.py:23-25`
- Modify: `scripts/extract_figures.py:16`

**Interfaces:**
- Consumes: `books/<name>/latex/`
- Produces: each script accepts `--book <name>` and resolves `LATEX_DIR = ROOT/books/<name>/latex`. Task 11 calls `python scripts/inventory_check.py --book <name>`.

- [ ] **Step 1: Update inventory_check.py**

Replace lines 1-6 of `scripts/inventory_check.py`:

```python
"""Quantitative inventory check: count sections, equations, figures, exercises per chapter."""
import argparse
import re
import glob
import os

_parser = argparse.ArgumentParser(description=__doc__)
_parser.add_argument('--book', required=True, help='Book name under books/')
_args = _parser.parse_args()

ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'books', _args.book, 'latex',
)
if not os.path.isdir(ROOT):
    raise SystemExit(f'No such book: {_args.book} (expected {ROOT})')
```

Leave the rest of the file unchanged — it already derives everything from `ROOT`.

- [ ] **Step 2: Verify inventory_check.py**

Run: `python scripts/inventory_check.py --book econometrics_hayashi`
Expected: a table with 10 chapter rows and non-zero section counts.

Run: `python scripts/inventory_check.py --book nope; echo "exit=$?"`
Expected: `No such book: nope ...` and `exit=1`

- [ ] **Step 3: Update compile_fix.py**

`compile_fix.py` already imports `argparse` (line 15) and defines its paths at module level (lines 22-25), which are consumed throughout the file (lines 76, 79, 84, 96, 109, 561). Parse `--book` at module level so those constants resolve correctly.

Replace lines 22-25:

```python
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LATEX_DIR = os.path.join(ROOT, 'latex')
BUILD_DIR = os.path.join(LATEX_DIR, 'build')
BOOK_CONF = os.path.join(ROOT, 'book.conf')
```

with:

```python
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_book_parser = argparse.ArgumentParser(add_help=False)
_book_parser.add_argument('--book', required=True, help='Book name under books/')
_book_args, _ = _book_parser.parse_known_args()
BOOK_NAME = _book_args.book

BOOK_DIR = os.path.join(ROOT, 'books', BOOK_NAME)
LATEX_DIR = os.path.join(BOOK_DIR, 'latex')
BUILD_DIR = os.path.join(BOOK_DIR, 'build')
BOOK_CONF = os.path.join(BOOK_DIR, 'book.conf')

if not os.path.isdir(LATEX_DIR):
    raise SystemExit(f'No such book: {BOOK_NAME} (expected {LATEX_DIR})')
```

`BUILD_DIR` moves from `latex/build` to `books/<name>/build`, matching `build.sh` from Task 7.

Then simplify `get_book_name()` (line 32) — `book.conf` no longer needs parsing for the name, since the directory is authoritative:

```python
def get_book_name():
    return BOOK_NAME
```

Finally, register `--book` on the real parser at line 509 so it appears in `--help` and is not rejected as unknown. Immediately after `parser = argparse.ArgumentParser(description='LaTeX compile-fix loop')`, add:

```python
    parser.add_argument('--book', required=True, help='Book name under books/')
```

Update the `Usage:` block in the module docstring (lines 8-14) to include `--book <name>` on every example line.

- [ ] **Step 4: Verify compile_fix.py resolves paths**

Run: `python scripts/compile_fix.py --book asymptotic_theory_white --help`
Expected: help text listing `--book`, no traceback.

Run: `python scripts/compile_fix.py --book nope --help; echo "exit=$?"`
Expected: `No such book: nope (expected .../books/nope/latex)` and `exit=1`

- [ ] **Step 5: Update extract_figures.py**

`extract_figures.py` has **no** argparse at all — it uses bare `sys`. Add `import argparse` to the import block (after `import sys` on line 5), then replace lines 15-18:

```python
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LATEX_DIR = os.path.join(ROOT, 'latex')
FIGURES_DIR = os.path.join(LATEX_DIR, 'figures')
SCANNED_PDF = os.path.join(ROOT, 'pdfs', 'scanned.pdf')
```

with:

```python
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_parser = argparse.ArgumentParser(description=__doc__)
_parser.add_argument('--book', required=True, help='Book name under books/')
_parser.add_argument('--pdf', default=os.path.join(ROOT, 'pdfs', 'scanned.pdf'),
                     help='Source scanned PDF (default: pdfs/scanned.pdf)')
_args = _parser.parse_args()

LATEX_DIR = os.path.join(ROOT, 'books', _args.book, 'latex')
FIGURES_DIR = os.path.join(LATEX_DIR, 'figures')
SCANNED_PDF = _args.pdf

if not os.path.isdir(LATEX_DIR):
    raise SystemExit(f'No such book: {_args.book} (expected {LATEX_DIR})')
```

- [ ] **Step 6: Verify extract_figures.py**

Run: `python scripts/extract_figures.py --help`
Expected: help text listing `--book` and `--pdf`, no traceback.

- [ ] **Step 7: Commit**

```bash
git add scripts/inventory_check.py scripts/compile_fix.py scripts/extract_figures.py
git commit -m "refactor: scripts resolve paths under books/<name>/"
```

---

### Task 9: Rewrite the conversion skill

**Files:**
- Modify: `skills/pdf-to-latex.md`

**Interfaces:**
- Consumes: nothing
- Produces: the skill that governs all future conversions — new paths, single-branch rule, copyright rule, model tiering, and Phase 1b.

- [ ] **Step 1: Update Phase 0**

In the Phase 0 subagent prompt:

Change the extraction list from `Title, author, edition, publisher` to `Title, author, edition`, and append this line to that bullet:

```
   - Do NOT extract publisher, imprint, ISBN, or Library of Congress number.
```

Delete step 2 of the prompt entirely (`Git: stash any changes, then create and switch to branch output/<BOOK_NAME>.`) and renumber the remaining steps. Replace step 5 (`Pop the git stash if one was created.`) with nothing — it existed only to support the branch switch.

Change step 3 to:

```
3. Create directory structure:
   mkdir -p books/<BOOK_NAME>/{latex/{ch01..chNN,backmatter,figures/{ch01..chNN}},build}
```

Change every path in step 4 from `latex/<file>` to `books/<BOOK_NAME>/latex/<file>`, move `book.conf` to `books/<BOOK_NAME>/book.conf`, and move `docs/progress.md` to `books/<BOOK_NAME>/progress.md`. In sub-step (b), delete `PUBLISHER` from the `book.conf` field list and delete `\bookpublisher` from the metadata macro list.

Add to sub-step (d):

```
   d. books/<BOOK_NAME>/latex/frontmatter.tex — title page using \booktitle,
      \bookauthor, \bookedition. NEVER typeset the copyright page: no ©, ISBN,
      Library of Congress number, "all rights reserved", publisher name, imprint,
      or address.
```

Prepend to the Phase 0 subagent prompt: `Run this task on Sonnet's more capable sibling — use model: opus for this agent.` and update the launch instruction to read `Launch ONE general-purpose Agent on **Opus**`.

- [ ] **Step 2: Add the model tiering section**

Insert immediately after the `## Output` block, before `## Phase 0: Setup`:

```markdown
## Model Tiering

Bulk transcription is tedious but well-specified — Sonnet does it. The judgment calls
that a deterministic OCR engine structurally cannot make are where Opus earns its cost:
OCR classifies each glyph in isolation, while an agent reads the surrounding mathematics
and infers which glyph was *meant*.

| Phase | Model | Why |
|---|---|---|
| 0 Setup / preamble | **Opus** | One call, but theorem-counter, geometry and exercise-style choices cascade into every chapter |
| 1a Transcription, 5–8 pg chunks | **Sonnet** | Highest volume, tightly specified, tedious |
| 1b Notation cross-check | **Opus** | The step OCR structurally cannot do |
| 2 Figures | script; Sonnet for placeholder swap | Deterministic |
| 3 Back matter | **Sonnet** | Repetitive reference formatting |
| compile-fix loop | **Sonnet** | Mechanical error → fix |
| 4 Final verification vs TOC | **Opus** | Real omission vs renamed section is a judgment call |

Pass the model explicitly on every Agent call — `model: "sonnet"` or `model: "opus"`.
Never leave it to inherit.
```

- [ ] **Step 3: Mark Phase 1a and add Phase 1b**

Retitle `## Phase 1: Content Conversion` to `## Phase 1a: Transcription (Sonnet)`, and change every output path in the per-chapter subagent prompt from `latex/chNN/...` to `books/<BOOK_NAME>/latex/chNN/...`. Change the final bullet from `update progress.md` to `update books/<BOOK_NAME>/progress.md`. Add to the prompt's rule list:

```
- Skip the copyright page if it falls inside your page range — do not typeset ©,
  ISBN, Library of Congress numbers, "all rights reserved", or publisher addresses.
```

Insert this new section immediately after Phase 1a, before `## Phase 2: Figures`:

````markdown
## Phase 1b: Notation Cross-Check (Opus)

This is the step that distinguishes an agent from an OCR engine. OCR classifies each
glyph in isolation. An agent reads the surrounding mathematics and infers which glyph
was *meant*: a subscript rendered `o` is almost always `0` when its neighbours are
indexed `x_1, x_2`; `ν` and `v` are indistinguishable in scanned serif type but decided
by whether the symbol is used elsewhere as a frequency or a velocity.

Run one Opus subagent per chunk, over the same page ranges Phase 1a used. Launch
concurrently within a chapter, after that chapter's Phase 1a chunks have all landed.

```
You are proofreading LaTeX source against the scanned pages it was typeset from.

Inputs:
- Scanned pages X–Y (attached)
- The generated source: books/<BOOK_NAME>/latex/chNN/*.tex covering those pages
- Symbol inventory established so far in this chapter: <list>

Correct ONLY glyph and notation errors that the mathematical context resolves:
- 0/o/O, 1/l/I, 2/z, 5/S, 8/B in subscripts, superscripts, and indices
- ν/v, ρ/p, κ/k, μ/u, ω/w, ε/e, χ/x, τ/t, γ/y
- × vs x, ∈ vs e, ∨ vs v, − vs -
- sub- vs superscript placement
- dropped hats, bars, tildes, primes, and vector arrows
- misread summation, product, and integral bounds
- misread equation and theorem cross-reference numbers

Rules:
- Resolve each candidate by how the symbol is used elsewhere in the chapter, not by
  how it looks. State that reasoning in the rationale.
- Never restyle prose. Never rewrite text that is correct but phrased differently
  than you would phrase it. Never touch \label or \ref keys that already resolve.
- If context does NOT resolve an ambiguity, leave the source alone and add
  % UNCLEAR: [description, page X]. Never guess.
- NEVER use \qed or \blacksquare or \hfill$\blacksquare$ inside
  \begin{proof}...\end{proof}. The proof environment auto-adds the QED symbol.
- Theorem-like environments share one counter — do not renumber them.

Output: apply the edits, then report one line per correction:
  chNN/secNN_M.tex:LINE  was → now  (reason)
```
````

- [ ] **Step 4: Update the remaining phases**

In Phase 2, change `latex/figures/chNN/` to `books/<BOOK_NAME>/latex/figures/chNN/` and note that the placeholder-replacement subagent runs on Sonnet.

Retitle Phase 3 to `## Phase 3: Back Matter (Sonnet)`.

Retitle Phase 4 to `## Phase 4: Verification (Opus)` and change its `/compile-fix` line to note the compile-fix loop itself runs on Sonnet while the TOC comparison runs on Opus. Change its step 1 to `python scripts/inventory_check.py --book <BOOK_NAME>`.

Change the `## Output` section's build line to `./scripts/build.sh <BOOK_NAME>`.

- [ ] **Step 5: Update the Critical Rules table**

Replace the row `| Branch \`output/<name>\`, never commit content to \`main\` | Framework stays reusable |` with:

```markdown
| One branch: `master`. Each book in `books/<name>/` | Per-book branches all claimed the same `latex/ch01/` paths, so they could never merge and the working tree mixed books together |
| Never typeset the copyright page | No ©, ISBN, Library of Congress number, "all rights reserved", publisher name, imprint, or address. Title, author, and edition only. This also removes a chunk of content-filter pressure — publisher and copyright text is exactly the recognizable metadata that trips it |
| Sonnet transcribes, Opus cross-checks | Bulk transcription is tedious but specified; resolving a glyph by mathematical context is the judgment OCR cannot do. See Model Tiering |
```

Change the row `| Build into \`latex/build/\`, PDFs to \`latex/\` root |` to `| Build into \`books/<name>/build/\`, PDF to \`books/<name>/\` |`.

- [ ] **Step 6: Verify no stale paths remain**

Run:
```bash
grep -n "output/<\|output/\$\|latex/ch\|docs/progress\|repo-root book.conf" skills/pdf-to-latex.md || echo "no stale paths"
```
Expected: `no stale paths`. Any hit is a path the rewrite missed.

Run: `grep -c "opus\|sonnet" skills/pdf-to-latex.md`
Expected: at least 10.

- [ ] **Step 7: Commit**

```bash
git add skills/pdf-to-latex.md
git commit -m "docs: single-branch layout, copyright rule, and Sonnet/Opus tiering in conversion skill"
```

---

### Task 10: Remove legacy paths, update project rules and README

**Files:**
- Delete: `latex/` (entire tree), repo-root `book.conf`, `docs/progress.md`
- Modify: `.claude/CLAUDE.md`
- Modify: `README.md`
- Create: `scripts/extract_figures_v2.py` (promote from untracked), plus the three salvaged scripts from `div_grad_curl`

**Interfaces:**
- Consumes: `scripts/check_repo_layout.py`
- Produces: a repo with no legacy paths — `python scripts/check_repo_layout.py` passes completely.

- [ ] **Step 1: Salvage framework scripts committed only on div_grad_curl**

```bash
git checkout output/div_grad_curl_and_all_that -- \
    scripts/extract_figures_ocr.py \
    scripts/extract_figures_roman.py \
    scripts/ocr_extract.py
git add scripts/extract_figures_ocr.py scripts/extract_figures_roman.py scripts/ocr_extract.py
```

- [ ] **Step 2: Promote the one reusable untracked script**

`extract_figures_v2.py` is generic (argparse `--pdf/--out/--dpi`). Change its `--out` default to reflect the new layout, then stage it:

```bash
python - <<'EOF'
import pathlib, re
p = pathlib.Path("scripts/extract_figures_v2.py")
t = p.read_text(encoding="utf-8")
t = t.replace('default="latex/figures"', 'default="books/<book>/latex/figures"')
t = t.replace("(default: latex/figures)", "(default: books/<book>/latex/figures)")
p.write_text(t, encoding="utf-8")
EOF
git add scripts/extract_figures_v2.py
```

`check_clean_textbook.py` and `codex_rewrite_chapter.ps1` are **not** salvaged — both hardcode the discarded `ai_ch02` / `ai_clean_chNN` scratch paths and the Option Volatility Pricing chapter 2. `scripts/check_repo_layout.py` from Task 1 is the generic replacement.

- [ ] **Step 3: Remove legacy tracked paths**

```bash
git rm -r --quiet latex/
git rm --quiet book.conf docs/progress.md
```

- [ ] **Step 4: Remove untracked scratch from the working tree**

```bash
rm -rf latex/ scripts/check_clean_textbook.py scripts/codex_rewrite_chapter.ps1
ls latex 2>/dev/null && echo "STILL PRESENT - investigate" || echo "latex/ gone"
```

`ocr_output/` (245 MB) and `ocr_output_previous_20260602_170150/` (65 MB) are now gitignored. They are left on disk deliberately — delete them manually when you no longer want them; they are regenerable from the source PDF.

- [ ] **Step 5: Update .claude/CLAUDE.md**

In the `## Build` section, replace:

```markdown
- `scripts/build.sh` reads `BOOK_NAME` from repo-root `book.conf`
- All aux files → `latex/build/`, PDFs → `latex/` root
```

with:

```markdown
- `scripts/build.sh <book_name>` reads `books/<book_name>/book.conf`
- All aux files → `books/<name>/build/`, PDF → `books/<name>/<name>.pdf`
```

Replace the entire `## Branches` section:

```markdown
## Branches
- **One branch: `master`.** Each book lives in `books/<book_name_snake_case>/`
- Per-book `output/*` branches are retired — they all claimed the same `latex/ch01/`
  paths, so they could never merge and the working tree mixed chapters from different books
- Feature work on the framework uses `feature/`, `fix/`, `docs/`, `refactor/`
```

Add to the `## LaTeX Conventions` section:

```markdown
### Copyright
- Title page carries **title, author, edition only**
- Never typeset the copyright page: no ©, ISBN, Library of Congress number,
  "all rights reserved", publisher name, imprint, or address
```

- [ ] **Step 6: Update README.md**

Rewrite the `## Project Structure` block to match the `books/` layout, replacing the `latex/` subtree with:

```
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
```

Add `check_repo_layout.py` and `import_book.sh` to the `scripts/` listing, and remove the `docs/progress.md` line from the `docs/` listing.

Update the build commands in the quick-start block:

```bash
./scripts/build.sh <book_name>          # Full book
./scripts/build.sh <book_name> 3        # Chapter 3 only
./scripts/build.sh <book_name> clean    # Remove build artifacts
```

- [ ] **Step 7: Run the validator — it must now pass completely**

Run: `python scripts/check_repo_layout.py`
Expected: `Layout OK`, exit 0. Any remaining violation must be fixed before committing.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "refactor: remove legacy latex/ tree, update project rules and README for books/ layout"
```

---

### Task 11: Full verification

**Files:** none modified

**Interfaces:**
- Consumes: everything above
- Produces: evidence that all five books are complete and building before any branch is deleted.

- [ ] **Step 1: Validator**

Run: `python scripts/check_repo_layout.py`
Expected: `Layout OK`

- [ ] **Step 2: Content counts match the baseline**

Run:
```bash
for n in econometrics_hayashi applied_partial_differential_equations \
         asymptotic_theory_white div_grad_curl_and_all_that \
         a_first_course_in_monte_carlo_methods; do
    printf "%s: chapters=%s png=%s\n" "$n" \
      "$(find books/$n/latex -maxdepth 1 -type d -name 'ch*' | wc -l)" \
      "$(find books/$n/latex -name '*.png' | wc -l)"
done
```
Expected, matching the Global Constraints:
```
econometrics_hayashi: chapters=10 png=30
applied_partial_differential_equations: chapters=14 png=391
asymptotic_theory_white: chapters=8 png=0
div_grad_curl_and_all_that: chapters=4 png=205
a_first_course_in_monte_carlo_methods: chapters=10 png=0
```

- [ ] **Step 3: Copyright scan over the whole repo**

Run:
```bash
git grep -inE "ISBN|all rights reserved|library of congress|\\\\textcopyright" -- books/ || echo "CLEAN"
```
Expected: `CLEAN`

- [ ] **Step 4: Build all five books**

```bash
for n in econometrics_hayashi applied_partial_differential_equations \
         asymptotic_theory_white div_grad_curl_and_all_that \
         a_first_course_in_monte_carlo_methods; do
    echo "=== $n ==="
    ./scripts/build.sh "$n" || echo "BUILD FAILED: $n"
done
```
Expected: five `Done: <name>.pdf (<size>)` lines. The three scrubbed books are rebuilt here so their PDFs match the cleaned source.

A build failure is a real finding, not a step to skip — if a book fails, capture the log path it prints and report it before proceeding to Task 12. Do not delete branches while any book fails to build.

- [ ] **Step 5: Inventory each book**

```bash
for n in econometrics_hayashi applied_partial_differential_equations \
         asymptotic_theory_white div_grad_curl_and_all_that \
         a_first_course_in_monte_carlo_methods; do
    echo "=== $n ==="
    python scripts/inventory_check.py --book "$n"
done
```
Expected: a populated table per book, no chapter showing zero sections.

- [ ] **Step 6: Unit tests still pass**

Run: `python -m pytest scripts/ -v`
Expected: PASS. `test_compile_fix.py` may need its own path fixes from Task 8 — if it fails on a `latex/` path, fix it and note it in the commit.

- [ ] **Step 7: Commit any fixes**

```bash
git add -A
git commit -m "fix: verification pass corrections" || echo "nothing to commit"
```

---

### Task 12: Delete branches

Runs only after Task 11 passes. This is the destructive step.

**Files:** none

**Interfaces:**
- Consumes: Task 11's passing verification
- Produces: `master` as the only branch, local and remote.

- [ ] **Step 1: Re-confirm the gate**

Run: `python scripts/check_repo_layout.py && git status --porcelain | grep -v '^??' || echo "clean and valid"`
Expected: `Layout OK` and `clean and valid`. If either fails, stop — do not delete anything.

- [ ] **Step 2: Confirm archive tags exist locally**

Run: `git tag -l 'archive/*' | wc -l`
Expected: `8`. These are the rollback path. If the count is wrong, recreate the missing tags before deleting.

- [ ] **Step 3: Merge the working branch into master**

```bash
git checkout master
git merge --no-ff refactor/consolidate-books -m "refactor: consolidate all books onto master under books/"
```
Expected: a clean merge — `master` has not moved since Task 0 cut the branch from it.

Run: `python scripts/check_repo_layout.py`
Expected: `Layout OK` on `master` too. If the merge lost anything, stop before pushing.

- [ ] **Step 4: Push master**

```bash
git push origin master
```
Expected: success. The remote must have the consolidated content before its branches are removed.

- [ ] **Step 5: Delete local branches**

```bash
for b in econometrics_hayashi applied_partial_differential_equations \
         asymptotic_theory_white div_grad_curl_and_all_that \
         a_first_course_in_monte_carlo_methods \
         option_volatility_pricing applied_pde_solutions_manual; do
    git branch -D "output/$b"
done
git branch -D dev
git branch -d refactor/consolidate-books
```

Step 3 switched to `master`, so neither `output/a_first_course_in_monte_carlo_methods` nor the working branch is checked out, and both can be deleted. If `git branch --show-current` does not print `master`, stop.

`-D` rather than `-d` for the `output/*` branches is deliberate: their content was imported, not merged, so `-d` would refuse. The working branch uses `-d` — it *was* merged in Step 3, and a refusal there is a real signal that the merge did not happen.

- [ ] **Step 6: Delete remote branches**

```bash
for b in applied_partial_differential_equations applied_pde_solutions_manual \
         asymptotic_theory_white div_grad_curl_and_all_that econometrics_hayashi; do
    git push origin --delete "output/$b"
done
git push origin --delete fix/content-filter-phase0-subagent
```

Only these six exist on the remote — `output/option_volatility_pricing` and `output/a_first_course_in_monte_carlo_methods` were never pushed. Run `git branch -r` first to confirm the live list rather than trusting this one.

- [ ] **Step 7: Verify one branch remains**

Run: `git branch -a`
Expected: only `* master` and `remotes/origin/master`.

Run: `git ls-remote --tags origin 'refs/tags/archive/*'`
Expected: empty — archive tags must never reach the public remote.

---

### Task 13: Final state report

**Files:** none modified

- [ ] **Step 1: Summarize the result**

```bash
echo "=== branches ==="; git branch -a
echo "=== local archive tags (rollback path) ==="; git tag -l 'archive/*'
echo "=== books ==="; ls -1 books/
echo "=== repo size ==="; du -sh .git
```

- [ ] **Step 2: Report to the user**

State plainly: which books are in `books/`, that `master` is the only branch, that archive tags exist locally only and can be deleted with `git tag -d 'archive/*'` once they are confident, and that `ocr_output*/` still occupies 310 MB on disk awaiting manual deletion.

Report any book that failed to build, with its log path. Do not describe the migration as complete if any step was skipped.
