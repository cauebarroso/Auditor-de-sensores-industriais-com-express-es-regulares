# Auditor Léxico de Telemetria de Sensores Industriais

Este projeto implementa uma ferramenta de linha de comando que funciona como um "firewall léxico". Ele analisa e audita pacotes de texto oriundos de sensores e atuadores industriais, utilizando Expressões Regulares estruturadas de acordo com as teorias de Linguagens Formais e Autômatos.

## Funcionalidades
A aplicação audita cinco padrões de comunicação, bloqueando pacotes malformatados:
1. ID do Dispositivo (Sensores e Atuadores)
2. Medições de Telemetria (Temperatura, Umidade e Pressão)
3. Comandos de Controle (Ordens de acionamento e ajuste)
4. Rotas de Rede (IPv4 com suporte a máscara CIDR)
5. Alertas de Log (Registros temporais de severidade)

O sistema possui:
* **Modo Interativo:** Onde o operador pode digitar ou colar um pacote diretamente no console e receber o diagnóstico instantâneo.
* **Modo de Lote (Arquivo):** Leitura de logs textuais inteiros gerando um relatório estatístico de pacotes íntegros e corrompidos.

## Requisitos
* Python 3.11+
* `pytest` (para execução da suíte de testes)
* Software JFLAP (para visualização dos Autômatos Finitos Não-Determinísticos)

## Estrutura do Repositório

```text
.
├── README.md                           # Visão geral e instruções de execução
├── Relatório_Técnico.md                # Documentação técnica formal completa
├── requirements.txt                    # Dependências do projeto (pytest)
├── .gitignore                          # Arquivos ignorados pelo Git
│
├── src/                                # Código-fonte da aplicação
│   ├── auditor.py                      # Firewall léxico (CLI interativa e lote)
│   ├── test_regex.py                   # Suíte de testes automatizados (60 testes)
│   ├── dados_exemplo.txt               # Amostra de pacotes válidos e corrompidos
│   └── build_jffs.py                   # Script de geração dos arquivos JFLAP
│
├── diagramas_jflap/                    # Autômatos Finitos Não-Determinísticos (AFN-ε)
│   ├── ER-01.jff                       # AFN-ε: ID do Dispositivo
│   ├── ER-02.jff                       # AFN-ε: Telemetria (Temp, Umid, Pres)
│   ├── ER-03.jff                       # AFN-ε: Comandos de Controle
│   ├── ER-04.jff                       # AFN-ε: Rotas IPv4/CIDR
│   └── ER-05.jff                       # AFN-ε: Alertas de Log ISO 8601
│
└── docs/                               # Materiais de referência e especificações
    ├── Lauda.txt                       # Diretrizes e critérios da avaliação
    ├── Plano de Ação + Análise Pré-mortem.docx
    └── GUIA_SINTAXE_EXPRESSOES_REGULARES_TRABALHO_LFA - FINAL.pdf
```

## Executando o Projeto

1. Clone o repositório e ative seu ambiente virtual (se necessário).
2. Execute o script principal:
   ```bash
   # Modo interativo com menu
   python src/auditor.py

   # Modo arquivo (lote) direto
   python src/auditor.py caminho/para/seu_arquivo_de_log.txt
   ```

## Instalação de Dependências

```bash
pip install -r requirements.txt
```

## Testes Automatizados (Pytest)
A suíte de validação cobre integralmente todas as expressões (6 cadeias aceitas e 6 cadeias rejeitadas para cada padrão, totalizando 60 testes rigorosos, incluindo casos-limites).

Para testar as restrições:
```bash
cd src
pytest -v
```

## Dados de Exemplo
O arquivo `src/dados_exemplo.txt` contém 29 pacotes de amostra (18 válidos e 11 inválidos/corrompidos) que podem ser usados para demonstração:

```bash
python src/auditor.py src/dados_exemplo.txt
```

## Contribuições dos Integrantes

| Integrante | Responsabilidades |
| :--- | :--- |
| *Nome 1* | *Descrever aqui* |
| *Nome 2* | *Descrever aqui* |
| *Nome 3* | *Descrever aqui* |

> **Nota:** Preencher esta tabela com os nomes completos e atribuições reais de cada membro da equipe antes da entrega.

## Declaração de Uso de Inteligência Artificial
Conforme estabelecido pela Resolução do curso de Ciência da Computação (CESUPA, 2026):
**Este trabalho utilizou a Inteligência Artificial Generativa (Antigravity) como ferramenta de apoio à programação, estruturação dos testes automatizados e auxílio na geração de diagramas JFLAP (AFN-λ), respeitando a autoria intelectual e os princípios éticos acadêmicos.** Todos os membros da equipe compreendem os códigos implementados, tendo total controle e capacidade de refatorá-los se necessário.

As tarefas em que a IA foi utilizada:
- Estruturação do código-fonte (`auditor.py`) e da suíte de testes (`test_regex.py`)
- Geração programática dos arquivos JFLAP (`.jff`) via script Python
- Organização e formatação do Relatório Técnico e do README
