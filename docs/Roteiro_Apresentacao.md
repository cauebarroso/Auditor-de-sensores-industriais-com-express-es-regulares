# Roteiro da apresentação (10 a 12 minutos)

As falas de cada slide também estão nas **anotações** do `Apresentacao.pptx`.

| Slides | Quem | Tempo | Conteúdo |
| :-- | :-- | :-- | :-- |
| 1–4 | Augusto | 2 min 30 s | Problema, entradas/processamento/saídas, notação formal × código |
| 5–7 | Augusto | 2 min | ER-01 e ER-02 (ER formal, código, AFNε) |
| 8–9 | Caue | 2 min | ER-03 e ER-04 |
| 10–12 | César | 2 min 30 s | ER-05: data válida por mês e fecho de Kleene na mensagem |
| 13 | Caue | 1 min 30 s | Como provamos que é a mesma linguagem (Thompson, equivalência, JFLAP) |
| 14 | César | 2 min | Demonstração ao vivo |
| 15–17 | Caue e César | 1 min 30 s | Testes, limitações, contribuições e uso de IA |

## Antes de começar

```bash
cd Auditor-de-sensores-industriais-com-express-es-regulares
python -m pytest -q                      # deve mostrar 314 passed
```

Deixe abertos: um terminal na pasta do projeto, o JFLAP com `automatos/jflap/ER-03.jff` e o
diagrama `automatos/diagramas/ER-05.svg` no navegador (dá para dar zoom).

## Demonstração (slide 14)

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

## Se o professor pedir uma alteração ao vivo

Exemplo: "aceite modelos com 2 a 4 letras na ER-01".

1. Em `src/expressoes.py`, troque `[A-Z]{2,3}` por `[A-Z]{2,4}` em `PADRAO_ER_01` e ajuste a ER formal
   em `DEF_ID`: `[A-Z][A-Z]([A-Z] | ε)([A-Z] | ε)`. Para mudar só a ER-01, crie uma definição separada
   em vez de alterar `DEF_ID`, que também é usada pela ER-05.
2. Rode `python -m pytest`. Os testes mostram o que mudou (ex.: `SEN-ABCD-1234` passa a ser aceita), e
   o teste de equivalência confirma que a ER formal acompanha o código.
3. Atualize o caso em `tests/casos_teste.py` e rode `python scripts/gerar_automatos.py` para gerar o
   novo `.jff` e o novo diagrama.
