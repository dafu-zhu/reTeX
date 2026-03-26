#!/usr/bin/env python3
"""Inventory check for LaTeX solutions manual."""
import re, glob, os

chapters = sorted(glob.glob("latex/ch*/ch*.tex"))
total_solutions = 0
total_sections = 0
total_display_eq = 0

print(f"{'Ch':>4} {'Title':<50} {'Secs':>5} {'Sols':>5} {'Eqs':>5}")
print("-" * 73)

for f in chapters:
    with open(f, encoding="utf-8") as fh:
        text = fh.read()
    ch_match = re.search(r"\\chapter\{(.+?)\}", text)
    title = ch_match.group(1) if ch_match else os.path.basename(f)
    secs = len(re.findall(r"\\section\{", text))
    sols = len(re.findall(r"\\begin\{solution\}", text))
    disp = len(re.findall(r"\\\[", text)) + len(re.findall(r"\\begin\{align", text))
    ch_num = re.search(r"ch(\d+)", f).group(1)
    print(f"{ch_num:>4} {title:<50} {secs:>5} {sols:>5} {disp:>5}")
    total_solutions += sols
    total_sections += secs
    total_display_eq += disp

print("-" * 73)
print(f"{'':>4} {'TOTAL':<50} {total_sections:>5} {total_solutions:>5} {total_display_eq:>5}")
