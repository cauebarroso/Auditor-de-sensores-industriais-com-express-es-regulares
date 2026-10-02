"""
Conteúdo textual das fichas que não pode ser derivado automaticamente do
código: tabela de equivalência (atalho do código -> operador formal) e
limitações/possíveis falsos resultados de cada ER.
"""

EQUIVALENCIAS = {
    "ER-01": [
        ("(SEN|ATU)", "(SEN | ATU)", "União de duas palavras. No AFNε: dois ramos abertos e fechados por movimentos ε."),
        ("-", "-", "Concatenação com o símbolo hífen (fora de uma classe, '-' não é operador)."),
        ("[A-Z]", "[A-Z] = (A | B | … | Z)", "Classe finita: união de 26 símbolos. No .jff, 26 transições paralelas."),
        ("[A-Z]{2,3}", "[A-Z][A-Z]([A-Z] | ε)", "Repetição limitada: r{2,3} = rr | rrr = rr(r | ε)."),
        ("[0-9]{4}", "[0-9][0-9][0-9][0-9]", "Repetição exata: r{4} é a concatenação de 4 cópias de r."),
        ("re.fullmatch", "—", "Exige que a cadeia inteira pertença a L (equivale às âncoras ^…$, que não são símbolos de Σ)."),
    ],
    "ER-02": [
        ("SEN-[A-Z]{2,3}-[0-9]{4}", "⟨SID⟩", "ID restrito a sensores: o ramo ATU da ER-01 é removido."),
        ("(TEMP=…|UMID=…|PRES=…)", "(⟨TEMP⟩ | ⟨UMID⟩ | ⟨PRES⟩)", "União de três ramos, um por grandeza física."),
        ("-?", "(- | ε)", "Opcionalidade: r? = (r | ε). Permite temperatura negativa."),
        ("1[0-9][0-9]", "1[0-9][0-9]", "Inteiros de 100 a 199."),
        ("[1-9]?[0-9]", "([1-9] | ε)[0-9]", "Inteiros de 0 a 99 sem zero à esquerda (rejeita 05)."),
        ("(\\.[0-9])?", "⟨DEC⟩ = .[0-9] | ε", "Casa decimal opcional. O escape \\. torna o ponto literal; sem ele, '.' seria qualquer caractere."),
        ("100(\\.0)?", "100(.0 | ε)", "Umidade máxima: só 100 ou 100.0 (rejeita 100.5)."),
        ("8[5-9][0-9]|9[0-9][0-9]|10[0-9][0-9]", "8[5-9][0-9] | 9[0-9][0-9] | 10[0-9][0-9]", "Pressão de 850 a 1099 hPa: três intervalos disjuntos."),
    ],
    "ER-03": [
        (" (espaço)", "⎵", "O espaço é um símbolo de Σ₃. Não usamos \\s, que também aceitaria tabulação e quebra de linha."),
        ("ATU-[A-Z]{2,3}-[0-9]{4}", "⟨AID⟩", "ID restrito a atuadores."),
        ("(LIGAR|DESLIGAR|ABRIR|FECHAR|AJUSTAR …)", "(LIGAR | DESLIGAR | ABRIR | FECHAR | AJUSTAR ⎵ ⟨PCT⟩ %)",
         "União de cinco ações. No AFNε: cinco ramos a partir de um estado, por movimentos ε."),
        ("(100|[1-9]?[0-9])", "⟨PCT⟩ = 100 | ([1-9] | ε)[0-9]", "Percentual de 0 a 100 sem zero à esquerda."),
        ("%", "%", "Símbolo literal que encerra o ajuste."),
    ],
    "ER-04": [
        ("(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])", "⟨OCT⟩",
         "Octeto de 0 a 255 dividido em faixas disjuntas: 250–255, 200–249, 100–199 e 0–99."),
        ("(…\\.){3}", "⟨OCT⟩.⟨OCT⟩.⟨OCT⟩.", "Repetição exata de um grupo: 3 cópias de (octeto seguido de ponto)."),
        ("\\.", ".", "Escape: o ponto do código vira o símbolo literal '.' do alfabeto."),
        ("(/(3[0-2]|[12]?[0-9]))?", "(/⟨MASC⟩ | ε)", "Máscara CIDR opcional de /0 a /32."),
    ],
    "ER-05": [
        ("[0-9]{4}", "[0-9][0-9][0-9][0-9]", "Ano com 4 dígitos (repetição exata)."),
        ("((0[1-9]|1[0-2])-(0[1-9]|[12][0-9])|(0[13-9]|1[0-2])-30|(0[13578]|1[02])-31)", "MM-DD de ⟨DATA⟩",
         "União de três casos: dias 01–29 em qualquer mês; dia 30 exceto fevereiro; dia 31 só nos meses de 31 dias."),
        ("([01][0-9]|2[0-3])", "([01][0-9] | 2[0-3])", "Hora de 00 a 23."),
        ("[0-5][0-9]", "[0-5][0-9]", "Minuto e segundo de 00 a 59."),
        ("(INFO|WARN|ERROR|CRIT)", "⟨SEV⟩", "União dos quatro níveis de severidade."),
        ("(SEN|ATU)-[A-Z]{2,3}-[0-9]{4}", "⟨ID⟩", "Reuso da ER-01: linguagens regulares são fechadas sob concatenação."),
        ("[A-Za-z0-9_.-]+", "⟨PAL⟩ = c c*", "Fecho positivo: r+ = rr*. Dentro da classe, '.' é literal e o '-' final também."),
        ("( [A-Za-z0-9_.-]+)*", "(⎵⟨PAL⟩)*", "Fecho de Kleene: zero ou mais palavras adicionais, cada uma precedida de um espaço."),
    ],
}

LIMITES = {
    "ER-01": [
        "A validação é léxica: um ID bem formado é aceito mesmo que o dispositivo não exista no cadastro da planta.",
        "O número de série 0000 é aceito; reservá-lo exigiria apenas mais um ramo na união, mas não é regra do domínio adotado.",
    ],
    "ER-02": [
        "Possível falso positivo: −0C e −0.0C (zero negativo) são aceitos, pois o sinal opcional precede qualquer valor.",
        "Possível falso negativo: leituras legítimas fora da faixa (ex.: caldeira acima de 199.9 °C) são bloqueadas; a faixa é fixa na ER.",
        "Umidade 100.00 é rejeitada (no máximo uma casa decimal); a ER não verifica coerência física entre leituras.",
    ],
    "ER-03": [
        "Não verifica se o atuador suporta a ação (ex.: AJUSTAR em uma bomba que só liga/desliga) nem o estado atual do equipamento.",
        "O espaço é exatamente um; comandos com espaços duplos são rejeitados (o programa só remove espaços nas extremidades da linha).",
    ],
    "ER-04": [
        "Endereços reservados (0.0.0.0, 255.255.255.255) são aceitos: a ER valida a forma, não o uso do endereço.",
        "Não confere se o endereço é a rede da máscara (10.0.0.1/8 é aceito embora a rede seja 10.0.0.0/8).",
    ],
    "ER-05": [
        "29 de fevereiro é aceito em qualquer ano. Verificar ano bissexto também seria REGULAR (o ano tem 4 dígitos, logo o conjunto é finito), mas multiplicaria o tamanho do AFNε.",
        "Ano 0000 é aceito; não há fuso horário (o carimbo é tratado como hora local da planta).",
        "A mensagem usa apenas ASCII (sem acentos) e não tem limite de tamanho: L₅ é infinita.",
    ],
}
