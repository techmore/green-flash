#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$ROOT_DIR"

TAG="${1:-}"
if [[ -z "$TAG" ]]; then
  if git describe --tags --abbrev=0 >/dev/null 2>&1; then
    TAG=$(git describe --tags --abbrev=0)
  else
    TAG=$(git rev-parse --short HEAD)
  fi
fi

OUT_DIR="${2:-$ROOT_DIR/dist}"
mkdir -p "$OUT_DIR"
ARCHIVE="$OUT_DIR/ugreen-flask-${TAG}.tar.gz"

LIST_FILE=$(mktemp)
trap 'rm -f "$LIST_FILE"' EXIT

git ls-files > "$LIST_FILE"

tar -czf "$ARCHIVE" \
  --exclude='.DS_Store' \
  --exclude='*/.DS_Store' \
  --exclude='__pycache__' \
  --exclude='__pycache__/*' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  --exclude='files.db' \
  --exclude='venv' \
  --exclude='venv/*' \
  --exclude='.venv' \
  --exclude='.venv/*' \
  --exclude='UGreenFileManager' \
  --exclude='UGreenFileManagerApp.app' \
  --exclude='UGreenFileManagerApp.app/*' \
  --exclude='dist' \
  --exclude='dist/*' \
  -T "$LIST_FILE"

echo "Created $ARCHIVE"
