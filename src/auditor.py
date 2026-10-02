"""
Auditor Léxico de Telemetria de Sensores Industriais.

Ferramenta de linha de comando que funciona como um "firewall léxico":
cada pacote de texto recebido de sensores/atuadores é validado contra cinco
Expressões Regulares; pacotes corrompidos são bloqueados e diagnosticados.

Uso:
  python src/auditor.py                         menu interativo
  python src/auditor.py ARQUIVO                 audita um arquivo (lote)
  python src/auditor.py ARQUIVO --exportar R    ... e salva o relatório (.json/.csv/.txt)
  python src/auditor.py --pacote "P1" "P2"      valida pacotes avulsos
  python src/auditor.py --explicar "P"          simula o AFNε passo a passo
  python src/auditor.py --expressoes            mostra as cinco ERs
"""

from __future__ import annotations

import argparse
import sys

from construtor_afn import formatar_simbolo
from diagnostico import AUTOMATOS, diagnosticar, identificar_intencao, localizar_erro
from expressoes import EXPRESSOES, POR_CODIGO, classificar
from relatorio import CATEGORIAS, Pacote, analisar_pacote, exportar, formatar_relatorio, ler_pacotes

# Garante acentos e símbolos (ε, Σ, ⎵) em terminais Windows (cp1252 / cmd / PowerShell)
for _fluxo in (sys.stdout, sys.stderr):
    if hasattr(_fluxo, "reconfigure"):
        try:
            _fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

LARGURA = 64


def caixa(*linhas: str) -> str:
    borda = "+" + "=" * LARGURA + "+"
    return "\n".join([borda, *(f"|{linha:^{LARGURA}}|" for linha in linhas), borda])


def ler(prompt: str) -> str | None:
    """input() que devolve None em Ctrl+C / Ctrl+D em vez de encerrar com erro."""
    try:
        return input(prompt)
    except (KeyboardInterrupt, EOFError):
        print()
        return None


# ---------------------------------------------------------------------- #
# Validação de um pacote
# ---------------------------------------------------------------------- #
def validar_pacote(pacote: str) -> tuple[bool, str, str]:
    """Valida um pacote contra as cinco ERs.

    Retorna (True, categoria, pacote) se alguma ER reconhece o pacote inteiro
    ou (False, diagnóstico, pacote) caso contrário. Espaços nas extremidades
    são removidos antes da validação (normalização de entrada).
    """
    pacote = pacote.strip()
    if not pacote:
        return False, "Falha estrutural: pacote vazio recebido.", pacote
    er = classificar(pacote)
    if er is not None:
        return True, er.categoria, pacote
    return False, diagnosticar(pacote).mensagem, pacote


def imprimir_resultado(pacote: Pacote, recuo: str = "  ") -> None:
    if pacote.valido:
        er = next(e for e in EXPRESSOES if e.categoria == pacote.categoria)
        print(f"{recuo}[OK] Pacote íntegro. Categoria: {pacote.categoria} ({er.codigo} - {er.nome})")
        return
    diag = pacote.diagnostico
    print(f"{recuo}[ERRO] {diag.mensagem}")
    if diag.localizacao:
        margem = recuo + " " * 7
        print(f"{margem}{pacote.texto}")
        print(f"{margem}{' ' * diag.localizacao.posicao}^")
        print(f"{margem}Onde: {diag.localizacao.descrever()}")


# ---------------------------------------------------------------------- #
# Modos de operação
# ---------------------------------------------------------------------- #
def modo_interativo() -> bool:
    """Valida pacotes digitados um a um. Retorna True se o usuário pediu 'sair'."""
    print("\n" + caixa("MODO INTERATIVO", "Digite um pacote por linha.",
                       "'voltar' retorna ao menu | 'sair' encerra"))
    while True:
        entrada = ler("\n>>> ")
        if entrada is None:
            return False
        comando = entrada.strip().lower()
        if comando == "sair":
            return True
        if comando == "voltar":
            return False
        if not entrada.strip():
            print("  [AVISO] Entrada vazia: digite um pacote (ex.: SEN-TM-0001:TEMP=25.5C).")
            continue
        imprimir_resultado(analisar_pacote(entrada.strip()))


def modo_arquivo(caminho: str, destino: str | None = None, filtros: bool = True) -> list[Pacote] | None:
    """Audita um arquivo em lote, mostra o relatório e (opcionalmente) o exporta."""
    caminho = caminho.strip().strip('"').strip("'")
    try:
        pacotes = ler_pacotes(caminho)
    except FileNotFoundError:
        print(f"  [ERRO] Arquivo '{caminho}' não encontrado.")
        return None
    except IsADirectoryError:
        print(f"  [ERRO] '{caminho}' é uma pasta; informe o caminho de um arquivo .txt.")
        return None
    except PermissionError:
        print(f"  [ERRO] Sem permissão para ler '{caminho}'.")
        return None
    except UnicodeDecodeError:
        print(f"  [ERRO] '{caminho}' não é um arquivo de texto UTF-8 válido.")
        return None

    if not pacotes:
        print(f"  [AVISO] O arquivo '{caminho}' não contém pacotes (vazio ou só comentários).")
        return pacotes

    print("\n" + formatar_relatorio(pacotes, caminho))
    if destino:
        salvar_relatorio(pacotes, destino)
    if filtros:
        menu_filtros(pacotes)
    return pacotes


def salvar_relatorio(pacotes: list[Pacote], destino: str) -> None:
    try:
        arquivo = exportar(pacotes, destino)
        print(f"\n  [OK] Relatório exportado para: {arquivo}")
    except ValueError as erro:
        print(f"  [ERRO] {erro}")
    except OSError as erro:
        print(f"  [ERRO] Não foi possível salvar o relatório: {erro}")


def menu_filtros(pacotes: list[Pacote]) -> None:
    opcoes = {str(i): categoria for i, categoria in enumerate(CATEGORIAS, start=1)}
    while True:
        print("\n--- Filtros do relatório ---")
        for numero, categoria in opcoes.items():
            print(f"  [{numero}] Pacotes íntegros do tipo {categoria}")
        print("  [6] Pacotes CORROMPIDOS (com diagnóstico)")
        print("  [7] TODOS os pacotes")
        print("  [8] Exportar relatório (.json, .csv ou .txt)")
        print("  [0] Voltar ao menu principal")
        opcao = ler("Filtro >>> ")
        if opcao is None or opcao.strip() == "0":
            return
        opcao = opcao.strip()
        if opcao in opcoes:
            exibir(p for p in pacotes if p.categoria == opcoes[opcao])
        elif opcao == "6":
            exibir(p for p in pacotes if not p.valido)
        elif opcao == "7":
            exibir(pacotes)
        elif opcao == "8":
            destino = ler("  Salvar como (ex.: relatorio.json): ")
            if destino and destino.strip():
                salvar_relatorio(pacotes, destino.strip())
            else:
                print("  [AVISO] Nome de arquivo vazio. Exportação cancelada.")
        else:
            print("  [AVISO] Opção inválida. Escolha um número de 0 a 8.")


def exibir(pacotes) -> None:
    contagem = 0
    print()
    for p in pacotes:
        print(f"  L{p.linha:<4}", end="")
        imprimir_resultado(p, recuo="")
        if p.valido:
            print(f"        {p.texto}")
        contagem += 1
    print("  Nenhum pacote encontrado para este filtro." if contagem == 0
          else f"\n  Total exibido: {contagem} pacote(s).")


def explicar_afn(pacote: str, codigo_er: str | None = None) -> None:
    """Mostra a simulação do AFNε (conjuntos de estados após cada símbolo)."""
    if codigo_er is None:
        er = classificar(pacote)
        codigo_er = er.codigo if er else identificar_intencao(pacote)
    if codigo_er is None:
        print("  [AVISO] Não foi possível identificar qual ER o pacote tenta seguir; "
              "informe a ER (ex.: --er ER-01).")
        return
    er = POR_CODIGO[codigo_er]
    afn = AUTOMATOS[codigo_er]
    resultado = afn.simular(pacote)

    print(f"\n  Simulação do AFNε da {er.codigo} ({er.nome}): "
          f"{afn.n_estados} estados, {afn.total_movimentos_vazios()} movimentos ε")
    print(f"  Cadeia: \"{pacote}\"  (|w| = {len(pacote)})\n")
    print(f"  {'passo':>5}  {'lido':^6}  conjunto de estados ativos (após o fecho-ε)")
    for passo in resultado.passos:
        lido = "—" if passo.simbolo is None else f"'{formatar_simbolo(passo.simbolo)}'"
        estados = ", ".join(f"q{e}" for e in sorted(passo.estados))
        print(f"  {passo.lidos:>5}  {lido:^6}  {{{estados}}}")

    finais = ", ".join(f"q{f}" for f in sorted(afn.finais))
    if resultado.aceita:
        print(f"\n  Resultado: ACEITA — o último conjunto contém o estado final ({finais}).")
    else:
        pos = resultado.posicao_erro
        if pos < len(pacote):
            lido = f"'{formatar_simbolo(pacote[pos])}'"
            print(f"  {pos + 1:>5}  {lido:^6}  ∅  (nenhuma transição definida)")
        print(f"\n  Resultado: REJEITADA — {localizar_erro(codigo_er, pacote).descrever()}.")
        print(f"  Estado(s) final(is) do AFNε: {{{finais}}}")


def mostrar_expressoes() -> None:
    for er in EXPRESSOES:
        afn = AUTOMATOS[er.codigo]
        print(f"\n{er.codigo} — {er.nome} [{er.categoria}]")
        print(f"  Finalidade : {er.finalidade}")
        print(f"  Alfabeto   : {er.alfabeto}")
        print("  ER formal  :")
        for linha in er.formal_completa():
            print(f"      {linha}")
        print(f"  No código  : re.fullmatch(r\"{er.padrao}\", pacote)")
        print(f"  AFNε       : {afn.n_estados} estados, {len(afn.transicoes)} transições "
              f"({afn.total_movimentos_vazios()} movimentos ε)")


def menu_principal() -> None:
    print(caixa("AUDITOR LÉXICO DE TELEMETRIA", "DE SENSORES INDUSTRIAIS  v2.0", "",
                "Firewall léxico para redes de sensores e atuadores"))
    while True:
        print("\n--- Menu principal ---")
        print("  [1] Auditar arquivo de pacotes (.txt) em lote")
        print("  [2] Validar pacotes digitados (modo interativo)")
        print("  [3] Simular o AFNε passo a passo para um pacote")
        print("  [4] Ver as cinco expressões regulares")
        print("  [0] Sair")
        opcao = ler("Opção >>> ")
        if opcao is None:
            break
        opcao = opcao.strip()
        if opcao == "1":
            caminho = ler("  Caminho do arquivo (ex.: dados/dados_exemplo.txt): ")
            if caminho and caminho.strip():
                modo_arquivo(caminho)
            else:
                print("  [AVISO] Caminho vazio. Operação cancelada.")
        elif opcao == "2":
            if modo_interativo():
                break
        elif opcao == "3":
            pacote = ler("  Pacote: ")
            if pacote and pacote.strip():
                explicar_afn(pacote.strip())
            else:
                print("  [AVISO] Pacote vazio. Operação cancelada.")
        elif opcao == "4":
            mostrar_expressoes()
        elif opcao == "0" or opcao.lower() == "sair":
            break
        else:
            print("  [AVISO] Opção inválida. Escolha 0, 1, 2, 3 ou 4.")
    print("Encerrando o Auditor Léxico.")


# ---------------------------------------------------------------------- #
# Linha de comando
# ---------------------------------------------------------------------- #
def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="auditor.py",
        description="Auditor Léxico de Telemetria de Sensores Industriais (firewall léxico com ERs).",
    )
    parser.add_argument("arquivo", nargs="?", help="arquivo .txt com um pacote por linha")
    parser.add_argument("--exportar", metavar="DESTINO",
                        help="salva o relatório do arquivo em .json, .csv ou .txt")
    parser.add_argument("--sem-filtros", action="store_true",
                        help="não abre o menu de filtros após o relatório")
    parser.add_argument("--pacote", nargs="+", metavar="PACOTE", help="valida um ou mais pacotes")
    parser.add_argument("--explicar", metavar="PACOTE", help="simula o AFNε passo a passo")
    parser.add_argument("--er", choices=sorted(POR_CODIGO), help="ER usada por --explicar")
    parser.add_argument("--expressoes", action="store_true", help="mostra as cinco ERs")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = criar_parser().parse_args(argv)

    if args.expressoes:
        mostrar_expressoes()
        return 0
    if args.explicar is not None:
        if not args.explicar.strip():
            print("  [AVISO] Pacote vazio.")
            return 1
        explicar_afn(args.explicar.strip(), args.er)
        return 0
    if args.pacote:
        todos_validos = True
        for texto in args.pacote:
            if not texto.strip():
                print("  [ERRO] Falha estrutural: pacote vazio recebido.")
                todos_validos = False
                continue
            pacote = analisar_pacote(texto.strip())
            print(f"\n  Pacote: {pacote.texto}")
            imprimir_resultado(pacote)
            todos_validos &= pacote.valido
        return 0 if todos_validos else 1
    if args.arquivo:
        filtros = not args.sem_filtros and sys.stdin.isatty()
        pacotes = modo_arquivo(args.arquivo, args.exportar, filtros)
        return 0 if pacotes is not None else 1

    menu_principal()
    return 0


if __name__ == "__main__":
    sys.exit(main())
