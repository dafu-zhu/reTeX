"""Tests for resume_check.py.

The failure these guard against: SOURCE_PDF="pdfs/scanned.pdf" is the shared
default for every book in this repo, so grepping for it matched an unrelated
existing book. The skill then said "skip Phase 0 entirely", which would have
pointed ~50 transcription agents at that book's tree and destroyed it.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import resume_check
from resume_check import evaluate, parse_book_conf, main

pymupdf = pytest.importorskip("pymupdf", exc_type=ImportError)


def make_pdf(path, pages):
    doc = pymupdf.open()
    for _ in range(pages):
        doc.new_page()
    doc.save(str(path))
    doc.close()
    return str(path)


GOOD_CONF = {
    "BOOK_NAME": "b",
    "SOURCE_PDF": "pdfs/scanned.pdf",
    "PAGE_COUNT": "341",
    "PAGE_OFFSET": "12",
    "COPYRIGHT_PAGE": "4",
    "FIGURE_NUMBERING": "two-part",
    "BACKMATTER_PAGES": "320-341",
    "CH01_PAGES": "17-42",
}


def write_conf(book_dir, conf):
    book_dir.mkdir(parents=True, exist_ok=True)
    text = "".join(f'{k}="{v}"\n' for k, v in conf.items())
    (book_dir / "book.conf").write_text(text, encoding="utf-8")


def test_matching_page_count_and_keys_verifies(tmp_path):
    ok, reasons = evaluate(str(tmp_path), dict(GOOD_CONF), 341)
    assert ok and reasons == []


def test_page_count_mismatch_blocks_resume(tmp_path):
    """The real repo case: PAGE_COUNT=175 recorded, PDF is 341 pages."""
    conf = dict(GOOD_CONF, PAGE_COUNT="175")
    ok, reasons = evaluate(str(tmp_path), conf, 341)
    assert not ok
    assert any("DIFFERENT book" in r for r in reasons)


def test_absent_page_count_blocks_resume(tmp_path):
    conf = {k: v for k, v in GOOD_CONF.items() if k != "PAGE_COUNT"}
    ok, reasons = evaluate(str(tmp_path), conf, 341)
    assert not ok
    assert any("no PAGE_COUNT" in r for r in reasons)


@pytest.mark.parametrize("missing", [
    "PAGE_OFFSET", "COPYRIGHT_PAGE", "FIGURE_NUMBERING", "BACKMATTER_PAGES",
])
def test_missing_key_later_phases_read_blocks_resume(tmp_path, missing):
    conf = {k: v for k, v in GOOD_CONF.items() if k != missing}
    ok, reasons = evaluate(str(tmp_path), conf, 341)
    assert not ok
    assert any(missing in r for r in reasons)


def test_missing_chapter_ranges_blocks_resume(tmp_path):
    conf = {k: v for k, v in GOOD_CONF.items() if k != "CH01_PAGES"}
    ok, reasons = evaluate(str(tmp_path), conf, 341)
    assert not ok
    assert any("CHNN_PAGES" in r for r in reasons)


def test_parse_book_conf_handles_quotes_bare_values_and_comments(tmp_path):
    path = tmp_path / "book.conf"
    path.write_text(
        '# a comment\n'
        'BOOK_NAME="b"\n'
        'PAGE_COUNT=175\n'
        "TITLE='single'\n"
        '\n'
        'CH01_PAGES="1-2"\n',
        encoding="utf-8")
    conf = parse_book_conf(str(path))
    assert conf["BOOK_NAME"] == "b"
    assert conf["PAGE_COUNT"] == "175"
    assert conf["TITLE"] == "single"
    assert conf["CH01_PAGES"] == "1-2"


# --- end-to-end decisions ---------------------------------------------------

def run_main(monkeypatch, capsys, pdf, books_dir, root):
    monkeypatch.setattr(resume_check, "ROOT", str(root))
    monkeypatch.setattr(sys, "argv", [
        "resume_check.py", "--pdf", str(pdf), "--books-dir", str(books_dir)])
    code = main()
    return code, capsys.readouterr().out


def test_decision_fresh_when_no_book_claims_the_pdf(tmp_path, monkeypatch, capsys):
    pdf = make_pdf(tmp_path / "scanned.pdf", 7)
    books = tmp_path / "books"
    books.mkdir()
    code, out = run_main(monkeypatch, capsys, pdf, books, tmp_path)
    assert code == 0
    assert "DECISION: FRESH" in out


def test_decision_resume_on_verified_identity(tmp_path, monkeypatch, capsys):
    pdf = make_pdf(tmp_path / "scanned.pdf", 341)
    books = tmp_path / "books"
    write_conf(books / "b", dict(GOOD_CONF, SOURCE_PDF=str(pdf)))
    code, out = run_main(monkeypatch, capsys, pdf, books, tmp_path)
    assert code == 0
    assert "DECISION: RESUME b" in out


def test_decision_stop_on_page_count_mismatch(tmp_path, monkeypatch, capsys):
    """Never 'resume', never a silent 'start fresh' — a hard stop."""
    pdf = make_pdf(tmp_path / "scanned.pdf", 341)
    books = tmp_path / "books"
    write_conf(books / "other_book", dict(GOOD_CONF, SOURCE_PDF=str(pdf),
                                          PAGE_COUNT="175"))
    code, out = run_main(monkeypatch, capsys, pdf, books, tmp_path)
    assert code == 1
    assert "DECISION: STOP" in out
    assert "DECISION: RESUME" not in out
    assert "DECISION: FRESH" not in out


def test_decision_stop_when_two_books_verify(tmp_path, monkeypatch, capsys):
    pdf = make_pdf(tmp_path / "scanned.pdf", 341)
    books = tmp_path / "books"
    write_conf(books / "b1", dict(GOOD_CONF, SOURCE_PDF=str(pdf)))
    write_conf(books / "b2", dict(GOOD_CONF, SOURCE_PDF=str(pdf)))
    code, out = run_main(monkeypatch, capsys, pdf, books, tmp_path)
    assert code == 1
    assert "DECISION: STOP" in out


def test_relative_source_pdf_resolves_against_root(tmp_path, monkeypatch, capsys):
    (tmp_path / "pdfs").mkdir()
    pdf = make_pdf(tmp_path / "pdfs" / "scanned.pdf", 341)
    books = tmp_path / "books"
    write_conf(books / "b", dict(GOOD_CONF, SOURCE_PDF="pdfs/scanned.pdf"))
    code, out = run_main(monkeypatch, capsys, pdf, books, tmp_path)
    assert code == 0
    assert "DECISION: RESUME b" in out


def test_no_book_metadata_is_ever_printed(tmp_path, monkeypatch, capsys):
    """Printing title/author in the main conversation trips the content filter."""
    pdf = make_pdf(tmp_path / "scanned.pdf", 341)
    books = tmp_path / "books"
    write_conf(books / "b", dict(GOOD_CONF, SOURCE_PDF=str(pdf),
                                 TITLE="A Very Recognisable Title",
                                 AUTHOR="Some Author"))
    _, out = run_main(monkeypatch, capsys, pdf, books, tmp_path)
    assert "A Very Recognisable Title" not in out
    assert "Some Author" not in out
