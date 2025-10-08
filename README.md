# Google Drive Batch OCR with Mistral

Batch process non-searchable PDFs in Google Drive using Mistral OCR. Extracts markdown + images.

## Features

- ✅ Detects non-searchable PDFs automatically
- ✅ **OCR JPG/PNG/GIF/WebP images** (new!)
- ✅ Parallel processing (configurable workers)
- ✅ Extracts text as markdown with preserved structure
- ✅ Saves embedded images separately
- ✅ Uploads results back to Google Drive or saves locally
- ✅ Cost: ~$0.001 per page (~200x cheaper than vision LLMs)

## Setup

### With Nix (recommended)

```bash
# Enter development environment
nix develop

# Or run directly
nix run .#gdrive-batch-ocr -- --help
```

### With uv

```bash
# Copy the example env file and add your API key
cp .env.local.example .env.local
# Edit .env.local and add your MISTRAL_API_KEY

# All scripts use inline dependencies and auto-load .env.local
uv run gdrive_batch_ocr.py --help
```

### Google Drive Authentication

1. Create OAuth credentials:
   - Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   - Create OAuth 2.0 Client ID (Desktop app)
   - Download as `credentials.json`

2. Place `credentials.json` in the same directory as the scripts

3. First run will open browser for authentication
   - Token saved to `~/.gdrive_token.json`

## Usage

### Check which PDFs need OCR

```bash
uv run gdrive_batch_ocr.py --folder-id YOUR_FOLDER_ID --max-files 5
```

### Process all PDFs in Drive

```bash
export MISTRAL_API_KEY="your_key"

# Upload results back to Drive
uv run gdrive_batch_ocr.py

# Or save locally
uv run gdrive_batch_ocr.py --local-only --output ./results
```

### Process specific folder

```bash
uv run gdrive_batch_ocr.py \
  --folder-id 1abc123xyz \
  --output-folder 1def456uvw \
  --workers 5
```

### Local batch processing

```bash
# Process local PDFs
uv run batch_ocr.py ~/Documents/pdfs/ ~/ocr_output/

# Single file
uv run mistral_ocr.py document.pdf --inline-images
```

### OCR JPG/PNG images

```bash
# OCR a single image
uv run example_usage.py  # Uncomment example_ocr_jpg()

# Batch OCR multiple images
uv run example_usage.py  # Uncomment example_batch_ocr_images()

# OCR mixed PDFs and images from a directory
uv run example_usage.py  # Uncomment example_ocr_mixed_documents()
```

## Output Structure

### Google Drive
```
OCR_Output/
├── document1_ocr/
│   ├── document1.md
│   ├── img-0.jpg
│   └── img-1.jpg
└── document2_ocr/
    ├── document2.md
    └── img-0.jpg
```

### Local
```
ocr_output/
├── document1.md
├── document1_images/
│   ├── img-0.jpg
│   └── img-1.jpg
├── document2.md
└── document2_images/
    └── img-0.jpg
```

## Scripts Overview

### gdrive_batch_ocr.py
Main script for batch processing Google Drive PDFs. Features:
- Auto-detects non-searchable PDFs
- Parallel processing
- Saves markdown + extracted images
- Upload to Drive or save locally

### mistral_ocr.py
Single PDF OCR with Mistral. Simple CLI:
```bash
uv run mistral_ocr.py input.pdf --inline-images
```

### batch_ocr.py
Process multiple local PDFs in parallel:
```bash
uv run batch_ocr.py input_dir/ output_dir/
```

### check_pdf_searchable.py
Check which PDFs have searchable text:
```bash
uv run check_pdf_searchable.py *.pdf
```

## Options

```bash
uv run gdrive_batch_ocr.py [options]

Options:
  --folder-id ID       Source folder in Google Drive
  --output-folder ID   Output folder in Google Drive
  --local-only         Save locally instead of uploading
  --output PATH        Local output directory (default: ./ocr_output)
  --max-files N        Limit number of files to process
  --workers N          Parallel workers (default: 3)
```

## Cost Estimation

- **Mistral OCR**: ~$1 per 1000 pages
- **Batch API**: ~$0.50 per 1000 pages (50% discount)

Example: 100 PDFs × 10 pages = 1000 pages = **~$1**

## Tips

1. **Start small**: Use `--max-files 5` to test first
2. **Adjust workers**: More workers = faster but higher API rate limits
3. **Local testing**: Use `--local-only` to inspect results before uploading
4. **Already searchable**: Script automatically skips PDFs with text

## Troubleshooting

**Rate limits**: Reduce `--workers` or add delays between requests

**Authentication errors**: 
- Delete `~/.gdrive_token.json` and re-authenticate
- Check `credentials.json` is valid

**Missing images**:
- Use `--inline-images` flag in `mistral_ocr.py`
- Some PDFs may not have extractable images

**Large files**: Mistral OCR handles up to ~50MB PDFs

## Development

```bash
# Enter dev environment
nix develop

# Run with debug output
MISTRAL_API_KEY=xxx uv run gdrive_batch_ocr.py --max-files 1
```
# searchable-pdf-creator-google-drive-OCR
