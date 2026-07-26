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
