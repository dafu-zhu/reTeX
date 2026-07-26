#!/bin/bash
# Import one book's LaTeX tree from an output/* branch into books/<name>/.
#
# Usage:
#   ./scripts/import_book.sh <branch> <book_name> <docs|root>
#
# The third argument selects the progress.md source: on some branches
# docs/progress.md is a stale shared template and the real per-book tracker
# is the repo-root progress.md.
#
# Imports into the working tree without staging. Caller commits.

set -euo pipefail

BRANCH="$1"
NAME="$2"
PROGRESS_SOURCE="$3"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$SCRIPT_DIR/.."
DEST="$ROOT/books/$NAME"

if ! git -C "$ROOT" rev-parse --verify "$BRANCH" >/dev/null 2>&1; then
    echo "Error: branch $BRANCH not found" >&2
    exit 1
fi

if [ -e "$DEST" ]; then
    echo "Error: $DEST already exists — refusing to overwrite" >&2
    exit 1
fi

mkdir -p "$DEST/latex"

# Book content
git -C "$ROOT" archive "$BRANCH:latex" | tar -x -C "$DEST/latex"

# book.conf always comes from the repo root of the source branch
git -C "$ROOT" show "$BRANCH:book.conf" > "$DEST/book.conf"

# progress.md source varies per branch
case "$PROGRESS_SOURCE" in
    docs) git -C "$ROOT" show "$BRANCH:docs/progress.md" > "$DEST/progress.md" ;;
    root) git -C "$ROOT" show "$BRANCH:progress.md"      > "$DEST/progress.md" ;;
    *) echo "Error: progress source must be 'docs' or 'root'" >&2; exit 1 ;;
esac

# Drop artifacts of the old per-branch layout
rm -f "$DEST/latex/.gitignore" "$DEST/latex/book.conf"

# Drop build artifacts that may have been committed
find "$DEST/latex" -type f \
    \( -name '*.aux' -o -name '*.log' -o -name '*.toc' -o -name '*.out' \
       -o -name '*.idx' -o -name '*.ilg' -o -name '*.ind' \) -delete
rm -rf "$DEST/latex/build"

echo "Imported $NAME:"
echo "  chapters: $(find "$DEST/latex" -maxdepth 1 -type d -name 'ch*' | wc -l)"
echo "  tex:      $(find "$DEST/latex" -name '*.tex' | wc -l)"
echo "  png:      $(find "$DEST/latex" -name '*.png' | wc -l)"
