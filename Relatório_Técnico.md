# Relatório Técnico
## Auditor Léxico de Telemetria de Sensores Industriais

**Disciplina:** Linguagens Formais e Autômatos  
**Curso:** Ciência da Computação — CESUPA  
**Linguagem de implementação:** Python 3.11+  
**Ferramentas:** módulo `re` (Python), `pytest`, JFLAP 7.1  

---

## 1. Descrição do Problema e Solução

Redes industriais de Controle e Aquisição de Dados (SCADA/IIoT) transmitem fluxos contínuos de pacotes de texto. A ausência de um mecanismo de auditoria léxica no nível da aplicação permite que pacotes corrompidos, malformatados ou injetados propaguem erros silenciosos para os controladores.

A solução proposta — o **Auditor Léxico de Telemetria** — atua como um *firewall* de camada léxica: uma ferramenta de linha de comando (CLI) que recebe esses pacotes por entrada interativa ou em lote (arquivo `.txt`) e, por meio de **cinco Expressões Regulares (ERs)** construídas com operadores regulares puros, classifica cada pacote como **íntegro** ou **corrompido**, emitindo diagnósticos ao operador e gerando relatórios estatísticos.

**Entradas:** Cadeias de texto representando pacotes de sensores e atuadores.  
**Processamento:** Correspondência exata (`re.fullmatch`) contra os cinco padrões léxicos.  
**Saídas:** Classificação, diagnóstico de erro e relatório de conformidade.

---

## 2. Fichas Formais das Expressões Regulares

> **Legenda de Alfabetos (base do projeto):**
> - **L** = {A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y, Z}
> - **D** = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}
> - **l** = {a, b, c, ..., z} (letras minúsculas — usadas exclusivamente na mensagem do log)

---

### ER-01 — ID do Dispositivo

**Nome e finalidade:** Identificar e extrair identificadores únicos de sensores (`SEN`) e atuadores (`ATU`) na rede.

**Alfabeto:** Σ₁ = L ∪ D ∪ {`-`}

**Descrição da linguagem reconhecida:** O conjunto de todas as cadeias sobre Σ₁ que começam com o prefixo literal `SEN` ou `ATU`, seguido de hífen (`-`), seguido de exatamente duas ou três letras maiúsculas, seguido de hífen (`-`), seguido de exatamente quatro dígitos decimais. A linguagem é finita em estrutura, embora infinita em combinação (pois L e D possuem múltiplos símbolos).

**Expressão Regular na notação formal:**

```
ER₁ = (SEN ∪ ATU) · - · LL(L ∪ ε) · - · DDDD
```

onde a concatenação de `LL(L ∪ ε)` gera exatamente as cadeias de 2 letras (`LL`) ou 3 letras (`LLL`), e `DDDD` representa a concatenação de 4 dígitos quaisquer.

**Sintaxe exatamente como aparece no código-fonte:**

```python
ER_01_ID = re.compile(r"(SEN|ATU)-[A-Z]{2,3}-[0-9]{4}")
```

**Explicação dos operadores utilizados:**

| Operador no código | Operador formal | Significado |
| :--- | :--- | :--- |
| `(SEN\|ATU)` | SEN ∪ ATU | **União**: aceita a cadeia `SEN` *ou* a cadeia `ATU` — não-determinismo. |
| `-` (literal) | · (concatenação implícita) | **Concatenação**: o hífen deve ocorrer nessa posição exata. |
| `[A-Z]` | L | **Classe de caractere**: representa a união de todos os 26 símbolos do alfabeto L. |
| `{2,3}` | LL ∪ LLL | **Repetição delimitada**: a construção `r{2,3}` é açúcar sintático para `rr ∪ rrr`. É estritamente regular. |
| `[0-9]` | D | **Classe de dígito**: representa a união dos 10 símbolos do alfabeto D. |
| `{4}` | DDDD | **Repetição exata**: `r{4}` é equivalente a `rrrr` (4 concatenações). |

**AFN-ε correspondente (ER-01):**

| # | Descrição | Transição |
| :--- | :--- | :--- |
| **Q** (Estados) | {q0, q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11, q12, q13, q14, q15, q16, q17} | — |
| **q0** | Estado inicial | — |
| **q17** | Estado final (aceitação) | — |
| q0 →(S) q1 | Ramo SEN | S |
| q1 →(E) q2 | | E |
| q2 →(N) q3 | | N |
| q0 →(A) q4 | Ramo ATU | A |
| q4 →(T) q5 | | T |
| q5 →(U) q6 | | U |
| **q3 →(ε) q7** | **Movimento vazio: une os ramos SEN e ATU** | ε |
| **q6 →(ε) q7** | **Movimento vazio: une os ramos SEN e ATU** | ε |
| q7 →(-) q8 | Primeiro hífen | `-` |
| q8 →(L) q9 | 1ª letra do campo tipo | L |
| q9 →(L) q10 | 2ª letra obrigatória | L |
| **q10 →(ε) q11** | **Movimento vazio: caminho para 2 letras** | ε |
| q10 →(L) q12 | 3ª letra opcional | L |
| **q12 →(ε) q11** | **Movimento vazio: caminho para 3 letras** | ε |
| q11 →(-) q13 | Segundo hífen | `-` |
| q13 →(D) q14 | 1º dígito | D |
| q14 →(D) q15 | 2º dígito | D |
| q15 →(D) q16 | 3º dígito | D |
| q16 →(D) q17 | 4º dígito → **estado final** | D |

Diagrama completo armazenado em: `diagramas_jflap/ER-01.jff`

**Testes (Pytest — `@pytest.mark.parametrize`):**

| # | Cadeia | Resultado | Justificativa |
| :--- | :--- | :---: | :--- |
| 1 | `SEN-TM-0001` | ✅ Aceita | Formato SEN, 2 letras, 4 dígitos |
| 2 | `ATU-VLV-0420` | ✅ Aceita | Formato ATU, 3 letras, 4 dígitos |
| 3 | `SEN-ABC-1234` | ✅ Aceita | Formato SEN, 3 letras |
| 4 | `ATU-XY-9999` | ✅ Aceita | Formato ATU, 2 letras |
| 5 | `SEN-XX-0000` | ✅ Aceita | Dígitos todos zero |
| 6 | `ATU-ZZZ-1111` | ✅ Aceita | 3 letras iguais |
| 7 | `sen-tm-0001` | ❌ Rejeitada | Letras minúsculas fora do alfabeto Σ₁ |
| 8 | `""` (vazia) | ❌ Rejeitada | **CASO-LIMITE:** cadeia vazia, não pertence à linguagem |
| 9 | `SEN-TM-00012` | ❌ Rejeitada | **CASO-LIMITE:** 5 dígitos — o {4} é exato |
| 10 | `SENO-TM-0001` | ❌ Rejeitada | Prefixo `SENO` não pertence à união (SEN ∪ ATU) |
| 11 | `ATU-A-1234` | ❌ Rejeitada | Apenas 1 letra no campo tipo — mínimo é 2 |
| 12 | `SEN-TM-123` | ❌ Rejeitada | Apenas 3 dígitos finais |

---

### ER-02 — Telemetria (Medições Físicas)

**Nome e finalidade:** Validar e extrair pacotes de leitura de sensor contendo uma medição física (Temperatura, Umidade ou Pressão) com sua respectiva unidade e dentro dos limites físicos admissíveis pela estrutura léxica.

**Alfabeto:** Σ₂ = L ∪ D ∪ {`-`, `:`, `=`, `.`, `%`, `h`, `P`, `a`, `C`}

**Descrição da linguagem reconhecida:** O conjunto de cadeias que iniciam com o ID de um sensor (conforme ER-01, restrito a `SEN`), seguido de `:`, e então *exatamente uma* das três medições: (1) `TEMP=` seguido de sinal negativo opcional, de um valor inteiro entre -199 e 199, e de uma casa decimal opcional, terminando em `C`; (2) `UMID=` seguido de um valor entre 0 e 100 com decimal opcional, terminando em `%`; (3) `PRES=` seguido de valor inteiro entre 850 e 1099, terminando em `hPa`.

**Expressão Regular na notação formal:**

```
ER₂ = SEN · - · LL(L ∪ ε) · - · DDDD · : ·
      ( TEMP · = · (- ∪ ε) · (1DD ∪ (D ∪ ε)D) · (.D ∪ ε) · C
      ∪ UMID · = · (100(.0 ∪ ε) ∪ (D ∪ ε)D(.D ∪ ε)) · %
      ∪ PRES · = · (8[5-9]D ∪ 9DD ∪ 10DD) · hPa )
```

**Sintaxe exatamente como aparece no código-fonte:**

```python
ER_02_TELEMETRIA = re.compile(
    r"SEN-[A-Z]{2,3}-[0-9]{4}:(TEMP=-?(1[0-9][0-9]|[1-9]?[0-9])(\.[0-9])?C"
    r"|UMID=(100(\.0)?|[1-9]?[0-9](\.[0-9])?)%"
    r"|PRES=(8[5-9][0-9]|9[0-9][0-9]|10[0-9][0-9])hPa)"
)
```

**Explicação dos operadores utilizados:**

| Operador no código | Operador formal | Significado |
| :--- | :--- | :--- |
| `(A\|B\|C)` externo | A ∪ B ∪ C | **União**: separa os três ramos de medição — não-determinismo do AFN-ε. |
| `-?` | (- ∪ ε) | **Opcionalidade**: `r?` é açúcar sintático para `r ∪ ε`. Permite sinal negativo. |
| `1[0-9][0-9]` | 1DD | **Concatenação + Classe**: temperatura de 100 a 199 (prefixo 1 + 2 dígitos). |
| `[1-9]?[0-9]` | (D\{1-9\} ∪ ε)D | **Classe restrita + Opcionalidade**: valores de 0 a 99. O `[1-9]?` evita `00`, `01`, etc. |
| `(\.[0-9])?` | (.D ∪ ε) | **Grupo opcional**: uma casa decimal, precedida de ponto literal escapado. |
| `\.` | `.` (literal) | **Escape**: o `\.` neutraliza o metacaractere `.` (que significaria "qualquer símbolo"). |
| `8[5-9][0-9]` | 8{5,6,7,8,9}D | **Classe com intervalo**: faixa de pressão 850–899 hPa. |

**AFN-ε correspondente (ER-02) — Estrutura Modular:**

O AFN-ε desta expressão reutiliza o módulo do ID de sensor da ER-01 (estados q0–q11) e adiciona a bifurcação tripla por movimentos vazios:

| Transição | Leitura | Descrição |
| :--- | :---: | :--- |
| q0 → ... → q11 | ID SEN | (mesmo módulo da ER-01, restrito ao ramo SEN) |
| q11 →(`:`) q12 | `:` | Delimitador após o ID |
| **q12 →(ε) q_t0** | ε | **Movimento vazio: abre ramo TEMP** |
| **q12 →(ε) q_u0** | ε | **Movimento vazio: abre ramo UMID** |
| **q12 →(ε) q_p0** | ε | **Movimento vazio: abre ramo PRES** |
| q_t0 → ... → q_tf | `TEMP=...C` | Ramo de temperatura (com estados internos de sinal e decimal) |
| q_u0 → ... → q_uf | `UMID=...%` | Ramo de umidade |
| q_p0 → ... → q_pf | `PRES=...hPa` | Ramo de pressão |
| **{q_tf, q_uf, q_pf}** | — | **Estados finais de aceitação** |

Diagrama completo armazenado em: `diagramas_jflap/ER-02.jff`

**Testes (Pytest):**

| # | Cadeia | Resultado | Justificativa |
| :--- | :--- | :---: | :--- |
| 1 | `SEN-TM-0001:TEMP=25.5C` | ✅ Aceita | Temperatura positiva com decimal |
| 2 | `SEN-TM-0001:TEMP=-10C` | ✅ Aceita | Temperatura negativa sem decimal |
| 3 | `SEN-AB-1234:UMID=100.0%` | ✅ Aceita | Umidade máxima com decimal |
| 4 | `SEN-AB-1234:UMID=5%` | ✅ Aceita | Umidade baixa sem decimal |
| 5 | `SEN-XX-9999:PRES=1013hPa` | ✅ Aceita | Pressão padrão atmosférica |
| 6 | `SEN-YY-0000:PRES=850hPa` | ✅ Aceita | Pressão no limite inferior |
| 7 | `SEN-TM-0001:TEMP=200C` | ❌ Rejeitada | **CASO-LIMITE:** 200 > 199 — fora do padrão ER₂ |
| 8 | `SEN-TM-0001:UMID=101%` | ❌ Rejeitada | **CASO-LIMITE:** 101% acima do máximo |
| 9 | `SEN-TM-0001:PRES=849hPa` | ❌ Rejeitada | **CASO-LIMITE:** 849 abaixo do limite |
| 10 | `SEN-TM-0001:TEMP=25.55C` | ❌ Rejeitada | Duas casas decimais — ER aceita apenas uma |
| 11 | `ATU-TM-0001:TEMP=25C` | ❌ Rejeitada | Prefixo `ATU` — telemetria só para `SEN` |
| 12 | `""` (vazia) | ❌ Rejeitada | **CASO-LIMITE:** cadeia vazia |

---

### ER-03 — Comando de Controle

**Nome e finalidade:** Validar ordens de acionamento e regulagem enviadas a atuadores (`ATU`) na rede industrial.

**Alfabeto:** Σ₃ = L ∪ D ∪ {`-`, ` ` (espaço), `%`}

**Descrição da linguagem reconhecida:** Cadeias que começam com o prefixo literal `CMD `, seguido do ID de um atuador (com `ATU`), seguido de espaço e então *exatamente um* dos comandos: `LIGAR`, `DESLIGAR`, `ABRIR`, `FECHAR`, ou `AJUSTAR N%` onde N é um inteiro entre 0 e 100.

**Expressão Regular na notação formal:**

```
ER₃ = CMD · ⎵ · ATU · - · LL(L ∪ ε) · - · DDDD · ⎵ ·
      (LIGAR ∪ DESLIGAR ∪ ABRIR ∪ FECHAR ∪ AJUSTAR · ⎵ · (100 ∪ (D\{1-9\} ∪ ε) · D) · %)
```

*(⎵ representa o caractere espaço literal)*

**Sintaxe exatamente como aparece no código-fonte:**

```python
ER_03_COMANDO = re.compile(
    r"CMD ATU-[A-Z]{2,3}-[0-9]{4} (LIGAR|DESLIGAR|ABRIR|FECHAR|AJUSTAR (100|[1-9]?[0-9])%)"
)
```

**Explicação dos operadores utilizados:**

| Operador no código | Operador formal | Significado |
| :--- | :--- | :--- |
| ` ` (espaço literal) | ⎵ | **Concatenação com símbolo específico**: o espaço faz parte da linguagem. Não usamos `\s` (não regular nativo). |
| `(LIGAR\|...\|AJUSTAR ...)` | LIGAR ∪ ... ∪ AJUSTAR... | **União de 5 ramos**: o AFN-ε bifurca em 5 caminhos por movimentos vazios a partir do estado após o ID. |
| `(100\|[1-9]?[0-9])` | 100 ∪ (D\{1-9\} ∪ ε)D | **União com restrição de intervalo**: aceita `100` exato ou valores de `0` a `99`. A ausência de `[1-9]?` antes do dígito final permitiria `00`–`09`, que são válidos como `0`–`9`. |
| `%` (literal) | % | **Símbolo terminal**: delimita a unidade do comando de ajuste. |

**AFN-ε correspondente (ER-03) — Estrutura:**

| Transição | Leitura | Descrição |
| :--- | :---: | :--- |
| q0 → q_cmd | `CMD ` | Prefixo fixo (4 símbolos concatenados) |
| q_cmd → ... → q_id | ID ATU | Módulo de ID do atuador (mesmo padrão da ER-01) |
| q_id →(` `) q_sep | ` ` | Espaço separador |
| **q_sep →(ε) q_L** | ε | **Movimento vazio: ramo LIGAR** |
| **q_sep →(ε) q_D** | ε | **Movimento vazio: ramo DESLIGAR** |
| **q_sep →(ε) q_A** | ε | **Movimento vazio: ramo ABRIR** |
| **q_sep →(ε) q_F** | ε | **Movimento vazio: ramo FECHAR** |
| **q_sep →(ε) q_J** | ε | **Movimento vazio: ramo AJUSTAR** |
| q_L → ... → q_Lf | `LIGAR` | Estado final deste ramo |
| q_D → ... → q_Df | `DESLIGAR` | Estado final |
| q_A → ... → q_Af | `ABRIR` | Estado final |
| q_F → ... → q_Ff | `FECHAR` | Estado final |
| q_J → ... → q_Jn | `AJUSTAR ` | Subcaminho de ajuste |
| q_Jn →(ε) q_J100 ou q_J2d | ε | Bifurcação `100` vs `0-99` |
| q_J100 → q_Jf | `100%` | Estado final |
| q_J2d → q_Jf | `(D?)D%` | Estado final |

Diagrama completo armazenado em: `diagramas_jflap/ER-03.jff`

**Testes (Pytest):**

| # | Cadeia | Resultado | Justificativa |
| :--- | :--- | :---: | :--- |
| 1 | `CMD ATU-VLV-0420 LIGAR` | ✅ Aceita | Comando simples de ligar |
| 2 | `CMD ATU-VLV-0420 DESLIGAR` | ✅ Aceita | Comando de desligar |
| 3 | `CMD ATU-XX-1234 ABRIR` | ✅ Aceita | Comando de abertura |
| 4 | `CMD ATU-XX-1234 FECHAR` | ✅ Aceita | Comando de fechamento |
| 5 | `CMD ATU-YY-9999 AJUSTAR 100%` | ✅ Aceita | Ajuste no máximo exato |
| 6 | `CMD ATU-YY-9999 AJUSTAR 5%` | ✅ Aceita | Ajuste de 1 dígito |
| 7 | `CMD ATU-VLV-0420 AJUSTAR 101%` | ❌ Rejeitada | **CASO-LIMITE:** 101 > 100, fora do intervalo |
| 8 | `CMD SEN-VLV-0420 LIGAR` | ❌ Rejeitada | `SEN` não recebe comandos (`ATU` obrigatório) |
| 9 | `CMD ATU-VLV-0420 PAUSAR` | ❌ Rejeitada | `PAUSAR` não pertence à união dos 5 comandos |
| 10 | `CMD ATU-VLV-0420 AJUSTAR %` | ❌ Rejeitada | Valor numérico ausente antes de `%` |
| 11 | `CMD ATU-VLV-0420 LIGAR ` | ❌ Rejeitada | **CASO-LIMITE:** espaço final não pertence à linguagem |
| 12 | `""` (vazia) | ❌ Rejeitada | Cadeia vazia |

---

### ER-04 — Rota de Rede IPv4/CIDR

**Nome e finalidade:** Validar endereços IPv4 e rotas de sub-rede em notação CIDR, bloqueando octetos fora do intervalo 0–255 e máscaras fora de 0–32.

**Alfabeto:** Σ₄ = D ∪ {`.`, `/`}

**Descrição da linguagem reconhecida:** Cadeias formadas por quatro octetos decimais (cada um de 0 a 255) separados pelo símbolo `.`, seguidos opcionalmente pelo símbolo `/` e um inteiro de 0 a 32. Um "octeto" é definido formalmente como: `255 | 25[0-5] | 2[0-4]D | 1DD | [1-9]D | D` (onde D representa qualquer dígito). A linguagem garante que a representação decimal é não-ambígua (sem zeros à esquerda).

**Expressão Regular na notação formal:**

Definindo o padrão de octeto como `OCT`:

```
OCT = (2 · 5 · (0|1|2|3|4|5))
    ∪ (2 · (0|1|2|3|4) · D)
    ∪ (1 · D · D)
    ∪ ((1|2|3|4|5|6|7|8|9) · D)
    ∪ D

ER₄ = (OCT · .) · (OCT · .) · (OCT · .) · OCT · (/ · CIDR ∪ ε)

CIDR = (3 · (0|1|2)) ∪ ((1|2 ∪ ε) · D)
```

**Sintaxe exatamente como aparece no código-fonte:**

```python
ER_04_IPV4_CIDR = re.compile(
    r"((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}"
    r"(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])"
    r"(/(3[0-2]|[12]?[0-9]))?"
)
```

**Explicação dos operadores utilizados:**

| Operador no código | Operador formal | Significado |
| :--- | :--- | :--- |
| `(OCT\.){3}` | (OCT · .){3} | **Repetição exata de grupo**: o grupo contendo o padrão de octeto + ponto se repete exatamente 3 vezes, gerando os 3 primeiros octetos. Equivale a `(OCT\.)(OCT\.)(OCT\.)`. |
| `25[0-5]` | 25(0∪1∪2∪3∪4∪5) | **Classe de intervalo restrito**: cobre 250–255 sem ultrapassar 255. |
| `2[0-4][0-9]` | 2(0∪1∪2∪3∪4)D | **Dupla restrição**: cobre 200–249 sem conflitar com o caso acima. |
| `1[0-9][0-9]` | 1DD | **Prefixo fixo**: cobre 100–199. |
| `[1-9]?[0-9]` | (D\{1-9\}∪ε)D | **Opcionalidade com restrição**: cobre 0–99 sem zeros à esquerda (ex: `01` seria inválido). |
| `\.` | `.` (literal) | **Escape de metacaractere**: ponto como separador de octeto. |
| `(/(...))?` | (/ · CIDR ∪ ε) | **Opcionalidade de grupo**: a máscara CIDR é opcional. |
| `3[0-2]` | 3(0∪1∪2) | **Classe restrita**: cobre 30, 31, 32 — máscara `/32` é a mais específica. |

**AFN-ε correspondente (ER-04):**

| Transição | Leitura | Descrição |
| :--- | :---: | :--- |
| q0 →(OCT) q1 | 1º Octeto | Módulo de octeto (4 ramos internos por ε) |
| q1 →(`.`) q2 | `.` | Ponto separador |
| q2 →(OCT) q3 | 2º Octeto | |
| q3 →(`.`) q4 | `.` | |
| q4 →(OCT) q5 | 3º Octeto | |
| q5 →(`.`) q6 | `.` | |
| **q6 →(OCT) q7** | 4º Octeto | **Estado final se sem CIDR** |
| **q7 →(ε) q_fim** | ε | **Movimento vazio para aceitação sem CIDR** |
| q7 →(`/`) q8 | `/` | Inicia opção CIDR |
| q8 →(CIDR) q9 | Máscara 0–32 | |
| **q9 = estado final** | — | **Aceitação com CIDR** |

Diagrama completo armazenado em: `diagramas_jflap/ER-04.jff`

**Testes (Pytest):**

| # | Cadeia | Resultado | Justificativa |
| :--- | :--- | :---: | :--- |
| 1 | `192.168.0.1` | ✅ Aceita | IP privado classe C |
| 2 | `10.0.0.1/8` | ✅ Aceita | IP com máscara CIDR |
| 3 | `255.255.255.255` | ✅ Aceita | Broadcast máximo |
| 4 | `0.0.0.0` | ✅ Aceita | Endereço padrão mínimo |
| 5 | `172.16.254.1/32` | ✅ Aceita | Host individual com máscara |
| 6 | `192.168.1.1/24` | ✅ Aceita | Rede privada com sub-rede |
| 7 | `256.0.0.1` | ❌ Rejeitada | **CASO-LIMITE:** 256 > 255, primeiro octeto inválido |
| 8 | `192.168.0` | ❌ Rejeitada | Apenas 3 octetos — faltam o 4º |
| 9 | `192.168.0.1/33` | ❌ Rejeitada | **CASO-LIMITE:** máscara 33 > 32 |
| 10 | `192.168.01.1` | ❌ Rejeitada | Zero à esquerda (`01`) — não pertence à linguagem |
| 11 | `10.0.0.1/` | ❌ Rejeitada | Barra sem máscara |
| 12 | `""` (vazia) | ❌ Rejeitada | Cadeia vazia |

---

### ER-05 — Alerta de Log (Severidade)

**Nome e finalidade:** Extrair e validar registros de eventos com timestamp ISO-8601, nível de severidade estruturado e identificação do equipamento de origem.

**Alfabeto:** Σ₅ = L ∪ l ∪ D ∪ {`-`, `T`, `:`, `[`, `]`, ` `, `_`, `.`}

**Descrição da linguagem reconhecida:** Cadeias que seguem o formato de registro de auditoria: um timestamp no formato `AAAA-MM-DDThh:mm:ss` (com restrições sobre mês 01–12, dia 01–31, hora 00–23, minuto/segundo 00–59), seguido de espaço e tag de severidade entre colchetes (`[INFO]`, `[WARN]`, `[ERROR]` ou `[CRIT]`), seguido do ID de um dispositivo (SEN ou ATU) e de uma mensagem descritiva de 1 a 60 caracteres.

**Expressão Regular na notação formal:**

```
ER₅ = DDDD · - · MES · - · DIA · T · HORA · : · MIN_SEG · : · MIN_SEG · ⎵ ·
      [ · (INFO ∪ WARN ∪ ERROR ∪ CRIT) · ] · ⎵ ·
      (SEN ∪ ATU) · - · LL(L ∪ ε) · - · DDDD · : · ⎵ · MSG{1,60}

MES     = (0 · (1∪2∪3∪4∪5∪6∪7∪8∪9)) ∪ (1 · (0∪1∪2))
DIA     = (0 · (1∪..∪9)) ∪ ((1∪2) · D) ∪ (3 · (0∪1))
HORA    = ((0∪1) · D) ∪ (2 · (0∪1∪2∪3))
MIN_SEG = (0∪1∪2∪3∪4∪5) · D
MSG     = L ∪ l ∪ D ∪ ⎵ ∪ _ ∪ . ∪ -
```

**Sintaxe exatamente como aparece no código-fonte:**

```python
ER_05_ALERTA_LOG = re.compile(
    r"[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])"
    r"T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r" \[(INFO|WARN|ERROR|CRIT)\]"
    r" (SEN|ATU)-[A-Z]{2,3}-[0-9]{4}: [A-Za-z0-9 _.-]{1,60}"
)
```

**Explicação dos operadores utilizados:**

| Operador no código | Operador formal | Significado |
| :--- | :--- | :--- |
| `[0-9]{4}` | DDDD | **Classe + Repetição exata**: 4 dígitos para o ano. |
| `(0[1-9]\|1[0-2])` | MES | **União com restrição**: `0[1-9]` cobre Jan–Set; `1[0-2]` cobre Out–Dez. Bloqueia mês 00 e 13+. |
| `(0[1-9]\|[12][0-9]\|3[01])` | DIA | **União tripla**: `[12][0-9]` cobre dias 10–29; `3[01]` cobre 30 e 31. Bloqueia dia 00 e 32+. |
| `([01][0-9]\|2[0-3])` | HORA | **União com teto**: `[01][0-9]` para 00–19; `2[0-3]` para 20–23. Bloqueia hora 24. |
| `[0-5][0-9]` | MIN_SEG | **Classe dupla**: dígito das dezenas restrito a 0–5 (minutos e segundos válidos). |
| `\[` e `\]` | `[` e `]` (literais) | **Escape**: colchetes fazem parte da sintaxe, não são operadores de classe aqui. |
| `[A-Za-z0-9 _.-]{1,60}` | MSG{1,60} | **Classe ampla + Repetição**: define o alfabeto da mensagem livre. `{1,60}` garante pelo menos 1 caractere e no máximo 60 (caso-limite). |

**AFN-ε correspondente (ER-05):**

| Transição | Leitura | Descrição |
| :--- | :---: | :--- |
| q0 →(DDDD) q_a | Ano | 4 transições de dígito |
| q_a →(`-`) q_b | `-` | |
| q_b →(MES) q_c | Mês | Bifurcação ε interna (01–09 vs 10–12) |
| q_c →(`-`) q_d | `-` | |
| q_d →(DIA) q_e | Dia | Bifurcação ε interna (3 ramos) |
| q_e →(`T`) q_f | `T` | Separador ISO |
| q_f →(HORA) q_g | Hora | Bifurcação ε interna |
| q_g →(`:`) q_h | `:` | |
| q_h →(MIN_SEG) q_i | Minuto | |
| q_i →(`:`) q_j | `:` | |
| q_j →(MIN_SEG) q_k | Segundo | |
| q_k →(` `) q_l | ` ` | Espaço separador |
| q_l →(`[`) q_m | `[` | Abre colchete literal |
| **q_m →(ε) q_INFO** | ε | **Movimento vazio: ramo INFO** |
| **q_m →(ε) q_WARN** | ε | **Movimento vazio: ramo WARN** |
| **q_m →(ε) q_ERROR** | ε | **Movimento vazio: ramo ERROR** |
| **q_m →(ε) q_CRIT** | ε | **Movimento vazio: ramo CRIT** |
| {q_INFO_f ... q_CRIT_f} →(ε) q_n | ε | **Movimento vazio: une os 4 ramos** |
| q_n →(`]`) q_o | `]` | Fecha colchete literal |
| q_o →(` `) q_p | ` ` | Espaço |
| q_p →(ε) q_SEN / q_ATU | ε | **Movimento vazio: bifurca SEN/ATU** |
| ... →(ε) q_id | ε | Módulo de ID compartilhado |
| q_id →(`:`) q_q | `:` | |
| q_q →(` `) q_r | ` ` | |
| **q_r →(MSG) q_r** | MSG | **Auto-laço**: leitura da mensagem (loop regular) |
| **q_r = estado final** (com ≥1 leitura) | — | **Estado final (aceitação)** |

Diagrama completo armazenado em: `diagramas_jflap/ER-05.jff`

**Testes (Pytest):**

| # | Cadeia | Resultado | Justificativa |
| :--- | :--- | :---: | :--- |
| 1 | `2026-09-30T08:15:00 [INFO] SEN-TM-0001: leitura normal` | ✅ Aceita | Log informativo padrão |
| 2 | `2026-12-31T23:59:59 [CRIT] ATU-XX-9999: falha critica` | ✅ Aceita | Log crítico no limite máximo do dia/hora |
| 3 | `2026-01-01T00:00:00 [WARN] SEN-AB-1234: bateria fraca` | ✅ Aceita | Timestamps mínimos válidos |
| 4 | `2026-02-28T12:30:45 [ERROR] ATU-VLV-0420: travamento_123` | ✅ Aceita | Mensagem com underscore e números |
| 5 | `9999-12-31T23:59:59 [INFO] SEN-XY-1234: ok` | ✅ Aceita | Ano futuro máximo e mensagem mínima |
| 6 | `2026-10-15T14:22:10 [INFO] SEN-ZZ-0000: .` | ✅ Aceita | Mensagem de 1 caractere (ponto) |
| 7 | `2026-13-01T10:00:00 [INFO] SEN-TM-0001: ok` | ❌ Rejeitada | **CASO-LIMITE:** mês 13 fora de `(0[1-9]\|1[0-2])` |
| 8 | `2026-09-32T10:00:00 [INFO] SEN-TM-0001: ok` | ❌ Rejeitada | **CASO-LIMITE:** dia 32 fora de `3[01]` |
| 9 | `2026-09-30T24:00:00 [INFO] SEN-TM-0001: ok` | ❌ Rejeitada | **CASO-LIMITE:** hora 24 fora de `2[0-3]` |
| 10 | `2026-09-30T08:15:00 [DEBUG] SEN-TM-0001: ok` | ❌ Rejeitada | `DEBUG` não pertence à união dos 4 níveis |
| 11 | `2026-09-30T08:15:00 [INFO] SEN-TM-0001: ` | ❌ Rejeitada | **CASO-LIMITE:** mensagem vazia — `{1,60}` exige ≥1 |
| 12 | `""` (vazia) | ❌ Rejeitada | Cadeia vazia |

---

## 3. Consistência entre as Representações

Conforme exigido pela Lauda (item 25): *"A expressão formal, a expressão apresentada nos slides, o padrão implementado no código, os testes e o AFN-ε deverão representar a mesma linguagem."*

| ER | ER Formal | Código Python | Pytest | JFLAP (.jff) | Linguagem idêntica? |
| :--- | :---: | :---: | :---: | :---: | :---: |
| ER-01 | ✅ | ✅ | ✅ | ✅ | ✅ |
| ER-02 | ✅ | ✅ | ✅ | ✅ | ✅ |
| ER-03 | ✅ | ✅ | ✅ | ✅ | ✅ |
| ER-04 | ✅ | ✅ | ✅ | ✅ | ✅ |
| ER-05 | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 4. Limitações Declaradas

Conforme previsto no Plano de Ação:

1. **Validação semântica:** O sistema audita a camada **léxica e estrutural** dos pacotes. Um sensor enviando `TEMP=199C` é aceito lexicamente, mesmo que aquela temperatura seja física e logicamente impossível para o equipamento. O sistema declara *conformidade morfológica*, não *validade física*.

2. **Camada OSI:** O Auditor atua na **camada de aplicação** (Layer 7 textual), processando fluxos de texto. Não realiza inspeção de tráfego binário TCP/IP, como firewalls de estado tradicionais.

3. **JFLAP e legendas:** Por limitação de legibilidade do JFLAP (52 transições para `[A-Za-z]` por estado), os autômatos utilizam rótulos consolidados (`L`, `D`, `OCT`, `MSG`) conforme explicitado neste relatório. As linguagens reconhecidas são idênticas às das ERs formais.

4. **Dia 31 para todos os meses (ER-05):** A ER aceita `2026-02-31`, pois a validação de dias por mês exigiria lógica semântica não alcançável por Autômatos Finitos.

---

## 5. Uso de Inteligência Artificial

Conforme exigido pela **Resolução de Uso de IA — BCC CESUPA 2026** e pela Lauda (item sobre Uso de Inteligência Artificial):

A ferramenta **Antigravity (Google DeepMind)** foi utilizada como apoio nas seguintes tarefas:
- Estruturação do código-fonte (`auditor.py`) e da suíte de testes (`test_regex.py`)
- Geração programática dos arquivos JFLAP (`.jff`) via script Python
- Organização e formatação deste relatório técnico

**Todos os membros da equipe compreendem, explicam e são capazes de modificar integralmente** os códigos e expressões regulares produzidos. O projeto é de autoria intelectual da equipe, tendo a IA atuado como ferramenta de apoio técnico e produtividade.

---

*Fim do Relatório Técnico*
