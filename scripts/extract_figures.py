"""
Extract figures from scanned PDF by finding "Figure X.Y.Z" captions.
Crops the figure region (above the caption) and saves as PNG.
"""
import sys
import os
import re
import glob

try:
    import pymupdf
except ImportError:
    import fitz as pymupdf  # older PyMuPDF versions

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LATEX_DIR = os.path.join(ROOT, 'latex')
FIGURES_DIR = os.path.join(LATEX_DIR, 'figures')
SCANNED_PDF = os.path.join(ROOT, 'pdfs', 'scanned.pdf')

def find_all_figures_in_pdf(pdf_path):
    """Scan every page for 'Figure X.Y.Z' captions and extract figure regions."""
    doc = pymupdf.open(pdf_path)
    figures = []

    fig_pattern = re.compile(r'Figure\s+(\d+)\.(\d+)\.(\d+)')

    for page_num in range(len(doc)):
        page = doc[page_num]
        # Search for "Figure X.Y.Z" text
        text_instances = page.search_for("Figure ")

        if not text_instances:
            continue

        # Get full page text to find figure captions
        text_dict = page.get_text("dict")
        page_text = page.get_text("text")

        # Find all figure references on this page
        for match in fig_pattern.finditer(page_text):
            ch = int(match.group(1))
            sec = int(match.group(2))
            fig_num = int(match.group(3))
            fig_id = f"{ch}.{sec}.{fig_num}"

            # Find the location of this caption on the page
            search_text = f"Figure {fig_id}"
            rects = page.search_for(search_text)

            if rects:
                caption_rect = rects[0]  # First occurrence
                figures.append({
                    'fig_id': fig_id,
                    'chapter': ch,
                    'section': sec,
                    'fig_num': fig_num,
                    'page_num': page_num,
                    'caption_y': caption_rect.y0,  # Top of caption text
                    'caption_rect': caption_rect,
                    'page_width': page.rect.width,
                    'page_height': page.rect.height,
                })

    doc.close()
    return figures

def extract_figure_image(pdf_path, fig_info, output_path, dpi=250):
    """Extract a cropped figure region from the PDF page."""
    doc = pymupdf.open(pdf_path)
    page = doc[fig_info['page_num']]

    page_rect = page.rect
    caption_y = fig_info['caption_y']

    # The figure is typically ABOVE the caption.
    # We need to find the top boundary of the figure.
    # Heuristic: scan upward from caption to find where the figure starts.
    # For now, take a generous region: from page top margin to below the caption.

    # Search for caption end (look for the full caption text block)
    # The caption typically spans 1-3 lines below "Figure X.Y.Z"
    caption_bottom = caption_y + 40  # Approximate: caption + 2-3 lines

    # Figure top: look for the nearest text block above the figure
    # Simple heuristic: take from ~40% above caption position or page top margin
    # Better: use the region from margin top to caption bottom

    # Get all text blocks to find the text block just above the figure
    blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)

    # Sort blocks by y position
    text_blocks_above = []
    for b in blocks:
        if b[4].strip() and b[3] < caption_y - 10:  # blocks ending above caption
            # Check if it looks like regular text (not part of figure)
            text = b[4].strip()
            if len(text) > 50 and not text.startswith('Figure'):
                text_blocks_above.append(b)

    if text_blocks_above:
        # The figure starts just below the last text paragraph above it
        last_text_above = max(text_blocks_above, key=lambda b: b[3])
        figure_top = last_text_above[3] + 5  # Just below last text block
    else:
        # No text above — figure is at top of page
        figure_top = max(30, page_rect.y0 + 30)  # Small margin from top

    # Ensure we capture enough
    figure_top = max(figure_top, caption_y - 350)  # At least 350 points above caption
    figure_top = max(figure_top, page_rect.y0 + 20)  # Don't go above page

    # Crop rectangle: full width, from figure_top to caption_bottom
    margin_x = 30
    clip_rect = pymupdf.Rect(
        page_rect.x0 + margin_x,
        figure_top,
        page_rect.x1 - margin_x,
        min(caption_bottom, page_rect.y1 - 10)
    )

    # Render the cropped region
    mat = pymupdf.Matrix(dpi/72, dpi/72)
    pix = page.get_pixmap(matrix=mat, clip=clip_rect)
    pix.save(output_path)

    doc.close()
    return output_path

def update_tex_files(figures):
    """Update .tex files to use correct figure filenames."""
    # Build a mapping from fig_id to image path
    fig_map = {}
    for fig in figures:
        fig_id = fig['fig_id']
        ch = fig['chapter']
        img_relpath = f"figures/ch{ch:02d}/fig_{fig_id.replace('.', '_')}.png"
        fig_map[fig_id] = img_relpath

    # Process each tex file
    for tex_file in sorted(glob.glob(os.path.join(LATEX_DIR, 'ch*', 'sec*.tex'))):
        with open(tex_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        original = content

        # Find all \includegraphics and update paths
        # Current pattern: \includegraphics[width=0.8\textwidth]{figures/chXX/some_label.png}
        def replace_includegraphics(m):
            old_path = m.group(1)
            # Extract the figure label from the nearby \label{} command
            return m.group(0)  # Don't change here — we'll do it differently

        # Instead, find figure environments and match by label
        fig_env_pattern = re.compile(
            r'(\\begin\{figure\}\[H\]\s*\n\\centering\s*\n)'
            r'(\\includegraphics\[.*?\]\{.*?\}\s*\n)'
            r'(\\caption\{.*?\}\s*\n\\label\{(.*?)\})',
            re.DOTALL
        )

        for match in fig_env_pattern.finditer(content):
            label = match.group(4)
            # Extract figure ID from label
            id_match = re.search(r'(\d+\.\d+\.\d+)', label)
            if id_match:
                fig_id = id_match.group(1)
                if fig_id in fig_map:
                    old_includegraphics = match.group(2)
                    new_includegraphics = f'\\includegraphics[width=0.8\\textwidth]{{{fig_map[fig_id]}}}\n'
                    content = content.replace(old_includegraphics, new_includegraphics, 1)

        if content != original:
            with open(tex_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  Updated: {os.path.relpath(tex_file, LATEX_DIR)}")

def main():
    print("=" * 60)
    print("FIGURE EXTRACTION v2: Find by caption index, crop region")
    print("=" * 60)

    # Step 1: Find all figures in the scanned PDF
    print("\nScanning PDF for 'Figure X.Y.Z' captions...")
    figures = find_all_figures_in_pdf(SCANNED_PDF)

    # Deduplicate (same figure ID might appear multiple times as references)
    seen = set()
    unique_figures = []
    for fig in figures:
        if fig['fig_id'] not in seen:
            seen.add(fig['fig_id'])
            unique_figures.append(fig)
    figures = unique_figures

    print(f"Found {len(figures)} unique figures in scanned PDF")

    # Print summary by chapter
    by_ch = {}
    for fig in figures:
        ch = fig['chapter']
        if ch not in by_ch:
            by_ch[ch] = []
        by_ch[ch].append(fig)

    for ch in sorted(by_ch.keys()):
        fig_ids = [f['fig_id'] for f in by_ch[ch]]
        print(f"  Ch {ch:2d}: {len(fig_ids)} figures — {fig_ids[0]} to {fig_ids[-1]}")

    # Step 2: Extract each figure as a cropped PNG
    print("\nExtracting figure images...")
    for fig in figures:
        ch = fig['chapter']
        ch_dir = os.path.join(FIGURES_DIR, f'ch{ch:02d}')
        os.makedirs(ch_dir, exist_ok=True)

        fig_id = fig['fig_id']
        img_filename = f"fig_{fig_id.replace('.', '_')}.png"
        img_path = os.path.join(ch_dir, img_filename)

        extract_figure_image(SCANNED_PDF, fig, img_path, dpi=250)
        fig['img_path'] = img_path
        fig['img_relpath'] = f"figures/ch{ch:02d}/{img_filename}"

    print(f"Extracted {len(figures)} figure images")

    # Step 3: Update .tex files
    print("\nUpdating .tex files...")
    update_tex_files(figures)

    # Step 4: Count figures in .tex vs extracted
    tex_fig_count = 0
    for tex_file in glob.glob(os.path.join(LATEX_DIR, 'ch*', 'sec*.tex')):
        with open(tex_file, 'r', encoding='utf-8', errors='replace') as f:
            tex_fig_count += f.read().count('\\begin{figure}')

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"  Figures found in scanned PDF: {len(figures)}")
    print(f"  Figure environments in .tex:  {tex_fig_count}")
    print(f"  Images saved to: {FIGURES_DIR}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
