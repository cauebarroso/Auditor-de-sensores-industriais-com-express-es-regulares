"""
Processamento em lote, extração de campos e relatório de conformidade.

Depois que um pacote é aceito por uma ER, a sua estrutura está garantida;
por isso os campos (dispositivo, grandeza, valor, ação, severidade...) podem
ser extraídos com operações simples de texto sobre a cadeia validada.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from diagnostico import Diagnostico, diagnosticar
from expressoes import EXPRESSOES, classificar

CATEGORIAS = [er.categoria for er in EXPRESSOES]
GRANDEZAS = {"TEMP": ("Temperatura", "C"), "UMID": ("Umidade", "%"), "PRES": ("Pressão", "hPa")}


@dataclass
class Pacote:
    linha: int                 # número da linha no arquivo (1 = primeira)
    texto: str
    categoria: str | None      # None = corrompido
    campos: dict = field(default_factory=dict)
    diagnostico: Diagnostico | None = None

    @property
    def valido(self) -> bool:
        return self.categoria is not None


# ---------------------------------------------------------------------- #
# Validação e extração
# ---------------------------------------------------------------------- #
def extrair_campos(categoria: str, pacote: str) -> dict:
    """Separa os campos de um pacote JÁ VALIDADO pela ER da categoria."""
    if categoria == "ID_DISPOSITIVO":
        return {"dispositivo": pacote, "classe": pacote[:3]}
    if categoria == "TELEMETRIA":
        dispositivo, medida = pacote.split(":")
        grandeza, leitura = medida.split("=")
        unidade = GRANDEZAS[grandeza][1]
        return {"dispositivo": dispositivo, "grandeza": grandeza,
                "valor": float(leitura[: -len(unidade)]), "unidade": unidade}
    if categoria == "COMANDO":
        partes = pacote.split(" ")
        campos = {"dispositivo": partes[1], "acao": partes[2]}
        if partes[2] == "AJUSTAR":
            campos["percentual"] = int(partes[3][:-1])
        return campos
    if categoria == "IPV4_CIDR":
        endereco, _, mascara = pacote.partition("/")
        return {"endereco": endereco, "mascara": int(mascara) if mascara else None}
    if categoria == "ALERTA_LOG":
        carimbo, severidade, resto = pacote.split(" ", 2)
        dispositivo, mensagem = resto.split(": ", 1)
        return {"data_hora": carimbo, "severidade": severidade.strip("[]"),
                "dispositivo": dispositivo, "mensagem": mensagem}
    raise ValueError(f"categoria desconhecida: {categoria}")


def analisar_pacote(texto: str, linha: int = 0) -> Pacote:
    er = classificar(texto)
    if er is None:
        return Pacote(linha, texto, None, diagnostico=diagnosticar(texto))
    return Pacote(linha, texto, er.categoria, extrair_campos(er.categoria, texto))


def ler_pacotes(caminho: str | Path) -> list[Pacote]:
    """Lê um arquivo texto (UTF-8), um pacote por linha.

    Linhas em branco e linhas iniciadas por '#' (comentários) são ignoradas;
    espaços nas extremidades de cada linha são removidos antes da validação.
    Lança FileNotFoundError, IsADirectoryError, PermissionError ou
    UnicodeDecodeError para o chamador tratar com mensagem amigável.
    """
    caminho = Path(caminho)
    if caminho.is_dir():
        raise IsADirectoryError(str(caminho))
    pacotes = []
    with open(caminho, "r", encoding="utf-8-sig") as arquivo:
        for numero, linha in enumerate(arquivo, start=1):
            texto = linha.strip()
            if not texto or texto.startswith("#"):
                continue
            pacotes.append(analisar_pacote(texto, numero))
    return pacotes


# ---------------------------------------------------------------------- #
# Relatório
# ---------------------------------------------------------------------- #
def resumir(pacotes: list[Pacote]) -> dict:
    """Estatísticas de conformidade e informações extraídas dos pacotes válidos."""
    validos = [p for p in pacotes if p.valido]
    por_categoria = Counter(p.categoria for p in validos)

    dispositivos = Counter(p.campos["dispositivo"] for p in validos if "dispositivo" in p.campos)

    leituras = defaultdict(list)
    for p in validos:
        if p.categoria == "TELEMETRIA":
            leituras[p.campos["grandeza"]].append(p.campos["valor"])
    telemetria = {
        grandeza: {
            "nome": GRANDEZAS[grandeza][0],
            "unidade": GRANDEZAS[grandeza][1],
            "leituras": len(valores),
            "minimo": min(valores),
            "maximo": max(valores),
            "media": round(sum(valores) / len(valores), 2),
        }
        for grandeza, valores in sorted(leituras.items())
    }

    total = len(pacotes)
    return {
        "total": total,
        "integros": len(validos),
        "corrompidos": total - len(validos),
        "conformidade_percentual": round(100 * len(validos) / total, 1) if total else 0.0,
        "por_categoria": {c: por_categoria.get(c, 0) for c in CATEGORIAS},
        "dispositivos": dict(sorted(dispositivos.items())),
        "telemetria": telemetria,
        "comandos": dict(Counter(p.campos["acao"] for p in validos if p.categoria == "COMANDO")),
        "alertas": dict(Counter(p.campos["severidade"] for p in validos if p.categoria == "ALERTA_LOG")),
        "rotas": [p.texto for p in validos if p.categoria == "IPV4_CIDR"],
    }


def formatar_relatorio(pacotes: list[Pacote], origem: str = "") -> str:
    r = resumir(pacotes)
    linhas = [
        "+" + "=" * 62 + "+",
        "|" + "RELATÓRIO DE CONFORMIDADE LÉXICA".center(62) + "|",
        "+" + "-" * 62 + "+",
    ]
    if origem:
        linhas.append(f"|  Arquivo: {origem[-50:]:<51}|")
    linhas += [
        f"|  Pacotes lidos:            {r['total']:>33} |",
        f"|  Pacotes íntegros:         {r['integros']:>33} |",
        f"|  Pacotes corrompidos:      {r['corrompidos']:>33} |",
        f"|  Taxa de conformidade:     {r['conformidade_percentual']:>32}% |",
        "+" + "-" * 62 + "+",
        "|  Pacotes íntegros por categoria (ER):" + " " * 24 + "|",
    ]
    for er in EXPRESSOES:
        rotulo = f"{er.codigo} {er.categoria}"
        linhas.append(f"|    {rotulo:<40} {r['por_categoria'][er.categoria]:>16} |")
    linhas.append("+" + "=" * 62 + "+")

    if r["telemetria"]:
        linhas.append("\n  Telemetria (valores extraídos dos pacotes válidos):")
        for g in r["telemetria"].values():
            linhas.append(
                f"    {g['nome']:<12} {g['leituras']:>3} leitura(s)  "
                f"mín {g['minimo']:g} {g['unidade']}  máx {g['maximo']:g} {g['unidade']}  "
                f"média {g['media']:g} {g['unidade']}"
            )
    if r["comandos"]:
        acoes = ", ".join(f"{acao} ×{n}" for acao, n in r["comandos"].items())
        linhas.append(f"\n  Comandos enviados a atuadores: {acoes}")
    if r["alertas"]:
        alertas = ", ".join(f"{sev} ×{n}" for sev, n in r["alertas"].items())
        linhas.append(f"  Alertas por severidade: {alertas}")
    if r["rotas"]:
        linhas.append(f"  Rotas/endereços de rede: {', '.join(r['rotas'])}")
    if r["dispositivos"]:
        linhas.append(f"  Dispositivos identificados ({len(r['dispositivos'])}): "
                      + ", ".join(r["dispositivos"]))

    corrompidos = [p for p in pacotes if not p.valido]
    if corrompidos:
        linhas.append("\n  Pacotes corrompidos (linha: diagnóstico):")
        for p in corrompidos:
            linhas.append(f"    L{p.linha}: {p.texto}")
            linhas.append(f"         -> {p.diagnostico.mensagem}")
    return "\n".join(linhas)


def exportar(pacotes: list[Pacote], destino: str | Path) -> Path:
    """Exporta o relatório. O formato é escolhido pela extensão:
    .json (resumo + pacotes), .csv (um pacote por linha) ou .txt (texto do relatório)."""
    destino = Path(destino)
    extensao = destino.suffix.lower()
    if extensao not in (".json", ".csv", ".txt"):
        raise ValueError("formato não suportado; use .json, .csv ou .txt")
    destino.parent.mkdir(parents=True, exist_ok=True)

    if extensao == ".txt":
        destino.write_text(formatar_relatorio(pacotes) + "\n", encoding="utf-8")
    elif extensao == ".csv":
        with open(destino, "w", encoding="utf-8-sig", newline="") as arquivo:
            escritor = csv.writer(arquivo, delimiter=";")
            escritor.writerow(["linha", "pacote", "status", "categoria", "diagnostico"])
            for p in pacotes:
                escritor.writerow([
                    p.linha, p.texto, "INTEGRO" if p.valido else "CORROMPIDO",
                    p.categoria or "", p.diagnostico.mensagem if p.diagnostico else "",
                ])
    else:
        dados = {
            "resumo": resumir(pacotes),
            "pacotes": [
                {
                    "linha": p.linha,
                    "pacote": p.texto,
                    "valido": p.valido,
                    "categoria": p.categoria,
                    "campos": p.campos,
                    "diagnostico": p.diagnostico.mensagem if p.diagnostico else None,
                }
                for p in pacotes
            ],
        }
        destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino
