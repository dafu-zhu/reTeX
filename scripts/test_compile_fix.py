#!/usr/bin/env python3
"""Tests for compile_fix.py fix patterns."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest

import compile_fix
from compile_fix import (
    fix_boxed_environment,
    fix_defbox_in_math,
    fix_double_math_boxed,
    fix_boxed_display_math,
    fix_missing_partial_backslash,
    fix_duplicate_qed,
    fix_undefined_control_sequences,
    fix_double_superscript,
    fix_double_subscript,
    parse_log_errors,
    _detect_wrap_width,
    _unwrap_log_lines,
)

def test(name, fix_fn, input_str, expected, expected_count=None):
    result, count = fix_fn(input_str)
    ok = result == expected
    if expected_count is not None:
        ok = ok and count == expected_count
    status = 'PASS' if ok else 'FAIL'
    print(f'  {status}: {name}')
    if not ok:
        print(f'    Input:    {input_str!r}')
        print(f'    Expected: {expected!r}')
        print(f'    Got:      {result!r}')
        if expected_count is not None:
            print(f'    Expected count: {expected_count}, got: {count}')
    return ok

# pytest's default python_functions pattern ("test*") matches this bare
# helper too, and pytest would try to collect it as a test item and inject
# its positional args as fixtures. It is a helper, not a test — exclude it.
test.__test__ = False

passed = 0
failed = 0

def run(name, fix_fn, inp, exp, cnt=None):
    global passed, failed
    if test(name, fix_fn, inp, exp, cnt):
        passed += 1
    else:
        failed += 1


def main():
    """Drive all checks and return a process exit code.

    Guarded by `if __name__ == "__main__":` below so that importing this
    module (as pytest does during collection, since it matches test_*.py)
    never runs the checks or calls sys.exit() as a side effect — it only
    defines functions.
    """
    global passed, failed
    passed = 0
    failed = 0

    print('Testing fix patterns...\n')

    _run_checks()

    print(f'\n{passed} passed, {failed} failed')
    return 1 if failed else 0


def _run_checks():
    # boxed environment
    run('boxed env basic',
        fix_boxed_environment,
        r'\begin{boxed}x^2 + y^2\end{boxed}',
        r'\boxed{x^2 + y^2}', 1)

    run('boxed env no match',
        fix_boxed_environment,
        r'\boxed{x}',
        r'\boxed{x}', 0)

    # defbox in math
    run('defbox basic',
        fix_defbox_in_math,
        r'\begin{defbox}E[X] = \mu\end{defbox}',
        r'\boxed{E[X] = \mu}', 1)

    # double math boxed
    run('double math $',
        fix_double_math_boxed,
        r'\boxed{$a+b$}',
        r'\boxed{a+b}', 1)

    # boxed display math
    run('boxed \\[\\]',
        fix_boxed_display_math,
        r'\boxed{\[a+b\]}',
        r'\[\boxed{a+b}\]', 1)

    # missing partial
    run('missing \\partial',
        fix_missing_partial_backslash,
        r'\frac{partial}{partial x}',
        r'\frac{\partial}{\partial x}', 1)

    run('correct \\partial unchanged',
        fix_missing_partial_backslash,
        r'\frac{\partial}{\partial x}',
        r'\frac{\partial}{\partial x}', 0)

    # duplicate QED
    run('\\qed in proof',
        fix_duplicate_qed,
        '\\begin{proof}\nSome proof.\n\\qed\n\\end{proof}',
        '\\begin{proof}\nSome proof.\n\\end{proof}', 1)

    run('\\qedhere preserved',
        fix_duplicate_qed,
        '\\begin{proof}\nSome proof.\n\\qedhere\n\\end{proof}',
        '\\begin{proof}\nSome proof.\n\\qedhere\n\\end{proof}', 0)

    run('\\hfill$\\blacksquare$ removed',
        fix_duplicate_qed,
        '\\begin{proof}\nDone.\n\\hfill$\\blacksquare$\n\\end{proof}',
        '\\begin{proof}\nDone.\n\\end{proof}', 1)

    # undefined control sequences
    run('\\textup → \\textrm',
        fix_undefined_control_sequences,
        r'\textup{hello}',
        r'\textrm{hello}', 1)

    run('\\bold → \\mathbf',
        fix_undefined_control_sequences,
        r'\bold{x}',
        r'\mathbf{x}', 1)

    # double superscript
    run('double superscript',
        fix_double_superscript,
        'x^2^3',
        'x^{2^{3}}', 1)

    # double subscript
    run('double subscript',
        fix_double_subscript,
        'a_i_j',
        'a_{i_{j}}', 1)

    # file paths should NOT be touched
    run('subscript in file path preserved',
        fix_double_subscript,
        r'\includegraphics[width=0.8\textwidth]{figures/ch01/fig_1_2_1.png}',
        r'\includegraphics[width=0.8\textwidth]{figures/ch01/fig_1_2_1.png}', 0)

    run('subscript in label preserved',
        fix_double_subscript,
        r'\label{fig:1_2_3}',
        r'\label{fig:1_2_3}', 0)

    run('superscript in file path preserved',
        fix_double_superscript,
        r'\input{ch01/sec01_2}',
        r'\input{ch01/sec01_2}', 0)


# ---------------------------------------------------------------------------
# parse_log_errors
#
# These exist because compile_latex() passes -file-line-error, which makes
# pdflatex emit "file.tex:LINE: message" *instead of* "! message". The parser
# used to match only `^!`, so it found zero errors in every log this repo
# produces and reported every broken book as "Compilation successful
# (0 errors)". Nothing covered it, so nothing caught it.
# ---------------------------------------------------------------------------

BANNER = "This is pdfTeX, Version 3.141592653-2.6-1.40.25 (MiKTeX 24.1) (preloaded format=pdflatex)"


def write_log(tmp_path, lines):
    path = tmp_path / "main.log"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def book_path(*parts):
    """An absolute path under the repo root, as pdflatex would print it."""
    return os.path.join(compile_fix.ROOT, "books", "b", "latex", *parts)


def test_file_line_error_form_is_parsed(tmp_path):
    """The -file-line-error shape — the only shape this repo's logs contain."""
    sec = book_path("ch01", "sec01_1.tex")
    log = write_log(tmp_path, [
        BANNER,
        f"({book_path('main.tex')}",
        f"{sec}:3: Undefined control sequence.",
        r"l.3 This uses \bfNope",
        f"{sec}:7: LaTeX Error: File `' not found.",
        ")",
    ])
    errors = parse_log_errors(log)
    assert len(errors) == 2
    assert errors[0]["line"] == 3
    assert errors[0]["message"] == "Undefined control sequence."
    assert errors[1]["line"] == 7
    assert errors[1]["message"] == "LaTeX Error: File `' not found."
    # Windows drive letters must not truncate the filename at "D:".
    assert errors[0]["file"].endswith("ch01/sec01_1.tex")
    assert not errors[0]["file"].startswith("D:")


def test_log_without_any_bang_lines_is_not_reported_clean(tmp_path):
    """The exact regression: no `^!` line anywhere, yet the book is broken."""
    sec = book_path("ch02", "sec02_1.tex")
    log = write_log(tmp_path, [
        BANNER,
        f"{sec}:12: LaTeX Error: Environment align undefined.",
    ])
    assert not any(line.startswith("!")
                   for line in open(log, encoding="utf-8").read().splitlines())
    assert len(parse_log_errors(log)) == 1


def test_classic_bang_form_is_still_parsed(tmp_path):
    """scripts/build.sh does not pass -file-line-error, so its logs use `! `."""
    log = write_log(tmp_path, [
        BANNER,
        f"({book_path('ch01', 'sec01_1.tex')}",
        "! Undefined control sequence.",
        r"l.3 This uses \bfNope",
        "! LaTeX Error: File `' not found.",
        "l.7 \\includegraphics[width=1in]{}",
    ])
    errors = parse_log_errors(log)
    assert len(errors) == 2
    # TeX echoes the offending line *below* the message, not above it.
    assert [e["line"] for e in errors] == [3, 7]
    assert errors[0]["file"].endswith("ch01/sec01_1.tex")


def test_warnings_are_not_errors(tmp_path):
    """A false positive here would send the Phase 4 ladder chasing nothing."""
    log = write_log(tmp_path, [
        BANNER,
        "LaTeX Warning: Reference `nosuch' on page 1 undefined on input line 3.",
        "LaTeX Warning: Citation `nosuch' on page 1 undefined on input line 3.",
        "Overfull \\hbox (25.0pt too wide) in paragraph at lines 9--10",
        "LaTeX Font Warning: Font shape `OT1/cmr/bx/sc' undefined",
        "Package hyperref Warning: Token not allowed in a PDF string.",
    ])
    assert parse_log_errors(log) == []


def test_identical_records_are_deduplicated(tmp_path):
    sec = book_path("ch01", "sec01_1.tex")
    log = write_log(tmp_path, [BANNER] + [f"{sec}:5: Undefined control sequence."] * 4)
    assert len(parse_log_errors(log)) == 1


def test_same_message_at_different_lines_is_kept(tmp_path):
    sec = book_path("ch01", "sec01_1.tex")
    log = write_log(tmp_path, [
        BANNER,
        f"{sec}:5: Undefined control sequence.",
        f"{sec}:9: Undefined control sequence.",
    ])
    assert len(parse_log_errors(log)) == 2


def test_hard_wrapped_log_is_unwrapped(tmp_path):
    """TeX wraps at max_print_line (79) mid-word — and mid-filename."""
    sec = "books/b/latex/ch01/sec01_1.tex"
    record = f"{sec}:3: Undefined control sequence."
    padded = record.ljust(100)  # force a wrap
    wrapped = [padded[i:i + 79] for i in range(0, len(padded), 79)]
    # Enough 79-char lines to look like a genuinely wrapped log.
    filler = ["x" * 79, "y" * 79, "z" * 79, "w" * 79]
    log = write_log(tmp_path, wrapped + filler)

    assert _detect_wrap_width([len(l) for l in wrapped + filler]) == 79
    errors = parse_log_errors(log)
    assert len(errors) == 1
    assert errors[0]["line"] == 3
    assert errors[0]["message"].startswith("Undefined control sequence.")


def test_equal_length_error_lines_are_never_merged(tmp_path):
    """Consecutive same-length errors must not be mistaken for a wrapped log.

    The same undefined macro, reported at the same path, at line numbers with
    the same digit count, produces byte-identical-length lines. Merging them
    would silently discard every error but the first.
    """
    sec = book_path("ch01", "sec01_1.tex")
    lines = [BANNER] + [
        f"{sec}:{n}: LaTeX Error: Something went wrong here and this line "
        f"is comfortably longer than seventy-nine characters."
        for n in range(11, 18)
    ]
    assert len({len(l) for l in lines[1:]}) == 1, "lines must be equal length"
    assert _unwrap_log_lines("\n".join(lines)) == lines
    assert len(parse_log_errors(write_log(tmp_path, lines))) == 7


def test_genuinely_unwrapped_log_is_left_alone(tmp_path):
    """Varied line lengths — nothing should be joined."""
    lines = [BANNER, "(./main.tex", "x" * 120, "y" * 95, "z" * 61, ")"]
    assert _detect_wrap_width([len(l) for l in lines]) is None
    assert _unwrap_log_lines("\n".join(lines)) == lines


def test_non_error_colon_lines_are_ignored(tmp_path):
    """Package banners and timestamps also contain colons."""
    log = write_log(tmp_path, [
        BANNER,
        "Package: graphicx 2021/09/16 v1.2d Enhanced LaTeX Graphics",
        "Document Class: book 2021/10/04 v1.4n Standard LaTeX document class",
        "File: preamble.tex Graphic file (type png)",
        "\\openout2 = `ch01/ch01.aux'.",
        " 62i,5n,68p,282b,181s stack positions out of 10000i,1000n,20000p",
    ])
    assert parse_log_errors(log) == []


if __name__ == "__main__":
    sys.exit(main())
