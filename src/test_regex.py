import pytest
from auditor import (
    ER_01_ID,
    ER_02_TELEMETRIA,
    ER_03_COMANDO,
    ER_04_IPV4_CIDR,
    ER_05_ALERTA_LOG
)

# Testes ER-01
@pytest.mark.parametrize("pacote, esperado", [
    # 6 aceitas
    ("SEN-TM-0001", True),
    ("ATU-VLV-0420", True),
    ("SEN-ABC-1234", True),
    ("ATU-XY-9999", True),
    ("SEN-XX-0000", True),
    ("ATU-ZZZ-1111", True),
    # 6 rejeitadas
    ("sen-tm-0001", False),
    ("", False),           # limite: vazia
    ("SEN-TM-00012", False), # limite: 5 digitos
    ("SENO-TM-0001", False),
    ("ATU-A-1234", False),
    ("SEN-TM-123", False),
])
def test_er_01(pacote, esperado):
    assert bool(ER_01_ID.fullmatch(pacote)) == esperado

# Testes ER-02
@pytest.mark.parametrize("pacote, esperado", [
    # 6 aceitas
    ("SEN-TM-0001:TEMP=25.5C", True),
    ("SEN-TM-0001:TEMP=-10C", True),
    ("SEN-AB-1234:UMID=100.0%", True),
    ("SEN-AB-1234:UMID=5%", True),
    ("SEN-XX-9999:PRES=1013hPa", True),
    ("SEN-YY-0000:PRES=850hPa", True),
    # 6 rejeitadas
    ("SEN-TM-0001:TEMP=200C", False), # limite: temperatura > 199
    ("SEN-TM-0001:UMID=101%", False), # limite: umidade > 100
    ("SEN-TM-0001:PRES=849hPa", False), # limite: pressao < 850
    ("SEN-TM-0001:TEMP=25.55C", False),
    ("ATU-TM-0001:TEMP=25C", False),  # ID deve ser SEN
    ("", False),
])
def test_er_02(pacote, esperado):
    assert bool(ER_02_TELEMETRIA.fullmatch(pacote)) == esperado

# Testes ER-03
@pytest.mark.parametrize("pacote, esperado", [
    # 6 aceitas
    ("CMD ATU-VLV-0420 LIGAR", True),
    ("CMD ATU-VLV-0420 DESLIGAR", True),
    ("CMD ATU-XX-1234 ABRIR", True),
    ("CMD ATU-XX-1234 FECHAR", True),
    ("CMD ATU-YY-9999 AJUSTAR 100%", True),
    ("CMD ATU-YY-9999 AJUSTAR 5%", True),
    # 6 rejeitadas
    ("CMD ATU-VLV-0420 AJUSTAR 101%", False), # limite: ajuste > 100%
    ("CMD SEN-VLV-0420 LIGAR", False),       # comando para SEN ao inves de ATU
    ("CMD ATU-VLV-0420 PAUSAR", False),      # comando inexistente
    ("CMD ATU-VLV-0420 AJUSTAR %", False),
    ("CMD ATU-VLV-0420 LIGAR ", False),      # espaco extra
    ("", False),
])
def test_er_03(pacote, esperado):
    assert bool(ER_03_COMANDO.fullmatch(pacote)) == esperado

# Testes ER-04
@pytest.mark.parametrize("pacote, esperado", [
    # 6 aceitas
    ("192.168.0.1", True),
    ("10.0.0.1/8", True),
    ("255.255.255.255", True),
    ("0.0.0.0", True),
    ("172.16.254.1/32", True),
    ("192.168.1.1/24", True),
    # 6 rejeitadas
    ("256.0.0.1", False),   # limite: octeto > 255
    ("192.168.0", False),   # apenas 3 octetos
    ("192.168.0.1/33", False), # limite: mascara > 32
    ("192.168.01.1", False), # zero a esquerda nao permitido senao for 0 sozinho
    ("10.0.0.1/", False),   # barra sem mascara
    ("", False),
])
def test_er_04(pacote, esperado):
    assert bool(ER_04_IPV4_CIDR.fullmatch(pacote)) == esperado

# Testes ER-05
@pytest.mark.parametrize("pacote, esperado", [
    # 6 aceitas
    ("2026-09-30T08:15:00 [INFO] SEN-TM-0001: leitura normal", True),
    ("2026-12-31T23:59:59 [CRIT] ATU-XX-9999: falha critica", True),
    ("2026-01-01T00:00:00 [WARN] SEN-AB-1234: bateria fraca", True),
    ("2026-02-28T12:30:45 [ERROR] ATU-VLV-0420: travamento_123", True),
    ("9999-12-31T23:59:59 [INFO] SEN-XY-1234: ok", True),
    ("2026-10-15T14:22:10 [INFO] SEN-ZZ-0000: .", True),
    # 6 rejeitadas
    ("2026-13-01T10:00:00 [INFO] SEN-TM-0001: ok", False), # limite: mes 13
    ("2026-09-32T10:00:00 [INFO] SEN-TM-0001: ok", False), # limite: dia 32
    ("2026-09-30T24:00:00 [INFO] SEN-TM-0001: ok", False), # limite: hora 24
    ("2026-09-30T08:15:00 [DEBUG] SEN-TM-0001: ok", False),# nivel de log invalido
    ("2026-09-30T08:15:00 [INFO] SEN-TM-0001: ", False),   # mensagem vazia
    ("", False),
])
def test_er_05(pacote, esperado):
    assert bool(ER_05_ALERTA_LOG.fullmatch(pacote)) == esperado
