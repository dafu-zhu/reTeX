"""Replace figure placeholder boxes with actual includegraphics."""
import re
import glob

fig_map = {
    '1.1': 'fig_1_1', '1.2': 'fig_1_2', '1.3': 'fig_1_3',
    '1.4': 'fig_1_4', '1.5': 'fig_1_5', '1.6': 'fig_1_6', '1.7': 'fig_1_7',
    '2.1': 'fig_2_1', '2.2': 'fig_2_2', '2.3': 'fig_2_3', '2.4': 'fig_2_4',
    '3.1': 'fig_3_1',
    '4.1': 'fig_4_1',
    '6.1': 'fig_6_1', '6.2': 'fig_6_2', '6.3': 'fig_6_3',
    '6.4': 'fig_6_4', '6.5': 'fig_6_5', '6.6': 'fig_6_6', '6.7': 'fig_6_7',
    '8.1': 'fig_8_1',
    '9.1': 'fig_9_1', '9.2': 'fig_9_2', '9.3': 'fig_9_3', '9.4': 'fig_9_4',
    '10.1': 'fig_10_1a', '10.2': 'fig_10_2', '10.3': 'fig_10_3', '10.4': 'fig_10_4',
}

replaced = 0
tex_files = glob.glob('latex/ch*/*.tex') + glob.glob('latex/backmatter/*.tex')

for f in tex_files:
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()
    original = content

    for fig_id, fig_file in fig_map.items():
        img_line = (
            '\\includegraphics[width=0.9\\textwidth,'
            'trim=50 350 50 350,clip]{figures/' + fig_file + '.png}'
        )

        # Remove commented-out includegraphics lines
        content = re.sub(
            r'% *\\includegraphics\[.*?\]\{.*?\}\n',
            '', content)

        # Replace single-line fbox placeholders mentioning Figure X.Y
        pat = (r'\\fbox\{\\parbox\{[^}]+\}\{[^}]*?Figure\s+'
               + re.escape(fig_id) + r'[^}]*?\}\}')
        content, n = re.subn(pat, lambda m: img_line, content, flags=re.DOTALL)
        replaced += n

        # Multiline fbox with % continuation
        pat2 = (r'\\fbox\{\\parbox\{[^}]+\}\{\\centering\\vspace\{[^}]+\}%\n'
                r'[^\}]*?Figure\s+' + re.escape(fig_id) + r'[^\}]*?\\vspace\{[^}]+\}\}\}')
        content, n = re.subn(pat2, lambda m: img_line, content, flags=re.DOTALL)
        replaced += n

    if content != original:
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(content)
        print(f'  Updated: {f}')

print(f'Replaced {replaced} figure placeholders total')
