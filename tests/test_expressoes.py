"""Testes das cinco Expressões Regulares (cadeias aceitas e rejeitadas)."""

import pytest

from casos_teste import CASOS
from expressoes import EXPRESSOES, POR_CODIGO, classificar

TODOS_OS_CASOS = [
    pytest.param(codigo, caso, id=f"{codigo}-{'aceita' if caso.aceita else 'rejeita'}-{caso.cadeia!r}")
    for codigo, casos in CASOS.items()
    for caso in casos
]


@pytest.mark.parametrize("codigo, caso", TODOS_OS_CASOS)
def test_cadeia(codigo, caso):
    """re.fullmatch com o padrão do código produz o resultado esperado."""
    assert POR_CODIGO[codigo].reconhece(caso.cadeia) is caso.aceita, caso.motivo


@pytest.mark.parametrize("er", EXPRESSOES, ids=lambda er: er.codigo)
def test_requisitos_minimos_da_disciplina(er):
    """No mínimo 6 aceitas, 6 rejeitadas e pelo menos um caso-limite por ER."""
    casos = CASOS[er.codigo]
    assert sum(c.aceita for c in casos) >= 6
    assert sum(not c.aceita for c in casos) >= 6
    assert any(c.limite for c in casos)


@pytest.mark.parametrize("codigo, caso", [p for p in TODOS_OS_CASOS if p.values[1].aceita])
def test_cada_cadeia_aceita_pertence_a_uma_unica_er(codigo, caso):
    """A classificação é determinística: só a ER esperada reconhece a cadeia."""
    reconhecem = [er.codigo for er in EXPRESSOES if er.reconhece(caso.cadeia)]
    assert reconhecem == [codigo]
    assert classificar(caso.cadeia).codigo == codigo


@pytest.mark.parametrize("er", EXPRESSOES, ids=lambda er: er.codigo)
def test_padroes_nao_usam_atalhos_proibidos(er):
    """O guia proíbe atalhos dependentes do motor e recursos não regulares."""
    for proibido in (r"\d", r"\w", r"\s", "^", "$", "(?=", "(?!", "(?<", r"\1"):
        assert proibido not in er.padrao
