# ALL FOR ONE

O **ALL FOR ONE** é um gerenciador de plugins para engenharia reversa e modding de jogos.
A aplicação centraliza, em uma única interface, ferramentas para:

- Extrair arquivos de contêineres proprietários.
- Reimportar/reempacotar conteúdos após edição.
- Converter dados específicos (texto, recursos, estruturas auxiliares).
- Organizar fluxos de trabalho com plugins por jogo ou formato.

## Motivo da aplicação

Este projeto existe para reduzir o trabalho manual de quem traduz, modifica ou pesquisa arquivos de jogos.
Em vez de abrir scripts isolados, o usuário escolhe um plugin na interface e executa as ações necessárias de forma padronizada.

## Como funciona

- O aplicativo carrega plugins Python da pasta `plugins/`.
- Cada plugin define nome, descrição, opções e comandos de execução.
- A interface permite trocar idioma, atualizar lista de plugins e acompanhar logs do processo.

## Requisitos

- Python 3.10+
- Dependência principal: `flet` (a aplicação valida a versão recomendada automaticamente na inicialização).

## Execução

No diretório do projeto:

```bash
python ALL_FOR_ONE.py
```

## Estrutura principal

- `ALL_FOR_ONE.py`: interface, carregamento e execução de plugins.
- `plugins/`: ferramentas especializadas por jogo/formato.
- `banners/`: imagens usadas no cabeçalho de cada plugin.

## Observação

Os plugins podem manipular formatos proprietários. Sempre trabalhe com cópias de segurança dos arquivos originais.
