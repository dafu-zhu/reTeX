#!/usr/bin/env python3
"""Tests for compile_fix.py fix patterns."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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

passed = 0
failed = 0

def run(name, fix_fn, inp, exp, cnt=None):
    global passed, failed
    if test(name, fix_fn, inp, exp, cnt):
        passed += 1
    else:
        failed += 1

print('Testing fix patterns...\n')

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

print(f'\n{passed} passed, {failed} failed')
sys.exit(1 if failed else 0)
