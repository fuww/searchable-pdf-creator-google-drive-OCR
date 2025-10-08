#!/usr/bin/env python3
"""
Example: Using Mistral OCR programmatically in your own scripts.

/// script
dependencies = ["mistralai>=1.0.0"]
///
"""

import os
import base64
from pathlib import Path
from mistralai import Mistral


def ocr_pdf_to_markdown(pdf_path: Path) -> tuple[str, dict[str, str]]:
    """
    OCR a PDF and return markdown + images.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        (markdown_text, images_dict) where images_dict maps 
        image names to base64-encoded image data
    """
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    
    # Encode PDF
    pdf_base64 = base64.b64encode(pdf_path.read_bytes()).decode("utf-8")
    
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
    
    # Extract results
    markdown = response.choices[0].message.content
    images = {}
    
    if hasattr(response.choices[0].message, 'images'):
        images = response.choices[0].message.images or {}
    
    return markdown, images


def save_ocr_results(markdown: str, images: dict, output_dir: Path):
    """Save OCR results to directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save markdown
    md_file = output_dir / "document.md"
    md_file.write_text(markdown)
    print(f"✓ Saved markdown: {md_file}")
    
    # Save images
    if images:
        for img_name, img_base64 in images.items():
            img_path = output_dir / img_name
            img_bytes = base64.b64decode(img_base64)
            img_path.write_bytes(img_bytes)
            print(f"✓ Saved image: {img_path}")


def example_basic():
    """Example 1: Basic OCR"""
    pdf_path = Path("document.pdf")
    markdown, images = ocr_pdf_to_markdown(pdf_path)
    
    print(f"Extracted {len(markdown)} chars")
    print(f"Found {len(images)} images")


def example_with_post_processing():
    """Example 2: OCR + post-processing"""
    pdf_path = Path("invoice.pdf")
    markdown, images = ocr_pdf_to_markdown(pdf_path)
    
    # Extract specific information
    lines = markdown.split('\n')
    
    # Find invoice number (example)
    for line in lines:
        if 'Invoice' in line and '#' in line:
            print(f"Found: {line}")
    
    # Save results
    save_ocr_results(markdown, images, Path("./output"))


def example_batch_with_custom_logic():
    """Example 3: Batch processing with custom logic"""
    pdf_dir = Path("./pdfs")
    output_dir = Path("./results")
    
    for pdf_path in pdf_dir.glob("*.pdf"):
        print(f"\nProcessing {pdf_path.name}...")
        
        try:
            markdown, images = ocr_pdf_to_markdown(pdf_path)
            
            # Custom logic: only save if it has tables
            if '|' in markdown:  # Markdown tables contain |
                result_dir = output_dir / pdf_path.stem
                save_ocr_results(markdown, images, result_dir)
                print(f"✓ Saved (contains tables)")
            else:
                print("⊘ Skipped (no tables)")
                
        except Exception as e:
            print(f"✗ Error: {e}")


def example_structured_extraction():
    """Example 4: Extract structured data from OCR'd text"""
    pdf_path = Path("receipt.pdf")
    markdown, _ = ocr_pdf_to_markdown(pdf_path)
    
    # Use another LLM to structure the data
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {
                "role": "user",
                "content": f"""Extract structured data from this receipt as JSON:

{markdown}

Return JSON with: merchant, date, total, items (array of {{name, price}})"""
            }
        ],
        response_format={"type": "json_object"}
    )
    
    structured_data = response.choices[0].message.content
    print(structured_data)


if __name__ == "__main__":
    # Check for API key
    if not os.environ.get("MISTRAL_API_KEY"):
        print("Error: Set MISTRAL_API_KEY environment variable")
        exit(1)
    
    # Run examples (uncomment to test)
    # example_basic()
    # example_with_post_processing()
    # example_batch_with_custom_logic()
    # example_structured_extraction()
    
    print(__doc__)
    print("\nUncomment examples in __main__ to run them")
