#!/usr/bin/env bash
# Regenera o diagrama de arquitetura (SVG/PNG) e o relatório PDF a partir do documento Markdown.
# Requisitos: python3 e Google Chrome (ou Chromium) — defina CHROME se estiver em outro caminho.
set -euo pipefail
cd "$(dirname "$0")/.."
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
command -v google-chrome >/dev/null 2>&1 && [ ! -x "$CHROME" ] && CHROME=google-chrome

VENV=scripts/.venv-docs
[ -d "$VENV" ] || { python3 -m venv "$VENV" && "$VENV/bin/pip" -q install markdown; }

python3 scripts/gerar_diagrama.py
"$CHROME" --headless --disable-gpu --hide-scrollbars --window-size=1680,1060 \
  --screenshot="$PWD/assets/arquitetura.png" "file://$PWD/assets/arquitetura.svg" 2>/dev/null
echo "Gerado assets/arquitetura.png"

"$VENV/bin/python" scripts/gerar_relatorio.py document/other/relatorio.html
"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$PWD/document/relatorio_cardioia.pdf" "file://$PWD/document/other/relatorio.html" 2>/dev/null
echo "Gerado document/relatorio_cardioia.pdf"
