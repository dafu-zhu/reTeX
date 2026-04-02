#!/usr/bin/env python3
"""
reTeX pipeline orchestrator — Python-first, AI only when needed.

Handles the full PDF→LaTeX pipeline:
  Phase 0: Setup (pure Python — parse TOC, create structure, write templates)
  Phase 1: Content conversion (requires AI — sonnet via Anthropic API)
  Phase 2: Figure extraction (pure Python — PyMuPDF)
  Phase 3: Back matter skeleton (pure Python — templates)
  Phase 4: Verification (pure Python — compile-fix + inventory)

Usage:
    python scripts/pipeline.py pdfs/scanned.pdf                 # Full pipeline
    python scripts/pipeline.py pdfs/scanned.pdf --phase 0       # Setup only
    python scripts/pipeline.py pdfs/scanned.pdf --phase 2       # Figures only
    python scripts/pipeline.py pdfs/scanned.pdf --phase 4       # Verify only
    python scripts/pipeline.py pdfs/scanned.pdf --skip-ai       # Everything except Phase 1
"""
import argparse
import os
import re
import subprocess
import sys
import textwrap

try:
    import pymupdf
except ImportError:
    try:
        import fitz as pymupdf
    except ImportError:
        pymupdf = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LATEX_DIR = os.path.join(ROOT, 'latex')
SCRIPTS_DIR = os.path.join(ROOT, 'scripts')


# ---------------------------------------------------------------------------
# Phase 0: Setup — parse PDF, create structure, write templates
# ---------------------------------------------------------------------------

def parse_toc_from_pdf(pdf_path, max_pages=20):
    """Extract TOC structure from scanned PDF front matter using PyMuPDF."""
    if pymupdf is None:
        print('ERROR: PyMuPDF not installed. Run: pip install pymupdf')
        sys.exit(1)

    doc = pymupdf.open(pdf_path)
    info = {
        'title': '',
        'author': '',
        'edition': '',
        'publisher': '',
        'chapters': [],
        'page_width': 0,
        'page_height': 0,
    }

    # Get page dimensions from first page
    if len(doc) > 0:
        rect = doc[0].rect
        info['page_width'] = rect.width
        info['page_height'] = rect.height

    # Extract text from first N pages to find TOC
    front_text = ''
    for i in range(min(max_pages, len(doc))):
        front_text += doc[i].get_text('text') + '\n---PAGE BREAK---\n'

    # Try to extract title from first page
    first_page_text = doc[0].get_text('text') if len(doc) > 0 else ''
    lines = [l.strip() for l in first_page_text.split('\n') if l.strip()]
    if lines:
        # Heuristic: title is usually the longest/most prominent line in first few
        info['title'] = lines[0] if lines else 'Untitled'

    # Find chapter entries in TOC
    # Common patterns: "Chapter 1 Title ... 17" or "1 Title 17" or "1. Title ... 17"
    ch_patterns = [
        # "Chapter N Title ... page"
        re.compile(r'(?:Chapter\s+)?(\d{1,2})\s+([A-Z][^\d\n]{5,}?)\s*\.{0,}\s*(\d{1,4})\s*$', re.MULTILINE),
        # "N.  Title    page" (with dots or spaces)
        re.compile(r'^(\d{1,2})\.\s+([A-Z][^\d\n]{5,}?)\s+(\d{1,4})\s*$', re.MULTILINE),
        # "N Title page" at start of line
        re.compile(r'^(\d{1,2})\s{2,}([A-Z][^\d\n]{5,}?)\s{2,}(\d{1,4})\s*$', re.MULTILINE),
    ]

    chapters = []
    for pattern in ch_patterns:
        for m in pattern.finditer(front_text):
            ch_num = int(m.group(1))
            title = m.group(2).strip().rstrip('.')
            page = int(m.group(3))
            if 1 <= ch_num <= 30 and page < len(doc):
                chapters.append((ch_num, title, page))
        if chapters:
            break

    # Deduplicate and sort
    seen = set()
    unique = []
    for ch_num, title, page in sorted(chapters):
        if ch_num not in seen:
            seen.add(ch_num)
            unique.append((ch_num, title, page))
    chapters = unique

    # Compute page ranges (each chapter ends where the next begins)
    for i, (ch_num, title, start_page) in enumerate(chapters):
        if i + 1 < len(chapters):
            end_page = chapters[i + 1][2] - 1
        else:
            end_page = len(doc) - 1  # Approximate
        info['chapters'].append({
            'number': ch_num,
            'title': title,
            'start_page': start_page,
            'end_page': end_page,
        })

    doc.close()
    return info


def slugify(title):
    """Convert title to a slug: lowercase, underscores, no special chars."""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s]', '', slug)
    slug = re.sub(r'\s+', '_', slug.strip())
    # Drop common subtitles after colon
    slug = slug.split('_with_')[0] if '_with_' in slug else slug
    return slug[:50]  # Cap length


def create_directory_structure(info):
    """Create latex/ directory tree."""
    num_chapters = len(info['chapters'])
    dirs = [
        os.path.join(LATEX_DIR, 'build'),
        os.path.join(LATEX_DIR, 'backmatter'),
    ]
    for ch in info['chapters']:
        ch_str = f'ch{ch["number"]:02d}'
        dirs.append(os.path.join(LATEX_DIR, ch_str))
        dirs.append(os.path.join(LATEX_DIR, 'figures', ch_str))

    for d in dirs:
        os.makedirs(d, exist_ok=True)
    print(f'  Created {len(dirs)} directories')


def write_book_conf(info, book_name):
    """Write book.conf with chapter page ranges."""
    lines = [
        f'BOOK_NAME="{book_name}"',
        f'TITLE="{info["title"]}"',
        f'AUTHOR="{info["author"]}"',
        f'EDITION="{info["edition"]}"',
        f'PUBLISHER="{info["publisher"]}"',
        f'NUM_CHAPTERS={len(info["chapters"])}',
        '',
    ]
    for ch in info['chapters']:
        lines.append(f'CH{ch["number"]:02d}_PAGES="{ch["start_page"]}-{ch["end_page"]}"')

    path = os.path.join(ROOT, 'book.conf')
    with open(path, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'  Wrote {path}')


def write_preamble(info):
    """Write preamble.tex with geometry matching source dimensions."""
    # Convert PDF points to inches (72 pt/inch)
    w_in = info['page_width'] / 72
    h_in = info['page_height'] / 72

    preamble = textwrap.dedent(f"""\
    \\documentclass[12pt]{{book}}

    % Page geometry matching source
    \\usepackage[
      paperwidth={w_in:.2f}in,
      paperheight={h_in:.2f}in,
      margin=1in
    ]{{geometry}}

    % Math
    \\usepackage{{amsmath,amssymb,amsthm}}
    \\usepackage{{mathtools}}

    % Figures and graphics
    \\usepackage{{graphicx}}
    \\usepackage{{float}}
    \\usepackage[dvipsnames]{{xcolor}}

    % Tables
    \\usepackage{{booktabs}}
    \\usepackage{{array}}

    % Code and algorithms
    \\usepackage{{listings}}

    % Boxes
    \\usepackage{{tcolorbox}}
    \\tcbuselibrary{{breakable,skins}}

    % Lists
    \\usepackage{{enumitem}}

    % Cross-references and hyperlinks
    \\usepackage{{hyperref}}
    \\hypersetup{{colorlinks=true,linkcolor=blue,citecolor=blue,urlcolor=blue}}

    % Index
    \\usepackage{{makeidx}}
    \\makeindex

    % PGF/TikZ
    \\usepackage{{tikz,pgfplots}}
    \\pgfplotsset{{compat=1.18}}

    % Custom math commands
    \\DeclareMathOperator{{\\E}}{{E}}
    \\DeclareMathOperator{{\\Var}}{{Var}}
    \\DeclareMathOperator{{\\Cov}}{{Cov}}
    \\newcommand{{\\plim}}{{\\operatorname{{plim}}}}
    \\newcommand{{\\dto}}{{\\xrightarrow{{d}}}}
    \\newcommand{{\\pto}}{{\\xrightarrow{{p}}}}
    \\newcommand{{\\pd}}[2]{{\\frac{{\\partial #1}}{{\\partial #2}}}}

    % Theorem environments — shared counter (sequential per chapter)
    \\newtheorem{{theorem}}{{Theorem}}[chapter]
    \\newtheorem{{lemma}}[theorem]{{Lemma}}
    \\newtheorem{{proposition}}[theorem]{{Proposition}}
    \\newtheorem{{corollary}}[theorem]{{Corollary}}
    \\newtheorem{{definition}}[theorem]{{Definition}}
    \\newtheorem{{example}}[theorem]{{Example}}
    \\newtheorem{{remark}}[theorem]{{Remark}}

    % Exercise label
    \\newcommand{{\\exerciselabel}}{{Exercises}}

    % Book metadata macros
    \\newcommand{{\\booktitle}}{{{info['title']}}}
    \\newcommand{{\\bookauthor}}{{{info['author']}}}
    \\newcommand{{\\bookedition}}{{{info['edition']}}}
    \\newcommand{{\\bookpublisher}}{{{info['publisher']}}}
    """)

    path = os.path.join(LATEX_DIR, 'preamble.tex')
    with open(path, 'w') as f:
        f.write(preamble)
    print(f'  Wrote {path}')


def write_main_tex(info):
    """Write main.tex skeleton."""
    includes = ['\\include{frontmatter}']
    for ch in info['chapters']:
        ch_str = f'ch{ch["number"]:02d}'
        includes.append(f'\\include{{{ch_str}/{ch_str}}}')
    includes.append('\\include{backmatter/backmatter}')

    content = '\\input{preamble}\n\n\\begin{document}\n\n'
    content += '\n'.join(includes)
    content += '\n\n\\printindex\n\\end{document}\n'

    path = os.path.join(LATEX_DIR, 'main.tex')
    with open(path, 'w') as f:
        f.write(content)
    print(f'  Wrote {path}')


def write_frontmatter():
    """Write frontmatter.tex template."""
    content = textwrap.dedent("""\
    \\begin{titlepage}
    \\centering
    \\vspace*{2in}
    {\\Huge \\booktitle}\\\\[1em]
    {\\Large \\bookauthor}\\\\[0.5em]
    {\\large \\bookedition}\\\\[2em]
    {\\large \\bookpublisher}
    \\vfill
    \\end{titlepage}

    \\tableofcontents
    """)

    path = os.path.join(LATEX_DIR, 'frontmatter.tex')
    with open(path, 'w') as f:
        f.write(content)
    print(f'  Wrote {path}')


def write_chapter_stubs(info):
    """Write chapter wrapper .tex files and empty section files."""
    for ch in info['chapters']:
        ch_num = ch['number']
        ch_str = f'ch{ch_num:02d}'
        ch_dir = os.path.join(LATEX_DIR, ch_str)

        # Chapter wrapper
        wrapper = os.path.join(ch_dir, f'{ch_str}.tex')
        if not os.path.exists(wrapper):
            with open(wrapper, 'w') as f:
                f.write(f'\\chapter{{{ch["title"]}}}\n\\label{{ch:{ch_num}}}\n\n')
                f.write(f'% Section files will be \\input{{}} here after conversion\n')
            print(f'  Wrote stub: {ch_str}/{ch_str}.tex')


def write_backmatter_stub():
    """Write backmatter skeleton."""
    path = os.path.join(LATEX_DIR, 'backmatter', 'backmatter.tex')
    if not os.path.exists(path):
        content = textwrap.dedent("""\
        \\chapter*{Bibliography}
        \\addcontentsline{toc}{chapter}{Bibliography}

        % TODO: Add bibliography entries

        \\chapter*{Answers to Starred Exercises}
        \\addcontentsline{toc}{chapter}{Answers to Starred Exercises}

        % TODO: Add answers

        """)
        with open(path, 'w') as f:
            f.write(content)
        print(f'  Wrote backmatter stub')


def write_progress_md(info, book_name):
    """Write docs/progress.md section-level checklist."""
    os.makedirs(os.path.join(ROOT, 'docs'), exist_ok=True)
    lines = [
        '# Progress Tracker',
        '',
        '## Phase 0: Setup',
        '- [x] Directory structure created',
        '- [x] `preamble.tex` written',
        '- [x] `main.tex` skeleton written',
        '- [x] `build.sh` written',
        '- [x] `frontmatter.tex` written',
        '',
        '## Chapter Progress',
        '',
        '| Ch | Title | Pages | Status |',
        '|----|-------|-------|--------|',
    ]
    for ch in info['chapters']:
        lines.append(f'| {ch["number"]} | {ch["title"]} | {ch["start_page"]}–{ch["end_page"]} | Pending |')

    path = os.path.join(ROOT, 'docs', 'progress.md')
    with open(path, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'  Wrote {path}')


def run_phase_0(pdf_path):
    """Phase 0: Parse PDF and create project structure."""
    print('\n=== Phase 0: Setup ===')

    print('Parsing PDF TOC...')
    info = parse_toc_from_pdf(pdf_path)

    if not info['chapters']:
        print('WARNING: Could not auto-detect chapters from TOC.')
        print('The PDF may need manual TOC parsing or AI assistance.')
        print('You can manually create book.conf with chapter page ranges.')
        return None

    book_name = slugify(info['title'])
    print(f'  Title: {info["title"]}')
    print(f'  Book name: {book_name}')
    print(f'  Chapters: {len(info["chapters"])}')
    print(f'  Page size: {info["page_width"]:.0f} x {info["page_height"]:.0f} pt')

    print('\nCreating structure...')
    create_directory_structure(info)
    write_book_conf(info, book_name)
    write_preamble(info)
    write_main_tex(info)
    write_frontmatter()
    write_chapter_stubs(info)
    write_backmatter_stub()
    write_progress_md(info, book_name)

    print(f'\nPhase 0 complete. {len(info["chapters"])} chapters ready for conversion.')
    return info


# ---------------------------------------------------------------------------
# Phase 1: Content conversion — requires AI
# ---------------------------------------------------------------------------

def run_phase_1(pdf_path, info=None):
    """Phase 1: Convert chapter content. Needs AI (Anthropic API)."""
    print('\n=== Phase 1: Content Conversion ===')

    # Load chapter info from book.conf if not provided
    if info is None:
        info = load_book_conf()
        if not info:
            print('ERROR: book.conf not found. Run Phase 0 first.')
            return False

    # Check for Anthropic API key
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        print('No ANTHROPIC_API_KEY found.')
        print('Phase 1 requires AI for content conversion.')
        print('Options:')
        print('  1. Set ANTHROPIC_API_KEY and re-run')
        print('  2. Use Claude Code: /pdf-to-latex (skip to Phase 1)')
        print('  3. Use another OCR tool (Nougat, Mathpix) and import results')
        return False

    try:
        import anthropic
    except ImportError:
        print('ERROR: anthropic package not installed.')
        print('Run: pip install anthropic')
        return False

    client = anthropic.Anthropic(api_key=api_key)
    chapters = info.get('chapters', [])

    print(f'Converting {len(chapters)} chapters using Claude sonnet...')

    for ch in chapters:
        ch_num = ch['number']
        ch_str = f'ch{ch_num:02d}'
        ch_dir = os.path.join(LATEX_DIR, ch_str)

        # Skip if already converted (has section files beyond the stub)
        existing_sections = [f for f in os.listdir(ch_dir)
                           if f.startswith('sec') and f.endswith('.tex')]
        if existing_sections:
            print(f'  Ch {ch_num}: already has {len(existing_sections)} sections, skipping')
            continue

        start = ch['start_page']
        end = ch['end_page']
        print(f'  Ch {ch_num}: pages {start}–{end} ...', end=' ', flush=True)

        # Read PDF pages as images
        success = convert_chapter_with_ai(client, pdf_path, ch, ch_dir)
        if success:
            print('done')
        else:
            print('FAILED')

    return True


def convert_chapter_with_ai(client, pdf_path, ch_info, ch_dir):
    """Convert a single chapter using Claude API with PDF page images."""
    import base64

    if pymupdf is None:
        return False

    doc = pymupdf.open(pdf_path)
    ch_num = ch_info['number']
    start = ch_info['start_page']
    end = min(ch_info['end_page'], len(doc) - 1)

    # Process in chunks of 5-8 pages
    chunk_size = 6
    all_content = []

    for chunk_start in range(start, end + 1, chunk_size):
        chunk_end = min(chunk_start + chunk_size - 1, end)

        # Render pages as images
        images = []
        for page_num in range(chunk_start, chunk_end + 1):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))  # 144 DPI
            img_bytes = pix.tobytes('png')
            b64 = base64.b64encode(img_bytes).decode()
            images.append({
                'type': 'image',
                'source': {
                    'type': 'base64',
                    'media_type': 'image/png',
                    'data': b64,
                }
            })

        prompt_content = images + [{
            'type': 'text',
            'text': (
                f'Typeset these scanned pages (Chapter {ch_num}, pages {chunk_start}-{chunk_end}) as LaTeX.\n'
                f'- Write section files as sec{ch_num:02d}_N.tex (one per section)\n'
                f'- Use conventions: \\E{{}}, \\Var{{}}, \\Cov{{}}, \\pd{{}}{{}}, \\vec{{x}} for bold vectors\n'
                f'- Figures: \\begin{{figure}}[H] with % TODO: extract figure\n'
                f'- Unclear content: % UNCLEAR: [description, page X]\n'
                f'- NEVER use \\qed or \\blacksquare inside proof environments\n'
                f'- Output ONLY the LaTeX source code for each section file.\n'
                f'- Separate files with: %%% FILE: sec{ch_num:02d}_N.tex %%%\n'
            )
        }]

        try:
            response = client.messages.create(
                model='claude-sonnet-4-20250514',
                max_tokens=8192,
                messages=[{'role': 'user', 'content': prompt_content}],
            )
            all_content.append(response.content[0].text)
        except Exception as e:
            print(f'\n    API error on pages {chunk_start}-{chunk_end}: {e}')
            # Retry with smaller chunks
            if chunk_size > 2:
                print(f'    Retrying with smaller chunks...')
                for p in range(chunk_start, chunk_end + 1):
                    try:
                        single_img = [{
                            'type': 'image',
                            'source': {
                                'type': 'base64',
                                'media_type': 'image/png',
                                'data': base64.b64encode(
                                    doc[p].get_pixmap(matrix=pymupdf.Matrix(2, 2)).tobytes('png')
                                ).decode(),
                            }
                        }]
                        resp = client.messages.create(
                            model='claude-sonnet-4-20250514',
                            max_tokens=4096,
                            messages=[{'role': 'user', 'content': single_img + [{
                                'type': 'text',
                                'text': f'Typeset this scanned page (Ch {ch_num}, p{p}) as LaTeX. Use \\pd{{}}{{}}, \\E{{}}, etc.'
                            }]}],
                        )
                        all_content.append(resp.content[0].text)
                    except Exception as e2:
                        print(f'    Page {p} failed: {e2}')

    doc.close()

    # Parse response into section files
    full_text = '\n'.join(all_content)
    file_sections = re.split(r'%%%\s*FILE:\s*(sec\d+_\d+\.tex)\s*%%%', full_text)

    if len(file_sections) > 1:
        # Paired: [preamble, filename, content, filename, content, ...]
        for i in range(1, len(file_sections), 2):
            filename = file_sections[i].strip()
            content = file_sections[i + 1].strip() if i + 1 < len(file_sections) else ''
            filepath = os.path.join(ch_dir, filename)
            with open(filepath, 'w') as f:
                f.write(content + '\n')
    else:
        # Single file output — save as one section file
        filepath = os.path.join(ch_dir, f'sec{ch_num:02d}_1.tex')
        with open(filepath, 'w') as f:
            f.write(full_text + '\n')

    # Update chapter wrapper to include section files
    wrapper = os.path.join(ch_dir, f'ch{ch_num:02d}.tex')
    section_files = sorted(f for f in os.listdir(ch_dir) if f.startswith('sec'))
    with open(wrapper, 'w') as f:
        f.write(f'\\chapter{{{ch_info["title"]}}}\n\\label{{ch:{ch_num}}}\n\n')
        for sec_file in section_files:
            sec_name = sec_file.replace('.tex', '')
            f.write(f'\\input{{ch{ch_num:02d}/{sec_name}}}\n')

    return True


def load_book_conf():
    """Load chapter info from book.conf."""
    conf_path = os.path.join(ROOT, 'book.conf')
    if not os.path.exists(conf_path):
        return None

    info = {'chapters': []}
    with open(conf_path) as f:
        content = f.read()

    for m in re.finditer(r'CH(\d+)_PAGES="(\d+)-(\d+)"', content):
        ch_num = int(m.group(1))
        start = int(m.group(2))
        end = int(m.group(3))
        info['chapters'].append({
            'number': ch_num,
            'start_page': start,
            'end_page': end,
            'title': f'Chapter {ch_num}',  # Would need to parse from progress.md
        })

    return info if info['chapters'] else None


# ---------------------------------------------------------------------------
# Phase 2: Figure extraction — pure Python
# ---------------------------------------------------------------------------

def run_phase_2(pdf_path):
    """Phase 2: Extract figures using existing script."""
    print('\n=== Phase 2: Figure Extraction ===')

    script = os.path.join(SCRIPTS_DIR, 'extract_figures.py')
    if not os.path.exists(script):
        print(f'ERROR: {script} not found')
        return False

    result = subprocess.run(
        [sys.executable, script],
        cwd=ROOT,
        capture_output=False,
    )
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Phase 3: Back matter — pure Python
# ---------------------------------------------------------------------------

def run_phase_3():
    """Phase 3: Ensure back matter skeleton exists."""
    print('\n=== Phase 3: Back Matter ===')
    write_backmatter_stub()
    print('  Back matter skeleton ready.')
    return True


# ---------------------------------------------------------------------------
# Phase 4: Verification — pure Python
# ---------------------------------------------------------------------------

def run_phase_4(chapter=None):
    """Phase 4: Compile-fix loop + inventory."""
    print('\n=== Phase 4: Verification ===')

    script = os.path.join(SCRIPTS_DIR, 'compile_fix.py')
    cmd = [sys.executable, script]
    if chapter:
        cmd.extend(['--chapter', str(chapter)])

    result = subprocess.run(cmd, cwd=ROOT, capture_output=False)
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='reTeX pipeline — Python-first PDF to LaTeX conversion')
    parser.add_argument('pdf', nargs='?', default=os.path.join(ROOT, 'pdfs', 'scanned.pdf'),
                        help='Path to scanned PDF (default: pdfs/scanned.pdf)')
    parser.add_argument('--phase', type=int, choices=[0, 1, 2, 3, 4],
                        help='Run only this phase')
    parser.add_argument('--skip-ai', action='store_true',
                        help='Skip Phase 1 (AI content conversion)')
    parser.add_argument('--chapter', type=int, help='Process single chapter')
    args = parser.parse_args()

    pdf_path = os.path.abspath(args.pdf) if args.pdf else None

    # PDF is only required for phases 0, 1, 2
    phases_needing_pdf = {0, 1, 2}
    if args.phase is not None:
        needed = args.phase in phases_needing_pdf
    elif args.skip_ai:
        needed = True  # phases 0, 2 need it
    else:
        needed = True

    if needed and (pdf_path is None or not os.path.exists(pdf_path)):
        # Check if we can skip — phases 3, 4 don't need PDF
        if args.phase in (3, 4):
            needed = False
        else:
            print(f'ERROR: PDF not found: {pdf_path}')
            sys.exit(1)

    print(f'reTeX Pipeline')
    if pdf_path and os.path.exists(pdf_path):
        print(f'PDF: {pdf_path}')
    print(f'Output: {LATEX_DIR}')

    if args.phase is not None:
        # Run single phase
        phases = [args.phase]
    elif args.skip_ai:
        phases = [0, 2, 3, 4]
    else:
        phases = [0, 1, 2, 3, 4]

    info = None

    for phase in phases:
        if phase == 0:
            # Check if already done
            if os.path.exists(os.path.join(ROOT, 'book.conf')):
                print('\n=== Phase 0: Setup (already done, skipping) ===')
                continue
            info = run_phase_0(pdf_path)
        elif phase == 1:
            run_phase_1(pdf_path, info)
        elif phase == 2:
            run_phase_2(pdf_path)
        elif phase == 3:
            run_phase_3()
        elif phase == 4:
            run_phase_4(args.chapter)

    print('\nPipeline complete.')


if __name__ == '__main__':
    main()
