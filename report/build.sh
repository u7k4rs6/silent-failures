#!/bin/sh
# Build the report PDF and an editable DOCX (styled with the Apart template) from silent_failures_report.md.
set -e
cd "$(dirname "$0")"
pandoc silent_failures_report.md -o silent_failures_report.pdf --pdf-engine=xelatex --resource-path=. \
  --columns=200 -V header-includes="\\usepackage{xurl}" -V geometry:margin=2.2cm -V fontsize=10pt -V linkcolor=blue -V urlcolor=blue -V colorlinks=true
pandoc silent_failures_report.md -o silent_failures_report.docx --resource-path=. \
  --reference-doc="../Copy of Apart Research hackathon submission template.docx"
