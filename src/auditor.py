import re
import sys

# Garante compatibilidade de encoding em terminais Windows (cp1252 / cmd / powershell)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# =============================================================================
# Expressões Regulares - Auditor Léxico
# Proibido o uso de \d, \w, \s e recursos não regulares.
# =============================================================================

ER_01_ID = re.compile(r"(SEN|ATU)-[A-Z]{2,3}-[0-9]{4}")

ER_02_TELEMETRIA = re.compile(
    r"SEN-[A-Z]{2,3}-[0-9]{4}:(TEMP=-?(1[0-9][0-9]|[1-9]?[0-9])(\.[0-9])?C|UMID=(100(\.0)?|[1-9]?[0-9](\.[0-9])?)%|PRES=(8[5-9][0-9]|9[0-9][0-9]|10[0-9][0-9])hPa)"
)

ER_03_COMANDO = re.compile(
    r"CMD ATU-[A-Z]{2,3}-[0-9]{4} (LIGAR|DESLIGAR|ABRIR|FECHAR|AJUSTAR (100|[1-9]?[0-9])%)"
)

ER_04_IPV4_CIDR = re.compile(
    r"((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(/(3[0-2]|[12]?[0-9]))?"
)

ER_05_ALERTA_LOG = re.compile(
    r"[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9] \[(INFO|WARN|ERROR|CRIT)\] (SEN|ATU)-[A-Z]{2,3}-[0-9]{4}: [A-Za-z0-9 _.-]{1,60}"
)

# =============================================================================
# Motor de Diagnóstico Específico de Erros Léxicos (AC-2)
# Identifica a intenção morfológica e aponta exatamente a regra violada.
# =============================================================================

def diagnosticar_falha(pacote: str) -> str:
    """Identifica especificamente a causa da falha léxica do pacote."""
    # 1. Intenção: Log (ER-05) - possui timestamp ISO ou severidade entre colchetes
    if re.search(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T", pacote) or re.search(r"\[[A-Za-z]+\]", pacote):
        if re.search(r"^[0-9]{4}-(1[3-9]|[2-9][0-9])-", pacote):
            return "Falha no Log: mes invalido (superior a 12). Meses aceitos: 01 a 12."
        if re.search(r"^[0-9]{4}-(0[1-9]|1[0-2])-(3[2-9]|[4-9][0-9])", pacote):
            return "Falha no Log: dia invalido (superior a 31). Dias aceitos: 01 a 31."
        if re.search(r"^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T(2[4-9]|[3-9][0-9])", pacote):
            return "Falha no Log: hora invalida (superior a 23). Horas aceitas: 00 a 23."
        if re.search(r"\[[A-Za-z]+\]", pacote) and not re.search(r"\[(INFO|WARN|ERROR|CRIT)\]", pacote):
            return "Falha no Log: nivel de severidade nao reconhecido. Niveis validos: INFO, WARN, ERROR, CRIT."
        if re.search(r":\s*$", pacote):
            return "Falha no Log: mensagem descritiva ausente apos o identificador do dispositivo."
        return "Falha no Log: formatacao do registro incompativel com o padrao ISO 8601 ou campos obrigatorios."

    # 2. Intenção: Comando de Controle (ER-03) - inicia com CMD
    if pacote.startswith("CMD ") or pacote.startswith("cmd "):
        if re.search(r"^CMD SEN-", pacote):
            return "Falha no Comando: comandos de controle sao direcionados a atuadores (ATU), nao a sensores (SEN)."
        if re.search(r"AJUSTAR (1[0-9][0-9]|[2-9][0-9][0-9]|[0-9]{4,})%", pacote):
            return "Falha no Comando: valor de ajuste acima de 100%. O intervalo aceito e 0 a 100%."
        if re.search(r"AJUSTAR %", pacote):
            return "Falha no Comando: valor percentual ausente na instrucao AJUSTAR."
        if re.search(r"^CMD ATU-[A-Z]{2,3}-[0-9]{4} [A-Z]+", pacote):
            return "Falha no Comando: acao nao reconhecida. Acoes validas: LIGAR, DESLIGAR, ABRIR, FECHAR, AJUSTAR."
        return "Falha no Comando: sintaxe da instrucao CMD malformada ou parametros incompativeis."

    # 3. Intenção: Telemetria (ER-02) - contem separadores :TEMP=, :UMID= ou :PRES=
    if any(k in pacote for k in (":TEMP=", ":UMID=", ":PRES=", ":temp=", ":umid=", ":pres=")):
        if pacote.startswith("ATU-"):
            return "Falha na Telemetria: atuadores (ATU) nao emitem telemetria. Apenas sensores (SEN) sao aceitos."
        if ":TEMP=" in pacote:
            return "Falha na Telemetria: valor de temperatura fora do intervalo admissivel (-199 a 199) ou formato decimal invalido."
        if ":UMID=" in pacote:
            return "Falha na Telemetria: valor de umidade fora do intervalo admissivel (0 a 100) ou formato decimal invalido."
        if ":PRES=" in pacote:
            return "Falha na Telemetria: valor de pressao fora do intervalo admissivel (850 a 1099 hPa)."
        return "Falha na Telemetria: variavel ou valor metrico nao conforme com a especificacao tecnica."

    # 4. Intenção: IPv4/CIDR (ER-04) - contem pontos e digitos
    if re.search(r"^[0-9.]+(/[0-9]*)?$", pacote) and "." in pacote:
        if re.search(r"(25[6-9]|2[6-9][0-9]|[3-9][0-9][0-9]|[0-9]{4,})\.", pacote) or re.search(r"\.(25[6-9]|2[6-9][0-9]|[3-9][0-9][0-9]|[0-9]{4,})($|/)", pacote):
            return "Falha no IPv4: octeto com valor superior a 255. Cada octeto deve estar no intervalo 0 a 255."
        if re.search(r"/(3[3-9]|[4-9][0-9]|[0-9]{3,})$", pacote):
            return "Falha no IPv4/CIDR: mascara de sub-rede superior a /32. O intervalo valido e /0 a /32."
        if pacote.endswith("/"):
            return "Falha no IPv4/CIDR: barra de mascara presente sem valor numerico."
        if re.search(r"(^|\.)0[0-9]+", pacote):
            return "Falha no IPv4: zero a esquerda detectado em octeto. Valores como '01' ou '007' nao sao permitidos."
        partes = pacote.split("/")[0].split(".")
        if len(partes) != 4:
            return f"Falha no IPv4: endereco incompleto ou excessivo ({len(partes)} octetos encontrados; esperado 4)."
        return "Falha no IPv4/CIDR: formato de endereco ou notacao CIDR invalida."

    # 5. Intenção: ID do Dispositivo (ER-01) - inicia com SEN ou ATU
    if re.search(r"^(sen|atu|SEN|ATU)-", pacote):
        if re.search(r"[a-z]", pacote):
            return "Falha no ID do Dispositivo: letras minusculas detectadas. O ID exige letras maiusculas (SEN/ATU)."
        if re.search(r"^(SEN|ATU)-[A-Z]{1}-[0-9]+", pacote):
            return "Falha no ID do Dispositivo: codigo do modelo possui apenas 1 letra. O minimo exigido e 2."
        if re.search(r"^(SEN|ATU)-[A-Z]{4,}-[0-9]+", pacote):
            return "Falha no ID do Dispositivo: codigo do modelo excede 3 letras (maximo 3)."
        if re.search(r"^(SEN|ATU)-[A-Z]{2,3}-[0-9]{5,}", pacote):
            return "Falha no ID do Dispositivo: campo numerico excede 4 digitos."
        if re.search(r"^(SEN|ATU)-[A-Z]{2,3}-[0-9]{1,3}$", pacote):
            return "Falha no ID do Dispositivo: campo numerico possui menos de 4 digitos."
        return "Falha no ID do Dispositivo: formato geral malformado."

    return "Falha estrutural: o pacote nao corresponde a nenhum padrao lexico conhecido."


def validar_pacote(pacote: str) -> tuple[bool, str, str]:
    """
    Tenta validar o pacote em uma das 5 categorias (ERs).
    Retorna (True, tipo, pacote) se for válido.
    Retorna (False, diagnóstico, pacote) se não combinar com nenhuma estrutura.
    """
    if not pacote:
        return False, "Falha estrutural: pacote vazio recebido.", pacote

    if ER_01_ID.fullmatch(pacote):
        return True, "ID_DISPOSITIVO", pacote
    if ER_02_TELEMETRIA.fullmatch(pacote):
        return True, "TELEMETRIA", pacote
    if ER_03_COMANDO.fullmatch(pacote):
        return True, "COMANDO", pacote
    if ER_04_IPV4_CIDR.fullmatch(pacote):
        return True, "IPV4_CIDR", pacote
    if ER_05_ALERTA_LOG.fullmatch(pacote):
        return True, "ALERTA_LOG", pacote

    # Diagnóstico específico por intenção e causa raiz
    return False, diagnosticar_falha(pacote), pacote


# =============================================================================
# Modo Interativo (AC-1: agora acessível via menu)
# =============================================================================

def modo_interativo():
    """Modo de entrada interativa: o operador digita pacotes um a um."""
    print("\n+======================================================+")
    print("|          MODO INTERATIVO - Auditor Lexico            |")
    print("|  Digite um pacote por linha. 'voltar' retorna ao     |")
    print("|  menu. 'sair' encerra o programa.                    |")
    print("+======================================================+\n")

    while True:
        try:
            pacote = input(">>> ").strip()
            if pacote.lower() == "sair":
                print("Encerrando o Auditor Léxico.")
                sys.exit(0)
            if pacote.lower() == "voltar":
                return
            if not pacote:
                continue

            valido, mensagem, _ = validar_pacote(pacote)
            if valido:
                print(f"  [OK] Pacote válido. Categoria: {mensagem}")
            else:
                print(f"  [ERRO] {mensagem}")
        except (KeyboardInterrupt, EOFError):
            print("\nRetornando ao menu...")
            return


# =============================================================================
# Modo Arquivo / Lote (AC-3: agora com filtros de relatório)
# =============================================================================

def modo_arquivo(caminho_arquivo: str):
    """Processa um arquivo de log em lote e gera relatório com filtros."""
    estatisticas = {
        "ID_DISPOSITIVO": 0,
        "TELEMETRIA": 0,
        "COMANDO": 0,
        "IPV4_CIDR": 0,
        "ALERTA_LOG": 0,
        "CORROMPIDOS": 0,
    }
    total = 0
    pacotes_processados = []  # Armazena (valido, tipo_ou_diag, pacote_original)

    try:
        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if not linha:
                    continue
                total += 1
                valido, mensagem, pacote_orig = validar_pacote(linha)
                pacotes_processados.append((valido, mensagem, pacote_orig))
                if valido:
                    estatisticas[mensagem] += 1
                else:
                    estatisticas["CORROMPIDOS"] += 1

    except FileNotFoundError:
        print(f"  Erro: Arquivo '{caminho_arquivo}' não encontrado.")
        return
    except Exception as e:
        print(f"  Erro ao ler arquivo: {e}")
        return

    # Relatório estatístico
    integros = total - estatisticas["CORROMPIDOS"]
    print("\n+======================================================+")
    print("|              RELATORIO ESTATISTICO                   |")
    print("+------------------------------------------------------+")
    print(f"|  Arquivo: {caminho_arquivo:<42} |")
    print(f"|  Total de pacotes lidos:       {total:>21} |")
    print(f"|  Pacotes integros:             {integros:>21} |")
    print(f"|  Pacotes corrompidos:          {estatisticas['CORROMPIDOS']:>21} |")
    print("+------------------------------------------------------+")
    print("|  Detalhes por categoria:                             |")
    for k, v in estatisticas.items():
        if k != "CORROMPIDOS":
            print(f"|    {k:<30} {v:>17} |")
    print("+======================================================+")

    # Filtros interativos (AC-3)
    menu_filtros(pacotes_processados)


def menu_filtros(pacotes: list):
    """Permite ao operador filtrar os pacotes processados por categoria."""
    categorias_validas = [
        "ID_DISPOSITIVO", "TELEMETRIA", "COMANDO",
        "IPV4_CIDR", "ALERTA_LOG", "CORROMPIDOS"
    ]

    while True:
        print("\n--- Filtros de Relatório ---")
        print("  [1] Exibir pacotes do tipo ID_DISPOSITIVO")
        print("  [2] Exibir pacotes do tipo TELEMETRIA")
        print("  [3] Exibir pacotes do tipo COMANDO")
        print("  [4] Exibir pacotes do tipo IPV4_CIDR")
        print("  [5] Exibir pacotes do tipo ALERTA_LOG")
        print("  [6] Exibir pacotes CORROMPIDOS (com diagnóstico)")
        print("  [7] Exibir TODOS os pacotes")
        print("  [0] Voltar ao menu principal")

        try:
            opcao = input("Filtro >>> ").strip()
        except (KeyboardInterrupt, EOFError):
            return

        if opcao == "0":
            return
        elif opcao == "7":
            exibir_pacotes_filtrados(pacotes, filtro=None)
        elif opcao in ("1", "2", "3", "4", "5"):
            cat = categorias_validas[int(opcao) - 1]
            exibir_pacotes_filtrados(pacotes, filtro=cat)
        elif opcao == "6":
            exibir_pacotes_filtrados(pacotes, filtro="CORROMPIDOS")
        else:
            print("  Opção inválida.")


def exibir_pacotes_filtrados(pacotes: list, filtro: str | None):
    """Exibe pacotes filtrados por categoria."""
    print()
    contagem = 0
    for valido, tipo_ou_diag, pacote_orig in pacotes:
        if filtro is None:
            # Exibir todos
            if valido:
                print(f"  [OK] [{tipo_ou_diag}] {pacote_orig}")
            else:
                print(f"  [ERRO] {pacote_orig}")
                print(f"         -> {tipo_ou_diag}")
            contagem += 1
        elif filtro == "CORROMPIDOS":
            if not valido:
                print(f"  [ERRO] {pacote_orig}")
                print(f"         -> {tipo_ou_diag}")
                contagem += 1
        else:
            if valido and tipo_ou_diag == filtro:
                print(f"  [OK] {pacote_orig}")
                contagem += 1

    if contagem == 0:
        print("  Nenhum pacote encontrado para este filtro.")
    else:
        print(f"\n  Total exibido: {contagem} pacote(s).")


# =============================================================================
# Menu Principal (AC-1)
# =============================================================================

def menu_principal():
    """Menu interativo principal do Auditor Léxico."""
    print("+======================================================+")
    print("|     AUDITOR LEXICO DE TELEMETRIA DE SENSORES         |")
    print("|              INDUSTRIAIS v1.0                        |")
    print("|                                                      |")
    print("|  Firewall lexico para redes de sensores/atuadores    |")
    print("+======================================================+")

    while True:
        print("\n--- Menu Principal ---")
        print("  [1] Ler arquivo de log (.txt) em lote")
        print("  [2] Entrada textual interativa")
        print("  [3] Sair")

        try:
            opcao = input("Opção >>> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando o Auditor Léxico.")
            break

        if opcao == "1":
            try:
                caminho = input("  Caminho do arquivo: ").strip()
            except (KeyboardInterrupt, EOFError):
                continue
            if caminho:
                modo_arquivo(caminho)
            else:
                print("  Caminho vazio. Operação cancelada.")
        elif opcao == "2":
            modo_interativo()
        elif opcao == "3":
            print("Encerrando o Auditor Léxico.")
            break
        else:
            print("  Opção inválida. Escolha 1, 2 ou 3.")


# =============================================================================
# Ponto de entrada
# =============================================================================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Atalho: se receber argumento de linha de comando, processa direto
        modo_arquivo(sys.argv[1])
    else:
        menu_principal()
