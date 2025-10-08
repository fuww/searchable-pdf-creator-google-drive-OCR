#!/usr/bin/env python3
"""
Batch OCR multiple PDFs using Mistral OCR.
Processes all PDFs in a directory with progress tracking.

Usage: uv run batch_ocr.py <input_dir> [output_dir]

/// script
dependencies = ["mistralai>=1.0.0"]
///
"""

import sys
import os
import base64
from pathlib import Path
from mistralai import Mistral
from concurrent.futures import ThreadPoolExecutor, as_completed


def encode_pdf(pdf_path: Path) -> str:
    """Encode PDF file as base64."""
    with open(pdf_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def ocr_single_pdf(pdf_path: Path, output_dir: Path, client: Mistral) -> tuple[Path, bool, str]:
    """OCR a single PDF and save to output directory."""
    try:
        # Encode PDF
        pdf_base64 = encode_pdf(pdf_path)
        
        # Call OCR
        response = client.chat.complete(
            model="mistral-ocr-latest",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document_url",
                            "document_url": f"data:application/pdf;base64,{pdf_base64}"
                        }
                    ]
                }
            ]
        )
        
        # Extract markdown
        markdown = response.choices[0].message.content
        
        # Save output
        output_file = output_dir / pdf_path.with_suffix('.md').name
        output_file.write_text(markdown)
        
        return pdf_path, True, f"{len(markdown):,} chars"
        
    except Exception as e:
        return pdf_path, False, str(e)


def batch_ocr(input_dir: Path, output_dir: Path, max_workers: int = 4):
    """Process all PDFs in input directory."""
    
    # Get all PDFs
    pdf_files = list(input_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        return
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize client
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY environment variable not set")
    
    client = Mistral(api_key=api_key)
    
    print(f"Processing {len(pdf_files)} PDFs from {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Workers: {max_workers}\n")
    
    # Process PDFs in parallel
    success_count = 0
    error_count = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(ocr_single_pdf, pdf, output_dir, client): pdf 
            for pdf in pdf_files
        }
        
        # Process results as they complete
        for i, future in enumerate(as_completed(futures), 1):
            pdf_path, success, message = future.result()
            
            if success:
                print(f"✓ [{i}/{len(pdf_files)}] {pdf_path.name}: {message}")
                success_count += 1
            else:
                print(f"✗ [{i}/{len(pdf_files)}] {pdf_path.name}: {message}")
                error_count += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Completed: {success_count} successful, {error_count} errors")
    print(f"Output: {output_dir}")
    
    # Cost estimation (rough)
    total_pages = success_count  # Assuming ~1 page per file for estimation
    cost = total_pages * 0.001
    print(f"Estimated cost: ${cost:.3f} (at $0.001/page)")


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run batch_ocr.py <input_dir> [output_dir]")
        sys.exit(1)
    
    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else input_dir / "ocr_output"
    
    if not input_dir.is_dir():
        print(f"Error: {input_dir} is not a directory")
        sys.exit(1)
    
    batch_ocr(input_dir, output_dir)


if __name__ == "__main__":
    main()
