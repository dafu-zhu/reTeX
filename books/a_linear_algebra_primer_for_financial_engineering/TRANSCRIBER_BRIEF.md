# Standing brief for chunk transcribers — this book

Read this in full before touching anything. Your dispatch message gives you
three things: a **PDF page range**, a **chapter number NN**, and a **chunk id
cK**. Everything else is here.

Source PDF: `pdfs/baruch_01_textbook.pdf`. It has **no text layer** — every
page must be read as an image.

---

## 1. Reading the pages — the part that has already cost this book real content

The reader renders each requested page as a **two-page SPREAD**, so asking for
page 60 and page 61 can return the same image showing two printed pages side
by side. Two agents early in this run concluded the PDF contained duplicate
spreads, reported "deduplicating" them, and risked silently dropping pages.
It does not: the PDF is single 6×9 pages, 1:1, with zero duplicates (verified
programmatically, and confirmed by consecutive pages having distinct CropBox
left-edge x-coordinates).

Render each page through **its own CropBox**, which resolves the shared spread
image down to exactly that one printed page:

```
python -c "import pymupdf; d=pymupdf.open('pdfs/baruch_01_textbook.pdf'); \
  p=d[N-1]; p.set_cropbox(p.cropbox); p.get_pixmap(dpi=300).save('pN.png')"
```

(0-based index: PDF page N is `d[N-1]`.) Then read `pN.png`. Confirm you are on
the right page by its printed folio: **printed page = PDF index − 16**. Use
600–1200 dpi for dense matrices, tables, and any typographic question.

Never skip a page as a duplicate. Never "deduplicate". A page dropped this way
is invisible until final verification, after ~50 agents have run.

## 2. File ownership — you write only your own files

- Write `books/a_linear_algebra_primer_for_financial_engineering/latex/chNN/secNN_cK_1.tex`,
  `..._cK_2.tex`, and so on. The `cK` marks them as yours.
- **Never** a plain `secNN_<n>.tex`, and never another chunk's `_cJ_` prefix.
- Never `chNN/chNN.tex` or `progress.md` — the orchestrator owns both and
  writes them once, after every chunk of the chapter has returned.
- Nothing outside `chNN/`.
- Line 1 of every file: `% PAGES: <your real PDF range for that file>`, e.g.
  `% PAGES: 141-142`. **PDF indices, never printed page numbers.** One agent
  recorded printed numbers and every header had to be repaired; the later
  cross-check pass maps pages to files using these.

## 3. Chunk boundaries

Sections, proofs and examples straddle page boundaries constantly.

- **Check the previous chunk's last file before you start**, and re-list the
  directory before you finish — a sibling may still have been writing.
- If the previous chunk left a `\begin{...}` open, **close it** at the top of
  your first file. Do not open a second one.
- If it ended **mid-display-math** with an open `\[`, close it with `\]`.
  This happened at the ch06 c1/c2 boundary.
- You may leave something open at the end of your last file for the next
  chunk. If you do, say so in an explicit comment naming it.
- If the source cuts off mid-construct and you cannot see how it continues,
  **leave it open and comment** — never invent the continuation.

Run before finishing:

```
python scripts/check_env_balance.py --book a_linear_algebra_primer_for_financial_engineering --chapter NN
```

It tracks `\begin`/`\end` and `\[`/`\]` across the whole chapter in page order.
A failure naming only something you deliberately left open for the next chunk
is expected; anything else is not.

## 4. The example-block trap

This book closes its **manually typeset** worked-example blocks with a printed
square **identical to a proof's QED symbol**. Those blocks are an italic run-in
label — `\textit{Example:}`, `\textit{Examples:}`, `\textit{Solution:}` —
sometimes with `\rule{\linewidth}{0.4pt}`, and they are **not environments**.
They close with `\hfill$\square$` then `\medskip` and a rule.

A square you meet at the top of a page may be closing an *example* begun on the
previous page, not a proof. Misreading exactly this broke chapter 3 once.
**Never emit `\end{proof}` unless a `\begin{proof}` is genuinely open.**

Because these blocks are not environments, `check_env_balance.py` cannot see
one straddling a boundary — so if one of yours runs past your last page, say so
explicitly in a comment.

Use `examplex` / `answerx` **only** where the source label is exactly
"Example:" / "Answer:". For "Examples:" (plural) or "Solution:", use a manual
italic run-in. `examplex` auto-appends its closing square; `answerx` does not,
so add `\hfill$\square$` there.

## 5. Conventions

- Macros: `\E{}`, `\Var{}`, `\Cov{}`, `\plim`, `\dto`, `\pto`, `\pd{}{}`.
  Prefer them over hand-written equivalents.
- Bold vectors and matrices: the `\bf<Name>` macros from `preamble.tex`
  (`\bfX`, `\bfbeta`). Never `\vec{}`, never a raw `\mathbf{}` for a whole
  symbol. Bolding an individual matrix **entry** to match the source's own
  emphasis is fine. If a bold symbol has no macro yet, still write
  `\bf<Name>` — the missing definition surfaces as a compile error and gets
  added to `preamble.tex`.
- **This book contains no figures.** Every graphic-like element is a framed
  pseudocode block. Captioned `Table N.M` → a captioned `table` float with
  `\fbox{\begin{minipage}...}`. Uncaptioned → a plain centered
  `fbox`/`minipage`.
- Pseudocode-box labels `Input:`, `Output:`, `Function Call:` are set in
  **regular weight**, not bold — verified at 1200 dpi against Tables 2.1 and
  6.8. Do not wrap them in `\textbf{}`.
- Exercises: the chapter's **whole** exercise list goes in ONE file inside a
  single `\begin{exercises}...\end{exercises}`. That environment opens a fresh
  `enumerate`, so splitting it across files silently restarts numbering at 1.
- References sections cite with `\cite{}` keys; match ch01–ch06.
- **Theorem-like environments do NOT share a counter in this book** — it is the
  exception to the usual convention. Definitions, Theorems and Lemmas each have
  their own per-chapter counter (verified on the scans: Definition 4.2 is
  immediately followed by Theorem 4.1; Theorem 5.1 by Lemma 5.1). Reproduce the
  printed numbering exactly; never renumber to make it sequential across types.
- QED: **never** `\qed`, `\blacksquare`, or `\hfill$\blacksquare$` inside
  `\begin{proof}...\end{proof}` — the environment appends the symbol itself.
  `\qedhere` only when a proof ends with a displayed equation or list.

## 6. Fidelity

- Reproduce the source **exactly**, including anything that looks like an
  error. This book has many: missing words, wrong indices, `Cauchy–Schwarz`
  spelled two ways on adjacent pages. Transcribe them as printed and add a `%`
  comment noting it. **The page is ground truth; never correct the author.**
- **If a dense matrix or table is hard to read, do NOT reconstruct it by
  deriving values from nearby formulas.** Transcribe what you can see and mark
  the rest `% UNCLEAR: [what, page X]`. A cross-check found a derived matrix
  had zeroed six real entries — because the equation supplying them had itself
  been dropped. The derivation looked entirely plausible and compiled fine.
- Any other ambiguity: `% UNCLEAR: [description, page X]`. Never guess.
- Output only LaTeX source.

## 7. What to report back

Files written, the true PDF range of each, section numbers and titles, anything
you closed from the previous chunk or left open for the next (including
non-environment example blocks and open `\[`), your `check_env_balance.py`
result, and explicit confirmation that you rendered and read every page in your
range individually via CropBox.

Do not paste the book's title, author, or extended prose into your reply — the
orchestrating conversation must stay free of book metadata.
