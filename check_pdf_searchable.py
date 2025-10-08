#!/usr/bin/env python3
"""
Check if PDFs contain searchable text.
Usage: uv run check_pdf_searchable.py <pdf_files_or_directory>

/// script
dependencies = ["pypdfium2"]
///
"""

import sys
from pathlib import Path
import pypdfium2 as pdfium


def is_searchable_pdf(pdf_path: Path, min_chars: int = 50) -> tuple[bool, int, str]:
    """
    Check if a PDF has extractable text.
    
    Returns:
        (is_searchable, char_count, status_message)
    """
    try:
        pdf = pdfium.PdfDocument(pdf_path)
        total_chars = 0
        
        # Check first 3 pages or all if fewer
        pages_to_check = min(3, len(pdf))
        
        for i in range(pages_to_check):
            page = pdf[i]
            text_page = page.get_textpage()
            text = text_page.get_text_range()
            total_chars += len(text.strip())
        
        pdf.close()
        
        if total_chars >= min_chars:
            return True, total_chars, "✓ Searchable"
        elif total_chars > 0:
            return False, total_chars, "⚠ Minimal text (likely scanned)"
        else:
            return False, 0, "✗ No text (image-only PDF)"
            
    except Exception as e:
        return False, 0, f"✗ Error: {str(e)}"


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run check_pdf_searchable.py <pdf_files_or_directory>")
        sys.exit(1)
    
    paths = [Path(arg) for arg in sys.argv[1:]]
    pdf_files = []
    
    for path in paths:
        if path.is_dir():
            pdf_files.extend(path.rglob("*.pdf"))
        elif path.suffix.lower() == ".pdf":
            pdf_files.append(path)
    
    if not pdf_files:
        print("No PDF files found")
        sys.exit(1)
    
    print(f"Checking {len(pdf_files)} PDF(s)...\n")
    
    searchable = []
    non_searchable = []
    
    for pdf_path in sorted(pdf_files):
        is_search, char_count, status = is_searchable_pdf(pdf_path)
        
        if is_search:
            searchable.append(pdf_path)
        else:
            non_searchable.append(pdf_path)
        
        print(f"{status:30} {pdf_path.name} ({char_count} chars)")
    
    print(f"\n--- Summary ---")
    print(f"Searchable: {len(searchable)}")
    print(f"Non-searchable: {len(non_searchable)}")


if __name__ == "__main__":
    main()
