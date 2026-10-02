"""
Executa os arquivos .jff no PRÓPRIO motor do JFLAP 7.1 e confere o resultado
de cada cadeia de teste com o esperado (tests/casos_teste.py). Também salva
como cada autômato aparece na tela do JFLAP (desenhado pelo próprio JFLAP).

Pré-requisitos: Java (JDK) e o arquivo JFLAP7.1.jar (https://www.jflap.org).
Uso (na raiz do repositório):
  python scripts/verificar_jflap.py [caminho/para/JFLAP7.1.jar]
(sem argumento, usa scripts/jflap/JFLAP7.1.jar)

Gera:
  automatos/jflap/resultado_jflap.md   tabela de resultados
  automatos/jflap/imagens/ER-0X.png    o .jff desenhado pelo JFLAP
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(RAIZ / "src"), str(RAIZ / "tests")]

from casos_teste import CASOS  # noqa: E402
from expressoes import EXPRESSOES  # noqa: E402

PASTA_JFLAP = RAIZ / "automatos" / "jflap"


def executavel(nome: str) -> str:
    caminho = shutil.which(nome)
    if caminho is None:
        sys.exit(f"[ERRO] '{nome}' não encontrado no PATH (é necessário um JDK).")
    return caminho


def executar(classe: str, classpath: str, *argumentos: Path) -> str:
    return subprocess.run([executavel("java"), "-Djava.awt.headless=true", "-cp", classpath, classe,
                           *map(str, argumentos)],
                          check=True, capture_output=True, text=True).stdout


def main() -> int:
    jar_padrao = RAIZ / "scripts" / "jflap" / "JFLAP7.1.jar"
    jar = Path(sys.argv[1]) if len(sys.argv) > 1 else jar_padrao
    if not jar.is_file():
        sys.exit("Uso: python scripts/verificar_jflap.py [caminho/para/JFLAP7.1.jar]\n"
                 f"(sem argumento, procura {jar_padrao.relative_to(RAIZ)})")
    separador = ";" if sys.platform == "win32" else ":"
    imagens = PASTA_JFLAP / "imagens"
    imagens.mkdir(exist_ok=True)

    linhas = ["# Execução dos AFNε no motor do JFLAP 7.1", "",
              "Gerado por `scripts/verificar_jflap.py`: cada `.jff` foi carregado pelo próprio JFLAP "
              "(`file.XMLCodec`) e simulado com `FSAStepWithClosureSimulator`, o simulador usado em "
              "*Input › Multiple Run*. As imagens em `imagens/` foram desenhadas pelo componente "
              "gráfico do JFLAP (`gui.viewer.AutomatonPane`).", ""]
    total = falhas = 0
    with tempfile.TemporaryDirectory() as pasta:
        classpath = f"{jar.resolve()}{separador}{pasta}"
        subprocess.run([executavel("javac"), "-nowarn", "-cp", str(jar.resolve()), "-d", pasta,
                        str(RAIZ / "scripts" / "jflap" / "TestaJFLAP.java"),
                        str(RAIZ / "scripts" / "jflap" / "DesenhaJFLAP.java")],
                       check=True, capture_output=True)
        for er in EXPRESSOES:
            jff = PASTA_JFLAP / f"{er.codigo}.jff"
            resultados = executar("TestaJFLAP", classpath, jff, PASTA_JFLAP / "entradas" / f"{er.codigo}.txt").split()
            executar("DesenhaJFLAP", classpath, jff, imagens / f"{er.codigo}.png")
            linhas += [f"## {er.codigo} — {er.nome}", "",
                       f"![{er.codigo} no JFLAP](imagens/{er.codigo}.png)", "",
                       "| # | Cadeia | Esperado | JFLAP | Confere |", "| --: | :-- | :-: | :-: | :-: |"]
            for i, (caso, resultado) in enumerate(zip(CASOS[er.codigo], resultados, strict=True), start=1):
                esperado = "ACEITA" if caso.aceita else "REJEITA"
                confere = resultado == esperado
                total += 1
                falhas += not confere
                cadeia = f"`{caso.cadeia}`" if caso.cadeia else "ε (vazia)"
                linhas.append(f"| {i} | {cadeia} | {esperado} | {resultado} | {'✅' if confere else '❌'} |")
            linhas.append("")
    linhas.insert(4, f"**Resultado: {total - falhas}/{total} cadeias com o resultado esperado.**\n")
    (PASTA_JFLAP / "resultado_jflap.md").write_text("\n".join(linhas), encoding="utf-8")
    print(f"JFLAP 7.1: {total - falhas}/{total} cadeias conferem com o esperado.")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
