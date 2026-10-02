"""
Construção do AFNε a partir da Expressão Regular (construção de Thompson).

O módulo tem duas partes:

1. Analisador sintático do SUBCONJUNTO REGULAR da sintaxe do Python que o guia
   da disciplina permite: literais, escapes de metacaracteres (\\. \\[ ...),
   classes e intervalos ([A-Z], [0-9_.-]), agrupamento ( ), união |,
   fechos * e +, opcionalidade ? e repetições {m}, {m,n}.
   Atalhos dependentes do motor (\\d, \\w, \\s, .), âncoras (^ $), classes
   negadas, retroreferências e lookarounds são REJEITADOS com erro — assim o
   próprio programa garante que as ERs avaliadas só usam operadores formais.

2. Construção de Thompson sobre a árvore sintática:
     símbolo/classe a    q --a--> f
     concatenação r s    o estado final de r é o estado inicial de s
     união r | s         q --ε--> (r) --ε--> f   e   q --ε--> (s) --ε--> f
     opcional r?         r com um desvio  q --ε--> f   (r | ε)
     fecho r*            q --ε--> a (r) b --ε--> a ;  b --ε--> f ;  q --ε--> f
     fecho r+            r r*
     repetição r{m,n}    m cópias de r seguidas de (n - m) cópias opcionais
"""

from __future__ import annotations

from dataclasses import dataclass

from afn import EPSILON, AFNe

METACARACTERES = set(".^$*+?{}[]\\|()")


class ErroPadraoNaoRegular(ValueError):
    """Padrão usa recurso fora da sintaxe formal permitida pelo guia."""


# ---------------------------------------------------------------------- #
# Árvore sintática
# ---------------------------------------------------------------------- #
@dataclass(frozen=True)
class Simbolos:
    """Um símbolo literal ou uma classe finita de símbolos."""

    conjunto: frozenset[str]


@dataclass(frozen=True)
class Concatenacao:
    partes: tuple  # sequência vazia representa ε


@dataclass(frozen=True)
class Uniao:
    opcoes: tuple


@dataclass(frozen=True)
class Repeticao:
    no: object
    minimo: int
    maximo: int | None  # None = ilimitado (fecho)


# ---------------------------------------------------------------------- #
# Analisador sintático (descida recursiva)
#   expr      := concat ('|' concat)*
#   concat    := repeticao*
#   repeticao := atomo ('*' | '+' | '?' | '{m}' | '{m,n}' | '{m,}')*
#   atomo     := '(' ['?:'] expr ')' | classe | '\' metacaractere | literal
# ---------------------------------------------------------------------- #
class _Analisador:
    def __init__(self, padrao: str):
        self.padrao = padrao
        self.pos = 0

    def erro(self, mensagem: str) -> ErroPadraoNaoRegular:
        return ErroPadraoNaoRegular(f"{mensagem} (posição {self.pos} de {self.padrao!r})")

    def atual(self) -> str | None:
        return self.padrao[self.pos] if self.pos < len(self.padrao) else None

    def consumir(self) -> str:
        c = self.padrao[self.pos]
        self.pos += 1
        return c

    def analisar(self):
        arvore = self.expr()
        if self.pos != len(self.padrao):
            raise self.erro(f"símbolo inesperado {self.atual()!r}")
        return arvore

    def expr(self):
        opcoes = [self.concat()]
        while self.atual() == "|":
            self.consumir()
            opcoes.append(self.concat())
        return opcoes[0] if len(opcoes) == 1 else Uniao(tuple(opcoes))

    def concat(self):
        partes = []
        while self.atual() is not None and self.atual() not in "|)":
            partes.append(self.repeticao())
        return partes[0] if len(partes) == 1 else Concatenacao(tuple(partes))

    def repeticao(self):
        no = self.atomo()
        if self.atual() is None or self.atual() not in "*+?{":
            return no
        c = self.consumir()
        if c == "*":
            no = Repeticao(no, 0, None)
        elif c == "+":
            no = Repeticao(no, 1, None)
        elif c == "?":
            no = Repeticao(no, 0, 1)
        else:
            minimo, maximo = self.limites()
            no = Repeticao(no, minimo, maximo)
        if self.atual() is not None and self.atual() in "*+?{":
            raise self.erro("quantificadores preguiçosos, possessivos ou encadeados não pertencem à notação formal")
        return no

    def limites(self) -> tuple[int, int | None]:
        fim = self.padrao.find("}", self.pos)
        if fim == -1:
            raise self.erro("repetição sem '}'")
        conteudo = self.padrao[self.pos:fim]
        self.pos = fim + 1
        partes = conteudo.split(",")
        if len(partes) == 1 and partes[0].isdigit():
            return int(partes[0]), int(partes[0])
        if len(partes) == 2 and partes[0].isdigit() and (partes[1].isdigit() or partes[1] == ""):
            minimo = int(partes[0])
            maximo = int(partes[1]) if partes[1] else None
            if maximo is not None and maximo < minimo:
                raise self.erro("repetição {m,n} com n < m")
            return minimo, maximo
        raise self.erro(f"repetição inválida {{{conteudo}}}")

    def atomo(self):
        c = self.atual()
        if c is None:
            raise self.erro("fim inesperado do padrão")
        if c == "(":
            self.consumir()
            if self.padrao.startswith("?:", self.pos):
                self.pos += 2
            elif self.atual() == "?":
                raise self.erro("grupos especiais (?=, ?!, ?<=, ?P...) não são operadores regulares formais")
            no = self.expr()
            if self.atual() != ")":
                raise self.erro("parêntese não fechado")
            self.consumir()
            return no
        if c == "[":
            return Simbolos(self.classe())
        if c == "\\":
            self.consumir()
            return Simbolos(frozenset(self.escape()))
        if c == ".":
            raise self.erro("o ponto '.' (qualquer caractere) depende do motor; use classes explícitas")
        if c in "^$":
            raise self.erro("âncoras ^ e $ não são símbolos do alfabeto; use fullmatch")
        if c in "*+?{":
            raise self.erro(f"quantificador {c!r} sem operando")
        if c == ")":
            raise self.erro("parêntese ')' sem abertura")
        return Simbolos(frozenset(self.consumir()))

    def escape(self) -> str:
        if self.atual() is None:
            raise self.erro("escape incompleto")
        c = self.consumir()
        if c in METACARACTERES or c in "-/ ":
            return c
        if c in "dDwWsSbB":
            raise self.erro(f"classe abreviada \\{c} varia com o motor/Unicode; expanda-a em uma classe explícita")
        if c.isdigit():
            raise self.erro("retroreferências podem reconhecer linguagens não regulares")
        raise self.erro(f"escape \\{c} não suportado")

    def classe(self) -> frozenset[str]:
        self.consumir()  # '['
        if self.atual() == "^":
            raise self.erro("classe negada depende do universo de caracteres; declare o alfabeto explicitamente")
        simbolos: set[str] = set()
        primeiro = True
        while True:
            c = self.atual()
            if c is None:
                raise self.erro("classe sem ']'")
            if c == "]" and not primeiro:
                self.consumir()
                break
            inicio = self.simbolo_de_classe()
            if self.atual() == "-" and self.pos + 1 < len(self.padrao) and self.padrao[self.pos + 1] != "]":
                self.consumir()  # '-'
                fim = self.simbolo_de_classe()
                if ord(fim) < ord(inicio):
                    raise self.erro(f"intervalo invertido {inicio}-{fim}")
                simbolos.update(chr(x) for x in range(ord(inicio), ord(fim) + 1))
            else:
                simbolos.add(inicio)
            primeiro = False
        return frozenset(simbolos)

    def simbolo_de_classe(self) -> str:
        c = self.consumir()
        if c == "\\":
            return self.escape()
        return c


def analisar(padrao: str):
    """Converte o padrão em árvore sintática (ou lança ErroPadraoNaoRegular)."""
    return _Analisador(padrao).analisar()


# ---------------------------------------------------------------------- #
# Construção de Thompson
# ---------------------------------------------------------------------- #
def _construir(afn: AFNe, no, origem: int) -> int:
    """Constrói o fragmento de `no` a partir do estado `origem` e devolve o
    estado final do fragmento."""
    if isinstance(no, Simbolos):
        destino = afn.novo_estado()
        afn.adicionar_transicao(origem, no.conjunto, destino)
        return destino

    if isinstance(no, Concatenacao):
        atual = origem
        for parte in no.partes:
            atual = _construir(afn, parte, atual)
        return atual

    if isinstance(no, Uniao):
        final = afn.novo_estado()
        for opcao in no.opcoes:
            entrada = afn.novo_estado()
            afn.adicionar_transicao(origem, EPSILON, entrada)
            saida = _construir(afn, opcao, entrada)
            afn.adicionar_transicao(saida, EPSILON, final)
        return final

    if isinstance(no, Repeticao):
        atual = origem
        for _ in range(no.minimo):
            atual = _construir(afn, no.no, atual)
        if no.maximo is None:
            # Fecho de Kleene (construção de Thompson)
            entrada = afn.novo_estado()
            afn.adicionar_transicao(atual, EPSILON, entrada)
            saida = _construir(afn, no.no, entrada)
            afn.adicionar_transicao(saida, EPSILON, entrada)
            final = afn.novo_estado()
            afn.adicionar_transicao(saida, EPSILON, final)
            afn.adicionar_transicao(atual, EPSILON, final)
            return final
        for _ in range(no.maximo - no.minimo):
            # Cópia opcional (r | ε): desvio por movimento vazio
            saida = _construir(afn, no.no, atual)
            afn.adicionar_transicao(atual, EPSILON, saida)
            atual = saida
        return atual

    raise TypeError(f"nó desconhecido: {no!r}")


def construir_afn(padrao: str, nome: str = "") -> AFNe:
    """Constrói o AFNε (com estados numerados q0, q1, ...) que reconhece
    exatamente a linguagem do padrão."""
    arvore = analisar(padrao)
    afn = AFNe(nome)
    inicial = afn.novo_estado()
    final = _construir(afn, arvore, inicial)
    afn.inicial = inicial
    afn.finais = {final}
    return afn.renumerado()


# ---------------------------------------------------------------------- #
# Formatação de rótulos para diagramas e mensagens
# ---------------------------------------------------------------------- #
ESPACO_VISIVEL = "⎵"


def formatar_simbolo(simbolo: str) -> str:
    return ESPACO_VISIVEL if simbolo == " " else simbolo


def formatar_conjunto(conjunto) -> str:
    """Escreve um conjunto de símbolos de forma compacta: {'0',...,'9'} -> [0-9]."""
    if conjunto is EPSILON:
        return "ε"
    if len(conjunto) == 1:
        return formatar_simbolo(next(iter(conjunto)))
    # O hífen literal fica no final da classe para não ser lido como intervalo
    simbolos = sorted(s for s in conjunto if s != "-")
    texto = ""
    i = 0
    while i < len(simbolos):
        j = i
        while j + 1 < len(simbolos) and ord(simbolos[j + 1]) == ord(simbolos[j]) + 1:
            j += 1
        if j - i >= 2:
            texto += f"{simbolos[i]}-{simbolos[j]}"
        else:
            texto += "".join(formatar_simbolo(s) for s in simbolos[i:j + 1])
        i = j + 1
    if "-" in conjunto:
        texto += "-"
    return f"[{texto}]"
