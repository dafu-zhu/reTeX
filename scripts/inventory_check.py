"""Quantitative inventory check: count sections, equations, figures, exercises per chapter."""
import argparse
import re
import glob
import os

_parser = argparse.ArgumentParser(description=__doc__)
_parser.add_argument('--book', required=True, help='Book name under books/')
_args = _parser.parse_args()

ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'books', _args.book, 'latex',
)
if not os.path.isdir(ROOT):
    raise SystemExit(f'No such book: {_args.book} (expected {ROOT})')

# Auto-detect chapters
chapters = sorted(set(
    int(re.search(r'ch(\d+)', d).group(1))
    for d in glob.glob(os.path.join(ROOT, 'ch*'))
    if re.search(r'ch(\d+)', d)
))

print(f"{'Ch':>3} | {'Sections':>8} | {'Equations':>9} | {'Figures':>7} | {'Exercises':>9}")
print("-" * 55)

total_sec = total_eq = total_fig = total_ex = 0

for ch in chapters:
    ch_dir = os.path.join(ROOT, f'ch{ch:02d}')
    content = ""
    for f in sorted(glob.glob(os.path.join(ch_dir, '*.tex'))):
        with open(f, 'r', encoding='utf-8', errors='replace') as fh:
            content += fh.read()

    sections = len(re.findall(r'\\section\{', content))
    equations = len(re.findall(r'\\begin\{(?:equation|align|gather|multline)\*?\}', content))
    figures = len(re.findall(r'\\begin\{figure\}', content))
    exercises = len(re.findall(r'\\item', content))

    print(f"{ch:3d} | {sections:8d} | {equations:9d} | {figures:7d} | {exercises:9d}")

    total_sec += sections
    total_eq += equations
    total_fig += figures
    total_ex += exercises

print("-" * 55)
print(f"{'Tot':>3} | {total_sec:8d} | {total_eq:9d} | {total_fig:7d} | {total_ex:9d}")
