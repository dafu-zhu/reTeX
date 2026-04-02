#!/usr/bin/env python3
"""
Automated LaTeX compile → diagnose → fix → recompile loop.

Reads .tex files, applies deterministic regex-based fixes for known error
patterns, compiles with pdflatex, and repeats until 0 errors or max iterations.

Usage:
    python scripts/compile_fix.py                  # Full compile-fix loop
    python scripts/compile_fix.py --fix-only       # Apply fixes without compiling
    python scripts/compile_fix.py --compile-only   # Compile without fixing
    python scripts/compile_fix.py --chapter 3      # Single chapter only
    python scripts/compile_fix.py --max-iter 5     # Limit iterations (default: 10)
"""
import argparse
import glob
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LATEX_DIR = os.path.join(ROOT, 'latex')
BUILD_DIR = os.path.join(LATEX_DIR, 'build')
BOOK_CONF = os.path.join(ROOT, 'book.conf')


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def get_book_name():
    if os.path.exists(BOOK_CONF):
        with open(BOOK_CONF) as f:
            for line in f:
                m = re.match(r'^BOOK_NAME\s*=\s*["\']?([^"\'#\n]+)', line)
                if m:
                    return m.group(1).strip()
    return 'textbook'


def read_tex(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def write_tex(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def collect_tex_files(chapter=None):
    """Return sorted list of .tex file paths to fix."""
    if chapter is not None:
        ch_dir = os.path.join(LATEX_DIR, f'ch{chapter:02d}')
        pattern = os.path.join(ch_dir, '*.tex')
    else:
        pattern = os.path.join(LATEX_DIR, 'ch*', '*.tex')
    files = sorted(glob.glob(pattern))
    # Also include preamble and backmatter
    if chapter is None:
        preamble = os.path.join(LATEX_DIR, 'preamble.tex')
        if os.path.exists(preamble):
            files.insert(0, preamble)
        for bm in sorted(glob.glob(os.path.join(LATEX_DIR, 'backmatter', '*.tex'))):
            files.append(bm)
    return files


# ---------------------------------------------------------------------------
# Compilation
# ---------------------------------------------------------------------------

def compile_latex(chapter=None):
    """Run pdflatex and return (success, error_count, errors_list)."""
    os.makedirs(BUILD_DIR, exist_ok=True)

    env = os.environ.copy()
    env['TEXINPUTS'] = f'{LATEX_DIR}//{os.pathsep}{BUILD_DIR}//{os.pathsep}'

    if chapter is not None:
        # Build standalone chapter wrapper
        ch_str = f'{chapter:02d}'
        wrapper = os.path.join(BUILD_DIR, f'ch{ch_str}_standalone.tex')
        with open(wrapper, 'w') as f:
            f.write(f'\\input{{preamble}}\n\\begin{{document}}\n'
                    f'\\include{{ch{ch_str}/ch{ch_str}}}\n\\end{{document}}\n')
        tex_file = wrapper
    else:
        tex_file = os.path.join(LATEX_DIR, 'main.tex')

    cmd = [
        'pdflatex',
        '-interaction=nonstopmode',
        '-file-line-error',
        f'-output-directory={BUILD_DIR}',
        tex_file,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=LATEX_DIR, env=env)
    except FileNotFoundError:
        print('ERROR: pdflatex not found. Install a TeX distribution (texlive-full).')
        sys.exit(1)
    output = result.stdout + result.stderr

    # Parse errors from log file
    basename = os.path.splitext(os.path.basename(tex_file))[0]
    log_file = os.path.join(BUILD_DIR, f'{basename}.log')
    errors = parse_log_errors(log_file) if os.path.exists(log_file) else []

    return len(errors) == 0, len(errors), errors


def parse_log_errors(log_path):
    """Parse pdflatex log for errors. Returns list of dicts."""
    errors = []
    with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
        log_content = f.read()

    # Match "! <error message>" lines
    for m in re.finditer(r'^! (.+?)$', log_content, re.MULTILINE):
        error_msg = m.group(1)
        # Look for file:line info nearby
        context_start = max(0, m.start() - 500)
        context = log_content[context_start:m.end() + 200]

        file_match = re.search(r'([./\w]+\.tex):(\d+):', context)
        file_path = file_match.group(1) if file_match else None
        line_num = int(file_match.group(2)) if file_match else None

        errors.append({
            'message': error_msg,
            'file': file_path,
            'line': line_num,
            'context': context[-200:],
        })

    return errors


# ---------------------------------------------------------------------------
# Fix patterns — each returns (new_content, fix_count)
# ---------------------------------------------------------------------------

def fix_form_feed_bytes(path):
    """Strip 0x0c form feed bytes (sed corruption artifact)."""
    with open(path, 'rb') as f:
        raw = f.read()
    if b'\x0c' in raw:
        cleaned = raw.replace(b'\x0c', b'')
        with open(path, 'wb') as f:
            f.write(cleaned)
        return True
    return False


def fix_boxed_environment(content):
    r"""Replace invalid \begin{boxed}...\end{boxed} with \boxed{...}."""
    count = 0
    def replacer(m):
        nonlocal count
        count += 1
        inner = m.group(1).strip()
        return f'\\boxed{{{inner}}}'
    content = re.sub(
        r'\\begin\{boxed\}(.*?)\\end\{boxed\}',
        replacer, content, flags=re.DOTALL)
    return content, count


def fix_defbox_in_math(content):
    r"""Replace \begin{defbox} inside equation with \boxed{...}."""
    count = 0
    def replacer(m):
        nonlocal count
        count += 1
        inner = m.group(1).strip()
        return f'\\boxed{{{inner}}}'
    content = re.sub(
        r'\\begin\{defbox\}(.*?)\\end\{defbox\}',
        replacer, content, flags=re.DOTALL)
    return content, count


def fix_double_math_boxed(content):
    r"""Fix \boxed{$...$} inside display math → \boxed{...} (strip inner $)."""
    count = 0
    def replacer(m):
        nonlocal count
        count += 1
        inner = m.group(1)
        return f'\\boxed{{{inner}}}'
    content = re.sub(
        r'\\boxed\{\$([^$]+)\$\}',
        replacer, content)
    return content, count


def fix_boxed_display_math(content):
    r"""Fix \boxed{\[...\]} → \[\boxed{...}\]."""
    count = 0
    def replacer(m):
        nonlocal count
        count += 1
        inner = m.group(1).strip()
        return f'\\[\\boxed{{{inner}}}\\]'
    content = re.sub(
        r'\\boxed\{\\?\[(.*?)\\?\]\}',
        replacer, content, flags=re.DOTALL)
    return content, count


def fix_missing_partial_backslash(content):
    r"""Fix \frac{partial}{partial x} → \frac{\partial}{\partial x}."""
    count = 0
    def replacer(m):
        nonlocal count
        count += 1
        var = m.group(1)
        return f'\\frac{{\\partial}}{{\\partial {var}}}'
    content = re.sub(
        r'\\frac\{partial\}\{partial\s+(\w)\}',
        replacer, content)
    return content, count


def fix_duplicate_qed(content):
    r"""Remove manual \qed, \blacksquare inside proof environments."""
    count = 0

    def strip_qed_in_proof(m):
        nonlocal count
        proof_body = m.group(1)
        # Remove \qed (but not \qedhere)
        new_body, n1 = re.subn(r'\s*\\qed\b(?!here)', '', proof_body)
        # Remove \hfill$\blacksquare$
        new_body, n2 = re.subn(r'\s*\\hfill\s*\$\\blacksquare\$', '', new_body)
        # Remove standalone $\blacksquare$
        new_body, n3 = re.subn(r'\s*\$\\blacksquare\$', '', new_body)
        # Remove \hfill\(\blacksquare\)
        new_body, n4 = re.subn(r'\s*\\hfill\s*\\\(\\blacksquare\\\)', '', new_body)
        count += n1 + n2 + n3 + n4
        return f'\\begin{{proof}}{new_body}\\end{{proof}}'

    content = re.sub(
        r'\\begin\{proof\}(.*?)\\end\{proof\}',
        strip_qed_in_proof, content, flags=re.DOTALL)
    return content, count


def fix_foreach_in_pgfplots(content):
    r"""Detect \foreach in pgfplots domain with arithmetic — flag for manual fix."""
    # This one is hard to auto-fix generically, so we just detect and warn
    matches = re.findall(r'\\foreach\s+\\?\w+\s+in\s*\{[^}]*\+[^}]*\}', content)
    return content, 0  # detection only, logged by caller


def fix_undefined_control_sequences(content):
    r"""Fix common undefined control sequence issues."""
    count = 0

    # \E → \mathbb{E} if \E not defined (check if \newcommand{\E} exists)
    # These are handled by preamble macros, skip

    # \textup → \textrm (common alternative)
    new_content, n = re.subn(r'\\textup\b', r'\\textrm', content)
    count += n
    content = new_content

    # \bold → \mathbf
    new_content, n = re.subn(r'\\bold\b', r'\\mathbf', content)
    count += n
    content = new_content

    # \eqref without amsmath — unlikely, but \ref as fallback
    # Skip — amsmath should be in preamble

    return content, count


def fix_mismatched_braces(content):
    """Fix obvious brace mismatches: unclosed { at end of line, missing }."""
    count = 0
    lines = content.split('\n')
    new_lines = []

    for line in lines:
        opens = line.count('{') - line.count('\\{')
        closes = line.count('}') - line.count('\\}')
        # Very conservative: only fix lines where difference is exactly 1
        # and it looks like a simple omission at end of line
        if opens - closes == 1 and line.rstrip().endswith('{'):
            # Don't fix — this is likely a multi-line construct
            pass
        new_lines.append(line)

    return '\n'.join(new_lines), count


def _is_math_line(line):
    """Check if a line is likely in a math context (not a file path, label, etc.)."""
    stripped = line.strip()
    # Skip lines with file paths, includes, labels, comments
    skip_patterns = [
        r'\\includegraphics',
        r'\\input\b',
        r'\\include\b',
        r'\\label\b',
        r'\\ref\b',
        r'\\caption\b',
        r'\\bibliography',
        r'\\url\b',
        r'\\href\b',
        r'\.png',
        r'\.pdf',
        r'\.tex',
    ]
    for pat in skip_patterns:
        if re.search(pat, stripped):
            return False
    # Skip pure comments
    if stripped.startswith('%'):
        return False
    return True


def fix_double_superscript(content):
    r"""Fix double superscript: x^a^b → x^{a^b} — only on math lines."""
    count = 0

    def fix_line(line):
        nonlocal count
        if not _is_math_line(line):
            return line

        def replacer(m):
            nonlocal count
            count += 1
            return f'{m.group(1)}^{{{m.group(2)}^{{{m.group(3)}}}}}'

        return re.sub(r'(\w)\^(\w)\^(\w)', replacer, line)

    lines = content.split('\n')
    content = '\n'.join(fix_line(l) for l in lines)
    return content, count


def fix_double_subscript(content):
    r"""Fix double subscript: x_a_b → x_{a_b} — only on math lines."""
    count = 0

    def fix_line(line):
        nonlocal count
        if not _is_math_line(line):
            return line

        def replacer(m):
            nonlocal count
            count += 1
            return f'{m.group(1)}_{{{m.group(2)}_{{{m.group(3)}}}}}'

        return re.sub(r'(\w)_(\w)_(\w)', replacer, line)

    lines = content.split('\n')
    content = '\n'.join(fix_line(l) for l in lines)
    return content, count


def fix_ampersand_outside_tabular(content):
    r"""Fix stray & outside tabular/align environments — escape as \&."""
    # This is risky to auto-fix globally. Only fix obvious cases:
    # & in regular paragraph text (not inside align, tabular, array, etc.)
    # Skip — too risky for automated fixing
    return content, 0


def fix_missing_item_in_enumerate(content):
    r"""Add \item to bare lines in enumerate/itemize environments."""
    count = 0

    def fix_list_env(m):
        nonlocal count
        env_name = m.group(1)
        body = m.group(2)
        end_tag = m.group(3)

        lines = body.split('\n')
        new_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip empty, comments, \item lines, \begin/\end, labels
            if (not stripped or stripped.startswith('%') or
                stripped.startswith('\\item') or
                stripped.startswith('\\begin') or
                stripped.startswith('\\end') or
                stripped.startswith('\\label')):
                new_lines.append(line)
            else:
                # Non-empty text without \item — might need one
                # Be very conservative: only flag, don't auto-fix
                new_lines.append(line)
        return f'\\begin{{{env_name}}}{body}{end_tag}'

    content = re.sub(
        r'\\begin\{(enumerate|itemize)\}(.*?)(\\end\{\1\})',
        fix_list_env, content, flags=re.DOTALL)
    return content, count


# ---------------------------------------------------------------------------
# Master fix pass
# ---------------------------------------------------------------------------

ALL_FIXES = [
    ('boxed environment', fix_boxed_environment),
    ('defbox in math', fix_defbox_in_math),
    ('double math boxed', fix_double_math_boxed),
    ('boxed display math', fix_boxed_display_math),
    ('missing \\partial', fix_missing_partial_backslash),
    ('duplicate QED', fix_duplicate_qed),
    ('undefined control sequences', fix_undefined_control_sequences),
    ('double superscript', fix_double_superscript),
    ('double subscript', fix_double_subscript),
]


def apply_fixes(tex_files, verbose=True):
    """Apply all fix patterns to the given .tex files. Returns total fix count."""
    total = 0

    for path in tex_files:
        # Binary-level fixes first
        if fix_form_feed_bytes(path):
            if verbose:
                relpath = os.path.relpath(path, ROOT)
                print(f'  Fixed form feed bytes: {relpath}')
            total += 1

        content = read_tex(path)
        original = content
        file_fixes = 0

        for name, fix_fn in ALL_FIXES:
            content, count = fix_fn(content)
            if count > 0:
                file_fixes += count
                if verbose:
                    relpath = os.path.relpath(path, ROOT)
                    print(f'  Fixed {name} ({count}x): {relpath}')

        if content != original:
            write_tex(path, content)
            total += file_fixes

    return total


# ---------------------------------------------------------------------------
# Inventory check (inline version of inventory_check.py)
# ---------------------------------------------------------------------------

def run_inventory(chapter=None):
    """Count sections, equations, figures, exercises per chapter."""
    if chapter is not None:
        chapters = [chapter]
    else:
        chapters = sorted(set(
            int(re.search(r'ch(\d+)', d).group(1))
            for d in glob.glob(os.path.join(LATEX_DIR, 'ch*'))
            if re.search(r'ch(\d+)', d)
        ))

    if not chapters:
        print('No chapters found.')
        return

    print(f'\n{"Ch":>3} | {"Sections":>8} | {"Equations":>9} | {"Figures":>7} | {"Exercises":>9}')
    print('-' * 55)

    total_sec = total_eq = total_fig = total_ex = 0

    for ch in chapters:
        ch_dir = os.path.join(LATEX_DIR, f'ch{ch:02d}')
        content = ''
        for f in sorted(glob.glob(os.path.join(ch_dir, '*.tex'))):
            content += read_tex(f)

        sections = len(re.findall(r'\\section\{', content))
        equations = len(re.findall(r'\\begin\{(?:equation|align|gather|multline)\*?\}', content))
        figures = len(re.findall(r'\\begin\{figure\}', content))
        exercises = len(re.findall(r'\\item', content))

        print(f'{ch:3d} | {sections:8d} | {equations:9d} | {figures:7d} | {exercises:9d}')
        total_sec += sections
        total_eq += equations
        total_fig += figures
        total_ex += exercises

    print('-' * 55)
    print(f'{"Tot":>3} | {total_sec:8d} | {total_eq:9d} | {total_fig:7d} | {total_ex:9d}')


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='LaTeX compile-fix loop')
    parser.add_argument('--fix-only', action='store_true', help='Apply fixes without compiling')
    parser.add_argument('--compile-only', action='store_true', help='Compile without fixing')
    parser.add_argument('--chapter', type=int, default=None, help='Single chapter number')
    parser.add_argument('--max-iter', type=int, default=10, help='Max fix-compile iterations')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()

    book_name = get_book_name()
    print(f'Book: {book_name}')
    print(f'LaTeX dir: {LATEX_DIR}')
    if args.chapter:
        print(f'Chapter: {args.chapter}')

    tex_files = collect_tex_files(args.chapter)
    if not tex_files:
        print('No .tex files found.')
        sys.exit(1)
    print(f'Found {len(tex_files)} .tex files\n')

    if args.fix_only:
        total = apply_fixes(tex_files, verbose=True)
        print(f'\nApplied {total} fixes.')
        return

    if args.compile_only:
        print('Compiling...')
        success, error_count, errors = compile_latex(args.chapter)
        if success:
            print('Compilation successful (0 errors)')
        else:
            print(f'Compilation finished with {error_count} errors:')
            for e in errors[:20]:
                loc = f'{e["file"]}:{e["line"]}' if e['file'] else '?'
                print(f'  [{loc}] {e["message"]}')
            if error_count > 20:
                print(f'  ... and {error_count - 20} more')
        run_inventory(args.chapter)
        return

    # Full compile-fix loop
    for iteration in range(1, args.max_iter + 1):
        print(f'=== Iteration {iteration}/{args.max_iter} ===')

        # Step 1: Compile
        print('Compiling...')
        success, error_count, errors = compile_latex(args.chapter)

        if success:
            print('Compilation successful (0 errors)')
            # Copy PDF
            basename = 'main' if args.chapter is None else f'ch{args.chapter:02d}_standalone'
            src_pdf = os.path.join(BUILD_DIR, f'{basename}.pdf')
            if args.chapter is None:
                dst_pdf = os.path.join(LATEX_DIR, f'{book_name}.pdf')
            else:
                dst_pdf = os.path.join(LATEX_DIR, f'{book_name}_ch{args.chapter:02d}.pdf')
            if os.path.exists(src_pdf):
                import shutil
                shutil.copy2(src_pdf, dst_pdf)
                size_mb = os.path.getsize(dst_pdf) / (1024 * 1024)
                print(f'Output: {os.path.relpath(dst_pdf, ROOT)} ({size_mb:.1f} MB)')
            run_inventory(args.chapter)
            return

        print(f'Found {error_count} errors')
        if args.verbose or error_count <= 10:
            for e in errors[:10]:
                loc = f'{e["file"]}:{e["line"]}' if e['file'] else '?'
                print(f'  [{loc}] {e["message"]}')

        # Step 2: Apply fixes
        print('\nApplying fixes...')
        fix_count = apply_fixes(tex_files, verbose=True)

        if fix_count == 0:
            print('No automatic fixes available for remaining errors.')
            print(f'\nRemaining {error_count} errors require manual intervention:')
            for e in errors[:20]:
                loc = f'{e["file"]}:{e["line"]}' if e['file'] else '?'
                print(f'  [{loc}] {e["message"]}')
            if error_count > 20:
                print(f'  ... and {error_count - 20} more')
            break

        print(f'Applied {fix_count} fixes, recompiling...\n')

    else:
        print(f'\nMax iterations ({args.max_iter}) reached with errors remaining.')

    run_inventory(args.chapter)


if __name__ == '__main__':
    main()
