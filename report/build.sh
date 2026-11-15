#!/bin/sh
# Print report.html to silent_failures_report.pdf with headless Chrome (fonts: Noto Serif / Noto Sans / DejaVu Sans Mono).
set -e
cd "$(dirname "$0")"
google-chrome --headless=new --disable-gpu --no-pdf-header-footer --user-data-dir="${TMPDIR:-/tmp}/sf-report-chrome" \
  --print-to-pdf="$PWD/silent_failures_report.pdf" "file://$PWD/report.html" 2>/dev/null
