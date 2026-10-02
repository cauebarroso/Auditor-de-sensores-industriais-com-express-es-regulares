"""
Executa os arquivos .jff no PRÓPRIO motor do JFLAP 7.1 e confere o resultado
de cada cadeia de teste com o esperado (tests/casos_teste.py).

Pré-requisitos: Java (JDK) e o arquivo JFLAP7.1.jar (https://www.jflap.org).
Uso (na raiz do repositório):
  python scripts/verificar_jflap.py caminho/para/JFLAP7.1.jar

Gera automatos/jflap/resultado_jflap.md com a tabela de resultados.
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


def main() -> int:
    if len(sys.argv) != 2 or not Path(sys.argv[1]).is_file():
        sys.exit("Uso: python scripts/verificar_jflap.py caminho/para/JFLAP7.1.jar")
    jar = str(Path(sys.argv[1]).resolve())
    separador = ";" if sys.platform == "win32" else ":"

    with tempfile.TemporaryDirectory() as pasta:
        subprocess.run([executavel("javac"), "-nowarn", "-cp", jar, "-d", pasta,
                        str(RAIZ / "scripts" / "jflap" / "TestaJFLAP.java")],
                       check=True, capture_output=True)
        linhas = ["# Execução dos AFNε no motor do JFLAP 7.1", "",
                  "Gerado por `scripts/verificar_jflap.py`: cada `.jff` foi carregado pelo próprio "
                  "JFLAP (`file.XMLCodec`) e simulado com `FSAStepWithClosureSimulator`, o mesmo "
                  "simulador usado em *Input > Multiple Run*.", ""]
        total = falhas = 0
        for er in EXPRESSOES:
            saida = subprocess.run(
                [executavel("java"), "-Djava.awt.headless=true", "-cp", f"{jar}{separador}{pasta}",
                 "TestaJFLAP", str(PASTA_JFLAP / f"{er.codigo}.jff"),
                 str(PASTA_JFLAP / "entradas" / f"{er.codigo}.txt")],
                check=True, capture_output=True, text=True).stdout.split()
            linhas += [f"## {er.codigo} — {er.nome}", "",
                       "| # | Cadeia | Esperado | JFLAP | Confere |", "| --: | :-- | :-: | :-: | :-: |"]
            for i, (caso, resultado) in enumerate(zip(CASOS[er.codigo], saida, strict=True), start=1):
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
