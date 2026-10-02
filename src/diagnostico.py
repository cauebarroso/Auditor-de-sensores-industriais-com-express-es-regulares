"""
Diagnóstico de pacotes rejeitados.

O diagnóstico tem duas camadas:

1. Intenção + causa provável (heurística): identifica qual padrão o operador
   provavelmente tentou enviar (log, comando, telemetria, IP ou ID) e explica,
   em linguagem do domínio, a regra violada (ex.: "mês 13 não existe").

2. Localização exata pelo AFNε: simula o autômato da ER pretendida sobre o
   pacote e aponta o primeiro símbolo que deixou o conjunto de estados vazio,
   junto com os símbolos que o autômato esperava naquela posição.

As expressões auxiliares deste módulo NÃO são as ERs avaliadas do trabalho;
servem apenas para escolher a mensagem mais útil ao operador.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from construtor_afn import construir_afn, formatar_conjunto, formatar_simbolo
from expressoes import EXPRESSOES, POR_CODIGO, ExpressaoRegular

# Um AFNε por ER, construído a partir do próprio padrão do código.
AUTOMATOS = {er.codigo: construir_afn(er.padrao, er.codigo) for er in EXPRESSOES}

MESES_30_DIAS = {4, 6, 9, 11}
SEVERIDADES = ("INFO", "WARN", "ERROR", "CRIT")


@dataclass(frozen=True)
class Localizacao:
    posicao: int          # índice (0-based) do símbolo problemático; len(pacote) = fim prematuro
    encontrado: str | None
    esperado: str

    def descrever(self) -> str:
        coluna = self.posicao + 1
        if self.encontrado is None:
            return f"a cadeia terminou na coluna {coluna}; esperado {self.esperado}"
        return (f"coluna {coluna}: símbolo '{formatar_simbolo(self.encontrado)}' inesperado; "
                f"esperado {self.esperado}")


@dataclass(frozen=True)
class Diagnostico:
    er: ExpressaoRegular | None   # ER que o pacote aparentemente tentou seguir
    causa: str
    localizacao: Localizacao | None

    @property
    def mensagem(self) -> str:
        if self.er is None:
            return self.causa
        return f"{self.er.codigo} {self.er.nome}: {self.causa}"


# ---------------------------------------------------------------------- #
# Localização pelo AFNε
# ---------------------------------------------------------------------- #
def _descrever_esperados(simbolos: frozenset[str], podia_terminar: bool) -> str:
    partes = []
    if len(simbolos) == 1:
        partes.append(f"'{formatar_simbolo(next(iter(simbolos)))}'")
    elif simbolos:
        partes.append(f"um símbolo de {formatar_conjunto(simbolos)}")
    if podia_terminar:
        partes.append("o fim do pacote")
    return " ou ".join(partes) if partes else "nenhum símbolo"


def localizar_erro(codigo_er: str, pacote: str) -> Localizacao | None:
    """Simula o AFNε da ER e devolve onde a leitura falhou (None se aceitou)."""
    resultado = AUTOMATOS[codigo_er].simular(pacote)
    if resultado.aceita:
        return None
    pos = resultado.posicao_erro
    encontrado = pacote[pos] if pos < len(pacote) else None
    return Localizacao(pos, encontrado, _descrever_esperados(resultado.esperados, resultado.podia_terminar))


def prefixo_viavel(codigo_er: str, pacote: str) -> int:
    """Quantos símbolos iniciais do pacote ainda são prefixo de alguma cadeia da ER."""
    resultado = AUTOMATOS[codigo_er].simular(pacote)
    return len(pacote) if resultado.aceita else resultado.posicao_erro


# ---------------------------------------------------------------------- #
# Intenção do operador
# ---------------------------------------------------------------------- #
def identificar_intencao(pacote: str) -> str | None:
    """Código da ER que o pacote aparentemente tentou seguir."""
    if re.match(r"[0-9]{2,4}-[0-9]{1,2}-[0-9]{1,2}", pacote) or re.search(r"[0-9]{2}:[0-9]{2}:[0-9]{2}", pacote):
        return "ER-05"
    if pacote[:4].upper() == "CMD ":
        return "ER-03"
    if re.search(r":(TEMP|UMID|PRES)=", pacote, re.IGNORECASE):
        return "ER-02"
    if re.fullmatch(r"[0-9.]+(/[0-9]*)?", pacote) and "." in pacote:
        return "ER-04"
    if re.match(r"(SEN|ATU)[-_]", pacote, re.IGNORECASE):
        return "ER-01"
    # Sem pista clara: escolhe a ER cujo AFNε leu o maior prefixo do pacote
    melhor = max(EXPRESSOES, key=lambda er: prefixo_viavel(er.codigo, pacote))
    return melhor.codigo if prefixo_viavel(melhor.codigo, pacote) >= 3 else None


# ---------------------------------------------------------------------- #
# Causa provável por tipo de pacote
# ---------------------------------------------------------------------- #
def _causa_id(pacote: str) -> str:
    if re.search(r"[a-z]", pacote):
        return "letras minúsculas detectadas; o ID usa apenas maiúsculas (SEN/ATU e modelo)."
    if "_" in pacote or " " in pacote:
        return "separador inválido; os campos do ID são separados por hífen (-)."
    if not re.match(r"(SEN|ATU)-", pacote):
        return "classe do dispositivo inválida; use SEN (sensor) ou ATU (atuador)."
    if re.match(r"(SEN|ATU)-[A-Z]-", pacote):
        return "código do modelo com apenas 1 letra; o mínimo é 2."
    if re.match(r"(SEN|ATU)-[A-Z]{4,}-", pacote):
        return "código do modelo com mais de 3 letras; o máximo é 3."
    if re.match(r"(SEN|ATU)-[A-Z]*[0-9]", pacote):
        return "o código do modelo aceita apenas letras (2 ou 3)."
    if re.fullmatch(r"(SEN|ATU)-[A-Z]{2,3}-[0-9]{5,}", pacote):
        return "número de série com mais de 4 dígitos."
    if re.fullmatch(r"(SEN|ATU)-[A-Z]{2,3}-[0-9]{0,3}", pacote):
        return "número de série com menos de 4 dígitos."
    return "formato geral do ID malformado (esperado SEN|ATU-LL[L]-DDDD)."


# grandeza -> (nome, unidade, mínimo, máximo, faixa por extenso)
GRANDEZAS = {
    "TEMP": ("temperatura", "C", -199.9, 199.9, "-199.9 a 199.9 C"),
    "UMID": ("umidade", "%", 0, 100, "0 a 100%"),
    "PRES": ("pressão", "hPa", 850, 1099, "850 a 1099 hPa"),
}


def _causa_telemetria(pacote: str) -> str:
    if pacote.upper().startswith("ATU-"):
        return "atuadores (ATU) não emitem telemetria; apenas sensores (SEN)."
    if re.search(r":(temp|umid|pres)=", pacote):
        return "o nome da grandeza deve estar em maiúsculas (TEMP, UMID ou PRES)."
    if not re.match(r"SEN-[A-Z]{2,3}-[0-9]{4}:", pacote):
        return "ID do sensor malformado antes do ':'."
    grandeza, _, resto = pacote.split(":", 1)[1].partition("=")
    if grandeza not in GRANDEZAS:
        return "grandeza desconhecida; use TEMP=, UMID= ou PRES= após o ':'."
    return _causa_valor_medido(grandeza, resto)


def _causa_valor_medido(grandeza: str, resto: str) -> str:
    nome, unidade_aceita, minimo, maximo, faixa = GRANDEZAS[grandeza]
    sinal, inteiro, decimal, unidade = re.match(r"(-?)([0-9]*)(\.[0-9]*)?(.*)", resto).groups()
    decimal = decimal or ""

    if not inteiro:
        return f"valor numérico ausente na medição de {nome}."
    if unidade != unidade_aceita and re.search(r"[0-9.]", unidade):
        return f"valor numérico malformado: símbolo '{unidade[0]}' no meio do número."
    if unidade != unidade_aceita:
        return f"unidade '{unidade or '(vazia)'}' inválida para {nome}; a unidade aceita é '{unidade_aceita}'."
    if len(inteiro) > 1 and inteiro.startswith("0"):
        return "zero à esquerda no valor medido não é permitido."
    if sinal and grandeza != "TEMP":
        return f"valor negativo não é admitido para {nome}."
    if grandeza == "PRES" and decimal:
        return "a pressão é registrada como inteiro (sem casas decimais)."
    if len(decimal) > 2:
        return "no máximo uma casa decimal é admitida."
    if decimal == ".":
        return "ponto decimal sem o dígito seguinte."
    texto_valor = f"{sinal}{inteiro}{decimal}"
    if not minimo <= float(texto_valor) <= maximo:
        return f"{nome} {texto_valor} fora da faixa admissível ({faixa})."
    if grandeza == "UMID" and inteiro == "100":
        return "umidade 100 só é aceita como 100 ou 100.0."
    return f"valor de {nome} fora do formato aceito."


def _causa_comando(pacote: str) -> str:
    if not pacote.startswith("CMD "):
        return "o prefixo do comando deve ser 'CMD' em maiúsculas."
    if pacote.startswith("CMD SEN-"):
        return "comandos são direcionados a atuadores (ATU), não a sensores (SEN)."
    if not re.match(r"CMD ATU-[A-Z]{2,3}-[0-9]{4}( |$)", pacote):
        return "ID do atuador malformado após 'CMD'."
    acao = pacote.split(" ", 2)[2] if pacote.count(" ") >= 2 else ""
    if acao.endswith(" ") or "  " in pacote:
        return "espaço extra no comando; os campos são separados por exatamente um espaço."
    if acao.startswith("AJUSTAR"):
        valor = acao[len("AJUSTAR"):].strip()
        if valor in ("", "%"):
            return "valor percentual ausente na instrução AJUSTAR."
        if not valor.endswith("%"):
            return "o valor de AJUSTAR deve terminar com o símbolo %."
        numero = valor[:-1]
        if not numero.isdigit():
            return "o valor de AJUSTAR deve ser um inteiro de 0 a 100."
        if len(numero) > 1 and numero.startswith("0"):
            return "zero à esquerda no valor de AJUSTAR não é permitido."
        return f"valor de ajuste {numero}% acima de 100%; o intervalo aceito é 0 a 100%."
    return "ação não reconhecida; ações válidas: LIGAR, DESLIGAR, ABRIR, FECHAR, AJUSTAR n%."


def _causa_ipv4(pacote: str) -> str:
    endereco, barra, mascara = pacote.partition("/")
    octetos = endereco.split(".")
    if not all(o.isdigit() or o == "" for o in octetos) or (mascara and not mascara.isdigit()):
        return "o endereço aceita apenas dígitos, '.' e uma única '/' antes da máscara."
    if len(octetos) != 4:
        return f"endereço com {len(octetos)} octeto(s); o IPv4 exige exatamente 4."
    if any(o == "" for o in octetos):
        return "octeto vazio entre pontos."
    for o in octetos:
        if len(o) > 1 and o.startswith("0"):
            return f"zero à esquerda no octeto '{o}' não é permitido."
        if int(o) > 255:
            return f"octeto {o} acima de 255; cada octeto vai de 0 a 255."
    if barra and not mascara:
        return "barra '/' presente sem o valor da máscara."
    if barra and len(mascara) > 1 and mascara.startswith("0"):
        return f"zero à esquerda na máscara '/{mascara}' não é permitido."
    if barra and int(mascara) > 32:
        return f"máscara /{mascara} acima de /32; o intervalo válido é /0 a /32."
    return "formato de endereço ou notação CIDR inválido."


def _causa_carimbo_de_tempo(pacote: str) -> str | None:
    """Problema na data/hora do log, ou None se o carimbo estiver correto."""
    data = re.match(r"([0-9]{4})-([0-9]{2})-([0-9]{2})T", pacote)
    if not data:
        return "carimbo de tempo ausente ou fora do formato AAAA-MM-DDThh:mm:ss."
    mes, dia = int(data.group(2)), int(data.group(3))
    if not 1 <= mes <= 12:
        return f"mês {data.group(2)} inválido; meses aceitos: 01 a 12."
    if not 1 <= dia <= 31:
        return f"dia {data.group(3)} inválido; dias aceitos: 01 a 31."
    if (mes == 2 and dia > 29) or (mes in MESES_30_DIAS and dia == 31):
        return (f"o dia {data.group(3)} não existe no mês {data.group(2)} "
                "(fevereiro vai até 29; abril, junho, setembro e novembro até 30).")
    hora = re.match(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T([0-9]{2}):([0-9]{2}):([0-9]{2}) ", pacote)
    if not hora:
        return "horário ausente ou fora do formato hh:mm:ss seguido de espaço."
    if int(hora.group(1)) > 23:
        return f"hora {hora.group(1)} inválida; horas aceitas: 00 a 23."
    if int(hora.group(2)) > 59 or int(hora.group(3)) > 59:
        return "minuto ou segundo acima de 59."
    return None


def _causa_log(pacote: str) -> str:
    causa = _causa_carimbo_de_tempo(pacote)
    if causa:
        return causa
    # Formato: <data>T<hora> <SEVERIDADE> <ID>: <mensagem>
    _, _, resto = pacote.partition(" ")
    severidade, _, corpo = resto.partition(" ")
    if severidade.strip("[]") in SEVERIDADES and severidade != severidade.strip("[]"):
        return f"a severidade é escrita sem colchetes: use {severidade.strip('[]')} em vez de {severidade}."
    if severidade not in SEVERIDADES:
        return (f"nível de severidade '{severidade}' não reconhecido; "
                f"níveis válidos: {', '.join(SEVERIDADES)}.")
    dispositivo, separador, mensagem = corpo.partition(": ")
    if not re.fullmatch(r"(SEN|ATU)-[A-Z]{2,3}-[0-9]{4}", dispositivo.rstrip(":")):
        return "ID do dispositivo ausente ou malformado após a severidade (esperado 'ID: mensagem')."
    if not separador:
        return "mensagem descritiva ausente após o identificador do dispositivo."
    if not mensagem.strip():
        return "mensagem descritiva ausente após o identificador do dispositivo."
    fora = sorted({c for c in mensagem if not re.fullmatch(r"[A-Za-z0-9_. -]", c)})
    if fora:
        return (f"a mensagem contém símbolo(s) fora do alfabeto Σ₅: {' '.join(fora)} "
                "(use letras sem acento, dígitos, '_', '.', '-').")
    if "  " in mensagem or mensagem.startswith(" ") or mensagem.endswith(" "):
        return "as palavras da mensagem devem ser separadas por exatamente um espaço."
    return "registro incompatível com o padrão do log."


_CAUSAS = {
    "ER-01": _causa_id,
    "ER-02": _causa_telemetria,
    "ER-03": _causa_comando,
    "ER-04": _causa_ipv4,
    "ER-05": _causa_log,
}


def diagnosticar(pacote: str) -> Diagnostico:
    """Explica por que um pacote (já rejeitado pelas cinco ERs) é inválido."""
    if not pacote:
        return Diagnostico(None, "Falha estrutural: pacote vazio recebido.", None)
    codigo = identificar_intencao(pacote)
    if codigo is None:
        return Diagnostico(
            None,
            "Falha estrutural: o pacote não corresponde a nenhum dos cinco padrões léxicos conhecidos.",
            None,
        )
    er = POR_CODIGO[codigo]
    return Diagnostico(er, _CAUSAS[codigo](pacote), localizar_erro(codigo, pacote))
