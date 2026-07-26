#!/usr/bin/env python3
"""Decide whether a source PDF resumes an existing book, or starts a new one.

    python scripts/resume_check.py --pdf pdfs/scanned.pdf

Prints exactly one DECISION line:

    DECISION: RESUME <book_name>   this PDF *is* that book — skip Phase 0
    DECISION: FRESH                no book claims this PDF — run Phase 0
    DECISION: STOP                 a book claims it but the identity does not
                                   hold; a human must resolve it

and exits 0 for RESUME/FRESH, 1 for STOP.

Why this is not a grep
----------------------
`SOURCE_PDF="pdfs/scanned.pdf"` is the shared default for every book in this
repo, so it is a *filename*, not an identity. Matching on it alone hands the
current PDF to whichever book happens to sit at that path — and because the
skill's rule is then "skip Phase 0 entirely", ~50 transcription agents write a
different book into an existing book's tree and destroy it, with nothing
surfacing until the final phase. Resuming therefore requires a verified match
between the PDF's real page count and the PAGE_COUNT recorded in book.conf,
plus the presence of every key later phases actually read.

This script deliberately never prints TITLE, AUTHOR, EDITION or any other book
metadata: it runs in the main conversation, and printing metadata there is what
trips the API content filter on every subsequent tool call.
"""
import argparse
import os
import re
import sys

try:
    import pymupdf
except ImportError:  # older PyMuPDF
    import fitz as pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Keys later phases actually read. A book.conf missing any of these is a stale
# conversion from an older pipeline, not something a resume can build on.
# TITLE/AUTHOR/EDITION are deliberately NOT required and never printed.
REQUIRED_KEYS = (
    'BOOK_NAME',
    'SOURCE_PDF',
    'PAGE_COUNT',
    'PAGE_OFFSET',
    'COPYRIGHT_PAGE',
    'FIGURE_NUMBERING',
    'BACKMATTER_PAGES',
)

_CONF_LINE_RE = re.compile(r'^\s*(?P<key>[A-Z0-9_]+)\s*=\s*(?P<value>.*?)\s*$')
_CH_PAGES_RE = re.compile(r'^CH\d+_PAGES$')


def _display_path(path):
    """Repo-relative when possible; absolute otherwise.

    os.path.relpath raises ValueError across Windows drives, so a PDF on
    another drive must not crash the check.
    """
    try:
        rel = os.path.relpath(path, ROOT)
    except ValueError:
        return path.replace('\\', '/')
    if rel.startswith('..'):
        return path.replace('\\', '/')
    return rel.replace('\\', '/')


def parse_book_conf(path):
    """Parse book.conf into a dict. Tolerates quoted and bare values."""
    conf = {}
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.split('#', 1)[0] if line.lstrip().startswith('#') else line
            m = _CONF_LINE_RE.match(line)
            if not m:
                continue
            value = m.group('value')
            if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
                value = value[1:-1]
            conf[m.group('key')] = value
    return conf


def _same_pdf(conf_value, pdf_path):
    """True if book.conf's SOURCE_PDF designates the same file as pdf_path."""
    if not conf_value:
        return False
    candidate = conf_value if os.path.isabs(conf_value) else os.path.join(ROOT, conf_value)
    try:
        return os.path.exists(candidate) and os.path.exists(pdf_path) and \
            os.path.samefile(candidate, pdf_path)
    except OSError:
        return os.path.normcase(os.path.abspath(candidate)) == \
            os.path.normcase(os.path.abspath(pdf_path))


def evaluate(book_dir, conf, real_pages):
    """Return (ok, [reasons]) for one candidate book."""
    reasons = []

    raw_count = conf.get('PAGE_COUNT', '').strip()
    if not raw_count:
        reasons.append(
            'book.conf has no PAGE_COUNT, so its identity cannot be verified '
            '(stale conversion from an older pipeline)')
    else:
        try:
            recorded = int(raw_count)
        except ValueError:
            reasons.append(f'PAGE_COUNT={raw_count!r} is not an integer')
        else:
            if recorded != real_pages:
                reasons.append(
                    f'PAGE_COUNT={recorded} but the PDF has {real_pages} pages '
                    f'— this is a DIFFERENT book at the same path')

    missing = [k for k in REQUIRED_KEYS if not conf.get(k, '').strip()]
    if not any(_CH_PAGES_RE.match(k) for k in conf):
        missing.append('CHNN_PAGES')
    if missing:
        reasons.append('book.conf is missing keys later phases read: '
                       + ', '.join(sorted(missing)))

    return (not reasons), reasons


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--pdf', required=True, help='Path to the source PDF')
    parser.add_argument('--books-dir', default=os.path.join(ROOT, 'books'),
                        help='Directory holding the books (default: books/)')
    args = parser.parse_args()

    pdf_path = args.pdf if os.path.isabs(args.pdf) else os.path.join(ROOT, args.pdf)
    if not os.path.exists(pdf_path):
        print(f'ERROR: no such PDF: {args.pdf}')
        print('DECISION: STOP')
        return 1

    with pymupdf.open(pdf_path) as doc:
        real_pages = len(doc)
    print(f'PDF: {_display_path(pdf_path)} ({real_pages} pages)')

    if not os.path.isdir(args.books_dir):
        print('No books/ directory yet.')
        print('DECISION: FRESH')
        return 0

    claimants = []
    for name in sorted(os.listdir(args.books_dir)):
        book_dir = os.path.join(args.books_dir, name)
        conf_path = os.path.join(book_dir, 'book.conf')
        if not os.path.isfile(conf_path):
            continue
        conf = parse_book_conf(conf_path)
        if _same_pdf(conf.get('SOURCE_PDF', ''), pdf_path):
            claimants.append((name, book_dir, conf))

    if not claimants:
        print('No book.conf references this PDF.')
        print('DECISION: FRESH')
        return 0

    print(f'{len(claimants)} book(s) reference this PDF path: '
          + ', '.join(n for n, _, _ in claimants))

    verified = []
    for name, book_dir, conf in claimants:
        ok, reasons = evaluate(book_dir, conf, real_pages)
        if ok:
            print(f'  {name}: identity VERIFIED (PAGE_COUNT={real_pages}, all required keys present)')
            verified.append(name)
        else:
            print(f'  {name}: identity NOT verified')
            for reason in reasons:
                print(f'      - {reason}')

    if len(verified) == 1:
        print(f'DECISION: RESUME {verified[0]}')
        return 0

    if not verified:
        print()
        print('SOURCE_PDF is the shared default for every book in this repo, so a')
        print('path match alone is not an identity. Do NOT resume into these books,')
        print('and do NOT silently start fresh — Phase 0 would overwrite whichever')
        print('tree a later agent picks. Resolve by hand:')
        print('  - if the named book is a DIFFERENT book, move its PDF aside and give')
        print('    this one its own path, then re-run this check;')
        print('  - if it is the same book with a stale book.conf, repair the missing')
        print('    keys (and PAGE_COUNT) before resuming.')
        print('DECISION: STOP')
        return 1

    print()
    print(f'{len(verified)} books both claim this PDF and verify against it — ambiguous.')
    print('DECISION: STOP')
    return 1


if __name__ == '__main__':
    sys.exit(main())
