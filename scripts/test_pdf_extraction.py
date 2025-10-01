#!/usr/bin/env python3
"""Small helper to test PDF extraction using pages.test_api.extract_text_from_pdf

Usage:
  python3 scripts/test_pdf_extraction.py /path/to/file.pdf

This opens the PDF in binary mode, passes the file-like object to the extractor,
and prints the first 2000 characters of the result.
"""
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: python3 scripts/test_pdf_extraction.py /path/to/file.pdf")
    raise SystemExit(1)

pdf_path = Path(sys.argv[1])
if not pdf_path.exists():
    print(f"File not found: {pdf_path}")
    raise SystemExit(2)

try:
    # import the extractor
    from pages.test_api import extract_text_from_pdf
except Exception as e:
    print(f"Failed to import extractor from pages.test_api: {e}")
    raise

with open(pdf_path, 'rb') as f:
    result = extract_text_from_pdf(f)

print("--- Extraction result (truncated) ---")
if isinstance(result, str):
    print(result[:2000])
else:
    print(repr(result))
