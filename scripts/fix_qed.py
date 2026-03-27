"""Remove duplicate QED symbols from proof environments."""
import re
import glob
import os

files = (
    glob.glob('D:/GitHub/reTeX/latex/ch*/ch*.tex') +
    glob.glob('D:/GitHub/reTeX/latex/backmatter/solutions.tex')
)

for f in sorted(files):
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()
    original = content

    # Remove \qed (with optional surrounding whitespace)
    # Handles: "result follows. \qed" and standalone "\qed" lines
    content = re.sub(r'\s*\\qed\b', '', content)

    # Remove \hfill$\blacksquare$ patterns (used in solutions)
    content = re.sub(r'\s*\\hfill\s*\$\\blacksquare\$', '', content)

    # Remove standalone $\blacksquare$ at end of lines
    content = re.sub(r'\s*\$\\blacksquare\$\s*$', '', content, flags=re.MULTILINE)

    # Remove \vspace{-\baselineskip} that was used before \qed
    content = re.sub(r'\\vspace\{-\\baselineskip\}\s*\n', '', content)

    # Clean up any resulting double blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)

    if content != original:
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(content)
        print(f'Fixed: {os.path.basename(f)}')

print('Done')
