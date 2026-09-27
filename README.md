# Operação XPTO: da base bruta à verdade analítica (Vendas, E-commerce)

**Objetivo do projeto:** preparar a base de vendas da XPTO para análise, com leitura direta da fonte, *profiling*, diagnóstico de qualidade, limpeza rastreável, criação de atributos e respostas a perguntas de negócio, tudo em um notebook reprodutível para o Google Colab.

**Autor:** Vinicius Machado

## Estrutura dos arquivos

| Arquivo | Descrição |
|---|---|
| `XPTO_Preparacao_Dados_Vinicius_Machado.ipynb` | Notebook principal, com as seções 1 a 11 e o checklist final, entregue já executado e com as saídas |
| `BaseVendasXPTO_CLEAN_Vinicius_Machado.csv` | Base final tratada: 28.504 linhas × 38 colunas, com `sep=";"`, `decimal=","` e `encoding="utf-8-sig"` |
| `Relatorio_Qualidade_Vinicius_Machado.md` | Relatório de qualidade: problemas, evidências, decisões, tratamentos e impacto |
| `README.md` | Este arquivo |
| `_ferramentas/` (opcional) | Scripts auxiliares do autor: `build_notebook.py` gera o `.ipynb` a partir das células escritas em `secoes_*.py`, e `executar_notebook.py` o executa do zero. **Não são necessários** para reproduzir o trabalho: o notebook é autossuficiente |

## Como executar no Google Colab, do zero

1. Acesse [colab.research.google.com](https://colab.research.google.com) e escolha **Arquivo → Fazer upload de notebook**.
2. Selecione `XPTO_Preparacao_Dados_Vinicius_Machado.ipynb`.
3. Escolha **Ambiente de execução → Executar tudo** (ou `Ctrl + F9`).
4. Ao final, o arquivo `BaseVendasXPTO_CLEAN_Vinicius_Machado.csv` aparece no painel **Arquivos** (ícone de pasta, à esquerda). Para baixá-lo, clique com o botão direito no arquivo, ou descomente a linha `files.download(...)` da seção 10.2.

Nenhum *upload* de dados é necessário. A base é lida **diretamente da URL** pelo próprio código:

```
https://raw.githubusercontent.com/alvaroriz/datascience_datasets/refs/heads/main/BaseVendasXPTO.csv
```

É preciso ter acesso à internet para essa leitura. A execução completa leva poucos minutos.

## Dependências

Todas já vêm instaladas no Google Colab, e nenhuma instalação adicional é necessária:

- Python 3.10 ou superior
- `pandas`: testado nas versões 3.0.5 e 2.3.3; nas duas, o notebook roda sem erros e gera um CSV final idêntico byte a byte (mesmo SHA-256)
- `numpy`
- `matplotlib`
- `seaborn`
- Biblioteca padrão do Python: `urllib`, `io`, `re`, `collections`, `decimal`, `unicodedata`, `os`

Para executar localmente (fora do Colab):

```bash
pip install pandas numpy matplotlib seaborn jupyter
jupyter notebook XPTO_Preparacao_Dados_Vinicius_Machado.ipynb
```

## Observação sobre reprodutibilidade

- **Fonte única:** nenhum CSV corrigido à mão nem arquivo intermediário. Toda transformação está no código, e o notebook gera sempre a mesma base final a partir da mesma URL.
- **RAW intocado:** o `df_raw` recebe uma "impressão digital" (*hash*) na leitura, que é conferida no fim da seção 7. Se algo tivesse modificado o RAW, a execução pararia com erro.
- **Sem dependência da data de execução:** a idade é calculada na **data da compra**, e não na data atual. Rodar o notebook em outro dia produz o mesmo resultado.
- **Sem valores "chumbados":** as regras não usam índices de linha nem códigos de cliente fixos. Os limites estão centralizados em `PARAMETROS_REGRAS` (seção 5.12), e os dicionários de domínio (UFs, formas de pagamento, taxonomia de canais) ficam explícitos no código.
- **Verificações automáticas:** diversos `assert` ao longo do notebook interrompem a execução se algo sair do esperado: leitura incompleta, ausentes criados por conversão, coluna sem descrição, arquivo final relido diferente do gravado.
- **Diferenças esperadas entre ambientes:** algumas saídas de **exibição** variam com a versão do `pandas`, sem alterar os dados. Exemplos: o nome do tipo textual (`object` ou `str`) e a memória medida na seção 2.3. O conteúdo da base final e os indicadores não mudam.
- **Se a fonte mudar:** o arquivo está em um repositório público de terceiros. Se ele for alterado, os números do texto podem deixar de coincidir com as saídas. As regras, porém, continuam válidas, porque são genéricas.
