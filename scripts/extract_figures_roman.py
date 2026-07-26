#!/usr/bin/env python3
"""Extract figures from scanned PDF with Roman numeral chapter format (Figure I-1)."""
import os
import re
import sys

try:
    import fitz as pymupdf
except ImportError:
    import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LATEX_DIR = os.path.join(ROOT, 'latex')

ROMAN_TO_INT = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5}
ROMAN_NUMS = ['I', 'II', 'III', 'IV', 'V']

def find_figures(pdf_path):
    """Find all 'Figure X-N' captions in the PDF."""
    doc = pymupdf.open(pdf_path)
    figures = []

    # Match "Figure I-1", "Figure II-15a", etc.
    fig_pattern = re.compile(r'Figure\s+(I{1,3}V?)\s*[-–]\s*(\d+[a-z]?)')

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = page.get_text("text")

        for match in fig_pattern.finditer(page_text):
            roman_ch = match.group(1)
            fig_num = match.group(2)
            ch_int = ROMAN_TO_INT.get(roman_ch, 0)
            fig_id = f"{roman_ch}-{fig_num}"

            # Find caption location on page
            search_text = f"Figure {fig_id}"
            rects = page.search_for(search_text)
            if not rects:
                # Try with en-dash
                search_text = f"Figure {roman_ch}\u2013{fig_num}"
                rects = page.search_for(search_text)

            if rects:
                caption_rect = rects[0]
                figures.append({
                    'fig_id': fig_id,
                    'chapter': ch_int,
                    'roman': roman_ch,
                    'fig_num': fig_num,
                    'page_num': page_num,
                    'caption_y': caption_rect.y0,
                    'caption_bottom': caption_rect.y1,
                    'page_width': page.rect.width,
                    'page_height': page.rect.height,
                })

    doc.close()
    return figures


def extract_figure(pdf_path, fig_info, output_dir, dpi=250):
    """Crop figure region above caption and save as PNG."""
    doc = pymupdf.open(pdf_path)
    page = doc[fig_info['page_num']]

    # Figure region: from some point above caption to bottom of caption
    # Heuristic: look for the nearest text block above the caption
    margin = 30  # points
    caption_y = fig_info['caption_y']
    caption_bottom = fig_info['caption_bottom']

    # Search upward from caption for the figure region
    # Use full page width minus margins
    x0 = margin
    x1 = fig_info['page_width'] - margin

    # Find text blocks to determine where figure starts
    blocks = page.get_text("blocks")
    blocks_above = [b for b in blocks if b[3] < caption_y - 5]

    if blocks_above:
        # Find the nearest text block above that isn't part of the figure area
        # Sort by y1 (bottom of block) descending
        blocks_above.sort(key=lambda b: b[3], reverse=True)

        # The figure starts after the last text block before it
        # But we need to skip blocks that are part of the figure (axis labels etc.)
        # Heuristic: look for text blocks with significant text content
        fig_top = None
        for block in blocks_above:
            block_text = block[4] if len(block) > 4 else ""
            # If block has substantial text (>50 chars), figure starts below it
            if len(str(block_text).strip()) > 50:
                fig_top = block[3] + 5  # Just below this text block
                break

        if fig_top is None:
            # If no substantial text found, use reasonable fraction of page
            fig_top = max(margin, caption_y - 300)
    else:
        fig_top = margin

    # Ensure minimum figure height
    if caption_y - fig_top < 50:
        fig_top = max(margin, caption_y - 200)

    # Clip region: from fig_top to caption_bottom + small padding
    clip = pymupdf.Rect(x0, fig_top, x1, caption_bottom + 10)

    # Render at specified DPI
    scale = dpi / 72
    mat = pymupdf.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, clip=clip)

    # Save
    ch_str = f"ch{fig_info['chapter']:02d}"
    fig_dir = os.path.join(output_dir, ch_str)
    os.makedirs(fig_dir, exist_ok=True)

    # Filename: fig_I_1.png, fig_II_15a.png
    filename = f"fig_{fig_info['roman']}_{fig_info['fig_num']}.png"
    filepath = os.path.join(fig_dir, filename)
    pix.save(filepath)

    doc.close()
    return filepath


def main():
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'pdfs', 'scanned.pdf')
    output_dir = os.path.join(LATEX_DIR, 'figures')

    print(f"Scanning {pdf_path} for figures...")
    figures = find_figures(pdf_path)
    print(f"Found {len(figures)} figures")

    for fig in figures:
        print(f"  Figure {fig['fig_id']} (PDF p.{fig['page_num']+1})")

    print(f"\nExtracting to {output_dir}...")
    for fig in figures:
        path = extract_figure(pdf_path, fig, output_dir)
        print(f"  {fig['fig_id']} -> {path}")

    # Summary per chapter
    from collections import Counter
    ch_counts = Counter(f['chapter'] for f in figures)
    print(f"\nSummary:")
    for ch in sorted(ch_counts):
        roman = ROMAN_NUMS[ch - 1] if ch <= len(ROMAN_NUMS) else str(ch)
        print(f"  Chapter {roman}: {ch_counts[ch]} figures")
    print(f"  Total: {len(figures)} figures")


if __name__ == "__main__":
    main()
