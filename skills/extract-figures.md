---
name: extract-figures
description: "Extract all figures from a scanned PDF textbook by finding 'Figure X.Y.Z' captions, cropping the figure region, and saving as PNGs. Then update LaTeX files to use \\includegraphics. Use when the user wants to extract figures from a PDF, import book figures into LaTeX, or says 'get the figures', 'extract images from PDF'. Also triggered as Phase 2 of /pdf-to-latex."
---

# Extract Figures from Scanned PDF

Find every figure in a scanned PDF by its caption index, crop the figure region, save as PNG, and wire into LaTeX.

## Input
- Scanned PDF path (e.g., `pdfs/scanned.pdf`)
- LaTeX directory (e.g., `latex/`)

## Output
- PNGs in `latex/figures/chNN/fig_X_Y_Z.png`
- Updated `.tex` files with `\includegraphics` pointing to extracted PNGs

---

## Step 1: Find Figures

Use PyMuPDF (`import pymupdf`) to scan every page for text matching `Figure X.Y.Z`:

```python
import pymupdf, re
doc = pymupdf.open(pdf_path)
pattern = re.compile(r'Figure\s+(\d+)\.(\d+)\.(\d+)')
for page_num in range(len(doc)):
    page_text = doc[page_num].get_text("text")
    for match in pattern.finditer(page_text):
        fig_id = f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
        rects = doc[page_num].search_for(f"Figure {fig_id}")
        # Record: fig_id, page_num, caption_y = rects[0].y0
```

Deduplicate: same figure ID may appear as a text reference elsewhere. Keep only the first occurrence (the actual figure).

## Step 2: Crop and Extract

For each figure, crop from the page:
- **Bottom boundary**: caption text + ~40pt (2–3 lines of caption)
- **Top boundary**: find the last paragraph of body text above the figure (text block with >50 chars ending above caption_y - 10pt). Figure starts just below that text block. Minimum: 350pt above caption.
- **Left/right**: full page width minus 30pt margins
- **DPI**: 250 (good quality, reasonable file size)

```python
clip_rect = pymupdf.Rect(x0+30, figure_top, x1-30, caption_bottom)
pix = page.get_pixmap(matrix=pymupdf.Matrix(250/72, 250/72), clip=clip_rect)
pix.save(output_path)
```

Save to: `latex/figures/ch{NN}/fig_{X_Y_Z}.png`

## Step 3: Update .tex Files

Find figure environments by matching `\label{...X.Y.Z...}` and replace the body between `\centering` and `\caption` with:
```latex
\includegraphics[width=0.8\textwidth]{figures/chNN/fig_X_Y_Z.png}
```

## Step 4: Verify

Compare counts:
- Figures extracted from PDF
- `\begin{figure}` environments in .tex files

Report mismatches. A small delta (±3) is acceptable due to label format differences.

---

## Rules

| Rule | Why |
|------|-----|
| Match by caption index `Figure X.Y.Z` | Every textbook figure has a numbered caption — this is the reliable identifier |
| Crop the region, not the full page | Full-page screenshots waste space and include surrounding text |
| Use PyMuPDF (`pymupdf`), not pdf2image | pymupdf handles cropping natively, no external dependencies |
| 250 DPI | Balances quality vs file size (~50KB per figure vs ~200KB at 300 DPI) |
| Deduplicate by fig_id | The same "Figure 1.2.1" text appears in cross-references — only extract the first hit |
