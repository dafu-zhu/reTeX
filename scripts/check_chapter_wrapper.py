#!/usr/bin/env python3
"""Verify every section file in a chapter is pulled in by its chapter wrapper.

    python scripts/check_chapter_wrapper.py --book <name>            # all chapters
    python scripts/check_chapter_wrapper.py --book <name> --chapter 3

Exits 1 and prints one line per violation.

Why this exists
---------------
Phase 1a runs up to 4 chunk agents concurrently inside one chapter. When every
one of them wrote `chNN/chNN.tex`, the last writer won and the other chunks'
`secNN_M.tex` files stayed on disk unreferenced — so they never reached the
PDF. Nothing caught it: the book compiled cleanly, and inventory_check.py globs
every `*.tex` under `chNN/`, so its section and equation counts still looked
right. Only a reference check finds it, so a section file on disk that no
wrapper reads is a hard failure here.
"""
import argparse
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# \input{ch01/sec01_1}, \include{sec01_1}, \input{ch01/sec01_1.tex}, \subfile{...}
_INCLUDE_RE = re.compile(r'\\(?:input|include|subfile)\s*\{([^}]*)\}')

# Section files a chunk agent produces. chNN.tex itself is the wrapper.
_SECTION_GLOB = 'sec*.tex'


def _display_path(path):
    """Repo-relative when possible; absolute otherwise.

    os.path.relpath raises ValueError across Windows drives.
    """
    try:
        rel = os.path.relpath(path, ROOT)
    except ValueError:
        return path.replace('\\', '/')
    if rel.startswith('..'):
        return path.replace('\\', '/')
    return rel.replace('\\', '/')


def _validate_book_name(name):
    if not name or '/' in name or '\\' in name or '..' in name:
        raise SystemExit(
            f"Error: invalid book name '{name}' "
            "(must be a plain directory name — no '/', '\\', or '..')"
        )


def _referenced_stems(wrapper_path):
    """Return the set of basenames (no .tex) the wrapper \\input/\\includes."""
    with open(wrapper_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    # Strip comment lines so a commented-out \input does not count as a reference.
    content = re.sub(r'(?<!\\)%.*', '', content)

    stems = set()
    for target in _INCLUDE_RE.findall(content):
        target = target.strip().replace('\\', '/')
        if not target:
            continue
        stem = os.path.basename(target)
        if stem.endswith('.tex'):
            stem = stem[:-4]
        stems.add(stem)
    return stems


def check_chapter(latex_dir, ch_dir):
    """Return a list of violation strings for one chapter directory."""
    violations = []
    ch_name = os.path.basename(ch_dir)
    wrapper = os.path.join(ch_dir, f'{ch_name}.tex')
    rel_ch = _display_path(ch_dir)

    section_files = sorted(glob.glob(os.path.join(ch_dir, _SECTION_GLOB)))

    if not os.path.isfile(wrapper):
        if section_files:
            violations.append(
                f'{rel_ch}: no wrapper {ch_name}.tex, but {len(section_files)} '
                f'section file(s) exist — none of them can reach the PDF')
        return violations

    referenced = _referenced_stems(wrapper)

    for path in section_files:
        stem = os.path.splitext(os.path.basename(path))[0]
        if stem not in referenced:
            rel = _display_path(path)
            violations.append(
                f'{rel}: ORPHAN — exists on disk but {ch_name}.tex never '
                f'\\input/\\includes it, so its content is missing from the PDF')

    on_disk = {os.path.splitext(os.path.basename(p))[0] for p in section_files}
    for stem in sorted(referenced):
        if stem == ch_name:
            continue
        if stem in on_disk:
            continue
        # Only complain about section-shaped references; wrappers legitimately
        # reference shared files that live elsewhere.
        if stem.startswith('sec') and not os.path.isfile(
                os.path.join(latex_dir, f'{stem}.tex')):
            violations.append(
                f'{rel_ch}/{ch_name}.tex: DANGLING — references {stem} '
                f'but no such file exists')

    if not section_files:
        violations.append(
            f'{rel_ch}: no {_SECTION_GLOB} files at all — the chapter is empty')

    return violations


def check_book(latex_dir, chapter=None):
    if chapter is not None:
        ch_dirs = [os.path.join(latex_dir, f'ch{chapter:02d}')]
        if not os.path.isdir(ch_dirs[0]):
            return [f'no such chapter directory: {_display_path(ch_dirs[0])}']
    else:
        ch_dirs = sorted(d for d in glob.glob(os.path.join(latex_dir, 'ch*'))
                         if os.path.isdir(d))
        if not ch_dirs:
            return [f'no chapter directories under {_display_path(latex_dir)}']

    violations = []
    for ch_dir in ch_dirs:
        violations.extend(check_chapter(latex_dir, ch_dir))
    return violations


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--book', required=True, help='Book name under books/')
    parser.add_argument('--chapter', type=int, default=None,
                        help='Check a single chapter number')
    args = parser.parse_args()
    _validate_book_name(args.book)

    latex_dir = os.path.join(ROOT, 'books', args.book, 'latex')
    if not os.path.isdir(latex_dir):
        raise SystemExit(f'No such book: {args.book} (expected {latex_dir})')

    violations = check_book(latex_dir, args.chapter)
    for violation in violations:
        print(f'FAIL: {violation}')
    if violations:
        print(f'\n{len(violations)} wrapper violation(s)')
        return 1

    scope = f'chapter {args.chapter}' if args.chapter is not None else 'all chapters'
    print(f'Wrapper check OK ({scope}): every section file is included')
    return 0


if __name__ == '__main__':
    sys.exit(main())
