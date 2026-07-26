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
