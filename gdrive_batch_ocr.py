#!/usr/bin/env python3
"""
Batch OCR PDFs from Google Drive using Mistral OCR.
Saves markdown + extracted images back to Drive.

Usage: 
  uv run gdrive_batch_ocr.py [options]

Options:
  --folder-id ID       Drive folder to search (default: entire drive)
  --output-folder ID   Drive folder for outputs (default: same as source)
  --local-only         Save to local directory instead of uploading
  --max-files N        Limit number of files to process (default: all)
  --workers N          Number of parallel workers (default: 3)

/// script
dependencies = [
  "mistralai>=1.0.0",
  "google-auth>=2.0.0",
  "google-auth-oauthlib>=1.0.0", 
  "google-auth-httplib2>=0.1.0",
  "google-api-python-client>=2.0.0",
  "pypdfium2>=4.0.0"
]
///
"""

import sys
import os
import base64
import json
from pathlib import Path
from mistralai import Mistral
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaInMemoryUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
import pypdfium2 as pdfium


SCOPES = ['https://www.googleapis.com/auth/drive']


def load_env_file(env_file: Path = Path(".env.local")):
    """Load environment variables from .env.local file if it exists."""
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())


def get_drive_service():
    """Authenticate and return Google Drive service."""
    creds = None
    token_path = Path.home() / '.gdrive_token.json'
    
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds_file = Path('credentials.json')
            if not creds_file.exists():
                print("Error: credentials.json not found")
                print("Download from: https://console.cloud.google.com/apis/credentials")
                sys.exit(1)
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(creds_file), SCOPES)
            creds = flow.run_local_server(port=0)
        
        token_path.write_text(creds.to_json())
    
    return build('drive', 'v3', credentials=creds)


def find_pdfs(service, folder_id=None):
    """Find all PDFs in Drive."""
    query = "mimeType='application/pdf' and trashed=false"
    if folder_id:
        query += f" and '{folder_id}' in parents"
    
    results = service.files().list(
        q=query,
        fields="files(id, name, parents, size)",
        pageSize=1000
    ).execute()
    
    return results.get('files', [])


def is_searchable_pdf(pdf_bytes: bytes) -> bool:
    """Check if PDF has searchable text."""
    try:
        # Save to temp file
        temp_path = Path("/tmp/check.pdf")
        temp_path.write_bytes(pdf_bytes)
        
        pdf = pdfium.PdfDocument(temp_path)
        
        # Check first 3 pages or all if fewer
        pages_to_check = min(3, len(pdf))
        total_chars = 0
        
        for i in range(pages_to_check):
            page = pdf[i]
            text_page = page.get_textpage()
            text = text_page.get_text_range()
            total_chars += len(text.strip())
        
        pdf.close()
        temp_path.unlink()
        
        # Consider searchable if >= 50 chars found
        return total_chars >= 50
        
    except Exception as e:
        print(f"    Error checking: {e}")
        return False


def download_file(service, file_id) -> bytes:
    """Download file from Google Drive."""
    request = service.files().get_media(fileId=file_id)
    file_data = io.BytesIO()
    downloader = MediaIoBaseDownload(file_data, request)
    
    done = False
    while not done:
        status, done = downloader.next_chunk()
    
    return file_data.getvalue()


def ocr_pdf_mistral(pdf_bytes: bytes) -> tuple[str, dict]:
    """
    OCR PDF using Mistral OCR.
    Returns: (markdown_text, images_dict)
    """
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY environment variable not set")
    
    client = Mistral(api_key=api_key)
    
    # Encode PDF
    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
    
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
    
    # Extract images if present
    images = {}
    if hasattr(response.choices[0].message, 'images') and response.choices[0].message.images:
        images = response.choices[0].message.images
    
    return markdown, images


def create_drive_folder(service, folder_name: str, parent_id=None):
    """Create a folder in Google Drive."""
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    
    if parent_id:
        file_metadata['parents'] = [parent_id]
    
    folder = service.files().create(
        body=file_metadata,
        fields='id'
    ).execute()
    
    return folder.get('id')


def upload_to_drive(service, file_name: str, content: bytes, mime_type: str, parent_id=None):
    """Upload file to Google Drive."""
    file_metadata = {'name': file_name}
    if parent_id:
        file_metadata['parents'] = [parent_id]
    
    media = MediaInMemoryUpload(content, mimetype=mime_type)
    
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()
    
    return file


def process_single_pdf(
    service,
    pdf_file: dict,
    output_folder_id: str,
    local_output_dir: Path = None
) -> tuple[str, bool, str]:
    """
    Process a single PDF: OCR and save markdown + images.
    Returns: (file_name, success, message)
    """
    file_name = pdf_file['name']
    file_id = pdf_file['id']
    
    try:
        # Download PDF
        pdf_bytes = download_file(service, file_id)
        
        # Check if searchable
        if is_searchable_pdf(pdf_bytes):
            return file_name, False, "Already searchable (skipped)"
        
        # OCR with Mistral
        markdown, images = ocr_pdf_mistral(pdf_bytes)
        
        # Prepare output name
        base_name = Path(file_name).stem
        
        if local_output_dir:
            # Save locally
            local_output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save markdown
            md_path = local_output_dir / f"{base_name}.md"
            md_path.write_text(markdown)
            
            # Save images
            if images:
                img_dir = local_output_dir / f"{base_name}_images"
                img_dir.mkdir(exist_ok=True)
                
                for img_name, img_base64 in images.items():
                    img_path = img_dir / img_name
                    img_bytes = base64.b64decode(img_base64)
                    img_path.write_bytes(img_bytes)
            
            msg = f"{len(markdown):,} chars, {len(images)} images → {md_path}"
        
        else:
            # Upload to Drive
            # Create subfolder for this PDF's outputs
            pdf_folder_id = create_drive_folder(
                service, 
                f"{base_name}_ocr",
                output_folder_id
            )
            
            # Upload markdown
            md_bytes = markdown.encode('utf-8')
            upload_to_drive(
                service,
                f"{base_name}.md",
                md_bytes,
                'text/markdown',
                pdf_folder_id
            )
            
            # Upload images
            for img_name, img_base64 in images.items():
                img_bytes = base64.b64decode(img_base64)
                upload_to_drive(
                    service,
                    img_name,
                    img_bytes,
                    'image/jpeg',
                    pdf_folder_id
                )
            
            msg = f"{len(markdown):,} chars, {len(images)} images → Drive"
        
        return file_name, True, msg
        
    except Exception as e:
        return file_name, False, f"Error: {str(e)}"


def batch_process(
    service,
    pdf_files: list,
    output_folder_id: str = None,
    local_output_dir: Path = None,
    max_workers: int = 3
):
    """Batch process PDFs with parallel workers."""
    
    total = len(pdf_files)
    success_count = 0
    skip_count = 0
    error_count = 0
    
    print(f"\nProcessing {total} PDFs with {max_workers} workers...\n")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(
                process_single_pdf, 
                service, 
                pdf, 
                output_folder_id,
                local_output_dir
            ): pdf 
            for pdf in pdf_files
        }
        
        # Process results as they complete
        for i, future in enumerate(as_completed(futures), 1):
            file_name, success, message = future.result()
            
            status_icon = "✓" if success else ("⊘" if "skipped" in message.lower() else "✗")
            print(f"{status_icon} [{i}/{total}] {file_name}")
            print(f"  {message}")
            
            if success:
                success_count += 1
            elif "skipped" in message.lower():
                skip_count += 1
            else:
                error_count += 1
    
    # Summary
    print(f"\n{'='*70}")
    print(f"Results: {success_count} processed, {skip_count} skipped, {error_count} errors")
    
    if success_count > 0:
        # Cost estimation
        cost = success_count * 0.001  # ~$0.001 per page estimate
        print(f"Estimated cost: ${cost:.3f}")


def main():
    import argparse

    # Load .env.local if it exists
    load_env_file()

    parser = argparse.ArgumentParser(
        description="Batch OCR Google Drive PDFs with Mistral",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all PDFs in My Drive
  uv run gdrive_batch_ocr.py
  
  # Process specific folder
  uv run gdrive_batch_ocr.py --folder-id 1abc123xyz
  
  # Save locally instead of uploading
  uv run gdrive_batch_ocr.py --local-only --output ./ocr_results
  
  # Limit to 10 files with 5 workers
  uv run gdrive_batch_ocr.py --max-files 10 --workers 5
        """
    )
    
    parser.add_argument("--folder-id", help="Source folder ID in Google Drive")
    parser.add_argument("--output-folder", help="Output folder ID in Google Drive")
    parser.add_argument("--local-only", action="store_true",
                       help="Save to local directory instead of Drive")
    parser.add_argument("--output", type=Path, default=Path("./ocr_output"),
                       help="Local output directory (with --local-only)")
    parser.add_argument("--max-files", type=int,
                       help="Maximum number of files to process")
    parser.add_argument("--workers", type=int, default=3,
                       help="Number of parallel workers (default: 3)")
    
    args = parser.parse_args()
    
    # Check for API key
    if not os.environ.get("MISTRAL_API_KEY"):
        print("Error: MISTRAL_API_KEY environment variable not set")
        sys.exit(1)
    
    # Connect to Drive
    print("Connecting to Google Drive...")
    service = get_drive_service()
    
    # Find PDFs
    print("Finding PDFs...")
    pdf_files = find_pdfs(service, args.folder_id)
    
    if not pdf_files:
        print("No PDF files found")
        return
    
    print(f"Found {len(pdf_files)} PDFs")
    
    # Limit if requested
    if args.max_files:
        pdf_files = pdf_files[:args.max_files]
        print(f"Limited to {len(pdf_files)} files")
    
    # Setup output
    if args.local_only:
        output_folder_id = None
        local_output_dir = args.output
        print(f"Output: {local_output_dir.absolute()}")
    else:
        # Create output folder in Drive if not specified
        if args.output_folder:
            output_folder_id = args.output_folder
        else:
            output_folder_id = create_drive_folder(service, "OCR_Output")
        local_output_dir = None
        print(f"Output folder ID: {output_folder_id}")
    
    # Process
    batch_process(
        service,
        pdf_files,
        output_folder_id,
        local_output_dir,
        args.workers
    )


if __name__ == "__main__":
    main()
