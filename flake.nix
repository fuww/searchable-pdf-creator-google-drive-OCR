{
  description = "Mistral OCR tools for Google Drive batch processing";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        
        python = pkgs.python312;
        
        pythonEnv = python.withPackages (ps: with ps; [
          google-auth
          google-auth-oauthlib
          google-auth-httplib2
          google-api-python-client
          pypdfium2
          pillow
          requests
        ]);
        
      in {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            pythonEnv
            uv
          ];
          
          shellHook = ''
            echo "🔍 Mistral OCR Environment"
            echo ""
            echo "Available scripts:"
            echo "  uv run mistral_ocr.py          - Single PDF OCR"
            echo "  uv run batch_ocr.py            - Batch local PDFs"
            echo "  uv run gdrive_batch_ocr.py     - Batch Google Drive PDFs"
            echo "  uv run check_pdf_searchable.py - Check if PDFs are searchable"
            echo ""
            if [ -f .env.local ]; then
              export $(cat .env.local | grep -v '^#' | xargs)
              echo "✓ Loaded .env.local"
            else
              echo "⚠ No .env.local found - copy .env.local.example and add your MISTRAL_API_KEY"
            fi
            echo ""
          '';
        };
        
        packages = {
          mistral-ocr = pkgs.writeShellScriptBin "mistral-ocr" ''
            exec ${pythonEnv}/bin/python ${./mistral_ocr.py} "$@"
          '';
          
          batch-ocr = pkgs.writeShellScriptBin "batch-ocr" ''
            exec ${pythonEnv}/bin/python ${./batch_ocr.py} "$@"
          '';
          
          gdrive-batch-ocr = pkgs.writeShellScriptBin "gdrive-batch-ocr" ''
            exec ${pythonEnv}/bin/python ${./gdrive_batch_ocr.py} "$@"
          '';
        };
        
        apps = {
          mistral-ocr = {
            type = "app";
            program = "${self.packages.${system}.mistral-ocr}/bin/mistral-ocr";
          };
          
          batch-ocr = {
            type = "app";
            program = "${self.packages.${system}.batch-ocr}/bin/batch-ocr";
          };
          
          gdrive-batch-ocr = {
            type = "app";
            program = "${self.packages.${system}.gdrive-batch-ocr}/bin/gdrive-batch-ocr";
          };
        };
      }
    );
}
