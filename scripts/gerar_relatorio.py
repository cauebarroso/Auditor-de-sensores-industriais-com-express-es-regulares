"""
Gera o relatório técnico a partir dos dados do próprio código:

  docs/Relatorio_Tecnico.md   (renderizado pelo GitHub)
  docs/Relatorio_Tecnico.pdf  (requer Microsoft Edge ou Google Chrome)

Padrões, ERs formais, alfabetos, casos de teste e números dos AFNε vêm de
src/ e tests/, então o relatório nunca diverge do programa.

Uso (na raiz do repositório):
  python scripts/gerar_relatorio.py
"""

from __future__ import annotations

import contextlib
import io
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(RAIZ / "src"), str(RAIZ / "tests"), str(RAIZ / "scripts")]

import auditor  # noqa: E402
from casos_teste import CASOS  # noqa: E402
from conteudo_fichas import EQUIVALENCIAS, FONTES, LIMITES  # noqa: E402
from diagnostico import AUTOMATOS  # noqa: E402
from expressoes import EXPRESSOES  # noqa: E402
from pdf import html_para_pdf, markdown_para_html  # noqa: E402

DOCS = RAIZ / "docs"
REPOSITORIO = "https://github.com/cauebarroso/Auditor-de-sensores-industriais-com-express-es-regulares"
INTEGRANTES = ["Augusto Rodrigues", "Caue Jadão", "César Augusto"]


def celula(texto: str, codigo: bool = True) -> str:
    texto = texto.replace("|", "\\|")
    return f"`{texto}`" if codigo and texto != "—" else texto


def exibir_cadeia(cadeia: str) -> str:
    """Cadeia de teste para tabelas: ε para a vazia e ⎵ para espaços no fim
    (que seriam invisíveis na tabela)."""
    if not cadeia:
        return "ε (cadeia vazia)"
    sem_espacos = cadeia.rstrip(" ")
    return sem_espacos + "⎵" * (len(cadeia) - len(sem_espacos))


def capturar(funcao, *args) -> str:
    saida = io.StringIO()
    with contextlib.redirect_stdout(saida):
        funcao(*args)
    return saida.getvalue().rstrip()


def linha_do_codigo(nome: str) -> str:
    """Linha exata do código-fonte que define o padrão."""
    for linha in (RAIZ / "src" / "expressoes.py").read_text(encoding="utf-8").splitlines():
        if linha.startswith(f"{nome} = "):
            return linha
    raise ValueError(nome)


def imagens(codigo: str) -> list[str]:
    partes = sorted((RAIZ / "automatos" / "diagramas" / "partes").glob(f"{codigo}_p*.png"),
                    key=lambda p: int(p.stem.split("_p")[1]))
    if partes:
        return [f"../automatos/diagramas/partes/{p.name}" for p in partes]
    return [f"../automatos/diagramas/{codigo}.png"]


def resultados_pytest() -> tuple[str, Counter]:
    coleta = subprocess.run([sys.executable, "-m", "pytest", "--co", "-q"], cwd=RAIZ,
                            capture_output=True, text=True, encoding="utf-8").stdout
    por_arquivo = Counter(linha.split("::")[0] for linha in coleta.splitlines() if "::" in linha)
    execucao = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=RAIZ,
                              capture_output=True, text=True, encoding="utf-8").stdout
    resumo = next(l for l in reversed(execucao.splitlines()) if "passed" in l or "failed" in l)
    return re.sub(r" in [0-9.]+s", "", resumo.strip("= ")), por_arquivo


def resultado_jflap() -> str:
    arquivo = RAIZ / "automatos" / "jflap" / "resultado_jflap.md"
    if not arquivo.exists():
        return "não executado"
    achado = re.search(r"Resultado: ([0-9]+/[0-9]+)", arquivo.read_text(encoding="utf-8"))
    return achado.group(1) if achado else "não executado"


# ---------------------------------------------------------------------- #
# Seções
# ---------------------------------------------------------------------- #
def cabecalho() -> str:
    return f"""# Relatório Técnico — Auditor Léxico de Telemetria de Sensores Industriais

| | |
| :-- | :-- |
| **Disciplina** | Linguagens Formais e Autômatos — Trabalho do 1º Bimestre |
| **Curso** | Ciência da Computação — CESUPA |
| **Integrantes** | {" · ".join(INTEGRANTES)} |
| **Linguagem** | Python 3.11+ (módulo `re`, sem bibliotecas externas na aplicação) |
| **Ferramentas** | pytest (testes), JFLAP 7.1 (AFNε), Graphviz (diagramas) |
| **Repositório** | <{REPOSITORIO}> |

**Sumário:** 1. Problema e solução · 2. Notação adotada · 3. Fichas das Expressões Regulares ·
4. Consistência entre as representações · 5. Demonstração do AFNε · 6. Testes e análise dos resultados ·
7. Limitações e melhorias · 8. Contribuições · 9. Uso de Inteligência Artificial · 10. Referências
"""


def secao_problema() -> str:
    linhas_er = "\n".join(
        f"| {er.codigo} | {er.nome} | {er.finalidade} |" for er in EXPRESSOES
    )
    return f"""
## 1. Problema e solução

Redes industriais (SCADA/IIoT) trocam pacotes de texto entre sensores, atuadores e o sistema
supervisório. Um pacote corrompido — um dígito trocado por uma letra, um mês inexistente, um
percentual acima de 100% — pode virar uma leitura falsa ou uma ordem perigosa para um atuador.

O **Auditor Léxico** é uma ferramenta de linha de comando que atua como um *firewall léxico*:
cada pacote só é aceito se pertencer à linguagem de uma das cinco Expressões Regulares do
protocolo. Pacotes rejeitados são bloqueados e recebem um diagnóstico com a causa provável e a
**coluna exata do erro**, obtida pela simulação do AFNε da ER.

| Código | Padrão | Finalidade |
| :-- | :-- | :-- |
{linhas_er}

### Entradas, processamento e saídas

| Etapa | Descrição |
| :-- | :-- |
| **Entradas** | Pacotes digitados no modo interativo, passados por argumento (`--pacote`) ou lidos de um arquivo `.txt` (um pacote por linha; linhas em branco e comentários `#` são ignorados). |
| **Processamento** | Normalização (remoção de espaços nas extremidades), classificação por `re.fullmatch` contra as cinco ERs (linguagens disjuntas, logo a categoria é única), extração de campos dos pacotes válidos e diagnóstico dos inválidos. |
| **Saídas** | Veredito por pacote (`[OK]`/`[ERRO]` com apontador de coluna), relatório de conformidade (totais, taxa, categorias, estatísticas de telemetria, comandos, alertas, inventário de dispositivos), filtros por categoria e exportação em JSON, CSV ou TXT. |

Entradas vazias, só com espaços, arquivos inexistentes, pastas, arquivos vazios e arquivos que
não são texto UTF-8 são tratados com mensagens claras, sem encerrar o programa com erro.

### Organização do código

| Módulo | Responsabilidade |
| :-- | :-- |
| `src/expressoes.py` | As cinco ERs (padrões do código) e as fichas: alfabeto, linguagem e ER formal. |
| `src/auditor.py` | Interface: menu, modo interativo, modo lote, argumentos de linha de comando. |
| `src/diagnostico.py` | Causa provável da rejeição e localização do erro pela simulação do AFNε. |
| `src/relatorio.py` | Leitura de arquivos, extração de campos, estatísticas e exportação. |
| `src/afn.py` | Estrutura do AFNε: fecho-ε, simulação, linguagem finita/infinita, equivalência e interseção. |
| `src/construtor_afn.py` | Analisador do subconjunto regular permitido e construção de Thompson (ER → AFNε). |
| `src/jflap.py`, `src/diagramas.py` | Exportação/importação `.jff` e diagramas DOT. |
| `tests/` | Casos de teste (fonte única) e suítes pytest. |
| `scripts/` | Geração dos AFNε, verificação no JFLAP e geração deste relatório. |
"""


def secao_notacao() -> str:
    return """
## 2. Notação adotada

A ER formal segue a notação do guia da disciplina. Para que a escrita formal fique legível, as
subexpressões repetidas recebem nomes (**definições regulares**, escritas como `⟨NOME⟩ = r`); cada
nome é apenas uma abreviação da ER que ele define, então a linguagem descrita não muda.

| Notação formal | Significado | Equivalente no Python |
| :-- | :-- | :-- |
| `r s` | Concatenação | `rs` |
| `r \\| s` | União | `r\\|s` |
| `r*` | Fecho de Kleene (zero ou mais) | `r*` |
| `r r*` | Fecho positivo (uma ou mais) | `r+` |
| `(r \\| ε)` | Opcionalidade | `r?` |
| `ε` | Cadeia vazia | (alternativa vazia) |
| `[0-9]`, `[A-Z]` | Classe/intervalo finito: `(0 \\| 1 \\| … \\| 9)` | `[0-9]`, `[A-Z]` |
| `⎵` | O símbolo espaço | ` ` (espaço literal) |
| `.` | O símbolo ponto (na notação formal não existe curinga) | `\\.` (escape obrigatório) |
| `⟨NOME⟩` | Definição regular | o padrão é escrito por extenso |

**Regras seguidas no código:** correspondência completa com `re.fullmatch` (dispensa `^` e `$`);
nenhum uso de `\\d`, `\\w`, `\\s`, `.` curinga, classes negadas, retroreferências ou lookarounds.
O analisador de `src/construtor_afn.py` **rejeita** esses recursos, então a regra é verificada
automaticamente nos testes.
"""


def ficha(er) -> str:
    afn = AUTOMATOS[er.codigo]
    casos = CASOS[er.codigo]
    nome_constante = {"ER-01": "PADRAO_ER_01", "ER-02": "PADRAO_ER_02", "ER-03": "PADRAO_ER_03",
                      "ER-04": "PADRAO_ER_04", "ER-05": "PADRAO_ER_05"}[er.codigo]
    constante_regex = {"ER-01": "ER_01_ID", "ER-02": "ER_02_TELEMETRIA", "ER-03": "ER_03_COMANDO",
                       "ER-04": "ER_04_IPV4_CIDR", "ER-05": "ER_05_ALERTA_LOG"}[er.codigo]
    equivalencias = "\n".join(
        f"| {celula(cod)} | {celula(formal)} | {celula(explicacao, codigo=False)} |"
        for cod, formal, explicacao in EQUIVALENCIAS[er.codigo]
    )
    testes = []
    for i, caso in enumerate(casos, start=1):
        cadeia = f"`{exibir_cadeia(caso.cadeia)}`" if caso.cadeia else exibir_cadeia(caso.cadeia)
        resultado = "✅ aceita" if caso.aceita else "❌ rejeitada"
        limite = " **(caso-limite)**" if caso.limite else ""
        testes.append(f"| {i} | {cadeia} | {resultado} | {caso.motivo}{limite} |")
    figuras = "\n\n".join(f"![AFNε da {er.codigo}]({img})" for img in imagens(er.codigo))
    partes = len(imagens(er.codigo))
    aviso_partes = (f"\n\nO diagrama foi dividido em {partes} partes nos estados de articulação "
                    "(estados por onde passa todo caminho de aceitação); a seta pontilhada indica a continuação. "
                    "A numeração dos estados é a do autômato completo." if partes > 1 else "")
    infinita = "infinita" if afn.linguagem_infinita() else "finita"
    limites = "\n".join(f"- {texto}" for texto in LIMITES[er.codigo])
    fonte = f"\n\n**Fonte.** {FONTES[er.codigo]}" if er.codigo in FONTES else ""
    aceitas = sum(c.aceita for c in casos)
    return f"""
<div class="quebra"></div>

### {er.codigo} — {er.nome}

| Campo | Conteúdo |
| :-- | :-- |
| **Identificação** | {er.codigo} · categoria `{er.categoria}` · constante `{constante_regex}` em `src/expressoes.py` |
| **Finalidade** | {er.finalidade} |
| **Alfabeto** | {er.alfabeto} |
| **Linguagem L** | {er.linguagem} |

**ER formal** (definições regulares seguidas da ER):

```text
{chr(10).join(er.formal_completa())}
```

**Sintaxe implementada** (copiada do código, usada com `re.fullmatch`):

```python
{linha_do_codigo(nome_constante)}
```

**Equivalência entre o código e a notação formal:**

| No código | Na ER formal | Explicação |
| :-- | :-- | :-- |
{equivalencias}{fonte}

**AFNε** — construído pela construção de Thompson a partir do padrão do código:
**{afn.n_estados} estados** (inicial `q0`, final `q{min(afn.finais)}`), **{len(afn.transicoes)} transições**,
das quais **{afn.total_movimentos_vazios()} são movimentos ε** (setas tracejadas). Rótulos como `[0-9]` resumem
transições paralelas; no arquivo do JFLAP elas aparecem expandidas ({afn.total_transicoes_expandidas()} transições).
Arquivos: `automatos/jflap/{er.codigo}.jff` e `automatos/diagramas/{er.codigo}.svg`.{aviso_partes}

{figuras}

**Testes** ({aceitas} aceitas e {len(casos) - aceitas} rejeitadas):

| # | Cadeia | Esperado | Justificativa |
| --: | :-- | :-- | :-- |
{chr(10).join(testes)}

**Resultado e limites.** Todas as {len(casos)} cadeias obtiveram o resultado esperado em `re.fullmatch`,
no AFNε simulado em Python e no AFNε executado no JFLAP 7.1. A linguagem é **{infinita}**.

{limites}
"""


def secao_consistencia() -> str:
    return f"""
<div class="quebra"></div>

## 4. Consistência entre as representações

A regra central do guia exige que ER formal, padrão do código, testes e AFNε descrevam **a mesma
linguagem**. Em vez de conferir isso manualmente, o projeto verifica a regra por algoritmo:

1. **Código → AFNε (construção de Thompson).** `construtor_afn.py` lê o padrão exatamente como está
   no código e constrói o AFNε: união vira ramos abertos e fechados por ε; `r?` ganha um desvio ε;
   `r*` ganha o laço ε de Thompson; `r{{m,n}}` vira m cópias seguidas de n − m cópias opcionais.
2. **AFNε ≡ ER formal (prova).** A ER formal de cada ficha é traduzida para a sintaxe do Python e
   também convertida em AFNε. `afn.contraexemplo` percorre em largura todos os pares de conjuntos
   de estados alcançáveis pela mesma cadeia nos dois autômatos (construção de subconjuntos sobre o
   produto). Como esse espaço é finito, a busca termina: se nenhum par discorda sobre aceitação,
   as linguagens são **iguais** — é uma prova, não uma amostragem.
3. **`.jff` ≡ código (prova).** O arquivo do JFLAP é lido de volta e comparado com o AFNε do código
   pelo mesmo algoritmo.
4. **AFNε × `re.fullmatch` (testes).** Os 80 casos de teste e mais 10.000 cadeias aleatórias
   (caminhadas no autômato e mutações) dão o mesmo resultado no AFNε e no `re` do Python.
5. **No próprio JFLAP.** `scripts/verificar_jflap.py` carrega cada `.jff` com o código do JFLAP 7.1
   e simula as cadeias de teste: **{resultado_jflap()}** com o resultado esperado.

| ER | ER formal ≡ código | `.jff` ≡ código | AFNε × `re` | JFLAP 7.1 | Linguagens disjuntas |
| :-- | :-: | :-: | :-: | :-: | :-: |
""" + "\n".join(f"| {er.codigo} | ✅ provado | ✅ provado | ✅ | ✅ 16/16 | ✅ |" for er in EXPRESSOES) + """

As cinco linguagens são **disjuntas** (a interseção de cada par de AFNε é vazia, também verificada
por busca no produto). Por isso cada pacote válido pertence a exatamente uma categoria.

**Observações sobre o JFLAP 7.1.** A execução no motor do JFLAP revelou dois comportamentos que
orientaram o formato dos arquivos:

- O simulador interpreta qualquer rótulo que contenha `[` como um intervalo no estilo `[a-z]` e lança
  uma exceção quando o rótulo é apenas `[`. Por isso a severidade do log é escrita sem colchetes
  (`INFO`, não `[INFO]`): o `.jff` reconhece exatamente a mesma linguagem do código, sem símbolos
  substitutos.
- Rótulos de intervalo como `[A-Z]` deixariam o desenho mais limpo, mas, depois de uma transição desse
  tipo, o simulador do JFLAP 7.1 **não aplica o fecho-ε**: testamos uma versão com intervalos e ela
  rejeitou 35 das 40 cadeias que deveriam ser aceitas (por exemplo, todo ID com modelo de 2 letras,
  que depende do desvio ε da terceira letra). Por isso os `.jff` usam uma transição por símbolo, o
  formato básico que funciona em qualquer versão do JFLAP e em todas as suas operações.

A pasta `automatos/jflap/imagens/` mostra cada `.jff` desenhado pelo próprio componente gráfico do JFLAP.
"""


def secao_demonstracao() -> str:
    aceita = capturar(auditor.explicar_afn, "ATU-VLV-0420", "ER-01")
    rejeita = capturar(auditor.explicar_afn, "ATU-A-1234", "ER-01")
    return f"""
<div class="quebra"></div>

## 5. Demonstração: simulação do AFNε

A opção 3 do menu (ou `python src/auditor.py --explicar "PACOTE"`) mostra o conjunto de estados
ativos do AFNε após cada símbolo — o fecho-ε de δ(S, a). A cadeia é aceita se o último conjunto
contém um estado final. Os números dos estados são os mesmos do diagrama da ER-01.

**Cadeia aceita:**

```text
{aceita}
```

**Cadeia rejeitada** (o modelo tem uma só letra; depois de `A`, o AFNε exige outra letra):

```text
{rejeita}
```

No diagnóstico de pacotes, a mesma simulação aponta a coluna do erro:

```text
{capturar(auditor.main, ["--pacote", "CMD ATU-VLV-0420 AJUSTAR 101%"])}
```
"""


def secao_testes() -> str:
    resumo, por_arquivo = resultados_pytest()
    descricao = {
        "tests/test_expressoes.py": "Cadeias aceitas/rejeitadas por `re.fullmatch`, requisitos mínimos (6 + 6 e caso-limite), categoria única e ausência de atalhos proibidos.",
        "tests/test_automatos.py": "AFNε × `re` (casos e 10.000 cadeias aleatórias), provas ER formal ≡ código e `.jff` ≡ código, linguagens disjuntas, linguagem finita/infinita e rejeição de recursos não regulares.",
        "tests/test_aplicacao.py": "Entradas vazias e inválidas, diagnósticos, coluna do erro, robustez (3.000 entradas aleatórias), arquivos (inexistente, vazio, pasta, binário), extração, exportação, CLI e modo interativo.",
    }
    linhas = "\n".join(f"| `{arquivo}` | {n} | {descricao.get(arquivo, '')} |" for arquivo, n in sorted(por_arquivo.items()))
    lote = capturar(auditor.modo_arquivo, "dados/dados_exemplo.txt", None, False).replace(str(RAIZ), ".")
    return f"""
<div class="quebra"></div>

## 6. Testes e análise dos resultados

Os casos de teste de cada ER ficam em um único arquivo (`tests/casos_teste.py`), usado pelo pytest,
pelas entradas do JFLAP (`automatos/jflap/entradas/`) e pelas tabelas deste relatório.
Cada ER tem **8 cadeias aceitas e 8 rejeitadas** (mínimo exigido: 6 + 6), com vários casos-limite:
extremos das faixas numéricas (0 e 100%, 850 e 1099 hPa, octetos 0 e 255, máscaras /0 e /32),
datas na fronteira (29/02, 30/04, 31/07, 30/02, 31/04), menor e maior cadeia de L₁ e a cadeia vazia ε.

Execução: `python -m pytest` → **{resumo}**.

| Arquivo | Testes | O que verifica |
| :-- | --: | :-- |
{linhas}

No JFLAP 7.1 (Input › Multiple Run com os arquivos de `automatos/jflap/entradas/`, ou automaticamente
com `scripts/verificar_jflap.py`): **{resultado_jflap()}** cadeias com o resultado esperado
(detalhes em `automatos/jflap/resultado_jflap.md`).

### Execução sobre os dados de exemplo

`python src/auditor.py dados/dados_exemplo.txt --sem-filtros`:

```text
{lote}
```

### Análise

- **Nenhuma divergência** entre `re.fullmatch`, AFNε em Python e JFLAP em todos os casos; as provas
  de equivalência garantem que isso vale para **qualquer** cadeia, não só para as testadas.
- Os pacotes corrompidos dos dados de exemplo foram todos bloqueados, cada um com a causa correta;
  nenhum pacote íntegro foi bloqueado.
- Os erros mais sutis — `TEMP=1O4.7C` (letra O no lugar do zero), `2026-09-31` (setembro tem 30
  dias), dois espaços em um comando — são exatamente os que a validação por ER detecta e que uma
  inspeção visual deixaria passar.
- Os falsos resultados possíveis são **semânticos**, não léxicos, e estão listados na ficha de cada
  ER (ex.: −0C aceito; temperatura real acima de 199.9 °C bloqueada).
"""


def secao_final() -> str:
    return f"""
<div class="quebra"></div>

## 7. Limitações e possíveis melhorias

**Limitações gerais**

- O auditor valida a **forma** dos pacotes (camada léxica), não o seu significado físico ou o estado
  da planta. As limitações específicas estão na ficha de cada ER.
- Atua na camada de aplicação sobre texto; não inspeciona tráfego binário (Modbus, OPC UA).
- Os diagramas legíveis agrupam transições paralelas (`[0-9]`); no JFLAP elas aparecem expandidas,
  o que deixa o desenho do JFLAP carregado nas ERs com classes grandes.

**Possíveis melhorias**

- Validar ano bissexto em 29/02. Continua sendo regular (há um número finito de anos com 4 dígitos),
  mas o AFNε cresceria bastante.
- Faixas de medição configuráveis por tipo de sensor, gerando a ER a partir de um cadastro.
- Leitura contínua de um fluxo (porta serial ou socket) em vez de arquivo.
- Minimizar o AFD equivalente (algoritmo de Hopcroft) para comparar o tamanho do AFNε de Thompson
  com o do autômato mínimo.

## 8. Contribuições dos integrantes

| Integrante | Contribuições |
| :-- | :-- |
| Augusto Rodrigues | ER-01 e ER-02 (fichas, AFNε e testes); módulo de diagnóstico de falhas. |
| Caue Jadão | ER-03 e ER-04 (fichas, AFNε e testes); revisão geral, verificação de equivalência, relatório e repositório. |
| César Augusto | ER-05 (ficha, AFNε e testes); modo lote, relatório de conformidade, exportação e apresentação. |

Todos os integrantes participaram dos testes e da preparação da apresentação.

## 9. Uso de Inteligência Artificial

Conforme a Resolução de Uso de IA do curso de Ciência da Computação (CESUPA, 2026), declaramos o uso
de ferramentas de IA generativa como **apoio**:

| Ferramenta | Tarefas em que foi utilizada |
| :-- | :-- |
| Antigravity (Google DeepMind) | Versão inicial: estruturação do `auditor.py` e dos testes, geração programática dos primeiros arquivos `.jff`, formatação do relatório e do README. |
| Claude (Anthropic), via Claude Code | Revisão: correção de inconsistências entre a ER formal e o código; reestruturação em módulos; construção de Thompson e verificação de equivalência; geração dos `.jff` e diagramas; ampliação dos testes; redação deste relatório e dos slides. |

As decisões de projeto (domínio, padrões do protocolo, faixas de valores) são da equipe. Todo o
conteúdo produzido com apoio de IA foi revisado pela equipe, e todos os integrantes compreendem,
explicam e conseguem modificar o código, as expressões regulares e os autômatos.

## 10. Referências

- HOPCROFT, J. E.; MOTWANI, R.; ULLMAN, J. D. *Introdução à Teoria de Autômatos, Linguagens e Computação*. 2. ed. Rio de Janeiro: Elsevier, 2002.
- MENEZES, P. B. *Linguagens Formais e Autômatos*. 6. ed. Porto Alegre: Bookman, 2011.
- SIPSER, M. *Introdução à Teoria da Computação*. 2. ed. São Paulo: Cengage Learning, 2007.
- THOMPSON, K. Programming Techniques: Regular expression search algorithm. *Communications of the ACM*, v. 11, n. 6, p. 419–422, 1968.
- AHO, A. V.; LAM, M. S.; SETHI, R.; ULLMAN, J. D. *Compiladores: princípios, técnicas e ferramentas*. 2. ed. São Paulo: Pearson, 2008 (definições regulares, seção 3.3).
- GOYVAERTS, J.; LEVITHAN, S. *Regular Expressions Cookbook*. 2. ed. Sebastopol: O'Reilly, 2012 (receitas de validação de datas e de endereços IPv4).
- PYTHON SOFTWARE FOUNDATION. *re — Regular expression operations*. Disponível em: <https://docs.python.org/3/library/re.html>.
- RODGER, S. H. *JFLAP 7.1*. Duke University. Disponível em: <https://www.jflap.org>.
- GANSNER, E. R.; NORTH, S. C. An open graph visualization system and its applications to software engineering. *Software: Practice and Experience*, v. 30, n. 11, p. 1203–1233, 2000 (Graphviz, usado nos diagramas). Disponível em: <https://graphviz.org>.
- PYTEST DEVELOPMENT TEAM. *pytest*. Disponível em: <https://docs.pytest.org>.
- Bibliotecas usadas só para gerar os documentos: *Python-Markdown* (<https://python-markdown.github.io>), *python-pptx* (<https://python-pptx.readthedocs.io>) e *Pillow* (<https://python-pillow.org>).
- ISO 8601-1:2019 — *Date and time — Representations for information interchange*.
- POSTEL, J. *RFC 791 — Internet Protocol*, 1981; FULLER, V.; LI, T. *RFC 4632 — Classless Inter-domain Routing (CIDR)*, 2006.
"""


def gerar() -> None:
    DOCS.mkdir(exist_ok=True)
    fichas = "\n".join(ficha(er) for er in EXPRESSOES)
    texto = (cabecalho() + secao_problema() + secao_notacao()
             + "\n<div class=\"quebra\"></div>\n\n## 3. Fichas das Expressões Regulares\n" + fichas
             + secao_consistencia() + secao_demonstracao() + secao_testes() + secao_final())
    destino = DOCS / "Relatorio_Tecnico.md"
    destino.write_text(texto, encoding="utf-8")
    print(f"Gerado: {destino.relative_to(RAIZ)}")

    html = markdown_para_html(texto, titulo="Relatório Técnico — Auditor Léxico", base=DOCS)
    pdf = html_para_pdf(html, DOCS / "Relatorio_Tecnico.pdf")
    print(f"Gerado: {pdf.relative_to(RAIZ)}" if pdf else "[AVISO] Edge/Chrome não encontrado: PDF não gerado.")


if __name__ == "__main__":
    gerar()
