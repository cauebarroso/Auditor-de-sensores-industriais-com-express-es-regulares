"""
Testes da regra central do guia: a ER formal, o padrão do código, os testes e
o AFNε devem representar A MESMA linguagem.

  * AFNε (construção de Thompson) x re.fullmatch: casos de teste + 2000 cadeias
    aleatórias por ER;
  * ER formal x padrão do código: PROVA de equivalência (busca exaustiva no
    produto dos autômatos, sem amostragem);
  * arquivo .jff do JFLAP x padrão do código: mesma prova de equivalência.
"""

import random
from pathlib import Path

import pytest

from afn import EPSILON, cadeia_em_comum, contraexemplo
from casos_teste import CASOS
from construtor_afn import ErroPadraoNaoRegular, analisar, construir_afn
from expressoes import EXPRESSOES, formal_para_python
from jflap import carregar_jff

PASTA_JFLAP = Path(__file__).resolve().parent.parent / "automatos" / "jflap"
AFNS = {er.codigo: construir_afn(er.padrao, er.codigo) for er in EXPRESSOES}
POR_ER = pytest.mark.parametrize("er", EXPRESSOES, ids=lambda er: er.codigo)


@pytest.mark.parametrize(
    "codigo, caso",
    [pytest.param(c, caso, id=f"{c}-{caso.cadeia!r}") for c, casos in CASOS.items() for caso in casos],
)
def test_afn_simula_os_casos_de_teste(codigo, caso):
    assert AFNS[codigo].aceita(caso.cadeia) is caso.aceita, caso.motivo


@POR_ER
def test_afn_concorda_com_re_em_cadeias_aleatorias(er):
    """Gera cadeias por caminhadas aleatórias no AFNε (muitas aceitas) e
    aplica mutações (inserção, troca, remoção) para obter quase-acertos."""
    afn = AFNS[er.codigo]
    sorteio = random.Random(er.codigo)
    alfabeto = sorted(afn.alfabeto()) + ["x", " ", "ã", "["]
    for _ in range(2000):
        cadeia, estados = "", afn.fecho_epsilon({afn.inicial})
        while len(cadeia) < 90 and not (afn.contem_final(estados) and sorteio.random() < 0.2):
            esperados = sorted(afn.simbolos_esperados(estados))
            if not esperados:
                break
            cadeia += sorteio.choice(esperados)
            estados = afn.passo(estados, cadeia[-1])
        if sorteio.random() < 0.5 and cadeia:
            i = sorteio.randrange(len(cadeia))
            cadeia = sorteio.choice([
                cadeia[:i] + sorteio.choice(alfabeto) + cadeia[i:],
                cadeia[:i] + sorteio.choice(alfabeto) + cadeia[i + 1:],
                cadeia[:i] + cadeia[i + 1:],
            ])
        assert afn.aceita(cadeia) is (er.regex.fullmatch(cadeia) is not None), repr(cadeia)


@POR_ER
def test_er_formal_equivale_ao_padrao_do_codigo(er):
    formal = construir_afn(er.formal_como_python(), er.codigo + "-formal")
    assert contraexemplo(AFNS[er.codigo], formal) is None


@POR_ER
def test_arquivo_jflap_reconhece_a_mesma_linguagem(er):
    jff = carregar_jff(PASTA_JFLAP / f"{er.codigo}.jff")
    assert contraexemplo(AFNS[er.codigo], jff) is None


@POR_ER
def test_arquivo_jflap_compativel_com_o_simulador_do_jflap(er):
    """O JFLAP 7.1 lê um símbolo por transição e interpreta rótulos que
    contêm '[' como intervalo ([a-z]); nenhum rótulo pode conter '['."""
    jff = carregar_jff(PASTA_JFLAP / f"{er.codigo}.jff")
    assert "[" not in jff.alfabeto()
    assert len(jff.finais) >= 1


@POR_ER
def test_afn_tem_movimentos_vazios_e_um_estado_final(er):
    afn = AFNS[er.codigo]
    assert afn.inicial == 0
    assert len(afn.finais) == 1
    assert any(rotulo is EPSILON for _, rotulo, _ in afn.transicoes)


def test_as_cinco_linguagens_sao_disjuntas():
    """Interseção vazia para todo par de ERs: cada pacote tem uma única categoria."""
    for i, a in enumerate(EXPRESSOES):
        for b in EXPRESSOES[i + 1:]:
            assert cadeia_em_comum(AFNS[a.codigo], AFNS[b.codigo]) is None, (a.codigo, b.codigo)


def test_verificador_detecta_divergencia_entre_formal_e_codigo():
    """Sanidade do verificador: a ER formal da versão antiga do relatório,
    OCT = ... | (D ∪ ε)D, aceita zeros à esquerda que o código rejeita."""
    errada = formal_para_python(
        "⟨OCT⟩ . ⟨OCT⟩ . ⟨OCT⟩ . ⟨OCT⟩",
        {"OCT": "25[0-5] | 2[0-4][0-9] | 1[0-9][0-9] | ([0-9] | ε) [0-9]"},
    )
    certa = r"((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])"
    exemplo = contraexemplo(construir_afn(certa), construir_afn(errada))
    assert exemplo is not None
    assert "0" in exemplo


def test_er05_e_infinita_e_as_demais_sao_finitas():
    """Confere a afirmação das fichas: só a ER-05 usa fecho de Kleene."""
    assert {er.codigo for er in EXPRESSOES if AFNS[er.codigo].linguagem_infinita()} == {"ER-05"}
    base = "2026-09-30T08:15:00 INFO SEN-TM-0001: a"
    assert all(AFNS["ER-05"].aceita(base + " a" * n) for n in (1, 10, 100))


@pytest.mark.parametrize("padrao", [
    r"[0-9]\d", r"a.b", r"^abc$", r"(a)\1", r"a(?=b)", r"a(?!b)", r"[^a]", r"a*?", r"a\s", r"a\w",
])
def test_construtor_rejeita_recursos_fora_da_notacao_formal(padrao):
    with pytest.raises(ErroPadraoNaoRegular):
        analisar(padrao)
