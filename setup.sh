#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Mistral OCR Setup"
echo ""

# Check for Mistral API key
if [ -z "${MISTRAL_API_KEY:-}" ]; then
    echo "⚠️  MISTRAL_API_KEY not set"
    echo "Get your key at: https://console.mistral.ai/"
    echo ""
    read -p "Enter your Mistral API key: " api_key
    export MISTRAL_API_KEY="$api_key"
    echo "export MISTRAL_API_KEY='$api_key'" >> ~/.bashrc
    echo "✓ API key saved to ~/.bashrc"
fi

# Check for Google credentials
if [ ! -f "credentials.json" ]; then
    echo ""
    echo "⚠️  credentials.json not found"
    echo "To use Google Drive integration:"
    echo "1. Go to: https://console.cloud.google.com/apis/credentials"
    echo "2. Create OAuth 2.0 Client ID (Desktop app)"
    echo "3. Download as credentials.json to this directory"
    echo ""
    read -p "Press Enter when credentials.json is ready (or Ctrl+C to skip)..."
fi

# Check for uv
if ! command -v uv &> /dev/null; then
    echo ""
    echo "⚠️  uv not found"
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

echo ""
echo "✓ Setup complete!"
echo ""
echo "Quick start:"
echo "  # Check which PDFs need OCR"
echo "  uv run check_pdf_searchable.py *.pdf"
echo ""
echo "  # Single file OCR"
echo "  uv run mistral_ocr.py document.pdf"
echo ""
echo "  # Batch Google Drive OCR (first 5 files)"
echo "  uv run gdrive_batch_ocr.py --max-files 5 --local-only"
echo ""
