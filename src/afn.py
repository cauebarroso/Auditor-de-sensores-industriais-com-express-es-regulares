"""
AFNε — Autômato Finito Não-Determinístico com movimentos vazios.

Representação usada no projeto:
  * estados são inteiros 0..n-1 (exibidos como q0, q1, ...);
  * cada transição é uma tripla (origem, rótulo, destino), em que o rótulo é
      - None (EPSILON)       -> movimento vazio ε;
      - frozenset de símbolos -> uma transição para CADA símbolo do conjunto.
    Exemplo: o rótulo [0-9] resume as 10 transições paralelas 0, 1, ..., 9.

O módulo implementa as operações clássicas da teoria:
  * fecho-ε (ε-closure) de um conjunto de estados;
  * função de transição estendida (simulação da cadeia símbolo a símbolo);
  * teste de equivalência entre dois AFNε (construção de subconjuntos
    feita sob demanda sobre o produto dos dois autômatos).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

EPSILON = None


@dataclass(frozen=True)
class Passo:
    """Um passo da simulação: conjunto de estados ativo após ler `lidos` símbolos."""

    lidos: int
    simbolo: str | None
    estados: frozenset[int]


@dataclass(frozen=True)
class ResultadoSimulacao:
    aceita: bool
    passos: tuple[Passo, ...]
    # Índice (0-based) do primeiro símbolo que esvaziou o conjunto de estados.
    # Vale len(cadeia) quando a leitura terminou fora de um estado final,
    # e None quando a cadeia foi aceita.
    posicao_erro: int | None
    # Símbolos que teriam transição a partir do último conjunto não vazio.
    esperados: frozenset[str]
    # Indica se o último conjunto não vazio continha um estado final
    # (ou seja, a cadeia poderia ter terminado ali).
    podia_terminar: bool


class AFNe:
    """Autômato finito não-determinístico com movimentos ε."""

    def __init__(self, nome: str = ""):
        self.nome = nome
        self.n_estados = 0
        self.inicial = 0
        self.finais: set[int] = set()
        self.transicoes: list[tuple[int, frozenset[str] | None, int]] = []
        self._saidas: dict[int, list[tuple[frozenset[str] | None, int]]] = {}

    # ------------------------------------------------------------------ #
    # Construção
    # ------------------------------------------------------------------ #
    def novo_estado(self) -> int:
        estado = self.n_estados
        self.n_estados += 1
        self._saidas[estado] = []
        return estado

    def adicionar_transicao(self, origem: int, rotulo: frozenset[str] | None, destino: int) -> None:
        self.transicoes.append((origem, rotulo, destino))
        self._saidas[origem].append((rotulo, destino))

    def renumerado(self) -> "AFNe":
        """Devolve uma cópia com estados renumerados em ordem de busca em largura
        a partir do estado inicial (q0 = inicial) e sem estados inalcançáveis."""
        ordem = [self.inicial]
        novo_id = {self.inicial: 0}
        fila = deque([self.inicial])
        while fila:
            estado = fila.popleft()
            for _, destino in self._saidas[estado]:
                if destino not in novo_id:
                    novo_id[destino] = len(ordem)
                    ordem.append(destino)
                    fila.append(destino)

        copia = AFNe(self.nome)
        for _ in ordem:
            copia.novo_estado()
        copia.inicial = 0
        copia.finais = {novo_id[f] for f in self.finais if f in novo_id}
        for estado in ordem:
            for rotulo, destino in self._saidas[estado]:
                copia.adicionar_transicao(novo_id[estado], rotulo, novo_id[destino])
        return copia

    # ------------------------------------------------------------------ #
    # Consultas
    # ------------------------------------------------------------------ #
    def saidas(self, estado: int) -> list[tuple[frozenset[str] | None, int]]:
        return self._saidas[estado]

    def alfabeto(self) -> set[str]:
        simbolos: set[str] = set()
        for _, rotulo, _ in self.transicoes:
            if rotulo is not EPSILON:
                simbolos |= rotulo
        return simbolos

    def total_transicoes_expandidas(self) -> int:
        """Número de transições contando cada símbolo de uma classe separadamente
        (é o número de transições que aparece no arquivo do JFLAP)."""
        return sum(1 if r is EPSILON else len(r) for _, r, _ in self.transicoes)

    def total_movimentos_vazios(self) -> int:
        return sum(1 for _, r, _ in self.transicoes if r is EPSILON)

    def _alcancaveis(self, origens, arestas) -> set[int]:
        vistos = set(origens)
        pilha = list(origens)
        while pilha:
            estado = pilha.pop()
            for destino in arestas.get(estado, ()):
                if destino not in vistos:
                    vistos.add(destino)
                    pilha.append(destino)
        return vistos

    def linguagem_infinita(self) -> bool:
        """L é infinita se, e somente se, existe um ciclo que lê pelo menos um
        símbolo passando por um estado útil (alcançável a partir do inicial e
        que alcança um final) — é o ciclo que o lema do bombeamento "bombeia"."""
        frente: dict[int, list[int]] = {}
        tras: dict[int, list[int]] = {}
        for origem, _, destino in self.transicoes:
            frente.setdefault(origem, []).append(destino)
            tras.setdefault(destino, []).append(origem)
        uteis = self._alcancaveis({self.inicial}, frente) & self._alcancaveis(self.finais, tras)
        for origem, rotulo, destino in self.transicoes:
            if rotulo is not EPSILON and origem in uteis and destino in uteis:
                if origem in self._alcancaveis({destino}, frente):
                    return True
        return False

    # ------------------------------------------------------------------ #
    # Operações da teoria
    # ------------------------------------------------------------------ #
    def fecho_epsilon(self, estados) -> frozenset[int]:
        """E(S): todos os estados alcançáveis a partir de S usando apenas ε."""
        fecho = set(estados)
        pilha = list(estados)
        while pilha:
            estado = pilha.pop()
            for rotulo, destino in self._saidas[estado]:
                if rotulo is EPSILON and destino not in fecho:
                    fecho.add(destino)
                    pilha.append(destino)
        return frozenset(fecho)

    def mover(self, estados, simbolo: str) -> frozenset[int]:
        """Estados alcançados lendo exatamente um `simbolo` (sem fecho-ε)."""
        return frozenset(
            destino
            for estado in estados
            for rotulo, destino in self._saidas[estado]
            if rotulo is not EPSILON and simbolo in rotulo
        )

    def passo(self, estados, simbolo: str) -> frozenset[int]:
        """δ̂ de um símbolo: E(mover(S, a))."""
        return self.fecho_epsilon(self.mover(estados, simbolo))

    def contem_final(self, estados) -> bool:
        return any(e in self.finais for e in estados)

    def simbolos_esperados(self, estados) -> frozenset[str]:
        return frozenset(
            simbolo
            for estado in estados
            for rotulo, _ in self._saidas[estado]
            if rotulo is not EPSILON
            for simbolo in rotulo
        )

    def simular(self, cadeia: str) -> ResultadoSimulacao:
        """Simula o AFNε sobre a cadeia, registrando o conjunto de estados ativo
        após cada símbolo lido."""
        atual = self.fecho_epsilon({self.inicial})
        passos = [Passo(0, None, atual)]
        for i, simbolo in enumerate(cadeia):
            proximo = self.passo(atual, simbolo)
            if not proximo:
                return ResultadoSimulacao(
                    aceita=False,
                    passos=tuple(passos),
                    posicao_erro=i,
                    esperados=self.simbolos_esperados(atual),
                    podia_terminar=self.contem_final(atual),
                )
            atual = proximo
            passos.append(Passo(i + 1, simbolo, atual))

        aceita = self.contem_final(atual)
        return ResultadoSimulacao(
            aceita=aceita,
            passos=tuple(passos),
            posicao_erro=None if aceita else len(cadeia),
            esperados=self.simbolos_esperados(atual),
            podia_terminar=aceita,
        )

    def aceita(self, cadeia: str) -> bool:
        atual = self.fecho_epsilon({self.inicial})
        for simbolo in cadeia:
            atual = self.passo(atual, simbolo)
            if not atual:
                return False
        return self.contem_final(atual)


# ---------------------------------------------------------------------- #
# Equivalência de linguagens
# ---------------------------------------------------------------------- #
def _classes_de_simbolos(*automatos: AFNe) -> list[str]:
    """Agrupa os símbolos que se comportam de forma idêntica em todas as
    transições dos autômatos e devolve um representante por grupo.
    Reduz o alfabeto (ex.: os 26 símbolos de [A-Z] viram poucos representantes)
    sem alterar o resultado do teste de equivalência."""
    rotulos = [r for a in automatos for _, r, _ in a.transicoes if r is not EPSILON]
    assinaturas: dict[tuple[int, ...], str] = {}
    simbolos = sorted(set().union(*(a.alfabeto() for a in automatos)))
    for simbolo in simbolos:
        assinatura = tuple(i for i, r in enumerate(rotulos) if simbolo in r)
        assinaturas.setdefault(assinatura, simbolo)
    return sorted(assinaturas.values())


def contraexemplo(a: AFNe, b: AFNe) -> str | None:
    """Procura a menor cadeia aceita por exatamente um dos autômatos.

    Percorre em largura os pares (E_a, E_b) de conjuntos de estados alcançáveis
    pela mesma cadeia — é a construção de subconjuntos aplicada ao produto dos
    dois AFNε. Se nenhum par discorda quanto à aceitação, L(a) = L(b) e a
    função devolve None. Como o número de pares é finito, o algoritmo sempre
    termina: é uma prova de equivalência, não uma amostragem.
    """
    simbolos = _classes_de_simbolos(a, b)
    inicio = (a.fecho_epsilon({a.inicial}), b.fecho_epsilon({b.inicial}))
    vistos = {inicio}
    fila = deque([(inicio, "")])
    while fila:
        (estados_a, estados_b), cadeia = fila.popleft()
        if a.contem_final(estados_a) != b.contem_final(estados_b):
            return cadeia
        if not estados_a and not estados_b:
            continue
        for simbolo in simbolos:
            par = (a.passo(estados_a, simbolo), b.passo(estados_b, simbolo))
            if par not in vistos:
                vistos.add(par)
                fila.append((par, cadeia + simbolo))
    return None


def equivalentes(a: AFNe, b: AFNe) -> bool:
    return contraexemplo(a, b) is None


def cadeia_em_comum(a: AFNe, b: AFNe) -> str | None:
    """Menor cadeia aceita pelos DOIS autômatos (L(a) ∩ L(b)), ou None se a
    interseção for vazia. Usa a mesma busca em largura sobre o produto."""
    simbolos = _classes_de_simbolos(a, b)
    inicio = (a.fecho_epsilon({a.inicial}), b.fecho_epsilon({b.inicial}))
    vistos = {inicio}
    fila = deque([(inicio, "")])
    while fila:
        (estados_a, estados_b), cadeia = fila.popleft()
        if a.contem_final(estados_a) and b.contem_final(estados_b):
            return cadeia
        for simbolo in simbolos:
            par = (a.passo(estados_a, simbolo), b.passo(estados_b, simbolo))
            if par[0] and par[1] and par not in vistos:
                vistos.add(par)
                fila.append((par, cadeia + simbolo))
    return None
