"""
Diagramas legíveis dos AFNε no formato DOT (Graphviz).

  * rótulos de classe agrupados ([0-9] em vez de 10 setas);
  * movimentos ε tracejados em vermelho;
  * estado inicial indicado por "início" e estados finais com círculo duplo.

Autômatos longos podem ser divididos em PARTES para caber em páginas e
slides. Os cortes são feitos em estados de articulação — estados pelos quais
passa todo caminho do estado inicial ao final —, de modo que cada parte é um
trecho contínuo do MESMO autômato, com a numeração original dos estados.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from afn import EPSILON, AFNe
from construtor_afn import formatar_conjunto


def _aspas(texto: str) -> str:
    return '"' + texto.replace("\\", "\\\\").replace('"', '\\"') + '"'


def gerar_dot(afn: AFNe, titulo: str = "", parte: "Parte | None" = None) -> str:
    """DOT do AFNε inteiro ou, se `parte` for dada, só daquele trecho, com
    setas pontilhadas indicando de onde o trecho vem e para onde segue."""
    estados = set(range(afn.n_estados)) if parte is None else parte.estados
    linhas = [
        f"digraph {_aspas(afn.nome or 'AFN')} {{",
        "  rankdir=LR;",
        '  graph [fontname="Segoe UI", fontsize=16, nodesep=0.22, ranksep=0.32, pad=0.3, '
        'labelloc=t, bgcolor="white"' + (f", label={_aspas(titulo)}" if titulo else "") + "];",
        '  node [shape=circle, fontname="Segoe UI", fontsize=11, width=0.46, fixedsize=true, '
        'style=filled, fillcolor="#f3f6fb", color="#1f3a5f", penwidth=1.2];',
        '  edge [fontname="Segoe UI", fontsize=12, color="#1f3a5f", fontcolor="#13263d", arrowsize=0.7];',
    ]
    estilo_seta = 'shape=none, width=0.6, fontsize=11, fontcolor="#1f3a5f", style=""'
    if afn.inicial in estados:
        linhas.append(f'  inicio [{estilo_seta}, label="início"];')
        linhas.append(f"  inicio -> q{afn.inicial} [penwidth=1.6];")
    else:
        linhas.append(f"  anterior [{estilo_seta}, label={_aspas(f'(parte {parte.numero - 1})')}];")
        linhas.append(f"  anterior -> q{parte.entrada} [style=dotted, penwidth=1.4];")
    for estado in sorted(afn.finais & estados):
        linhas.append(f'  q{estado} [shape=doublecircle, fillcolor="#dff2e6", color="#1d6b3f", width=0.5];')
    for estado in sorted(estados):
        linhas.append(f"  q{estado};")
    for origem, rotulo, destino in afn.transicoes:
        if origem not in estados or destino not in estados:
            continue
        if rotulo is EPSILON:
            atributos = 'label="ε", style=dashed, color="#c0392b", fontcolor="#c0392b"'
        else:
            atributos = f"label={_aspas(formatar_conjunto(rotulo))}"
        linhas.append(f"  q{origem} -> q{destino} [{atributos}];")
    if parte is not None and parte.saida is not None:
        linhas.append(f"  seguinte [{estilo_seta}, label={_aspas(f'(parte {parte.numero + 1})')}];")
        linhas.append(f"  q{parte.saida} -> seguinte [style=dotted, penwidth=1.4];")
    linhas.append("}")
    return "\n".join(linhas) + "\n"


def _alcanca_final_sem(afn: AFNe, proibido: int) -> bool:
    if proibido == afn.inicial:
        return False
    vistos = {afn.inicial}
    fila = deque([afn.inicial])
    while fila:
        estado = fila.popleft()
        if estado in afn.finais:
            return True
        for _, destino in afn.saidas(estado):
            if destino != proibido and destino not in vistos:
                vistos.add(destino)
                fila.append(destino)
    return False


@dataclass(frozen=True)
class Parte:
    numero: int            # 1, 2, ...
    estados: frozenset[int]
    entrada: int           # estado de corte por onde o trecho começa
    saida: int | None      # estado de corte onde o trecho termina (None na última parte)


def dividir_em_partes(afn: AFNe, max_estados: int = 18) -> list[Parte]:
    """Divide o AFNε em trechos de ~max_estados estados, cortando em estados
    de articulação. O estado de corte aparece no fim de um trecho e no início
    do seguinte. Devolve uma única parte se não houver cortes adequados."""
    # Como os estados são numerados em largura a partir do inicial, a ordem
    # numérica dos estados de articulação é a ordem em que são percorridos.
    cortes = [e for e in range(afn.n_estados) if not _alcanca_final_sem(afn, e)]
    escolhidos = []
    ultimo = 0
    for corte in cortes:
        if corte - ultimo >= max_estados and corte not in afn.finais:
            escolhidos.append(corte)
            ultimo = corte
    limites = [afn.inicial, *escolhidos, None]
    partes = []
    for numero, (inicio, fim) in enumerate(zip(limites, limites[1:]), start=1):
        trecho = {inicio}
        fila = deque([inicio])
        while fila:
            estado = fila.popleft()
            if estado == fim:
                continue
            for _, destino in afn.saidas(estado):
                if destino not in trecho:
                    trecho.add(destino)
                    fila.append(destino)
        partes.append(Parte(numero, frozenset(trecho), inicio, fim))
    return partes
