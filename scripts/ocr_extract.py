#!/usr/bin/env python3
"""Extract text from scanned PDF pages using EasyOCR."""
import sys
import os
import json

try:
    import fitz as pymupdf
except ImportError:
    import pymupdf

import easyocr

def extract_pages(pdf_path, start_page, end_page, output_dir):
    """Render PDF pages and OCR them."""
    os.makedirs(output_dir, exist_ok=True)

    reader = easyocr.Reader(['en'], gpu=False)
    doc = pymupdf.open(pdf_path)

    results = {}
    for page_num in range(start_page - 1, min(end_page, len(doc))):
        print(f"  OCR page {page_num + 1}...", end=" ", flush=True)
        page = doc[page_num]
        # Render at 200 DPI for good OCR quality
        pix = page.get_pixmap(matrix=pymupdf.Matrix(200/72, 200/72))
        img_path = os.path.join(output_dir, f"page_{page_num + 1:03d}.png")
        pix.save(img_path)

        # OCR the image
        ocr_results = reader.readtext(img_path, detail=0, paragraph=True)
        text = "\n".join(ocr_results)
        results[page_num + 1] = text

        # Save individual page text
        txt_path = os.path.join(output_dir, f"page_{page_num + 1:03d}.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"({len(text)} chars)")

    doc.close()

    # Save combined output
    combined_path = os.path.join(output_dir, "combined.txt")
    with open(combined_path, 'w', encoding='utf-8') as f:
        for page_num in sorted(results.keys()):
            f.write(f"\n{'='*60}\n")
            f.write(f"PAGE {page_num} (printed p.{page_num - 11})\n")
            f.write(f"{'='*60}\n\n")
            f.write(results[page_num])
            f.write("\n")

    print(f"\nSaved {len(results)} pages to {output_dir}")
    return results

if __name__ == "__main__":
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "pdfs/scanned.pdf"
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    end = int(sys.argv[3]) if len(sys.argv) > 3 else 21
    output_dir = sys.argv[4] if len(sys.argv) > 4 else "ocr_output"

    print(f"Extracting pages {start}-{end} from {pdf_path}")
    extract_pages(pdf_path, start, end, output_dir)
