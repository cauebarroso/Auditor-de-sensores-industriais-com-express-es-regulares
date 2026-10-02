"""Testes da aplicação: validação, diagnóstico, lote, relatório e linha de comando."""

import json
import random
from pathlib import Path

import pytest

import auditor
from diagnostico import diagnosticar, localizar_erro
from relatorio import analisar_pacote, exportar, extrair_campos, ler_pacotes, resumir

DADOS = Path(__file__).resolve().parent.parent / "dados"


# ---------------------------------------------------------------------- #
# Entradas vazias ou inválidas
# ---------------------------------------------------------------------- #
@pytest.mark.parametrize("entrada", ["", "   ", "\t\n"])
def test_pacote_vazio_e_rejeitado_com_mensagem(entrada):
    valido, mensagem, _ = auditor.validar_pacote(entrada)
    assert not valido
    assert "vazio" in mensagem


def test_validar_pacote_remove_espacos_das_extremidades():
    assert auditor.validar_pacote("  SEN-TM-0001\r\n") == (True, "ID_DISPOSITIVO", "SEN-TM-0001")


@pytest.mark.parametrize("pacote, trecho", [
    ("sen-tm-0001", "minúsculas"),
    ("SEN_TM_0001", "separador"),
    ("SEN-TM-00012", "mais de 4 dígitos"),
    ("SEN-TM-123", "menos de 4 dígitos"),
    ("ATU-A-1234", "apenas 1 letra"),
    ("SEN-ABCD-1234", "mais de 3 letras"),
    ("SEN-TM-0001:TEMP=200C", "fora da faixa"),
    ("SEN-TM-0001:TEMP=25F", "unidade 'F'"),
    ("SEN-TM-0001:TEMP=025C", "zero à esquerda"),
    ("SEN-TM-0001:TEMP=25.55C", "casa decimal"),
    ("SEN-TM-0001:TEMP=1O4.7C", "malformado"),
    ("SEN-TM-0001:PRES=1100hPa", "fora da faixa"),
    ("ATU-TM-0001:TEMP=25C", "atuadores (ATU) não emitem"),
    ("CMD ATU-VLV-0420 AJUSTAR 101%", "acima de 100%"),
    ("CMD ATU-VLV-0420 AJUSTAR %", "ausente"),
    ("CMD SEN-VLV-0420 LIGAR", "não a sensores"),
    ("CMD ATU-VLV-0420 PAUSAR", "ação não reconhecida"),
    ("CMD ATU-BMB-0202  DESLIGAR", "espaço extra"),
    ("256.0.0.1", "acima de 255"),
    ("192.168.0.1/33", "acima de /32"),
    ("192.168.01.1", "zero à esquerda"),
    ("192.168.0", "3 octeto"),
    ("10.0.0.1/", "sem o valor"),
    ("2026-13-01T10:00:00 INFO SEN-TM-0001: ok", "mês 13"),
    ("2026-02-30T10:00:00 INFO SEN-TM-0001: ok", "não existe no mês 02"),
    ("2026-04-31T10:00:00 INFO SEN-TM-0001: ok", "não existe no mês 04"),
    ("2026-09-30T24:00:00 INFO SEN-TM-0001: ok", "hora 24"),
    ("2026-09-30T08:15:00 DEBUG SEN-TM-0001: ok", "severidade 'DEBUG'"),
    ("2026-09-30T08:15:00 [INFO] SEN-TM-0001: ok", "sem colchetes"),
    ("2026-09-30T08:15:00 INFO SEN-TM-0001:", "mensagem descritiva ausente"),
    ("2026-09-30T08:15:00 INFO SEN-TM-0001: pressão alta", "fora do alfabeto"),
    ("2026-09-30T08:15:00 INFO SEN-TM-0001: a  b", "exatamente um espaço"),
    ("PACOTE_TOTALMENTE_INVALIDO", "nenhum dos cinco padrões"),
])
def test_diagnostico_explica_a_causa(pacote, trecho):
    valido, mensagem, _ = auditor.validar_pacote(pacote)
    assert not valido
    assert trecho in mensagem


@pytest.mark.parametrize("codigo, pacote, posicao, encontrado", [
    ("ER-01", "SEN-TM-00012", 11, "2"),
    ("ER-01", "SEN-TM-001", 10, None),
    ("ER-03", "CMD ATU-VLV-0420 AJUSTAR 101%", 27, "1"),
    ("ER-04", "192.168.0.1/33", 13, "3"),
    ("ER-05", "2026-04-31T10:00:00 INFO SEN-TM-0001: ok", 9, "1"),
])
def test_afn_localiza_o_simbolo_que_causou_a_rejeicao(codigo, pacote, posicao, encontrado):
    local = localizar_erro(codigo, pacote)
    assert (local.posicao, local.encontrado) == (posicao, encontrado)


def test_localizacao_indica_simbolos_esperados():
    local = localizar_erro("ER-01", "SEN-TM-00012")
    assert "fim do pacote" in local.esperado
    assert localizar_erro("ER-01", "SEN-TM-0001") is None


def test_diagnostico_nunca_falha_com_entradas_arbitrarias():
    sorteio = random.Random(42)
    simbolos = "SENATUCMD-:=.%/ 0123456789abcxyzTHPa[]_ãé#"
    for _ in range(3000):
        pacote = "".join(sorteio.choice(simbolos) for _ in range(sorteio.randint(1, 40)))
        assert diagnosticar(pacote).mensagem


# ---------------------------------------------------------------------- #
# Lote (arquivo)
# ---------------------------------------------------------------------- #
def test_arquivo_de_exemplo():
    pacotes = ler_pacotes(DADOS / "dados_exemplo.txt")
    resumo = resumir(pacotes)
    assert (resumo["total"], resumo["integros"], resumo["corrompidos"]) == (34, 20, 14)
    assert resumo["por_categoria"] == {
        "ID_DISPOSITIVO": 3, "TELEMETRIA": 5, "COMANDO": 3, "IPV4_CIDR": 4, "ALERTA_LOG": 5,
    }


def test_linhas_vazias_e_comentarios_sao_ignorados(tmp_path):
    arquivo = tmp_path / "pacotes.txt"
    arquivo.write_text("# comentario\n\n   \nSEN-TM-0001\nlixo\n", encoding="utf-8")
    pacotes = ler_pacotes(arquivo)
    assert [(p.linha, p.valido) for p in pacotes] == [(4, True), (5, False)]


def test_arquivo_inexistente(capsys):
    assert auditor.modo_arquivo("nao_existe.txt", filtros=False) is None
    assert "não encontrado" in capsys.readouterr().out


def test_arquivo_vazio(capsys):
    assert auditor.modo_arquivo(str(DADOS / "vazio.txt"), filtros=False) == []
    assert "não contém pacotes" in capsys.readouterr().out


def test_pasta_no_lugar_de_arquivo(capsys, tmp_path):
    assert auditor.modo_arquivo(str(tmp_path), filtros=False) is None
    assert "é uma pasta" in capsys.readouterr().out


def test_arquivo_binario(capsys, tmp_path):
    arquivo = tmp_path / "binario.txt"
    arquivo.write_bytes(b"\xff\xfe\x00\x81SEN")
    assert auditor.modo_arquivo(str(arquivo), filtros=False) is None
    assert "UTF-8" in capsys.readouterr().out


# ---------------------------------------------------------------------- #
# Extração e relatório
# ---------------------------------------------------------------------- #
@pytest.mark.parametrize("pacote, campos", [
    ("SEN-TM-0001:TEMP=-10.5C",
     {"dispositivo": "SEN-TM-0001", "grandeza": "TEMP", "valor": -10.5, "unidade": "C"}),
    ("SEN-XX-9999:PRES=1013hPa",
     {"dispositivo": "SEN-XX-9999", "grandeza": "PRES", "valor": 1013.0, "unidade": "hPa"}),
    ("CMD ATU-YY-9999 AJUSTAR 75%", {"dispositivo": "ATU-YY-9999", "acao": "AJUSTAR", "percentual": 75}),
    ("10.0.0.1/8", {"endereco": "10.0.0.1", "mascara": 8}),
    ("2026-09-30T08:15:00 WARN SEN-TM-0001: bateria fraca",
     {"data_hora": "2026-09-30T08:15:00", "severidade": "WARN", "dispositivo": "SEN-TM-0001",
      "mensagem": "bateria fraca"}),
])
def test_extracao_de_campos(pacote, campos):
    resultado = analisar_pacote(pacote)
    assert resultado.valido
    assert extrair_campos(resultado.categoria, pacote) == campos


def test_resumo_da_telemetria():
    pacotes = ler_pacotes(DADOS / "turno_caldeira.txt")
    temperatura = resumir(pacotes)["telemetria"]["TEMP"]
    assert temperatura["leituras"] == 5
    assert (temperatura["minimo"], temperatura["maximo"]) == (78.4, 104.7)


@pytest.mark.parametrize("extensao", [".json", ".csv", ".txt"])
def test_exportacao_do_relatorio(tmp_path, extensao):
    pacotes = ler_pacotes(DADOS / "dados_exemplo.txt")
    destino = exportar(pacotes, tmp_path / f"relatorio{extensao}")
    conteudo = destino.read_text(encoding="utf-8-sig")
    assert "SEN-TM-0001" in conteudo
    if extensao == ".json":
        assert json.loads(conteudo)["resumo"]["integros"] == 20


def test_exportacao_com_formato_invalido(tmp_path):
    with pytest.raises(ValueError):
        exportar([], tmp_path / "relatorio.pdf")


# ---------------------------------------------------------------------- #
# Linha de comando e modo interativo
# ---------------------------------------------------------------------- #
def test_cli_pacote_valido_e_invalido(capsys):
    assert auditor.main(["--pacote", "SEN-TM-0001"]) == 0
    assert auditor.main(["--pacote", "SEN-TM-0001", "SEN-TM-00012"]) == 1
    saida = capsys.readouterr().out
    assert "[OK]" in saida
    assert "[ERRO]" in saida


def test_cli_explicar_mostra_os_conjuntos_de_estados(capsys):
    auditor.main(["--explicar", "ATU-VLV-0420"])
    saida = capsys.readouterr().out
    assert "{q0, q1, q2}" in saida
    assert "ACEITA" in saida
    auditor.main(["--explicar", "ATU-A-1234"])
    assert "REJEITADA" in capsys.readouterr().out


def test_cli_arquivo_com_exportacao(tmp_path, capsys):
    destino = tmp_path / "saida.csv"
    assert auditor.main([str(DADOS / "dados_exemplo.txt"), "--sem-filtros", "--exportar", str(destino)]) == 0
    assert destino.exists()
    assert "RELATÓRIO" in capsys.readouterr().out


def test_cli_expressoes(capsys):
    auditor.main(["--expressoes"])
    saida = capsys.readouterr().out
    for codigo in ("ER-01", "ER-02", "ER-03", "ER-04", "ER-05"):
        assert codigo in saida


def test_modo_interativo(monkeypatch, capsys):
    entradas = iter(["", "SEN-TM-0001", "CMD ATU-VLV-0420 AJUSTAR 101%", "voltar"])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))
    assert auditor.modo_interativo() is False
    saida = capsys.readouterr().out
    assert "Entrada vazia" in saida
    assert "[OK]" in saida
    assert "^" in saida


def test_menu_principal_trata_opcao_invalida_e_sai(monkeypatch, capsys):
    entradas = iter(["9", "1", "", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))
    auditor.menu_principal()
    saida = capsys.readouterr().out
    assert "Opção inválida" in saida
    assert "Caminho vazio" in saida
    assert "Encerrando" in saida
