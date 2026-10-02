"""
Gera os artefatos dos AFNε a partir das ERs do código:

  automatos/diagramas/ER-0X.dot|.svg|.png   diagramas legíveis (Graphviz)
  automatos/jflap/ER-0X.jff                 autômatos exatos para o JFLAP 7.1
  automatos/jflap/entradas/ER-0X.txt        cadeias de teste para "Multiple Run"

Uso (na raiz do repositório):
  python scripts/gerar_automatos.py

O Graphviz (programa `dot`) é opcional: sem ele, somente os .dot e os .jff
(com layout em grade) são gerados. Para indicar o executável:
  set GRAPHVIZ_DOT=C:\\caminho\\para\\dot.exe
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(RAIZ / "src"), str(RAIZ / "tests")]

from afn import EPSILON, AFNe  # noqa: E402
from casos_teste import CASOS  # noqa: E402
from construtor_afn import construir_afn  # noqa: E402
from expressoes import EXPRESSOES  # noqa: E402
from jflap import gerar_dot, salvar_jff  # noqa: E402

PASTA_DIAGRAMAS = RAIZ / "automatos" / "diagramas"
PASTA_JFLAP = RAIZ / "automatos" / "jflap"


def localizar_dot() -> str | None:
    return os.environ.get("GRAPHVIZ_DOT") or shutil.which("dot")


def dot_jflap(afn: AFNe) -> str:
    """DOT auxiliar só para calcular posições no JFLAP: os rótulos são
    empilhados (um símbolo por linha), como o JFLAP desenha transições
    paralelas, para que o layout reserve espaço vertical suficiente."""
    linhas = ["digraph G {", "  rankdir=LR; nodesep=0.35; ranksep=0.55;",
              "  node [shape=circle, width=0.55, fixedsize=true];",
              "  edge [fontsize=11];"]
    for origem, rotulo, destino in afn.transicoes:
        texto = "λ" if rotulo is EPSILON else "\\n".join(sorted(rotulo)).replace('"', '\\"')
        linhas.append(f'  q{origem} -> q{destino} [label="{texto}"];')
    linhas.append("}")
    return "\n".join(linhas)


def posicoes_jflap(dot: str, afn: AFNe) -> dict[int, tuple[float, float]] | None:
    saida = subprocess.run([dot, "-Tplain"], input=dot_jflap(afn), capture_output=True,
                           text=True, encoding="utf-8", check=True).stdout
    altura = None
    posicoes = {}
    for linha in saida.splitlines():
        partes = linha.split()
        if partes[0] == "graph":
            altura = float(partes[3])
        elif partes[0] == "node" and partes[1].startswith("q"):
            x, y = float(partes[2]), float(partes[3])
            posicoes[int(partes[1][1:])] = (60 + 72 * x, 60 + 72 * (altura - y))
    return posicoes


def main() -> None:
    dot = localizar_dot()
    if dot is None:
        print("[AVISO] Graphviz não encontrado: SVG/PNG não serão gerados e o .jff usará layout em grade.")
    (PASTA_JFLAP / "entradas").mkdir(parents=True, exist_ok=True)
    PASTA_DIAGRAMAS.mkdir(parents=True, exist_ok=True)

    for er in EXPRESSOES:
        afn = construir_afn(er.padrao, er.codigo)
        titulo = (f"{er.codigo} — {er.nome}   |   AFNε: {afn.n_estados} estados, "
                  f"{len(afn.transicoes)} transições ({afn.total_movimentos_vazios()} movimentos ε)")
        arquivo_dot = PASTA_DIAGRAMAS / f"{er.codigo}.dot"
        arquivo_dot.write_text(gerar_dot(afn, titulo), encoding="utf-8")

        posicoes = None
        if dot:
            for formato, extras in (("svg", []), ("png", ["-Gdpi=110"])):
                subprocess.run([dot, f"-T{formato}", *extras, str(arquivo_dot),
                                "-o", str(PASTA_DIAGRAMAS / f"{er.codigo}.{formato}")], check=True)
            posicoes = posicoes_jflap(dot, afn)

        salvar_jff(afn, PASTA_JFLAP / f"{er.codigo}.jff", posicoes)
        entradas = "\n".join(caso.cadeia for caso in CASOS[er.codigo]) + "\n"
        (PASTA_JFLAP / "entradas" / f"{er.codigo}.txt").write_text(entradas, encoding="utf-8")
        print(f"{er.codigo}: {afn.n_estados} estados, {len(afn.transicoes)} transições "
              f"({afn.total_movimentos_vazios()} ε; {afn.total_transicoes_expandidas()} no JFLAP)")


if __name__ == "__main__":
    main()
