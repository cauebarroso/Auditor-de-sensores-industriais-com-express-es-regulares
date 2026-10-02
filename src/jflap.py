"""
Exportação e importação de AFNε no formato do JFLAP 7.1 (.jff).

No arquivo .jff cada rótulo de classe é expandido em UMA transição por
símbolo (ex.: [0-9] vira 10 transições), porque o JFLAP só lê um símbolo por
transição. Assim o autômato pode ser executado no próprio JFLAP
(Input > Multiple Run) e reconhece exatamente a mesma linguagem da ER.
Movimentos vazios são gravados com <read/> vazio (exibidos como λ no JFLAP).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from afn import EPSILON, AFNe


def salvar_jff(afn: AFNe, caminho: str | Path, posicoes: dict[int, tuple[float, float]] | None = None) -> Path:
    """Grava o AFNε em .jff. `posicoes` (pixels) vem do layout do Graphviz;
    sem ele os estados são dispostos em grade."""
    raiz = ET.Element("structure")
    ET.SubElement(raiz, "type").text = "fa"
    automato = ET.SubElement(raiz, "automaton")
    automato.append(ET.Comment(f" {afn.nome}: {afn.n_estados} estados "))
    for estado in range(afn.n_estados):
        x, y = (posicoes or {}).get(estado, (80 + 90 * (estado % 12), 80 + 120 * (estado // 12)))
        no = ET.SubElement(automato, "state", id=str(estado), name=f"q{estado}")
        ET.SubElement(no, "x").text = f"{x:.1f}"
        ET.SubElement(no, "y").text = f"{y:.1f}"
        if estado == afn.inicial:
            ET.SubElement(no, "initial")
        if estado in afn.finais:
            ET.SubElement(no, "final")
    for origem, rotulo, destino in afn.transicoes:
        simbolos = [None] if rotulo is EPSILON else sorted(rotulo)
        for simbolo in simbolos:
            transicao = ET.SubElement(automato, "transition")
            ET.SubElement(transicao, "from").text = str(origem)
            ET.SubElement(transicao, "to").text = str(destino)
            leitura = ET.SubElement(transicao, "read")
            if simbolo is not None:
                leitura.text = simbolo
    ET.indent(raiz, space="\t")
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "wb") as arquivo:
        arquivo.write(b'<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
        arquivo.write(b"<!--Created with JFLAP 7.1.-->\n")
        arquivo.write(ET.tostring(raiz, encoding="utf-8"))
        arquivo.write(b"\n")
    return caminho


def carregar_jff(caminho: str | Path) -> AFNe:
    """Lê um .jff do JFLAP como AFNε (transições paralelas viram um conjunto)."""
    raiz = ET.parse(caminho).getroot()
    automato = raiz.find("automaton")
    afn = AFNe(Path(caminho).stem)
    ids = {}
    for no in automato.findall("state"):
        ids[no.get("id")] = afn.novo_estado()
        if no.find("initial") is not None:
            afn.inicial = ids[no.get("id")]
        if no.find("final") is not None:
            afn.finais.add(ids[no.get("id")])
    agrupadas: dict[tuple[int, int], set[str]] = {}
    for transicao in automato.findall("transition"):
        origem = ids[transicao.findtext("from")]
        destino = ids[transicao.findtext("to")]
        leitura = transicao.findtext("read") or ""
        if leitura == "":
            afn.adicionar_transicao(origem, EPSILON, destino)
        else:
            if len(leitura) != 1:
                raise ValueError(f"transição com mais de um símbolo: {leitura!r}")
            agrupadas.setdefault((origem, destino), set()).add(leitura)
    for (origem, destino), simbolos in agrupadas.items():
        afn.adicionar_transicao(origem, frozenset(simbolos), destino)
    return afn

