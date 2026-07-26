"""Verify LaTeX environments balance across a chapter's section files.

Why this exists
---------------
Phase 1a splits a chapter across concurrent chunk agents, each owning a page
range. A section — or a proof, or a worked example — routinely straddles a
chunk boundary, so an agent may legitimately leave an environment OPEN at the
end of its last file, expecting the next chunk's file to close it.

That works only if the closer actually exists. If the continuing agent starts
a fresh `\\begin{proof}` instead of closing the open one, or omits the closer
entirely, the chapter fails to compile with an error pointing at the end of
the document rather than at the boundary where the mistake happened.

`check_chapter_wrapper.py` cannot catch this: it verifies that every section
file is *referenced* by the wrapper, not that the concatenation is
well-formed. This script closes that gap by walking the files in `% PAGES:`
order — the same order the wrapper inputs them — and tracking the environment
stack across file boundaries.

Comment lines are ignored, so a file whose comments discuss `\\begin{proof}`
(as continuation notes often do) is not miscounted.

Usage:
    python scripts/check_env_balance.py --book <name> [--chapter N]

Exits non-zero when a chapter's environments do not balance.
"""
import argparse
import os
import pathlib
import re
import sys

BEGIN_END = re.compile(r"\\(begin|end)\{(\w+\*?)\}")
PAGES = re.compile(r"% PAGES:\s*(\d+)")


def _validate_book_name(name):
    if not name or "/" in name or "\\" in name or ".." in name:
        raise SystemExit(
            f"Error: invalid book name {name!r} "
            "(must be a plain directory name -- no '/', '\\', or '..')"
        )
    return name


def check_chapter(ch_dir):
    """Return (violations, ordered_rows) for one chapter directory."""
    prefix = "sec" + ch_dir.name[2:]
    rows = []
    for f in sorted(ch_dir.glob(f"{prefix}_*.tex")):
        text = f.read_text(encoding="utf-8", errors="replace")
        m = PAGES.search(text.split("\n")[0])
        rows.append((int(m.group(1)) if m else 10**9, f.name, text))
    rows.sort()

    stack = []
    violations = []
    for _, name, text in rows:
        body = "\n".join(
            l for l in text.split("\n") if not l.lstrip().startswith("%")
        )
        for m in BEGIN_END.finditer(body):
            kind, env = m.group(1), m.group(2)
            if kind == "begin":
                stack.append((env, name))
            else:
                if stack and stack[-1][0] == env:
                    stack.pop()
                else:
                    violations.append(
                        f"{ch_dir.name}/{name}: \\end{{{env}}} with no matching "
                        f"\\begin — innermost open is "
                        f"{stack[-1][0] if stack else '(none)'}"
                    )
    for env, name in stack:
        violations.append(
            f"{ch_dir.name}/{name}: \\begin{{{env}}} is never closed by any "
            f"later section file in this chapter"
        )
    return violations, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", required=True, help="Book name under books/")
    parser.add_argument("--chapter", type=int, help="Chapter number (default: all)")
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()

    _validate_book_name(args.book)
    latex = args.root / "books" / args.book / "latex"
    if not latex.is_dir():
        raise SystemExit(f"No such book: {args.book} (expected {latex})")

    if args.chapter is not None:
        ch_dirs = [latex / f"ch{args.chapter:02d}"]
        if not ch_dirs[0].is_dir():
            raise SystemExit(f"No such chapter directory: {ch_dirs[0]}")
    else:
        ch_dirs = sorted(d for d in latex.glob("ch[0-9][0-9]") if d.is_dir())

    all_violations = []
    for ch_dir in ch_dirs:
        violations, rows = check_chapter(ch_dir)
        if not rows:
            continue
        if violations:
            all_violations.extend(violations)
        else:
            print(f"Env balance OK ({ch_dir.name}): {len(rows)} section file(s)")

    for v in all_violations:
        print(f"FAIL: {v}")
    if all_violations:
        print(f"\n{len(all_violations)} unbalanced environment(s)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
