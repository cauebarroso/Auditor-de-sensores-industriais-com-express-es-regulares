# Roteiro da apresentação (10 a 12 minutos)

As falas de cada slide também estão nas **anotações** do `Apresentacao.pptx`.

Cada ER tem a ficha completa do guia nos slides: **ficha** (finalidade, Σ, ER formal, sintaxe no
código e operadores), **AFNε** e **linguagem L + as 16 cadeias de teste**. Nos slides de testes, não
leia a tabela inteira: diga "as 16 cadeias estão aqui" e destaque um ou dois casos-limite.

| Slides | Quem | Tempo | Conteúdo |
| :-- | :-- | :-- | :-- |
| 1–4 | Augusto | 1 min 30 s | Problema, entradas/processamento/saídas, notação formal × código |
| 5–9 | Augusto | 2 min 30 s | ER-01 (ficha, AFNε e testes) e ER-02 (ficha, AFNε, testes) |
| 10–15 | Caue | 2 min 30 s | ER-03 e ER-04 (ficha, AFNε, testes) |
| 16–19 | César | 2 min | ER-05: ficha, data válida por mês, fecho de Kleene na mensagem, testes |
| 20 | Caue | 1 min | Como provamos que é a mesma linguagem (Thompson, equivalência, JFLAP) |
| 21 | César | 1 min 30 s | Demonstração ao vivo |
| 22–25 | Caue, César e todos | 1 min | Resultados dos testes, limitações, contribuições e uso de IA |

## Antes de começar

```bash
cd Auditor-de-sensores-industriais-com-express-es-regulares
python -m pytest -q                      # deve mostrar 319 passed
```

Deixe abertos: um terminal na pasta do projeto, o JFLAP com `automatos/jflap/ER-03.jff` e o
diagrama `automatos/diagramas/ER-05.svg` no navegador (dá para dar zoom).

## Demonstração (slide 21)

1. **Lote:** `python src/auditor.py dados/turno_caldeira.txt` → mostrar a taxa de conformidade, a
   telemetria extraída e os corrompidos. Abrir o filtro **6** (corrompidos com diagnóstico).
2. **Pacote rejeitado com apontador:** `python src/auditor.py --pacote "CMD ATU-VLV-0201 AJUSTAR 120%"`.
3. **Aceita e rejeitada no AFNε:** `python src/auditor.py --explicar "ATU-VLV-0420"` e depois
   `--explicar "ATU-A-1234"` → apontar no diagrama da ER-01 os estados que aparecem na tabela.
4. **JFLAP:** Input › Multiple Run → Load Inputs → `automatos/jflap/entradas/ER-03.txt` → Run Inputs.
   No JFLAP o espaço aparece como um rótulo em branco; o λ do JFLAP é o nosso ε.
5. Se o professor pedir uma cadeia nova: menu opção **2** (modo interativo) ou `--pacote "..."`.

## Perguntas prováveis

**Por que escrever `(r | ε)` em vez de `r?` na ER formal?**
`r?` é açúcar sintático; na notação estudada a opcionalidade é a união com a cadeia vazia. No AFNε,
é o desvio por movimento ε que pula o fragmento de `r`.

**O que é o fecho-ε e onde ele aparece?**
É o conjunto de estados alcançáveis só com movimentos ε. Na simulação (`--explicar`), cada linha
mostra o fecho-ε depois de ler o símbolo. Ex.: no início da ER-01 o conjunto é `{q0, q1, q2}`, porque
q0 tem ε para os ramos SEN e ATU.

**As linguagens são finitas ou infinitas?**
L₁ a L₄ são finitas (só usam repetições limitadas). L₅ é infinita porque a mensagem usa o fecho de
Kleene. O programa verifica isso: há um ciclo que lê símbolo em um caminho útil do AFNε só na ER-05.

**Validar o dia do mês não precisaria de algo além de ER?**
Não. O conjunto de pares mês-dia válidos é finito, e toda linguagem finita é regular. A ER-05 usa
uma união de três casos. Ano bissexto também seria regular (anos com 4 dígitos), só não foi incluído
para não multiplicar o tamanho do AFNε.

**Como vocês sabem que a ER formal e o código são a mesma linguagem?**
Os dois viram AFNε e o algoritmo percorre todos os pares de conjuntos de estados alcançáveis pela
mesma cadeia (construção de subconjuntos no produto). Se nenhum par discorda sobre aceitação, as
linguagens são iguais. Como o número de pares é finito, é uma prova, não um teste por amostragem.
O teste `test_verificador_detecta_divergencia_entre_formal_e_codigo` mostra que, com `([0-9] | ε)[0-9]`
no octeto, o algoritmo encontra um contraexemplo com zero à esquerda.

**Como o AFNε da ER-04 rejeita 256?**
Depois de ler `25`, restam duas continuações: o ramo `25[0-5]` (terceiro dígito de 0 a 5) ou o ponto,
porque o octeto `25` do ramo `([1-9] | ε)[0-9]` já terminou. O símbolo `6` não tem transição em
nenhuma delas e o conjunto de estados fica vazio. Para mostrar: `python src/auditor.py --explicar "256.0.0.1"`
termina com "coluna 3: símbolo '6' inesperado; esperado um símbolo de [0-5.]".

**Por que `[0-9]` e não `\d`?**
O guia pede classes explícitas: no Python, `\d` também aceita dígitos Unicode (ex.: `٣`), o que mudaria
o alfabeto. O nosso analisador rejeita `\d`, `\w`, `\s` e o ponto curinga.

**Por que a severidade não tem colchetes?**
O JFLAP 7.1 trata rótulos com `[` como intervalo e falha com o símbolo `[`. Sem colchetes, o `.jff`
reconhece exatamente a linguagem do código, sem símbolos substitutos.

**Por que o `.jff` tem tantas transições (26 para `[A-Z]`) em vez de um rótulo `[A-Z]`?**
O JFLAP 7.1 até aceita rótulos de intervalo, mas depois de uma transição desse tipo o simulador não
aplica o fecho-ε. Testamos: a versão com intervalos rejeitou 35 das 40 cadeias que deveriam ser
aceitas. Com um símbolo por transição, o `.jff` funciona em qualquer versão e dá 80/80.

## Se o professor pedir uma alteração ao vivo

Exemplo: "aceite modelos com 2 a 4 letras na ER-01" (procedimento testado).

1. Em `src/expressoes.py`, troque `[A-Z]{2,3}` por `[A-Z]{2,4}` em `PADRAO_ER_01`. Na ficha `ER01`, troque
   `definicoes=(DEF_ID,)` por uma definição própria com a nova ER formal:
   `("ID", "(SEN | ATU) - [A-Z][A-Z]([A-Z] | ε)([A-Z] | ε) - [0-9][0-9][0-9][0-9]")`.
   Não altere `DEF_ID`, que também é usada pela ER-05.
2. Rode `python -m pytest`. Falham exatamente os pontos afetados: o caso `SEN-ABCD-1234` (agora aceito),
   o `.jff` antigo e a mensagem de diagnóstico "mais de 3 letras". Se a ER formal não acompanhar o
   código, o teste de equivalência também falha e mostra uma cadeia que distingue as duas.
3. Em `tests/casos_teste.py`, transforme o caso em `aceita("SEN-ABCD-1234", ...)`; em
   `src/diagnostico.py` (`_causa_id`), troque `{4,}` por `{5,}` e o texto para "máximo 4" (e o trecho
   esperado em `tests/test_aplicacao.py`). Rode `python scripts/gerar_automatos.py` para gerar o novo
   `.jff` e o diagrama, e `python -m pytest` de novo.

## Como o código funciona (para estudar)

| Arquivo | O que explicar |
| :-- | :-- |
| `src/expressoes.py` | Os cinco padrões (`PADRAO_ER_0X`) e as fichas. A ER formal fica em `definicoes` + `formal`; `formal_para_python` traduz a ER formal para o Python só para os testes compararem. |
| `src/afn.py` | A classe `AFNe`: `fecho_epsilon` (estados alcançáveis só por ε), `passo` (lê um símbolo e aplica o fecho), `simular` (guarda o conjunto de estados após cada símbolo), `contraexemplo` (prova de equivalência) e `linguagem_infinita`. |
| `src/construtor_afn.py` | Lê o padrão (descida recursiva) e aplica Thompson: símbolo = uma transição; concatenação = encadear; união = ramos abertos e fechados por ε; `?` = desvio ε; `*` = laço ε; `{m,n}` = cópias. Recursos não regulares (`\d`, `.`, `^`, `\1`) são rejeitados. |
| `src/diagnostico.py` | Para um pacote rejeitado: adivinha qual ER ele tentou seguir, explica a causa e usa `simular` para achar a coluna onde o conjunto de estados ficou vazio. |
| `src/relatorio.py` e `src/auditor.py` | Leitura do arquivo, extração de campos, estatísticas, exportação, menu e linha de comando. |

Ideia central para a banca: **o AFNε não foi desenhado à mão**. Ele é construído a partir do padrão
do código pela construção de Thompson, exportado para o JFLAP e comparado com a ER formal por um
algoritmo que percorre todos os pares de estados possíveis. Por isso as cinco representações exigidas
(ER formal, slides, código, testes e AFNε) descrevem a mesma linguagem.
