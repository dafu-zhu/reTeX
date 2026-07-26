#!/usr/bin/env python3
"""
extract_figures_v2.py — Extract figures from scanned PDF by caption index.

Usage:
    python scripts/extract_figures_v2.py [--pdf PATH] [--out DIR] [--dpi N]

Searches for "Figure X.Y" captions using PyMuPDF text search, crops the
figure region (caption + image above), and saves as PNG at the specified DPI.

Output filenames: fig_01_1.png, fig_02_3.png, etc. (chap_fig)
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("ERROR: PyMuPDF not installed. Run: pip install pymupdf", file=sys.stderr)
    sys.exit(1)


CAPTION_RE = re.compile(r'Figure\s+(\d+)\.(\d+)', re.IGNORECASE)
CONTEXT_ABOVE_PT = 200   # points above caption baseline to include


def extract_figures(pdf_path: Path, out_dir: Path, dpi: int) -> int:
    doc = fitz.open(str(pdf_path))
    out_dir.mkdir(parents=True, exist_ok=True)
    found = 0

    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("blocks")
        page_rect = page.rect

        for block in blocks:
            x0, y0, x1, y1, text, *_ = block
            match = CAPTION_RE.search(text.strip())
            if not match:
                continue

            ch_num = int(match.group(1))
            fig_num = int(match.group(2))
            label = f"fig_{ch_num:02d}_{fig_num}"
            out_path = out_dir / f"{label}.png"

            # Crop region: from CONTEXT_ABOVE_PT above caption top to caption bottom
            crop_top = max(0, y0 - CONTEXT_ABOVE_PT)
            crop_rect = fitz.Rect(
                page_rect.x0, crop_top,
                page_rect.x1, y1 + 4  # tiny padding below caption
            )

            scale = dpi / 72.0
            mat = fitz.Matrix(scale, scale)
            clip = page.get_pixmap(matrix=mat, clip=crop_rect, alpha=False)
            clip.save(str(out_path))

            print(f"  Extracted Figure {ch_num}.{fig_num} (page {page_num}) → {out_path.name}")
            found += 1

    doc.close()
    return found


def main():
    parser = argparse.ArgumentParser(description="Extract figures from scanned PDF")
    parser.add_argument("--pdf", default="pdfs/scanned.pdf",
                        help="Path to source PDF (default: pdfs/scanned.pdf)")
    parser.add_argument("--out", default="books/<book>/latex/figures",
                        help="Output directory (default: books/<book>/latex/figures)")
    parser.add_argument("--dpi", type=int, default=250,
                        help="Output resolution in DPI (default: 250)")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out)
    print(f"Scanning {pdf_path} for Figure captions...")
    count = extract_figures(pdf_path, out_dir, args.dpi)

    if count == 0:
        print("Phase 2: 0 figures detected — confirmed via PyMuPDF scan")
    else:
        print(f"Phase 2: {count} figures extracted to {out_dir}/")


if __name__ == "__main__":
    main()
