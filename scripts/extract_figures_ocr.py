#!/usr/bin/env python3
"""Extract figures from scanned PDF using OCR to find captions."""
import os
import re
import sys

try:
    import fitz as pymupdf
except ImportError:
    import pymupdf

import easyocr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LATEX_DIR = os.path.join(ROOT, 'latex')

ROMAN_NUMS = ['I', 'II', 'III', 'IV', 'V']


def extract_all_figures(pdf_path, output_dir, dpi=250):
    """Scan PDF pages with OCR, find figure captions, crop regions."""
    doc = pymupdf.open(pdf_path)
    reader = easyocr.Reader(['en'], gpu=False)

    fig_pattern = re.compile(r'Figure\s+(I{1,3}V?)\s*[-–—]\s*(\d+[a-z]?)', re.IGNORECASE)
    figures_found = []

    total_pages = len(doc)
    print(f"Scanning {total_pages} pages for figures...")

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
                roman_ch = match.group(1).upper()
                fig_num = match.group(2)
                ch_int = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5}.get(roman_ch, 0)

                # bbox is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                # Get center y of caption in OCR image coords
                caption_y_ocr = (bbox[0][1] + bbox[2][1]) / 2
                caption_top_ocr = bbox[0][1]

                # Convert OCR coords to PDF coords
                ocr_scale = 150 / 72
                caption_y_pdf = caption_top_ocr / ocr_scale

                print(f"  Page {page_num+1}: Figure {roman_ch}-{fig_num} (y={caption_y_pdf:.0f})")

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

                # Save
                ch_str = f"ch{ch_int:02d}"
                fig_dir = os.path.join(output_dir, ch_str)
                os.makedirs(fig_dir, exist_ok=True)
                filename = f"fig_{roman_ch}_{fig_num}.png"
                filepath = os.path.join(fig_dir, filename)
                pix_crop.save(filepath)

                figures_found.append({
                    'fig_id': f"{roman_ch}-{fig_num}",
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


def main():
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'pdfs', 'scanned.pdf')
    output_dir = os.path.join(LATEX_DIR, 'figures')

    figures = extract_all_figures(pdf_path, output_dir)

    print(f"\n=== Summary ===")
    from collections import Counter
    ch_counts = Counter(f['chapter'] for f in figures)
    for ch in sorted(ch_counts):
        roman = ROMAN_NUMS[ch - 1] if ch <= len(ROMAN_NUMS) else str(ch)
        print(f"  Chapter {roman}: {ch_counts[ch]} figures")
    print(f"  Total: {len(figures)} figures extracted")


if __name__ == "__main__":
    main()
