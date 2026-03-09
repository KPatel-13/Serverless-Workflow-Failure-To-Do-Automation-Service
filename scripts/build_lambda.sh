#!/usr/bin/env bash
set -euo pipefail

# Build a reproducible Lambda deployment zip (lambda.zip) on Linux.
# - Installs runtime deps from requirements.txt into build/
# - Copies app/ into build/
# - Zips build/ into lambda.zip

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD="$ROOT/build"
OUT="$ROOT/lambda.zip"

rm -rf "$BUILD" "$OUT"
mkdir -p "$BUILD"

python -m pip install --upgrade pip >/dev/null
python -m pip install -r "$ROOT/requirements.txt" -t "$BUILD" >/dev/null

mkdir -p "$BUILD/app"
cp -r "$ROOT/app/"*.py "$BUILD/app/"

(cd "$BUILD" && zip -qr "$OUT" .)
echo "Built: $OUT"
