"""
Conversão Markdown -> HTML -> PDF para os documentos do projeto.

O PDF é impresso por um navegador Chromium em modo headless (Microsoft Edge,
que acompanha o Windows, ou Google Chrome). Requer o pacote `markdown`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import markdown

CSS = """
@page { size: A4; margin: 16mm 15mm 18mm 15mm; }
:root { --azul: #1f3a5f; --azul-claro: #eef3f9; --borda: #c9d4e2; --texto: #1b1f24; }
body { font-family: "Segoe UI", Calibri, Arial, sans-serif; color: var(--texto);
       font-size: 10.2pt; line-height: 1.45; }
h1 { color: var(--azul); font-size: 21pt; margin: 0 0 10pt; border-bottom: 3px solid var(--azul);
     padding-bottom: 6pt; }
h2 { color: var(--azul); font-size: 15pt; margin: 18pt 0 8pt; border-bottom: 1px solid var(--borda);
     padding-bottom: 3pt; }
h3 { color: var(--azul); font-size: 12.5pt; margin: 14pt 0 6pt; }
p, li { text-align: justify; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt; font-size: 9pt;
        page-break-inside: auto; }
tr { page-break-inside: avoid; }
th { background: var(--azul); color: white; text-align: left; padding: 4pt 6pt; }
td { border: 1px solid var(--borda); padding: 3pt 6pt; vertical-align: top; }
tr:nth-child(even) td { background: #f7f9fc; }
code { font-family: Consolas, "Cascadia Mono", monospace; font-size: 8.8pt;
       background: var(--azul-claro); padding: 0 2pt; border-radius: 2px; }
pre { background: #f4f6f9; border: 1px solid var(--borda); border-left: 3px solid var(--azul);
      padding: 6pt 8pt; font-size: 8.4pt; line-height: 1.3; white-space: pre-wrap;
      word-break: break-all; page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: inherit; }
img { max-width: 100%; display: block; margin: 4pt auto 8pt; page-break-inside: avoid; }
.quebra { page-break-before: always; }
a { color: var(--azul); }
"""


def markdown_para_html(texto: str, titulo: str, base: Path) -> str:
    corpo = markdown.markdown(texto, extensions=["tables", "fenced_code", "sane_lists"])
    # Em tabelas, o Markdown do GitHub converte "\|" em "|" (inclusive dentro de código);
    # a biblioteca markdown do Python mantém a barra invertida.
    corpo = corpo.replace(r"\|", "|")
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<base href="{base.resolve().as_uri()}/"><title>{titulo}</title>'
            f"<style>{CSS}</style></head><body>{corpo}</body></html>")


def localizar_navegador() -> str | None:
    candidatos = [
        os.environ.get("NAVEGADOR_PDF"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        shutil.which("msedge"), shutil.which("google-chrome"), shutil.which("chromium"),
    ]
    return next((c for c in candidatos if c and Path(c).exists()), None)


def html_para_pdf(html: str, destino: Path) -> Path | None:
    navegador = localizar_navegador()
    if navegador is None:
        return None
    destino = destino.resolve()
    destino.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as pasta:
        pagina = Path(pasta) / "documento.html"
        pagina.write_text(html, encoding="utf-8")
        subprocess.run([
            navegador, "--headless=new", "--disable-gpu", "--no-first-run",
            f"--user-data-dir={Path(pasta) / 'perfil'}", "--no-pdf-header-footer",
            "--allow-file-access-from-files", f"--print-to-pdf={destino}",
            pagina.as_uri(),
        ], check=True, capture_output=True, timeout=180)
        # O Edge pode devolver o controle antes de terminar de gravar o PDF:
        # espera o arquivo aparecer e o tamanho estabilizar.
        tamanho_anterior = -1
        for _ in range(120):
            if destino.exists() and destino.stat().st_size == tamanho_anterior > 0:
                break
            tamanho_anterior = destino.stat().st_size if destino.exists() else -1
            time.sleep(0.5)
    return destino if destino.exists() else None
