"""
As cinco Expressões Regulares do Auditor Léxico.

Cada ER é registrada com os campos da ficha exigida pelo guia da disciplina:
identificação, alfabeto, linguagem, ER formal e sintaxe implementada.

Regras seguidas em TODOS os padrões avaliados:
  * correspondência completa com re.fullmatch (dispensa as âncoras ^ e $);
  * proibidos: \\d, \\w, \\s, o ponto curinga '.', classes negadas,
    retroreferências e lookarounds (verificado automaticamente pelo
    analisador em construtor_afn.py).

Notação formal usada nas fichas
-------------------------------
  r s        concatenação (justaposição)
  r | s      união
  r*         fecho de Kleene
  ε          cadeia vazia (r | ε) = r opcional
  [0-9]      classe/intervalo finito, abreviação de (0 | 1 | ... | 9)
  ⎵          o símbolo espaço
  'x'        símbolo literal entre aspas (quando coincide com um operador)
  ⟨NOME⟩     definição regular (nome dado a uma subexpressão)
Os espaços comuns na escrita formal servem apenas para leitura.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ============================================================================
# Padrões exatamente como são usados pelo programa
# ============================================================================

PADRAO_ER_01 = r"(SEN|ATU)-[A-Z]{2,3}-[0-9]{4}"

PADRAO_ER_02 = r"SEN-[A-Z]{2,3}-[0-9]{4}:(TEMP=-?(1[0-9][0-9]|[1-9]?[0-9])(\.[0-9])?C|UMID=(100(\.0)?|[1-9]?[0-9](\.[0-9])?)%|PRES=(8[5-9][0-9]|9[0-9][0-9]|10[0-9][0-9])hPa)"

PADRAO_ER_03 = r"CMD ATU-[A-Z]{2,3}-[0-9]{4} (LIGAR|DESLIGAR|ABRIR|FECHAR|AJUSTAR (100|[1-9]?[0-9])%)"

PADRAO_ER_04 = r"((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(/(3[0-2]|[12]?[0-9]))?"

PADRAO_ER_05 = r"[0-9]{4}-((0[1-9]|1[0-2])-(0[1-9]|[12][0-9])|(0[13-9]|1[0-2])-30|(0[13578]|1[02])-31)T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9] (INFO|WARN|ERROR|CRIT) (SEN|ATU)-[A-Z]{2,3}-[0-9]{4}: [A-Za-z0-9_.-]+( [A-Za-z0-9_.-]+)*"

ER_01_ID = re.compile(PADRAO_ER_01)
ER_02_TELEMETRIA = re.compile(PADRAO_ER_02)
ER_03_COMANDO = re.compile(PADRAO_ER_03)
ER_04_IPV4_CIDR = re.compile(PADRAO_ER_04)
ER_05_ALERTA_LOG = re.compile(PADRAO_ER_05)


# ============================================================================
# Fichas das expressões
# ============================================================================

@dataclass(frozen=True)
class ExpressaoRegular:
    codigo: str
    nome: str
    categoria: str
    finalidade: str
    alfabeto: str
    linguagem: str
    definicoes: tuple[tuple[str, str], ...]  # definições regulares na notação formal
    formal: str                              # ER formal (pode usar as definições)
    padrao: str                              # sintaxe exatamente como no código
    regex: re.Pattern = field(compare=False)

    def reconhece(self, cadeia: str) -> bool:
        return self.regex.fullmatch(cadeia) is not None

    def formal_completa(self) -> list[str]:
        """Linhas da ER formal: definições regulares seguidas da ER principal."""
        linhas = [f"⟨{nome}⟩ = {corpo}" for nome, corpo in self.definicoes]
        linhas.append(f"{self.codigo.replace('-', '')} = {self.formal}")
        return linhas

    def formal_como_python(self) -> str:
        """Traduz a ER formal para a sintaxe do Python (usado para PROVAR, nos
        testes, que a ER formal e o padrão do código descrevem a mesma linguagem)."""
        return formal_para_python(self.formal, dict(self.definicoes))


DEF_ID = ("ID", "(SEN | ATU) - [A-Z][A-Z]([A-Z] | ε) - [0-9][0-9][0-9][0-9]")

ER01 = ExpressaoRegular(
    codigo="ER-01",
    nome="ID do Dispositivo",
    categoria="ID_DISPOSITIVO",
    finalidade=(
        "Validar o identificador único de um sensor (SEN) ou atuador (ATU) da rede. "
        "É também o bloco reutilizado dentro das ERs 02, 03 e 05."
    ),
    alfabeto="Σ₁ = {A, …, Z} ∪ {0, …, 9} ∪ {-}   (37 símbolos)",
    linguagem=(
        "Cadeias formadas pela classe do dispositivo (SEN ou ATU), um hífen, o código do "
        "modelo com 2 ou 3 letras maiúsculas, um hífen e o número de série com exatamente "
        "4 dígitos. L₁ é FINITA: |L₁| = 2 × (26² + 26³) × 10⁴ = 365.040.000 cadeias."
    ),
    definicoes=(DEF_ID,),
    formal="⟨ID⟩",
    padrao=PADRAO_ER_01,
    regex=ER_01_ID,
)

ER02 = ExpressaoRegular(
    codigo="ER-02",
    nome="Telemetria (medição física)",
    categoria="TELEMETRIA",
    finalidade=(
        "Validar a leitura enviada por um sensor: temperatura (°C), umidade relativa (%) "
        "ou pressão atmosférica (hPa), com a unidade correta e dentro da faixa do instrumento."
    ),
    alfabeto="Σ₂ = {A, …, Z} ∪ {0, …, 9} ∪ {-, :, =, ., %, h, a}   (43 símbolos)",
    linguagem=(
        "ID de um SENSOR (SEN), ':' e exatamente uma medição: TEMP= com sinal '-' opcional, "
        "inteiro de 0 a 199 sem zeros à esquerda, uma casa decimal opcional e a unidade C; "
        "UMID= com valor de 0 a 100 (uma casa decimal opcional; 100 só como 100 ou 100.0) "
        "e a unidade %; ou PRES= com inteiro de 850 a 1099 e a unidade hPa. L₂ é finita."
    ),
    definicoes=(
        ("SID", "SEN - [A-Z][A-Z]([A-Z] | ε) - [0-9][0-9][0-9][0-9]"),
        ("DEC", ". [0-9] | ε"),
        ("TEMP", "TEMP= (- | ε) (1[0-9][0-9] | ([1-9] | ε) [0-9]) ⟨DEC⟩ C"),
        ("UMID", "UMID= (100 (.0 | ε) | ([1-9] | ε) [0-9] ⟨DEC⟩) %"),
        ("PRES", "PRES= (8[5-9][0-9] | 9[0-9][0-9] | 10[0-9][0-9]) hPa"),
    ),
    formal="⟨SID⟩ : (⟨TEMP⟩ | ⟨UMID⟩ | ⟨PRES⟩)",
    padrao=PADRAO_ER_02,
    regex=ER_02_TELEMETRIA,
)

ER03 = ExpressaoRegular(
    codigo="ER-03",
    nome="Comando de Controle",
    categoria="COMANDO",
    finalidade=(
        "Validar ordens enviadas a ATUADORES: ligar, desligar, abrir, fechar ou ajustar "
        "a abertura/potência em percentual (0 a 100%)."
    ),
    alfabeto="Σ₃ = {A, …, Z} ∪ {0, …, 9} ∪ {-, ⎵, %}   (39 símbolos)",
    linguagem=(
        "O prefixo 'CMD', um espaço, o ID de um ATUADOR (ATU), um espaço e exatamente uma "
        "ação: LIGAR, DESLIGAR, ABRIR, FECHAR ou 'AJUSTAR ' seguido de um inteiro de 0 a 100 "
        "sem zeros à esquerda e do símbolo %. L₃ é finita."
    ),
    definicoes=(
        ("AID", "ATU - [A-Z][A-Z]([A-Z] | ε) - [0-9][0-9][0-9][0-9]"),
        ("PCT", "100 | ([1-9] | ε) [0-9]"),
    ),
    formal="CMD ⎵ ⟨AID⟩ ⎵ (LIGAR | DESLIGAR | ABRIR | FECHAR | AJUSTAR ⎵ ⟨PCT⟩ %)",
    padrao=PADRAO_ER_03,
    regex=ER_03_COMANDO,
)

ER04 = ExpressaoRegular(
    codigo="ER-04",
    nome="Rota de Rede IPv4/CIDR",
    categoria="IPV4_CIDR",
    finalidade=(
        "Validar o endereço IPv4 (ou a rota em notação CIDR) de um equipamento, bloqueando "
        "octetos acima de 255, zeros à esquerda e máscaras acima de /32."
    ),
    alfabeto="Σ₄ = {0, …, 9} ∪ {., /}   (12 símbolos)",
    linguagem=(
        "Quatro octetos decimais de 0 a 255, sem zeros à esquerda, separados por '.', "
        "seguidos opcionalmente de '/' e de uma máscara de 0 a 32. L₄ é finita: "
        "256⁴ × (1 + 33) endereços/rotas."
    ),
    definicoes=(
        ("OCT", "25[0-5] | 2[0-4][0-9] | 1[0-9][0-9] | ([1-9] | ε) [0-9]"),
        ("MASC", "3[0-2] | ([12] | ε) [0-9]"),
    ),
    formal="⟨OCT⟩ . ⟨OCT⟩ . ⟨OCT⟩ . ⟨OCT⟩ (/ ⟨MASC⟩ | ε)",
    padrao=PADRAO_ER_04,
    regex=ER_04_IPV4_CIDR,
)

ER05 = ExpressaoRegular(
    codigo="ER-05",
    nome="Alerta de Log (severidade)",
    categoria="ALERTA_LOG",
    finalidade=(
        "Validar registros de eventos com carimbo de tempo ISO 8601, nível de severidade, "
        "dispositivo de origem e mensagem descritiva."
    ),
    alfabeto="Σ₅ = {A, …, Z} ∪ {a, …, z} ∪ {0, …, 9} ∪ {-, :, ⎵, _, .}   (67 símbolos)",
    linguagem=(
        "Data AAAA-MM-DD com dia válido para o mês (fevereiro até 29; abril, junho, setembro "
        "e novembro até 30; os demais até 31), 'T', hora hh:mm:ss (00:00:00 a 23:59:59), "
        "espaço, nível de severidade (INFO, WARN, ERROR ou CRIT), espaço, ID do "
        "dispositivo, ': ' e uma mensagem formada por uma ou mais palavras de "
        "[A-Za-z0-9_.-] separadas por exatamente um espaço. L₅ é INFINITA, pois a mensagem "
        "usa o fecho de Kleene."
    ),
    definicoes=(
        ("DATA",
         "[0-9][0-9][0-9][0-9] - ((0[1-9] | 1[0-2]) - (0[1-9] | [12][0-9])"
         " | (0[13-9] | 1[0-2]) - 30 | (0[13578] | 1[02]) - 31)"),
        ("HORA", "([01][0-9] | 2[0-3]) : [0-5][0-9] : [0-5][0-9]"),
        ("SEV", "INFO | WARN | ERROR | CRIT"),
        DEF_ID,
        ("PAL", "[A-Za-z0-9_.-] [A-Za-z0-9_.-]*"),
        ("MSG", "⟨PAL⟩ (⎵ ⟨PAL⟩)*"),
    ),
    formal="⟨DATA⟩ T ⟨HORA⟩ ⎵ ⟨SEV⟩ ⎵ ⟨ID⟩ : ⎵ ⟨MSG⟩",
    padrao=PADRAO_ER_05,
    regex=ER_05_ALERTA_LOG,
)

EXPRESSOES: tuple[ExpressaoRegular, ...] = (ER01, ER02, ER03, ER04, ER05)
POR_CATEGORIA: dict[str, ExpressaoRegular] = {er.categoria: er for er in EXPRESSOES}
POR_CODIGO: dict[str, ExpressaoRegular] = {er.codigo: er for er in EXPRESSOES}


def classificar(pacote: str) -> ExpressaoRegular | None:
    """Devolve a ER cuja linguagem contém o pacote (as cinco linguagens são
    disjuntas, então no máximo uma reconhece cada cadeia)."""
    for er in EXPRESSOES:
        if er.reconhece(pacote):
            return er
    return None


# ============================================================================
# Tradução da notação formal para a sintaxe do Python
# ============================================================================

def formal_para_python(texto: str, definicoes: dict[str, str]) -> str:
    """Converte a ER formal (com definições regulares) em um padrão do Python.

    ⟨NOME⟩ -> (?:definição)   ε -> cadeia vazia   ⎵ -> espaço
    'x'    -> símbolo x       [..] -> classe     demais símbolos -> literais
    """
    saida = []
    i = 0
    while i < len(texto):
        c = texto[i]
        if c == " " or c == "ε":
            i += 1
        elif c == "⟨":
            fim = texto.index("⟩", i)
            corpo = definicoes[texto[i + 1:fim]]
            saida.append("(?:" + formal_para_python(corpo, definicoes) + ")")
            i = fim + 1
        elif c == "⎵":
            saida.append(" ")
            i += 1
        elif c == "'":
            if texto[i + 2] != "'":
                raise ValueError(f"literal entre aspas malformado em {texto!r}")
            saida.append(re.escape(texto[i + 1]))
            i += 3
        elif c == "[":
            fim = texto.index("]", i)
            saida.append(texto[i:fim + 1])
            i = fim + 1
        elif c == "(":
            saida.append("(?:")
            i += 1
        elif c in ")|*":
            saida.append(c)
            i += 1
        else:
            saida.append(re.escape(c))
            i += 1
    return "".join(saida)
