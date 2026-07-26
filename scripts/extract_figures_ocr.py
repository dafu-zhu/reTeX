#!/usr/bin/env python3
"""Extract figures from scanned PDF using OCR to find captions.

Use this when the source PDF has no text layer, so the caption-scanning
extractor (scripts/extract_figures.py, which uses PyMuPDF text search)
cannot find any figures.
"""
import argparse
import os
import re
import sys

try:
    import fitz as pymupdf
except ImportError:
    import pymupdf

import easyocr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ROMAN_NUMS = ['I', 'II', 'III', 'IV', 'V']
ROMAN_TO_INT = {r: i + 1 for i, r in enumerate(ROMAN_NUMS)}

# Caption numbering styles. Each pattern must match ONLY its own style's
# sample caption, not the other styles' (see the __main__ self-test below).
NUMBERING_STYLES = {
    # "Figure 3.7" — two-part arabic (chapter.figure). Most common.
    # Negative lookahead keeps this from also matching the first two
    # components of a three-part "Figure 3.7.1" caption.
    'arabic-dot': re.compile(r'Figure\s+(\d+)\.(\d+)(?!\.\d)', re.IGNORECASE),
    # "Figure 3.7.1" — three-part arabic (chapter.section.figure).
    'arabic-dot3': re.compile(r'Figure\s+(\d+)\.(\d+)\.(\d+)', re.IGNORECASE),
    # "Figure I-3" — roman-numeral chapter, dash, figure number.
    'roman-dash': re.compile(r'Figure\s+(I{1,3}V?)\s*[-–—]\s*(\d+[a-z]?)', re.IGNORECASE),
}


def _validate_book_name(name):
    """Reject book names that could escape books/ via a path-traversal component."""
    if not name or '/' in name or '\\' in name or '..' in name:
        raise SystemExit(
            f"Error: invalid book name '{name}' "
            "(must be a plain directory name — no '/', '\\', or '..')"
        )


def parse_caption(numbering, match):
    """Turn a regex match for the given numbering style into (chapter:int, fig_id:str).

    fig_id is the human-readable figure identifier used in log output and,
    with '.'/'-' replaced by '_', in output filenames.
    """
    if numbering == 'arabic-dot':
        ch = int(match.group(1))
        fig_id = f"{match.group(1)}.{match.group(2)}"
    elif numbering == 'arabic-dot3':
        ch = int(match.group(1))
        fig_id = f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
    elif numbering == 'roman-dash':
        roman_ch = match.group(1).upper()
        ch = ROMAN_TO_INT.get(roman_ch, 0)
        fig_id = f"{roman_ch}-{match.group(2)}"
    else:
        raise ValueError(f"Unknown numbering style: {numbering}")
    return ch, fig_id


def extract_all_figures(pdf_path, output_dir, numbering='arabic-dot', dpi=250):
    """Scan PDF pages with OCR, find figure captions, crop regions."""
    doc = pymupdf.open(pdf_path)
    reader = easyocr.Reader(['en'], gpu=False)

    fig_pattern = NUMBERING_STYLES[numbering]
    figures_found = []

    total_pages = len(doc)
    print(f"Scanning {total_pages} pages for figures (numbering: {numbering})...")

    for page_num in range(total_pages):
        page = doc[page_num]

        # Render page for OCR at moderate DPI
        pix_ocr = page.get_pixmap(matrix=pymupdf.Matrix(150/72, 150/72))
        img_bytes = pix_ocr.tobytes('png')

        # Save temp image for easyocr
        tmp_path = os.path.join(output_dir, '_temp_page.png')
        os.makedirs(output_dir, exist_ok=True)
        pix_ocr.save(tmp_path)

        # OCR with bounding boxes
        results = reader.readtext(tmp_path, detail=1)

        for bbox, text, conf in results:
            match = fig_pattern.search(text)
            if match:
                ch_int, fig_id = parse_caption(numbering, match)

                # bbox is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                # Get center y of caption in OCR image coords
                caption_y_ocr = (bbox[0][1] + bbox[2][1]) / 2
                caption_top_ocr = bbox[0][1]

                # Convert OCR coords to PDF coords
                ocr_scale = 150 / 72
                caption_y_pdf = caption_top_ocr / ocr_scale

                print(f"  Page {page_num+1}: Figure {fig_id} (y={caption_y_pdf:.0f})")

                # Crop figure region: from above caption to just below caption text
                margin_x = 25  # points from edges
                page_w = page.rect.width
                page_h = page.rect.height

                # Find figure top: scan upward for empty space
                # Simple heuristic: figure starts at max(top_margin, caption_y - 250)
                fig_top = max(30, caption_y_pdf - 280)
                fig_bottom = caption_y_pdf + 25  # Include caption text

                clip = pymupdf.Rect(margin_x, fig_top, page_w - margin_x, fig_bottom)

                # Render at high DPI
                scale = dpi / 72
                mat = pymupdf.Matrix(scale, scale)
                pix_crop = page.get_pixmap(matrix=mat, clip=clip)

                # Save — filename convention matches scripts/extract_figures.py:
                # fig_<id with '.'/'-' -> '_'>.png inside figures/chNN/
                ch_str = f"ch{ch_int:02d}"
                fig_dir = os.path.join(output_dir, ch_str)
                os.makedirs(fig_dir, exist_ok=True)
                safe_id = fig_id.replace('.', '_').replace('-', '_')
                filename = f"fig_{safe_id}.png"
                filepath = os.path.join(fig_dir, filename)
                pix_crop.save(filepath)

                figures_found.append({
                    'fig_id': fig_id,
                    'chapter': ch_int,
                    'page': page_num + 1,
                    'path': filepath,
                })

    # Cleanup
    tmp_path = os.path.join(output_dir, '_temp_page.png')
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    doc.close()
    return figures_found


def build_arg_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--book', required=True, help='Book name under books/')
    parser.add_argument('--pdf', default=os.path.join(ROOT, 'pdfs', 'scanned.pdf'),
                         help='Source scanned PDF (default: pdfs/scanned.pdf)')
    parser.add_argument('--dpi', type=int, default=250,
                         help='Render DPI for cropped figure images (default: 250)')
    parser.add_argument('--numbering', choices=sorted(NUMBERING_STYLES.keys()),
                         default='arabic-dot',
                         help="Caption numbering style: arabic-dot 'Figure 3.7' "
                              "(default), arabic-dot3 'Figure 3.7.1', "
                              "roman-dash 'Figure I-3'")
    return parser


def main():
    parser = build_arg_parser()
    args = parser.parse_args()
    _validate_book_name(args.book)

    latex_dir = os.path.join(ROOT, 'books', args.book, 'latex')
    if not os.path.isdir(latex_dir):
        raise SystemExit(f'No such book: {args.book} (expected {latex_dir})')

    output_dir = os.path.join(latex_dir, 'figures')

    figures = extract_all_figures(args.pdf, output_dir, numbering=args.numbering, dpi=args.dpi)

    print(f"\n=== Summary ===")
    from collections import Counter
    ch_counts = Counter(f['chapter'] for f in figures)
    for ch in sorted(ch_counts):
        if args.numbering == 'roman-dash' and ch <= len(ROMAN_NUMS):
            label = ROMAN_NUMS[ch - 1]
        else:
            label = str(ch)
        print(f"  Chapter {label}: {ch_counts[ch]} figures")
    print(f"  Total: {len(figures)} figures extracted")


if __name__ == "__main__":
    main()
