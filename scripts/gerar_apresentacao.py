"""
Gera a apresentação em dois formatos a partir da mesma descrição de slides:

  docs/Apresentacao.pptx  editável (PowerPoint / Google Slides), com o roteiro
                          de fala nas anotações de cada slide
  docs/Apresentacao.pdf   impressa pelo Microsoft Edge / Google Chrome

Requer: python-pptx, Pillow e markdown (pip install python-pptx pillow markdown).
Uso (na raiz do repositório):
  python scripts/gerar_apresentacao.py
"""

from __future__ import annotations

import html
import sys
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

RAIZ = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(RAIZ / "src"), str(RAIZ / "tests"), str(RAIZ / "scripts")]

from casos_teste import CASOS  # noqa: E402
from conteudo_fichas import LINGUAGEM_CURTA, OPERADORES  # noqa: E402
from diagnostico import AUTOMATOS  # noqa: E402
from expressoes import POR_CODIGO  # noqa: E402
import auditor  # noqa: E402
from gerar_relatorio import capturar, exibir_cadeia, resultados_pytest  # noqa: E402
from pdf import html_para_pdf  # noqa: E402

LARGURA, ALTURA = 13.333, 7.5
AZUL, AZUL_CLARO, CINZA, VERDE, VERMELHO = "1F3A5F", "EEF3F9", "5B6573", "1D6B3F", "B03A2E"
FONTE, FONTE_CODIGO = "Segoe UI", "Consolas"
DIAGRAMAS = RAIZ / "automatos" / "diagramas"


# ---------------------------------------------------------------------- #
# Descrição dos slides
# ---------------------------------------------------------------------- #
@dataclass
class Texto:
    x: float
    y: float
    w: float
    h: float
    linhas: list[str]          # "• " no início vira marcador; "**" no início = negrito
    tamanho: int = 18
    cor: str = "1B1F24"
    alinhamento: str = "esquerda"
    codigo: bool = False
    fundo: str | None = None


@dataclass
class Imagem:
    x: float
    y: float
    w: float
    h: float
    caminho: Path


@dataclass
class Tabela:
    x: float
    y: float
    w: float
    linhas: list[list[str]]    # a primeira linha é o cabeçalho
    larguras: list[float]
    tamanho: int = 13
    altura_linha: float = 0.36
    codigo_colunas: tuple[int, ...] = ()


@dataclass
class Slide:
    titulo: str
    elementos: list = field(default_factory=list)
    notas: str = ""
    capa: bool = False


@dataclass
class Medidas:
    """Medidas da coluna esquerda do slide de uma ER (dependem do tamanho da ER formal)."""
    altura_formal: float
    altura_codigo: float
    fonte_formal: int = 12
    fonte_codigo: int = 11
    linha_tabela: float = 0.27


MEDIDAS = {
    "ER-01": Medidas(0.45, 0.32),
    "ER-02": Medidas(1.4, 0.75),
    "ER-03": Medidas(0.95, 0.55),
    "ER-04": Medidas(0.8, 0.55),
    "ER-05": Medidas(1.85, 0.85, fonte_formal=11, fonte_codigo=10, linha_tabela=0.25),
}


def slide_er(codigo: str, resumo: str, notas: str, imagem: Path | None = None) -> Slide:
    """Ficha completa de uma ER em um slide: finalidade, linguagem, alfabeto,
    ER formal, padrão do código, operadores e 6 + 6 cadeias de teste.
    A ER-01 é pequena e também recebe o AFNε no rodapé."""
    er = POR_CODIGO[codigo]
    afn = AUTOMATOS[codigo]
    m = MEDIDAS[codigo]

    y_rotulo_codigo = 2.23 + m.altura_formal + 0.08
    y_codigo = y_rotulo_codigo + 0.28
    y_operadores = y_codigo + m.altura_codigo + 0.12
    operadores = [["No código", "Na ER formal", "Operador"], *[list(linha) for linha in OPERADORES[codigo]]]

    aceitas = [c for c in CASOS[codigo] if c.aceita][:6]
    rejeitadas = [c for c in CASOS[codigo] if not c.aceita][:6]
    testes = [["", "Cadeia (★ = caso-limite)"]]
    testes += [["✔", exibir_cadeia(c.cadeia) + (" ★" if c.limite else "")] for c in aceitas]
    testes += [["✘", exibir_cadeia(c.cadeia) + (" ★" if c.limite else "")] for c in rejeitadas]
    longo = max(len(c.cadeia) for c in aceitas + rejeitadas) > 45
    linha_testes = 0.25 if imagem else 0.29

    elementos = [
        Texto(0.5, 0.95, 12.3, 0.32, [resumo], 14, CINZA),
        Texto(0.5, 1.27, 12.3, 0.3, [LINGUAGEM_CURTA[codigo]], 13),
        Texto(0.5, 1.57, 12.3, 0.3, [er.alfabeto], 13, AZUL),
        Texto(0.5, 1.95, 3.0, 0.28, ["ER formal"], 12, AZUL),
        Texto(0.5, 2.23, 6.45, m.altura_formal, er.formal_completa(), m.fonte_formal, codigo=True, fundo=AZUL_CLARO),
        Texto(0.5, y_rotulo_codigo, 3.5, 0.28, ["No código (re.fullmatch)"], 12, AZUL),
        Texto(0.5, y_codigo, 6.45, m.altura_codigo, [f'r"{er.padrao}"'], m.fonte_codigo, codigo=True, fundo=AZUL_CLARO),
        Tabela(0.5, y_operadores, 6.45, operadores, [2.45, 2.3, 1.7], 11, m.linha_tabela, codigo_colunas=(0, 1)),
        Texto(7.15, 1.95, 5.7, 0.28, ["Testes: 6 aceitas e 6 rejeitadas (as 16 estão no relatório)"], 12, AZUL),
        Tabela(7.15, 2.23, 5.7, testes, [0.4, 5.3], 10 if longo else 12, linha_testes, codigo_colunas=(1,)),
        Texto(10.3, 0.35, 2.6, 0.4, [f"AFNε: {afn.n_estados} estados · {afn.total_movimentos_vazios()} ε"],
              12, "FFFFFF", "direita"),
    ]
    if imagem is not None:
        elementos.append(Imagem(0.5, 5.6, 12.35, 1.45, imagem))
    return Slide(f"{codigo} — {er.nome}", elementos, notas)


def saida_demonstracao() -> list[str]:
    """Saída REAL do programa para os comandos mostrados no slide."""
    erro = capturar(auditor.main, ["--pacote", "CMD ATU-VLV-0201 AJUSTAR 120%"]).splitlines()
    erro = [linha for linha in erro if linha.strip() and "Pacote:" not in linha]
    traco = [linha for linha in capturar(auditor.explicar_afn, "ATU-VLV-0420", "ER-01").splitlines() if linha.strip()]
    inicio = next(i for i, linha in enumerate(traco) if "passo" in linha)
    passos = traco[inicio:inicio + 4] + ["      ⋮"] + [traco[inicio + 13], traco[inicio + 14].strip()]
    return [*erro, "", *passos]


def slide_verificacao() -> Slide:
    """Consistência entre as representações e resultados reais dos testes."""
    resumo, por_arquivo = resultados_pytest()
    return Slide("Mesma linguagem em todas as representações", [
        Texto(0.5, 1.1, 6.4, 5.7, [
            "**1. Código → AFNε (construção de Thompson)",
            "O AFNε é construído a partir do padrão exato do código e exportado para o JFLAP.",
            "**2. ER formal ≡ código: prova",
            "Busca em largura sobre o produto dos dois AFNε (construção de subconjuntos): nenhuma cadeia "
            "distingue as linguagens.",
            "**3. Arquivo .jff ≡ código: prova",
            "O .jff é lido de volta e comparado pelo mesmo algoritmo.",
            "**4. Executado no próprio JFLAP 7.1",
            "Cada .jff rodou no motor do JFLAP com as 16 cadeias da sua ER.",
        ], 15),
        Tabela(7.2, 1.2, 5.65, [
            ["Verificação", "Resultado"],
            ["python -m pytest", f"{sum(por_arquivo.values())} testes ✔"],
            ["ER formal ≡ código", "5/5 provadas"],
            [".jff ≡ código", "5/5 provadas"],
            ["JFLAP 7.1 (16 cadeias por ER)", "80/80"],
            ["AFNε × re, cadeias aleatórias", "10.000, 0 divergências"],
            ["Linguagens disjuntas", "interseções vazias"],
            ["Dados de exemplo", "20 íntegros, 14 corrompidos"],
        ], [3.05, 2.6], 13, 0.42),
        Texto(7.2, 4.75, 5.65, 1.05, [
            "Achados no JFLAP 7.1: rótulos com '[' viram intervalo (por isso INFO, não [INFO]) e, após um "
            "rótulo de intervalo como [A-Z], o simulador não aplica o fecho-ε (por isso uma transição por símbolo)."],
            12, CINZA, fundo=AZUL_CLARO),
    ], f"Caue (~1 min). Esta é a regra central do guia. Não comparamos só exemplos: o algoritmo percorre todos "
       f"os pares de estados alcançáveis, então é uma prova de equivalência. Resultado atual do pytest: {resumo}.")


def slides() -> list[Slide]:
    return [
        Slide("", [
            Texto(0.8, 1.7, 11.7, 1.4, ["Auditor Léxico de Telemetria", "de Sensores Industriais"], 40, "FFFFFF"),
            Texto(0.8, 3.25, 11.7, 0.6, ["Um firewall léxico construído com Expressões Regulares e AFNε"], 22, "D6E2F0"),
            Texto(0.8, 4.6, 11.7, 0.5, ["Linguagens Formais e Autômatos · Trabalho do 1º Bimestre · CESUPA"], 16, "D6E2F0"),
            Texto(0.8, 5.1, 11.7, 0.5, ["Augusto Rodrigues  ·  Caue Jadão  ·  César Augusto"], 18, "FFFFFF"),
            Texto(0.8, 6.4, 11.7, 0.4, ["github.com/cauebarroso/Auditor-de-sensores-industriais-com-express-es-regulares"], 13, "AFC3DB"),
        ], "Augusto (~15 s). Apresentar a equipe e o tema em uma frase: um firewall que só deixa passar pacotes "
           "de sensores e atuadores que pertencem à linguagem de uma das cinco ERs.", capa=True),

        Slide("Problema, solução, entradas e saídas", [
            Texto(0.5, 1.1, 6.4, 3.6, [
                "• Sensores e atuadores conversam com o supervisório (SCADA/IIoT) por pacotes de texto.",
                "• Um único símbolo errado vira leitura falsa ou ordem perigosa: TEMP=1O4.7C, AJUSTAR 120%, 2026-09-31.",
                "• Solução: um firewall léxico. O pacote só passa se pertencer à linguagem de uma das cinco ERs.",
                "• Pacotes bloqueados recebem a causa e a coluna exata do erro, obtida simulando o AFNε.",
            ], 17),
            Texto(0.5, 4.85, 6.4, 1.9, [
                "**Código em módulos",
                "expressoes · afn · construtor_afn · diagnostico · relatorio · auditor",
                "Python 3.11+, só biblioteca padrão; testes com pytest.",
            ], 14),
            Texto(7.2, 1.1, 5.65, 1.75, ["**Entradas", "• Pacote digitado (modo interativo) ou --pacote",
                                        "• Arquivo .txt em lote (comentários # e linhas vazias ignorados)"],
                  14, fundo=AZUL_CLARO),
            Texto(7.2, 3.0, 5.65, 1.75, ["**Processamento", "• re.fullmatch nas 5 ERs (linguagens disjuntas)",
                                        "• Extrai campos dos válidos e diagnostica os inválidos"],
                  14, fundo=AZUL_CLARO),
            Texto(7.2, 4.9, 5.65, 1.85, ["**Saídas", "• [OK] / [ERRO] com a coluna do erro",
                                        "• Relatório de conformidade, filtros e exportação JSON/CSV/TXT",
                                        "• Entradas vazias ou inválidas: mensagem clara, sem travar"],
                  14, fundo=AZUL_CLARO),
        ], "Augusto (~1 min). Contextualizar o problema e mostrar entradas, processamento e saídas. Destacar o "
           "tratamento de entradas vazias e inválidas e a organização em módulos."),

        Slide("Notação formal × sintaxe no código", [
            Tabela(0.5, 1.15, 12.35, [
                ["Notação formal", "No Python", "Significado"],
                ["r s", "rs", "Concatenação"],
                ["r | s", "r|s", "União"],
                ["r*", "r*", "Fecho de Kleene (zero ou mais)"],
                ["r r*", "r+", "Fecho positivo (uma ou mais)"],
                ["(r | ε)", "r?", "Opcionalidade"],
                ["r r r r", "r{4}", "Repetição exata"],
                ["r r (r | ε)", "r{2,3}", "Repetição limitada = rr | rrr"],
                ["[0-9]", "[0-9]", "Classe finita: (0 | 1 | … | 9)"],
                ["⎵   e   .", "' '   e   \\.", "Espaço e ponto literais (o ponto do Python precisa de escape)"],
                ["⟨NOME⟩ = r", "—", "Definição regular: só um nome para a subexpressão"],
            ], [3.2, 2.6, 6.55], 15, 0.42, codigo_colunas=(0, 1)),
            Texto(0.5, 6.0, 12.35, 0.9, [
                "Sempre re.fullmatch (dispensa ^ e $). Proibidos e rejeitados pelo nosso analisador: "
                "\\d \\w \\s, ponto curinga, classes negadas, retroreferências e lookarounds."], 15, CINZA),
        ], "Augusto (~40 s). A ER formal e o código são duas escritas da mesma linguagem; os atalhos do Python "
           "(+, ?, {m,n}) são derivados dos operadores básicos. O próprio programa rejeita recursos não regulares."),

        slide_er("ER-01", "Identificador de um sensor (SEN) ou atuador (ATU); bloco reutilizado nas ERs 02, 03 e 05.",
                 "Augusto (~1 min). Ficha: ER formal com ⟨ID⟩; {2,3} é rr(r | ε) e {4} é a concatenação de 4 cópias. "
                 "No AFNε (rodapé): a união SEN | ATU abre dois ramos por ε; o desvio ε entre q12 e q13 é a terceira "
                 "letra opcional. Casos-limite: 0000, 9999, 5 dígitos, ε.", DIAGRAMAS / "ER-01.png"),

        slide_er("ER-02", "Leitura de um sensor: temperatura (C), umidade (%) ou pressão (hPa), dentro da faixa.",
                 "Augusto (~45 s). Três ramos na união, um por grandeza. ([1-9] | ε)[0-9] impede zero à esquerda; "
                 "o escape \\. torna o ponto literal. Casos-limite: extremos de cada faixa (−199.9 e 199.9 C, "
                 "100.0%, 850 hPa; 200C, 100.5%, 849 e 1100 hPa rejeitados)."),
        Slide("ER-02 — AFNε: o ID do sensor e a união das três medições", [
            Imagem(0.5, 1.05, 12.3, 1.3, DIAGRAMAS / "partes" / "ER-02_p1.png"),
            Imagem(0.5, 2.4, 12.3, 4.55, DIAGRAMAS / "partes" / "ER-02_p2.png"),
        ], "Augusto (~30 s). Parte 1: o ID do sensor. Parte 2: três movimentos ε abrem os ramos TEMP, UMID e PRES. "
           "No ramo TEMP, o desvio ε paralelo ao '-' é o sinal opcional (- | ε)."),

        slide_er("ER-03", "Ordem para um atuador: ligar, desligar, abrir, fechar ou ajustar de 0 a 100%.",
                 "Caue (~45 s). Cinco ações por união; o espaço é símbolo do alfabeto (⎵), por isso não usamos \\s. "
                 "⟨PCT⟩ = 100 | ([1-9] | ε)[0-9] cobre 0 a 100. Casos-limite: 0% e 100% aceitos, 101% e espaço extra "
                 "no final rejeitados."),
        Slide("ER-03 — AFNε: o ID do atuador e as cinco ações", [
            Imagem(0.5, 1.05, 12.3, 1.5, DIAGRAMAS / "partes" / "ER-03_p1.png"),
            Imagem(0.5, 2.7, 12.3, 4.25, DIAGRAMAS / "partes" / "ER-03_p2.png"),
        ], "Caue (~30 s). A partir de q17, cinco movimentos ε abrem os ramos das ações. No ramo AJUSTAR, a união "
           "100 | ([1-9] | ε)[0-9] aparece como dois ramos, com o desvio ε do dígito opcional."),

        slide_er("ER-04", "Endereço IPv4 com octetos de 0 a 255, sem zero à esquerda, e máscara CIDR opcional.",
                 "Caue (~45 s). O octeto é dividido em faixas disjuntas (250–255, 200–249, 100–199, 0–99), construção "
                 "clássica citada no relatório; a máscara CIDR e a proibição de zeros à esquerda completam a ER. "
                 "Casos-limite: 0.0.0.0, 255.255.255.255, /0 e /32 aceitos; 256 e /33 rejeitados."),
        Slide("ER-04 — AFNε: quatro octetos e a máscara opcional", [
            Imagem(0.5, 1.0, 12.3, 2.0, DIAGRAMAS / "partes" / "ER-04_p1.png"),
            Imagem(0.5, 3.05, 12.3, 2.0, DIAGRAMAS / "partes" / "ER-04_p2.png"),
            Imagem(0.5, 5.1, 12.3, 1.85, DIAGRAMAS / "partes" / "ER-04_p3.png"),
        ], "Caue (~30 s). Cada ⟨OCT⟩ abre 4 ramos por ε e os fecha antes do ponto. Na parte 3, o desvio ε de q67 "
           "para o final é a máscara opcional (/⟨MASC⟩ | ε)."),

        slide_er("ER-05", "Registro de evento: data válida, hora, severidade, dispositivo e mensagem.",
                 "César (~45 s). Definições regulares: ⟨DATA⟩, ⟨HORA⟩, ⟨SEV⟩, ⟨ID⟩ (reuso da ER-01) e ⟨MSG⟩. "
                 "Casos-limite de data: 29/02, 30/04 e 31/07 aceitos; 30/02, 31/04, mês 13 e hora 24 rejeitados."),
        Slide("ER-05 — AFNε: a data e a mensagem", [
            Imagem(0.5, 0.95, 12.3, 2.95, DIAGRAMAS / "partes" / "ER-05_p1.png"),
            Imagem(0.5, 3.95, 12.3, 2.45, DIAGRAMAS / "partes" / "ER-05_p4.png"),
            Texto(0.5, 6.45, 12.35, 0.6, [
                "Parte 1: dia válido para cada mês (união de 3 casos). Parte 4: fecho de Kleene — laço interno de ⟨PAL⟩ "
                "(q104 ↔ q106) e externo (⎵⟨PAL⟩)* (q112 → q107), por isso L₅ é infinita. As partes 2 e 3 (hora, "
                "severidade e ID) estão no relatório."], 12, CINZA),
        ], "César (~1 min). A data aceita o dia certo de cada mês: validar dia por mês É regular, porque o conjunto "
           "de datas é finito. Na mensagem, os dois laços do fecho de Kleene tornam L₅ a única linguagem infinita."),

        slide_verificacao(),

        Slide("Demonstração", [
            Texto(0.5, 1.05, 12.35, 1.45, [
                "python src/auditor.py dados/turno_caldeira.txt          # lote + relatório + filtros",
                'python src/auditor.py --pacote "CMD ATU-VLV-0201 AJUSTAR 120%"',
                'python src/auditor.py --explicar "ATU-VLV-0420"            # simulação do AFNε',
                "JFLAP: automatos/jflap/ER-03.jff → Input › Multiple Run → Load Inputs (entradas/ER-03.txt)",
            ], 14, codigo=True, fundo=AZUL_CLARO),
            Texto(0.5, 2.75, 12.35, 4.2, saida_demonstracao(), 13, codigo=True),
        ], "César (~1 min 30 s). Rodar ao vivo: lote com o turno da caldeira, um pacote rejeitado com o apontador "
           "de coluna e a simulação passo a passo (uma cadeia aceita e uma rejeitada). Se o professor pedir uma "
           "cadeia nova, usar --pacote ou o modo interativo (opção 2)."),

        Slide("Limitações, contribuições e uso de IA", [
            Texto(0.5, 1.05, 6.1, 2.6, [
                "**Limitações (falsos resultados)",
                "• Validação léxica: um ID bem formado passa mesmo se o dispositivo não existir.",
                "• −0C é aceito; uma leitura real acima de 199.9 °C é bloqueada; 29/02 vale em qualquer ano.",
            ], 15),
            Texto(6.85, 1.05, 6.0, 2.6, [
                "**Melhorias",
                "• Ano bissexto (também é regular, mas o AFNε cresceria muito).",
                "• Faixas configuráveis por sensor; leitura contínua de porta serial.",
            ], 15),
            Tabela(0.5, 3.0, 12.35, [
                ["Integrante", "Contribuições"],
                ["Augusto Rodrigues", "ER-01 e ER-02 (fichas, AFNε, testes); diagnóstico de falhas"],
                ["Caue Jadão", "ER-03 e ER-04; revisão geral, verificação de equivalência, relatório e repositório"],
                ["César Augusto", "ER-05; modo lote, relatório de conformidade, exportação e apresentação"],
            ], [3.0, 9.35], 14, 0.42),
            Texto(0.5, 4.95, 12.35, 1.8, [
                "**Uso de IA (declarado no relatório e no README)",
                "Antigravity: versão inicial do código, dos testes e dos primeiros .jff. Claude (Anthropic): revisão das "
                "ERs e da notação formal, construção de Thompson, verificação de equivalência, testes, relatório e slides. "
                "As decisões de projeto são da equipe; todos compreendem, explicam e modificam o conteúdo.",
            ], 15),
        ], "Todos (~1 min). Cada integrante diz em uma frase o que fez. Encerrar abrindo para perguntas, com o "
           "terminal no modo interativo para testar cadeias pedidas pelo professor."),
    ]


# ---------------------------------------------------------------------- #
# Renderização PPTX
# ---------------------------------------------------------------------- #
def _cor(hexa: str) -> RGBColor:
    return RGBColor.from_string(hexa)


def _texto_pptx(slide, el: Texto) -> None:
    caixa = slide.shapes.add_textbox(Inches(el.x), Inches(el.y), Inches(el.w), Inches(el.h))
    if el.fundo:
        caixa.fill.solid()
        caixa.fill.fore_color.rgb = _cor(el.fundo)
    quadro = caixa.text_frame
    quadro.word_wrap = True
    quadro.vertical_anchor = MSO_ANCHOR.TOP
    margem = Inches(0.12 if el.fundo else 0.04)
    quadro.margin_left = quadro.margin_right = margem
    quadro.margin_top = quadro.margin_bottom = Inches(0.08 if el.fundo else 0.02)
    for i, linha in enumerate(el.linhas):
        p = quadro.paragraphs[0] if i == 0 else quadro.add_paragraph()
        negrito = linha.startswith("**")
        p.text = linha[2:] if negrito else linha
        p.alignment = {"esquerda": PP_ALIGN.LEFT, "direita": PP_ALIGN.RIGHT, "centro": PP_ALIGN.CENTER}[el.alinhamento]
        if negrito and i > 0:
            p.space_before = Pt(10)
        elif not el.codigo:
            p.space_after = Pt(4)
        for run in p.runs:
            run.font.size = Pt(el.tamanho + (1 if negrito else 0))
            run.font.bold = negrito
            run.font.name = FONTE_CODIGO if el.codigo else FONTE
            run.font.color.rgb = _cor(AZUL if negrito else el.cor)


def _imagem_pptx(slide, el: Imagem) -> None:
    largura, altura = Image.open(el.caminho).size
    escala = min(el.w / largura, el.h / altura)
    w, h = largura * escala, altura * escala
    slide.shapes.add_picture(str(el.caminho), Inches(el.x + (el.w - w) / 2), Inches(el.y + (el.h - h) / 2),
                             Inches(w), Inches(h))


def _tabela_pptx(slide, el: Tabela) -> None:
    forma = slide.shapes.add_table(len(el.linhas), len(el.larguras), Inches(el.x), Inches(el.y),
                                   Inches(sum(el.larguras)), Inches(el.altura_linha * len(el.linhas)))
    tabela = forma.table
    for j, largura in enumerate(el.larguras):
        tabela.columns[j].width = Inches(largura)
    for i, linha in enumerate(el.linhas):
        tabela.rows[i].height = Inches(el.altura_linha)
        for j, valor in enumerate(linha):
            celula = tabela.cell(i, j)
            celula.text = valor
            celula.margin_left = celula.margin_right = Inches(0.08)
            celula.margin_top = celula.margin_bottom = Inches(0.01 if el.altura_linha < 0.3 else 0.03)
            celula.vertical_anchor = MSO_ANCHOR.MIDDLE
            celula.fill.solid()
            celula.fill.fore_color.rgb = _cor(AZUL if i == 0 else ("F7F9FC" if i % 2 else "FFFFFF"))
            for run in celula.text_frame.paragraphs[0].runs:
                run.font.size = Pt(el.tamanho)
                run.font.bold = i == 0
                run.font.name = FONTE_CODIGO if (i > 0 and j in el.codigo_colunas) else FONTE
                run.font.color.rgb = _cor("FFFFFF" if i == 0 else "1B1F24")


def gerar_pptx(lista: list[Slide], destino: Path) -> None:
    apresentacao = Presentation()
    apresentacao.slide_width, apresentacao.slide_height = Inches(LARGURA), Inches(ALTURA)
    vazio = apresentacao.slide_layouts[6]
    for numero, s in enumerate(lista, start=1):
        slide = apresentacao.slides.add_slide(vazio)
        fundo = slide.background.fill
        fundo.solid()
        fundo.fore_color.rgb = _cor(AZUL if s.capa else "FFFFFF")
        if not s.capa:
            faixa = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(LARGURA), Inches(0.85))
            faixa.fill.solid()
            faixa.fill.fore_color.rgb = _cor(AZUL)
            faixa.line.fill.background()
            _texto_pptx(slide, Texto(0.45, 0.14, 10.0, 0.6, [s.titulo], 26, "FFFFFF"))
            _texto_pptx(slide, Texto(11.9, 7.05, 1.0, 0.3, [f"{numero}/{len(lista)}"], 11, CINZA, "direita"))
        for el in s.elementos:
            {Texto: _texto_pptx, Imagem: _imagem_pptx, Tabela: _tabela_pptx}[type(el)](slide, el)
        if s.notas:
            slide.notes_slide.notes_text_frame.text = s.notas
    apresentacao.save(destino)


# ---------------------------------------------------------------------- #
# Renderização HTML -> PDF
# ---------------------------------------------------------------------- #
def _caixa(el, conteudo: str, extra: str = "") -> str:
    return (f'<div style="position:absolute;left:{el.x}in;top:{el.y}in;width:{el.w}in;'
            f'{f"height:{el.h}in;" if hasattr(el, "h") else ""}{extra}">{conteudo}</div>')


def _texto_html(el: Texto) -> str:
    paragrafos = []
    for i, linha in enumerate(el.linhas):
        negrito = linha.startswith("**")
        texto = html.escape(linha[2:] if negrito else linha) or "&nbsp;"
        estilo = (f"font-weight:700;color:#{AZUL};font-size:{el.tamanho + 1}pt;"
                  f"{'margin-top:10pt;' if i else ''}") if negrito else ""
        paragrafos.append(f'<p style="margin:0 0 {0 if el.codigo else 4}pt;{estilo}">{texto}</p>')
    fonte = f"'{FONTE_CODIGO}',monospace;white-space:pre-wrap" if el.codigo else f"'{FONTE}',sans-serif"
    alinhamento = {"esquerda": "left", "direita": "right", "centro": "center"}[el.alinhamento]
    preenchimento = f"background:#{el.fundo};padding:0.08in 0.12in;" if el.fundo else "padding:0.02in 0.04in;"
    return _caixa(el, "".join(paragrafos),
                  f"box-sizing:border-box;{preenchimento}font-family:{fonte};font-size:{el.tamanho}pt;"
                  f"color:#{el.cor};text-align:{alinhamento};line-height:1.2;overflow:hidden;")


def _imagem_html(el: Imagem) -> str:
    return _caixa(el, f'<img src="{el.caminho.resolve().as_uri()}" '
                      'style="width:100%;height:100%;object-fit:contain">')


def _tabela_html(el: Tabela) -> str:
    linhas = []
    for i, linha in enumerate(el.linhas):
        celulas = []
        for j, valor in enumerate(linha):
            fonte = FONTE_CODIGO if (i > 0 and j in el.codigo_colunas) else FONTE
            fundo = AZUL if i == 0 else ("F7F9FC" if i % 2 else "FFFFFF")
            celulas.append(
                f'<td style="width:{el.larguras[j]}in;height:{el.altura_linha}in;background:#{fundo};'
                f"font-family:'{fonte}';font-weight:{700 if i == 0 else 400};color:#{'FFFFFF' if i == 0 else '1B1F24'};"
                f'padding:{0.01 if el.altura_linha < 0.3 else 0.03}in 0.08in;border:1px solid #C9D4E2;box-sizing:border-box">{html.escape(valor)}</td>')
        linhas.append(f"<tr>{''.join(celulas)}</tr>")
    return _caixa(el, f'<table style="border-collapse:collapse;font-size:{el.tamanho}pt">{"".join(linhas)}</table>')


def gerar_pdf(lista: list[Slide], destino: Path) -> Path | None:
    paginas = []
    for numero, s in enumerate(lista, start=1):
        partes = []
        if not s.capa:
            partes.append(f'<div style="position:absolute;left:0;top:0;width:{LARGURA}in;height:0.85in;background:#{AZUL}"></div>')
            partes.append(_texto_html(Texto(0.45, 0.14, 10.0, 0.6, [s.titulo], 26, "FFFFFF")))
            partes.append(_texto_html(Texto(11.9, 7.05, 1.0, 0.3, [f"{numero}/{len(lista)}"], 11, CINZA, "direita")))
        for el in s.elementos:
            partes.append({Texto: _texto_html, Imagem: _imagem_html, Tabela: _tabela_html}[type(el)](el))
        fundo = AZUL if s.capa else "FFFFFF"
        paginas.append(f'<section style="position:relative;width:{LARGURA}in;height:{ALTURA}in;'
                       f'background:#{fundo};overflow:hidden;page-break-after:always">{"".join(partes)}</section>')
    documento = (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>'
                 f"@page{{size:{LARGURA}in {ALTURA}in;margin:0}}body{{margin:0}}"
                 f"</style></head><body>{''.join(paginas)}</body></html>")
    return html_para_pdf(documento, destino)


def main() -> None:
    lista = slides()
    destino = RAIZ / "docs"
    destino.mkdir(exist_ok=True)
    gerar_pptx(lista, destino / "Apresentacao.pptx")
    print("Gerado: docs/Apresentacao.pptx")
    pdf = gerar_pdf(lista, destino / "Apresentacao.pdf")
    print("Gerado: docs/Apresentacao.pdf" if pdf else "[AVISO] Edge/Chrome não encontrado: PDF não gerado.")


if __name__ == "__main__":
    main()
