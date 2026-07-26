import pathlib
import pytest
from check_repo_layout import check_layout

REQUIRED = ["book.conf", "progress.md", "latex/main.tex", "latex/preamble.tex"]


def make_book(root: pathlib.Path, name: str) -> pathlib.Path:
    book = root / "books" / name
    (book / "latex").mkdir(parents=True)
    for rel in REQUIRED:
        path = book / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("placeholder\n", encoding="utf-8")
    return book


def test_clean_repo_has_no_violations(tmp_path):
    make_book(tmp_path, "some_book")
    assert check_layout(tmp_path) == []


def test_missing_required_file_is_reported(tmp_path):
    book = make_book(tmp_path, "some_book")
    (book / "book.conf").unlink()
    violations = check_layout(tmp_path)
    assert len(violations) == 1
    assert "book.conf" in violations[0]
    assert "some_book" in violations[0]


def test_isbn_is_reported(tmp_path):
    book = make_book(tmp_path, "some_book")
    (book / "latex" / "frontmatter.tex").write_text(
        "ISBN 0-13-065243-1\n", encoding="utf-8"
    )
    violations = check_layout(tmp_path)
    assert any("ISBN" in v for v in violations)


@pytest.mark.parametrize(
    "text",
    [
        "All rights reserved.",
        "Library of Congress Catalog Card Number: 00-107735",
        r"\textcopyright{} 2004 Pearson Education, Inc.",
        r"Copyright \copyright\ 2001 by Academic Press",
    ],
)
def test_copyright_markers_are_reported(tmp_path, text):
    book = make_book(tmp_path, "some_book")
    (book / "latex" / "frontmatter.tex").write_text(text + "\n", encoding="utf-8")
    assert check_layout(tmp_path) != []


def test_edition_and_author_are_allowed(tmp_path):
    book = make_book(tmp_path, "some_book")
    (book / "latex" / "frontmatter.tex").write_text(
        "{\\Large Fourth Edition}\\\\[3cm]\n{\\Large Richard Haberman}\n",
        encoding="utf-8",
    )
    assert check_layout(tmp_path) == []


def test_legacy_paths_are_reported(tmp_path):
    make_book(tmp_path, "some_book")
    (tmp_path / "book.conf").write_text("BOOK_NAME=x\n", encoding="utf-8")
    (tmp_path / "latex" / "ch01").mkdir(parents=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "progress.md").write_text("# p\n", encoding="utf-8")
    violations = check_layout(tmp_path)
    assert any("book.conf" in v for v in violations)
    assert any("latex/ch01" in v for v in violations)
    assert any("docs/progress.md" in v for v in violations)


def test_binary_files_do_not_crash_the_scan(tmp_path):
    book = make_book(tmp_path, "some_book")
    (book / "latex" / "figures").mkdir()
    (book / "latex" / "figures" / "fig.png").write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe")
    assert check_layout(tmp_path) == []
