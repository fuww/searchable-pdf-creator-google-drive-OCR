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


def load_env_file(env_file: Path = Path(".env.local")):
    """Load environment variables from .env.local file if it exists."""
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())


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


def ocr_image_to_markdown(image_path: Path) -> str:
    """
    OCR a JPG/PNG image and return markdown text.

    Args:
        image_path: Path to image file (JPG, PNG, etc.)

    Returns:
        Extracted markdown text
    """
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    # Encode image
    image_base64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")

    # Determine MIME type
    suffix = image_path.suffix.lower()
    mime_type = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }.get(suffix, 'image/jpeg')

    # Call OCR
    response = client.chat.complete(
        model="mistral-ocr-latest",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": f"data:{mime_type};base64,{image_base64}"
                    }
                ]
            }
        ]
    )

    # Extract results
    markdown = response.choices[0].message.content
    return markdown


def example_ocr_jpg():
    """Example 5: OCR a single JPG/PNG image"""
    image_path = Path("screenshot.jpg")

    if not image_path.exists():
        print(f"Skipping: {image_path} not found")
        return

    markdown = ocr_image_to_markdown(image_path)

    print(f"\n{'='*60}")
    print(f"OCR Results from {image_path.name}:")
    print(f"{'='*60}")
    print(markdown)
    print(f"\nExtracted {len(markdown)} characters")


def example_batch_ocr_images():
    """Example 6: Batch OCR multiple images"""
    image_dir = Path("./screenshots")
    output_dir = Path("./image_ocr_results")

    if not image_dir.exists():
        print(f"Skipping: {image_dir} not found")
        return

    # Supported image extensions
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']

    # Find all images
    image_files = [
        f for f in image_dir.iterdir()
        if f.suffix.lower() in image_extensions
    ]

    if not image_files:
        print(f"No images found in {image_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nProcessing {len(image_files)} images from {image_dir}\n")

    for i, image_path in enumerate(image_files, 1):
        try:
            print(f"[{i}/{len(image_files)}] Processing {image_path.name}...")

            markdown = ocr_image_to_markdown(image_path)

            # Save to markdown file
            output_file = output_dir / f"{image_path.stem}.md"
            output_file.write_text(markdown)

            print(f"  ✓ Extracted {len(markdown)} chars → {output_file.name}")

        except Exception as e:
            print(f"  ✗ Error: {e}")

    print(f"\n✓ Results saved to {output_dir}")


def example_ocr_mixed_documents():
    """Example 7: OCR both PDFs and images from a directory"""
    docs_dir = Path("./documents")
    output_dir = Path("./ocr_all_results")

    if not docs_dir.exists():
        print(f"Skipping: {docs_dir} not found")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # Process PDFs
    pdf_files = list(docs_dir.glob("*.pdf"))
    for pdf_path in pdf_files:
        print(f"Processing PDF: {pdf_path.name}")
        markdown, images = ocr_pdf_to_markdown(pdf_path)
        save_ocr_results(markdown, images, output_dir / pdf_path.stem)

    # Process images
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    image_files = [
        f for f in docs_dir.iterdir()
        if f.suffix.lower() in image_extensions
    ]

    for image_path in image_files:
        print(f"Processing image: {image_path.name}")
        markdown = ocr_image_to_markdown(image_path)

        output_file = output_dir / f"{image_path.stem}.md"
        output_file.write_text(markdown)

    print(f"\n✓ Processed {len(pdf_files)} PDFs and {len(image_files)} images")
    print(f"✓ Results saved to {output_dir}")


if __name__ == "__main__":
    # Load .env.local if it exists
    load_env_file()

    # Check for API key
    if not os.environ.get("MISTRAL_API_KEY"):
        print("Error: Set MISTRAL_API_KEY environment variable")
        print("Copy .env.local.example to .env.local and add your key")
        exit(1)

    # Run examples (uncomment to test)
    # example_basic()
    # example_with_post_processing()
    # example_batch_with_custom_logic()
    # example_structured_extraction()
    # example_ocr_jpg()
    # example_batch_ocr_images()
    # example_ocr_mixed_documents()

    print(__doc__)
    print("\nUncomment examples in __main__ to run them")
