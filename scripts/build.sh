#!/bin/bash
# Generic LaTeX textbook build script
#
# Usage:
#   ./scripts/build.sh              # Build full book
#   ./scripts/build.sh 3            # Build chapter 3 only
#   ./scripts/build.sh clean        # Remove build artifacts
#
# Configuration:
#   Set BOOK_NAME in book.conf (auto-detected from main.tex title if missing)
#
# Output:
#   latex/<book_name>.pdf              (full book)
#   latex/<book_name>_ch03.pdf         (single chapter)
#   latex/build/                       (all aux/log/idx/toc — never in latex/)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."
LATEX_DIR="$PROJECT_DIR/latex"
BUILD_DIR="$LATEX_DIR/build"

# Load book name from book.conf, or default to "textbook"
if [ -f "$PROJECT_DIR/book.conf" ]; then
    source "$PROJECT_DIR/book.conf"
fi
BOOK_NAME="${BOOK_NAME:-textbook}"

mkdir -p "$BUILD_DIR"

# Clean command
if [ "$1" = "clean" ]; then
    rm -rf "$BUILD_DIR"/*
    rm -f "$LATEX_DIR/$BOOK_NAME"*.pdf
    echo "Cleaned build artifacts."
    exit 0
fi

compile() {
    local TEX_FILE="$1"
    local OUTPUT_NAME="$2"
    local BASENAME=$(basename "$TEX_FILE" .tex)

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
        cp "$BUILD_DIR/$BASENAME.pdf" "$LATEX_DIR/$OUTPUT_NAME.pdf"
        SIZE=$(ls -lh "$LATEX_DIR/$OUTPUT_NAME.pdf" | awk '{print $5}')
        echo "  Done: $OUTPUT_NAME.pdf ($SIZE)"
    else
        echo "  Failed. Check $BUILD_DIR/$BASENAME.log"
        exit 1
    fi
}

if [ -z "$1" ]; then
    compile "$LATEX_DIR/main.tex" "$BOOK_NAME"
else
    CH_NUM=$(printf "%02d" "$1")
    CH_DIR="ch${CH_NUM}"

    if [ ! -d "$LATEX_DIR/$CH_DIR" ]; then
        echo "Error: $CH_DIR not found"
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
