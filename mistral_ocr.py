#!/usr/bin/env python3
"""
Extract text from PDFs using Mistral OCR model (mistral-ocr-latest).
Outputs markdown with preserved structure and optional embedded images.

Usage: 
  uv run mistral_ocr.py <pdf_file> [options]

Options:
  --output, -o      Output file (default: same name with .md extension)
  --inline-images   Include images inline as base64 in markdown
  --batch           Use batch API for async processing (cheaper, slower)

/// script
dependencies = ["mistralai>=1.0.0"]
///
"""

import sys
import os
import base64
from pathlib import Path
from mistralai import Mistral


def encode_pdf(pdf_path: Path) -> str:
    """Encode PDF file as base64."""
    with open(pdf_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def ocr_pdf_sync(pdf_path: Path, inline_images: bool = False) -> str:
    """OCR a PDF using Mistral OCR API (synchronous)."""
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY environment variable not set")
    
    client = Mistral(api_key=api_key)
    
    # Encode PDF
    pdf_base64 = encode_pdf(pdf_path)
    
    # Call OCR endpoint
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
    
    # Extract markdown from response
    markdown = response.choices[0].message.content
    
    # Handle images if inline_images is True
    if inline_images and hasattr(response.choices[0].message, 'images'):
        images = response.choices[0].message.images or {}
        for img_name, img_base64 in images.items():
            # Replace image references with inline base64
            markdown = markdown.replace(
                f"![{img_name}]({img_name})",
                f"![{img_name}](data:image/jpeg;base64,{img_base64})"
            )
    
    return markdown


def ocr_pdf_batch(pdf_path: Path, inline_images: bool = False) -> str:
    """OCR a PDF using Mistral Batch API (async, ~50% cheaper)."""
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY environment variable not set")
    
    client = Mistral(api_key=api_key)
    
    # Encode PDF
    pdf_base64 = encode_pdf(pdf_path)
    
    # Create batch job
    batch_job = client.batch.jobs.create(
        input_files=[],
        metadata={},
        endpoint="/v1/chat/completions",
        model="mistral-ocr-latest",
    )
    
    # Note: Full batch implementation requires uploading to Mistral's file storage
    # For now, falling back to sync
    print("⚠ Batch API requires file upload - using sync API for now")
    return ocr_pdf_sync(pdf_path, inline_images)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="OCR PDFs with Mistral OCR")
    parser.add_argument("pdf_file", type=Path, help="PDF file to OCR")
    parser.add_argument("-o", "--output", type=Path, help="Output markdown file")
    parser.add_argument("--inline-images", action="store_true", 
                       help="Include images inline as base64")
    parser.add_argument("--batch", action="store_true",
                       help="Use batch API (cheaper but async)")
    
    args = parser.parse_args()
    
    if not args.pdf_file.exists():
        print(f"Error: {args.pdf_file} not found")
        sys.exit(1)
    
    output_file = args.output or args.pdf_file.with_suffix('.md')
    
    print(f"Processing {args.pdf_file.name}...")
    print(f"Model: mistral-ocr-latest (~$0.001/page)")
    
    # Process PDF
    if args.batch:
        markdown = ocr_pdf_batch(args.pdf_file, args.inline_images)
    else:
        markdown = ocr_pdf_sync(args.pdf_file, args.inline_images)
    
    # Write output
    output_file.write_text(markdown)
    
    pages = markdown.count("---") + 1  # Rough page count
    print(f"✓ Extracted {len(markdown):,} chars (~{pages} pages)")
    print(f"✓ Saved to {output_file}")
    
    if not args.inline_images and "![" in markdown:
        print("\n💡 Tip: Use --inline-images to embed images in markdown")


if __name__ == "__main__":
    main()
