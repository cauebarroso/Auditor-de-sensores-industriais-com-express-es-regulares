"""
Casos de teste de cada Expressão Regular (fonte única).

Estes mesmos casos são usados:
  * pelo pytest (tests/test_expressoes.py e tests/test_automatos.py);
  * pelo script que gera as entradas de "Multiple Run" do JFLAP;
  * pelas tabelas de testes do relatório técnico.
Assim, testes, relatório e AFNε nunca divergem.

Requisito da disciplina: no mínimo 6 cadeias aceitas e 6 rejeitadas por ER,
com pelo menos um caso-limite. Aqui há 8 + 8 por ER.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Caso:
    cadeia: str
    aceita: bool
    motivo: str
    limite: bool = False


def aceita(cadeia, motivo, limite=False):
    return Caso(cadeia, True, motivo, limite)


def rejeita(cadeia, motivo, limite=False):
    return Caso(cadeia, False, motivo, limite)


CASOS = {
    "ER-01": [
        aceita("SEN-TM-0001", "Sensor com modelo de 2 letras"),
        aceita("ATU-VLV-0420", "Atuador com modelo de 3 letras"),
        aceita("SEN-ABC-1234", "Sensor com modelo de 3 letras"),
        aceita("ATU-XY-9999", "Maior número de série (9999)", limite=True),
        aceita("SEN-XX-0000", "Menor número de série (0000)", limite=True),
        aceita("SEN-PH-0750", "Sensor de pH"),
        aceita("SEN-AA-0000", "Menor cadeia de L₁ (11 símbolos)", limite=True),
        aceita("ATU-ZZZ-9999", "Maior cadeia de L₁ (12 símbolos)", limite=True),
        rejeita("", "Cadeia vazia ε não pertence a L₁", limite=True),
        rejeita("sen-tm-0001", "Minúsculas não pertencem a Σ₁"),
        rejeita("SEN-TM-00012", "5 dígitos: {4} exige exatamente 4", limite=True),
        rejeita("SEN-TM-123", "Apenas 3 dígitos no número de série", limite=True),
        rejeita("ATU-A-1234", "Modelo com 1 letra (mínimo 2)", limite=True),
        rejeita("SEN-ABCD-1234", "Modelo com 4 letras (máximo 3)", limite=True),
        rejeita("SENO-TM-0001", "Prefixo SENO não pertence a (SEN | ATU)"),
        rejeita("SEN_TM_0001", "Separador '_' não pertence a Σ₁"),
    ],
    "ER-02": [
        aceita("SEN-TM-0001:TEMP=25.5C", "Temperatura típica com uma casa decimal"),
        aceita("SEN-TM-0001:TEMP=-10C", "Temperatura negativa sem casa decimal"),
        aceita("SEN-TMP-0002:TEMP=-199.9C", "Menor temperatura da faixa", limite=True),
        aceita("SEN-TM-0002:TEMP=199.9C", "Maior temperatura da faixa", limite=True),
        aceita("SEN-AB-1234:UMID=100.0%", "Umidade máxima (100.0)", limite=True),
        aceita("SEN-AB-1234:UMID=0%", "Umidade mínima (0)", limite=True),
        aceita("SEN-YY-0000:PRES=850hPa", "Menor pressão da faixa", limite=True),
        aceita("SEN-XX-9999:PRES=1099hPa", "Maior pressão da faixa", limite=True),
        rejeita("SEN-TM-0001:TEMP=200C", "200 > 199: fora da faixa", limite=True),
        rejeita("SEN-TM-0001:UMID=100.5%", "100.5% > 100%: fora da faixa", limite=True),
        rejeita("SEN-TM-0001:PRES=849hPa", "849 < 850: fora da faixa", limite=True),
        rejeita("SEN-TM-0001:PRES=1100hPa", "1100 > 1099: fora da faixa", limite=True),
        rejeita("SEN-TM-0001:TEMP=25.55C", "Duas casas decimais (máximo uma)"),
        rejeita("SEN-TM-0001:TEMP=025C", "Zero à esquerda não é permitido"),
        rejeita("ATU-TM-0001:TEMP=25C", "Atuador (ATU) não emite telemetria"),
        rejeita("SEN-TM-0001:TEMP=25F", "Unidade F não pertence à linguagem (só C)"),
    ],
    "ER-03": [
        aceita("CMD ATU-VLV-0420 LIGAR", "Ação LIGAR"),
        aceita("CMD ATU-VLV-0420 DESLIGAR", "Ação DESLIGAR"),
        aceita("CMD ATU-XX-1234 ABRIR", "Ação ABRIR"),
        aceita("CMD ATU-XX-1234 FECHAR", "Ação FECHAR"),
        aceita("CMD ATU-YY-9999 AJUSTAR 100%", "Maior ajuste (100%)", limite=True),
        aceita("CMD ATU-YY-9999 AJUSTAR 0%", "Menor ajuste (0%)", limite=True),
        aceita("CMD ATU-MTR-0007 AJUSTAR 75%", "Ajuste com 2 dígitos"),
        aceita("CMD ATU-BB-0001 AJUSTAR 9%", "Ajuste com 1 dígito"),
        rejeita("CMD ATU-VLV-0420 AJUSTAR 101%", "101 > 100: fora da faixa", limite=True),
        rejeita("CMD SEN-VLV-0420 LIGAR", "Sensor (SEN) não recebe comandos"),
        rejeita("CMD ATU-VLV-0420 PAUSAR", "PAUSAR não pertence à união de ações"),
        rejeita("CMD ATU-VLV-0420 AJUSTAR %", "Valor percentual ausente"),
        rejeita("CMD ATU-VLV-0420 LIGAR ", "Espaço extra no final", limite=True),
        rejeita("CMD ATU-VLV-0420 AJUSTAR 050%", "Zero à esquerda não é permitido"),
        rejeita("cmd ATU-VLV-0420 LIGAR", "Prefixo em minúsculas"),
        rejeita("CMD ATU-VLV-0420 AJUSTAR 50", "Falta o símbolo %"),
    ],
    "ER-04": [
        aceita("192.168.0.1", "IP privado sem máscara"),
        aceita("10.0.0.1/8", "IP com máscara CIDR"),
        aceita("255.255.255.255", "Maior octeto em todas as posições", limite=True),
        aceita("0.0.0.0", "Menor octeto em todas as posições", limite=True),
        aceita("172.16.254.1/32", "Maior máscara (/32)", limite=True),
        aceita("0.0.0.0/0", "Menor máscara (/0): rota padrão", limite=True),
        aceita("192.168.1.0/24", "Rede /24"),
        aceita("200.249.250.199", "Usa os ramos 2[0-4]D, 25[0-5] e 1DD do octeto"),
        rejeita("256.0.0.1", "256 > 255: octeto fora da faixa", limite=True),
        rejeita("192.168.0.1/33", "Máscara 33 > 32", limite=True),
        rejeita("192.168.0", "Apenas 3 octetos"),
        rejeita("1.2.3.4.5", "5 octetos"),
        rejeita("192.168.01.1", "Zero à esquerda no octeto"),
        rejeita("192.168.0.1/08", "Zero à esquerda na máscara"),
        rejeita("10.0.0.1/", "Barra sem máscara"),
        rejeita("", "Cadeia vazia ε não pertence a L₄", limite=True),
    ],
    "ER-05": [
        aceita("2026-09-30T08:15:00 INFO SEN-TM-0001: leitura normal", "Registro informativo típico"),
        aceita("2026-12-31T23:59:59 CRIT ATU-XX-9999: falha critica no motor",
               "Último segundo do ano", limite=True),
        aceita("2026-01-01T00:00:00 WARN SEN-AB-1234: bateria fraca",
               "Primeiro instante do ano", limite=True),
        aceita("2026-02-28T12:30:45 ERROR ATU-VLV-0420: travamento_123", "Mensagem com _ e dígitos"),
        aceita("2028-02-29T06:00:00 INFO SEN-TM-0001: ok", "29 de fevereiro", limite=True),
        aceita("2026-04-30T10:00:00 WARN ATU-VLV-0420: valvula 80.5 aberta",
               "Dia 30 em mês de 30 dias", limite=True),
        aceita("2026-07-31T18:45:00 ERROR SEN-PH-0750: sensor-ph fora_de_faixa",
               "Dia 31 em mês de 31 dias", limite=True),
        aceita("2026-10-15T14:22:10 INFO SEN-ZZ-0000: .", "Mensagem de 1 símbolo", limite=True),
        rejeita("2026-13-01T10:00:00 INFO SEN-TM-0001: ok", "Mês 13 não existe", limite=True),
        rejeita("2026-02-30T10:00:00 INFO SEN-TM-0001: ok", "30 de fevereiro não existe", limite=True),
        rejeita("2026-04-31T10:00:00 INFO SEN-TM-0001: ok", "31 de abril não existe", limite=True),
        rejeita("2026-09-30T24:00:00 INFO SEN-TM-0001: ok", "Hora 24 (máximo 23)", limite=True),
        rejeita("2026-09-30T08:15:00 DEBUG SEN-TM-0001: ok", "DEBUG não pertence à união de severidades"),
        rejeita("2026-09-30T08:15:00 INFO SEN-TM-0001: ", "Mensagem vazia", limite=True),
        rejeita("2026-09-30T08:15:00 INFO SEN-TM-0001: leitura  dupla", "Dois espaços seguidos na mensagem"),
        rejeita("2026-09-30T08:15:00 INFO SEN-TM-0001: pressão alta", "'ã' não pertence a Σ₅"),
    ],
}
