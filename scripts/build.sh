#!/bin/bash
# LaTeX textbook build script — one book per books/<name>/ directory.
#
# Usage:
#   ./scripts/build.sh <book_name>          # Build full book
#   ./scripts/build.sh <book_name> 3        # Build chapter 3 only
#   ./scripts/build.sh <book_name> clean    # Remove build artifacts
#   ./scripts/build.sh                      # List available books
#
# Output:
#   books/<name>/<name>.pdf          (full book)
#   books/<name>/<name>_ch03.pdf     (single chapter)
#   books/<name>/build/              (all aux/log/idx/toc)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."
BOOKS_DIR="$PROJECT_DIR/books"

list_books() {
    echo "Available books:"
    for d in "$BOOKS_DIR"/*/; do
        [ -d "$d" ] && echo "  $(basename "$d")"
    done
}

if [ -z "$1" ]; then
    echo "Error: no book specified."
    echo
    list_books
    echo
    echo "Usage: ./scripts/build.sh <book_name> [chapter|clean]"
    exit 1
fi

BOOK_NAME="$1"
BOOK_DIR="$BOOKS_DIR/$BOOK_NAME"
LATEX_DIR="$BOOK_DIR/latex"
BUILD_DIR="$BOOK_DIR/build"

if [ ! -d "$LATEX_DIR" ]; then
    echo "Error: no book named '$BOOK_NAME' (expected $LATEX_DIR)"
    echo
    list_books
    exit 1
fi

# book.conf is optional metadata; the directory name is authoritative
if [ -f "$BOOK_DIR/book.conf" ]; then
    # shellcheck disable=SC1090
    source "$BOOK_DIR/book.conf"
fi

mkdir -p "$BUILD_DIR"

if [ "$2" = "clean" ]; then
    rm -rf "${BUILD_DIR:?}"/*
    rm -f "$BOOK_DIR/$BOOK_NAME"*.pdf
    echo "Cleaned build artifacts for $BOOK_NAME."
    exit 0
fi

compile() {
    local TEX_FILE="$1"
    local OUTPUT_NAME="$2"
    local BASENAME
    BASENAME=$(basename "$TEX_FILE" .tex)

    echo "Building $OUTPUT_NAME.pdf ..."

    export TEXINPUTS="$LATEX_DIR//:$BUILD_DIR//:"
    cd "$LATEX_DIR"

    # Two passes for cross-references
    pdflatex -interaction=nonstopmode \
             -output-directory="$BUILD_DIR" \
             "$TEX_FILE" > /dev/null 2>&1 || true

    pdflatex -interaction=nonstopmode \
             -output-directory="$BUILD_DIR" \
             "$TEX_FILE" > /dev/null 2>&1 || true

    if [ -f "$BUILD_DIR/$BASENAME.pdf" ]; then
        cp "$BUILD_DIR/$BASENAME.pdf" "$BOOK_DIR/$OUTPUT_NAME.pdf"
        SIZE=$(ls -lh "$BOOK_DIR/$OUTPUT_NAME.pdf" | awk '{print $5}')
        echo "  Done: $OUTPUT_NAME.pdf ($SIZE)"
    else
        echo "  Failed. Check $BUILD_DIR/$BASENAME.log"
        exit 1
    fi
}

if [ -z "$2" ]; then
    compile "$LATEX_DIR/main.tex" "$BOOK_NAME"
else
    CH_NUM=$(printf "%02d" "$2")
    CH_DIR="ch${CH_NUM}"

    if [ ! -d "$LATEX_DIR/$CH_DIR" ]; then
        echo "Error: $CH_DIR not found in $BOOK_NAME"
        exit 1
    fi

    WRAPPER="$BUILD_DIR/ch${CH_NUM}_standalone.tex"
    cat > "$WRAPPER" << WRAPEOF
\\input{preamble}
\\begin{document}
\\include{${CH_DIR}/${CH_DIR}}
\\end{document}
WRAPEOF

    compile "$WRAPPER" "${BOOK_NAME}_ch${CH_NUM}"
fi
