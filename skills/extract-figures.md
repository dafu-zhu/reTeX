# Extract Figures from Scanned PDF

Extract all figures from a scanned PDF by finding "Figure X.Y.Z" captions, cropping the figure region, and importing into LaTeX.

## Usage
`/extract-figures <scanned_pdf_path> <latex_dir>`

## Process

### Step 1: Scan PDF for figure captions
Use PyMuPDF to search every page for text matching `Figure \d+\.\d+\.\d+`. Record:
- Figure ID (e.g., 1.2.1)
- Page number
- Caption Y-coordinate (for cropping)

### Step 2: Crop and extract
For each figure:
1. Find text blocks above the caption to determine figure top boundary
2. Crop region: from figure top to caption bottom, full page width minus margins
3. Render at 250 DPI as PNG
4. Save to `figures/chXX/fig_X_Y_Z.png`

### Step 3: Update .tex files
Replace any existing figure body (TikZ or placeholder) with:
```latex
\includegraphics[width=0.8\textwidth]{figures/chXX/fig_X_Y_Z.png}
```

### Step 4: Verify
- Count extracted figures vs figure environments in .tex
- Report any mismatches

## Key Rules
- **Match by caption index** — every figure in the book has "Figure X.Y.Z" caption
- **Crop, don't full-page** — extract just the figure region, not the entire page
- **Use PyMuPDF** (`import pymupdf`), not pdf2image
- **250 DPI** for good quality without huge file sizes
- **Deduplicate** — same figure ID may appear as reference elsewhere; only extract the first (actual figure)

## Arguments
- `$ARGUMENTS` — scanned PDF path and latex directory
