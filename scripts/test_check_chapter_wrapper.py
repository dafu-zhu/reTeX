"""Tests for check_chapter_wrapper.py.

The failure these guard against: Phase 1a ran 4 chunk agents concurrently and
every one of them wrote chNN/chNN.tex, so the last writer won and the other
chunks' section files were left on disk unreferenced. The book still compiled,
and inventory_check.py still counted the orphans, so nothing surfaced it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from check_chapter_wrapper import check_book, _referenced_stems


def make_chapter(latex_dir, ch, sections, wrapper_inputs):
    """Create chNN/ with the given section files and a wrapper referencing some."""
    ch_name = f"ch{ch:02d}"
    ch_dir = latex_dir / ch_name
    ch_dir.mkdir(parents=True, exist_ok=True)
    for s in sections:
        (ch_dir / f"sec{ch:02d}_{s}.tex").write_text(
            f"% PAGES: {s}-{s}\n\\section{{S{s}}}\n", encoding="utf-8")
    body = "".join(f"\\input{{{ch_name}/{name}}}\n" for name in wrapper_inputs)
    (ch_dir / f"{ch_name}.tex").write_text(
        f"\\chapter{{C{ch}}}\n{body}", encoding="utf-8")
    return ch_dir


def test_complete_wrapper_passes(tmp_path):
    make_chapter(tmp_path, 1, [1, 2, 3], ["sec01_1", "sec01_2", "sec01_3"])
    assert check_book(tmp_path) == []


def test_clobbered_wrapper_reports_every_orphan(tmp_path):
    """Only the last chunk's wrapper survived — the other two are orphans."""
    make_chapter(tmp_path, 1, [1, 2, 3], ["sec01_3"])
    violations = check_book(tmp_path)
    assert len(violations) == 2
    assert all("ORPHAN" in v for v in violations)
    assert any("sec01_1.tex" in v for v in violations)
    assert any("sec01_2.tex" in v for v in violations)


def test_orphan_is_reported_even_though_the_book_would_compile(tmp_path):
    """An orphan is not a compile error, which is exactly why it needs a check."""
    make_chapter(tmp_path, 1, [1, 2], ["sec01_1"])
    assert check_book(tmp_path, chapter=1)


def test_commented_out_input_does_not_count_as_a_reference(tmp_path):
    ch_dir = make_chapter(tmp_path, 1, [1, 2], ["sec01_2"])
    (ch_dir / "ch01.tex").write_text(
        "\\chapter{C1}\n% \\input{ch01/sec01_1}\n\\input{ch01/sec01_2}\n",
        encoding="utf-8")
    violations = check_book(tmp_path)
    assert len(violations) == 1
    assert "sec01_1.tex" in violations[0] and "ORPHAN" in violations[0]


def test_dangling_reference_is_reported(tmp_path):
    make_chapter(tmp_path, 1, [1], ["sec01_1", "sec01_9"])
    violations = check_book(tmp_path)
    assert len(violations) == 1
    assert "DANGLING" in violations[0] and "sec01_9" in violations[0]


def test_missing_wrapper_is_reported(tmp_path):
    ch_dir = make_chapter(tmp_path, 1, [1, 2], ["sec01_1", "sec01_2"])
    (ch_dir / "ch01.tex").unlink()
    violations = check_book(tmp_path)
    assert len(violations) == 1
    assert "no wrapper" in violations[0]


def test_empty_chapter_is_reported(tmp_path):
    ch_dir = tmp_path / "ch01"
    ch_dir.mkdir(parents=True)
    (ch_dir / "ch01.tex").write_text("\\chapter{C1}\n", encoding="utf-8")
    violations = check_book(tmp_path)
    assert len(violations) == 1
    assert "no sec*.tex files" in violations[0]


def test_include_and_tex_suffix_both_count(tmp_path):
    ch_dir = make_chapter(tmp_path, 1, [1, 2], [])
    (ch_dir / "ch01.tex").write_text(
        "\\chapter{C1}\n\\include{ch01/sec01_1}\n\\input{ch01/sec01_2.tex}\n",
        encoding="utf-8")
    assert check_book(tmp_path) == []


def test_chapters_are_checked_independently(tmp_path):
    make_chapter(tmp_path, 1, [1, 2], ["sec01_1", "sec01_2"])
    make_chapter(tmp_path, 2, [1, 2], ["sec02_1"])
    assert check_book(tmp_path, chapter=1) == []
    assert len(check_book(tmp_path, chapter=2)) == 1
    assert len(check_book(tmp_path)) == 1


def test_referenced_stems_strips_paths_and_suffixes(tmp_path):
    wrapper = tmp_path / "ch01.tex"
    wrapper.write_text(
        "\\input{ch01/sec01_1}\n\\include{sec01_2.tex}\n\\input{  ch01/sec01_3  }\n",
        encoding="utf-8")
    assert _referenced_stems(str(wrapper)) == {"sec01_1", "sec01_2", "sec01_3"}
