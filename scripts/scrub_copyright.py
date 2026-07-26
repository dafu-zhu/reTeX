"""Remove reproduced copyright pages and publisher imprints from imported books.

Idempotent: re-running on already-scrubbed files is a no-op.

Exits non-zero if any target file still contains a forbidden copyright
marker after scrubbing -- whether because a regex only partially matched
(rewrote the file but left markers behind) or because it did not match at
all (left the file completely unchanged while markers remain). Both cases
are treated as failures, never as silent success, because this script is
meant to run unattended on future book imports.

Usage:
    python scripts/scrub_copyright.py [--root PATH]
"""
import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from check_repo_layout import FORBIDDEN  # noqa: E402  (path setup must run first)

BOOKS = "books"


def scrub_applied_pde(text: str) -> str:
    # Publisher imprint block on the title page. The closing literal
    # ("...Upper Saddle River, New Jersey 07458}\n") is a multi-token
    # address string unlikely to recur elsewhere in the document, so a
    # plain non-greedy match to it is safe.
    text = re.sub(
        r"\{\\large PEARSON.*?\{\\normalsize Upper Saddle River, New Jersey 07458\}\n",
        "",
        text,
        flags=re.DOTALL,
    )
    # The whole copyright page, from its comment marker to the following
    # \cleardoublepage. Bounded so the match can never cross \mainmatter --
    # the LaTeX book-class marker for the end of front matter -- even if
    # the copyright block's own trailing \cleardoublepage is missing or
    # duplicated elsewhere in the document. Without this bound, a missing
    # or relocated \cleardoublepage lets the (?:...)*.? run past \mainmatter
    # and eat real chapter content; with it, a malformed block simply fails
    # to match (caught by the forbidden-marker re-scan below) instead of
    # silently deleting book text.
    text = re.sub(
        r"% Copyright page\n(?:(?!\\mainmatter)[\s\S])*?\\cleardoublepage\n",
        "",
        text,
    )
    return text


def scrub_asymptotic(text: str) -> str:
    # Publisher imprint block on the title page. As above, the closing
    # literal is a distinctive multi-token line, so an unbounded non-greedy
    # match to it is safe.
    text = re.sub(
        r"\{\\large Academic Press\}.*?London \\quad Sydney \\quad Tokyo \\quad Toronto\}\n",
        "",
        text,
        flags=re.DOTALL,
    )
    # Copyright page: from the cover-photo credit through the closing
    # \clearpage. This file has no \mainmatter marker to anchor on --
    # \mainmatter lives in main.tex, not frontmatter.tex, for this book --
    # so instead the match is bound to the literal end of the file (\Z):
    # frontmatter.tex is a standalone \input fragment whose only content is
    # the title page followed by the copyright page, so the true closing
    # \clearpage is always the last thing in the file. A non-greedy .*?
    # would normally stop at the first \clearpage it finds; requiring
    # \s*\Z after it instead forces the match to the last \clearpage in the
    # file, so an earlier or relocated \clearpage elsewhere in the document
    # can never falsely terminate the match early or bleed past appended
    # content -- a mismatch here fails closed (caught by the forbidden-
    # marker re-scan) rather than eating unrelated text.
    text = re.sub(
        r"\\thispagestyle\{empty\}\n\\vspace\*\{\\fill\}\n"
        r"\\noindent\\textit\{Cover photo credit:\}.*?\\clearpage\s*\Z",
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


# applied_partial_differential_equations was removed from the repo (it carried
# pre-existing malformed markup inherited from its source branch), so its
# scrubber above is retained only as a worked example of the pattern.
TARGETS = [
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

    exit_code = 0

    for rel, scrubber in TARGETS:
        path = args.root / BOOKS / rel
        if not path.is_file():
            print(f"SKIP (absent): {rel}")
            continue
        original = path.read_text(encoding="utf-8")
        scrubbed = scrubber(original)
        if scrubbed == original:
            print(f"unchanged: {rel}")
        else:
            # newline="\n" pins LF line endings regardless of platform or
            # core.autocrlf, so a re-run on a clone with autocrlf=false
            # never rewrites these files to CRLF.
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(scrubbed)
            removed = len(original) - len(scrubbed)
            print(f"scrubbed:  {rel} (-{removed} bytes)")

        # Re-scan the file's final content -- whether just rewritten or left
        # unchanged -- for forbidden copyright markers. A survivor means the
        # scrub is incomplete: either a regex fired but only partially
        # matched (rewrote the file, markers still present), or no regex
        # matched at all (the input's shape no longer matches what the
        # scrubber expects). Both must fail loudly; neither is safe to wave
        # through as "unchanged" or "scrubbed".
        for pattern in FORBIDDEN:
            match = pattern.search(scrubbed)
            if match:
                print(
                    f"FAIL: {rel} still contains forbidden marker "
                    f"{pattern.pattern!r} after scrubbing "
                    f"(matched: {match.group()!r})"
                )
                exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
