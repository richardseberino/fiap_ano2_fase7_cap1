"""Converte document/ai_project_document_fiap.md em HTML estilizado para impressão em PDF."""
import re
import sys
from pathlib import Path

import markdown

RAIZ = Path(__file__).resolve().parents[1]
origem = RAIZ / "document" / "ai_project_document_fiap.md"
destino = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "document" / "other" / "relatorio.html"

texto = origem.read_text(encoding="utf-8")
# No PDF o sumário vira índice simples (links internos não ajudam no papel)
texto = texto.replace("../assets/", (RAIZ / "assets").as_uri() + "/")
corpo = markdown.markdown(texto, extensions=["tables", "fenced_code", "attr_list", "md_in_html"])
# Cada capítulo (h1 com âncora c1..c7) começa em página nova, exceto o primeiro bloco
corpo = re.sub(r'<h1><a name="c([2-7])"', r'<h1 class="quebra"><a name="c\1"', corpo)

CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
* { box-sizing: border-box; }
body { font-family: Inter, 'Segoe UI', Helvetica, Arial, sans-serif; color: #0E1A1F; font-size: 10.5pt; line-height: 1.5; }
h1 { font-size: 20pt; color: #0B7A84; margin: 18pt 0 8pt; border-bottom: 2px solid #DDF0F1; padding-bottom: 4pt; }
h1.quebra { page-break-before: always; }
h2 { font-size: 14pt; color: #0E1A1F; margin: 14pt 0 6pt; }
h3 { font-size: 11.5pt; color: #0B7A84; margin: 12pt 0 4pt; }
h4 { font-size: 11pt; margin: 4pt 0; font-weight: 600; color: #5B6B73; }
p, li { text-align: justify; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0 12pt; font-size: 9pt; page-break-inside: avoid; }
th { background: #0B7A84; color: #fff; text-align: left; padding: 5pt 6pt; }
td { border-bottom: 1px solid #DDE5E8; padding: 4pt 6pt; vertical-align: top; }
tr:nth-child(even) td { background: #F3F6F7; }
code { font-family: ui-monospace, Menlo, monospace; font-size: 8.8pt; background: #EAF0F2; padding: 0 3px; border-radius: 3px; }
img { max-width: 100%; page-break-inside: avoid; }
a { color: #0B7A84; text-decoration: none; }
"""
html = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>CardioIA · Relatório</title>
<style>{CSS}</style></head><body>{corpo}</body></html>"""
destino.parent.mkdir(parents=True, exist_ok=True)
destino.write_text(html, encoding="utf-8")
print(f"HTML gerado: {destino}")
