"""Gera o notebook XPTO_Preparacao_Dados_[NOME_SOBRENOME].ipynb a partir das células definidas aqui."""
import os

import nbformat as nbf

PASTA_FERRAMENTAS = os.path.dirname(os.path.abspath(__file__))
PASTA_PROJETO = os.path.dirname(PASTA_FERRAMENTAS)

NOME = "Vinicius_Machado"
cells = []


def md(texto):
    cells.append(nbf.v4.new_markdown_cell(texto.strip("\n")))


def code(texto):
    cells.append(nbf.v4.new_code_cell(texto.strip("\n")))


# =====================================================================
# Cabeçalho
# =====================================================================
md("""
# Operação XPTO: da base bruta à verdade analítica (Vendas, E-commerce)

**Objetivo deste notebook:** transformar a base bruta de vendas da XPTO em uma base analítica confiável, documentando cada problema encontrado, cada decisão tomada e o impacto dessas decisões nos indicadores de negócio.

**Sumário**

1. Extração da base
2. Inspeção inicial
3. *Data profiling*
4. Diagnóstico da qualidade
5. Decisões sobre os problemas
6. Limpeza e transformação
7. Criação de atributos
8. Comparação RAW × CLEAN
9. Perguntas de negócio
10. Geração da base final
11. Pergunta final sobre produção

Checklist final do trabalho
""")

md("""
## 0.1 Ambiente: bibliotecas e configurações

O notebook usa apenas bibliotecas já disponíveis no Google Colab — `pandas`, `numpy`, `matplotlib` e `seaborn` — além de módulos da biblioteca padrão do Python (`urllib`, `io`, `re`, `collections`). Nenhuma instalação adicional é necessária.

As versões são impressas para fins de **reprodutibilidade**: alguns detalhes de exibição (por exemplo, o nome do tipo textual, `object` ou `str`, e o consumo de memória de colunas de texto) variam entre versões do `pandas`, sem alterar o conteúdo dos dados.
""")

code("""
import io
import re
import sys
import urllib.request
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Exibição mais legível das tabelas
pd.set_option("display.max_columns", 50)
pd.set_option("display.width", 160)
pd.set_option("display.float_format", lambda x: f"{x:,.2f}")

print(f"Python : {sys.version.split()[0]}")
print(f"pandas : {pd.__version__}")
print(f"numpy  : {np.__version__}")
""")

# =====================================================================
# 1. Extração
# =====================================================================
md("""
# 1. Extração da base
""")

md("""
## 1.1 Contexto: por que ler direto da fonte

A base é lida **diretamente da URL pública** do repositório, sem downloads manuais nem arquivos intermediários. Isso garante que qualquer pessoa, em um ambiente limpo, obtenha exatamente a mesma entrada e, portanto, a mesma base final.

Antes de chamar `pd.read_csv`, porém, é preciso **descobrir** os parâmetros de leitura — separador de campos, separador decimal, *encoding* e cabeçalho. Assumir os padrões do `pandas` (vírgula como separador, ponto como decimal) é uma fonte clássica de erros silenciosos: a leitura "funciona", mas produz colunas coladas ou números lidos como texto.
""")

code("""
URL_BASE = "https://raw.githubusercontent.com/alvaroriz/datascience_datasets/refs/heads/main/BaseVendasXPTO.csv"
""")

md("""
## 1.2 Inspeção dos bytes brutos: *encoding* e quebra de linha

O primeiro passo é olhar o arquivo **como bytes**, antes de qualquer interpretação. Os três primeiros bytes revelam se há um BOM — *Byte Order Mark*, marcador invisível que alguns programas (como o Excel) gravam no início de arquivos UTF-8. Se ele não for tratado, o nome da primeira coluna é lido com um caractere oculto (`\\ufeffDataVenda` em vez de `DataVenda`).
""")

code("""
# Leitura dos bytes apenas para inspeção (o DataFrame será criado com pd.read_csv na etapa 1.4)
with urllib.request.urlopen(URL_BASE) as resposta:
    bytes_brutos = resposta.read()

BOM_UTF8 = b"\\xef\\xbb\\xbf"
n_crlf = bytes_brutos.count(b"\\r\\n")

print(f"Tamanho do arquivo : {len(bytes_brutos):,} bytes")
print(f"Primeiros 3 bytes  : {bytes_brutos[:3]!r}")
print(f"Possui BOM UTF-8   : {bytes_brutos.startswith(BOM_UTF8)}")
print(f"Quebras de linha CRLF (Windows): {n_crlf:,}")
""")

code("""
# Teste de decodificação: UTF-8 falha se o arquivo estiver em Latin-1/CP1252 com acentos
try:
    texto_bruto = bytes_brutos.decode("utf-8-sig")
    print("Decodificação UTF-8 bem-sucedida (BOM removido pelo codec 'utf-8-sig').")
except UnicodeDecodeError as erro:
    print(f"Falha em UTF-8: {erro}")

# Os acentos só aparecem corretamente se o encoding estiver certo
acentuadas = sorted(set(re.findall(r"\\w*[áéíóúâêôãõçÁÉÍÓÚÂÊÔÃÕÇ]\\w*", texto_bruto)))
print(f"Palavras acentuadas encontradas no arquivo: {acentuadas}")
""")

md("""
## 1.3 Descoberta do separador e do formato decimal

Com o texto decodificado, inspecionamos as primeiras linhas e contamos, em **todas** as linhas, quantas vezes cada separador candidato aparece. Um separador correto aparece o mesmo número de vezes em todas as linhas (número de colunas − 1).
""")

code("""
linhas = texto_bruto.splitlines()
print(f"Total de linhas no arquivo (incluindo cabeçalho): {len(linhas):,}\\n")
for linha in linhas[:6]:
    print(linha)
""")

code("""
# Quantas ocorrências de cada separador candidato existem por linha?
candidatos = [";", ",", "\\t", "|"]
resumo_sep = pd.DataFrame({
    "separador": [repr(c) for c in candidatos],
    "ocorrencias_por_linha (distribuição)": [dict(Counter(l.count(c) for l in linhas)) for c in candidatos],
})
resumo_sep
""")

md("""
A tabela acima deixa claro o papel de cada caractere:

- **`;` é o separador de campos:** aparece exatamente 9 vezes em todas as linhas, o que corresponde a 10 colunas, sem nenhuma linha "quebrada".
- **`,` não é separador de campos:** sua contagem varia entre as linhas (1 na maioria, 2 em algumas); se fosse usada como separador, parte das linhas teria uma coluna a mais.

A variação da vírgula merece ser explicada, e não apenas ignorada. A célula abaixo verifica **em quais campos** ela aparece.
""")

code("""
# Em quais colunas a vírgula aparece? (divisão pelo separador já confirmado)
cabecalho = linhas[0].lstrip("\\ufeff").split(";")
registros_brutos = [l.split(";") for l in linhas[1:]]

virgula_por_coluna = Counter(
    col for reg in registros_brutos for col, valor in zip(cabecalho, reg) if "," in valor
)
print(f"Linhas com vírgula, por coluna: {dict(virgula_por_coluna)}\\n")

pos_canal = cabecalho.index("CanalVenda")
exemplos = [reg[pos_canal] for reg in registros_brutos if "," in reg[pos_canal]][:5]
print("Exemplos de CanalVenda com vírgula:", exemplos)
""")

md("""
**Diagnóstico:** a vírgula aparece em **todas** as linhas dentro de `ValorVenda` — é o **separador decimal** — e, adicionalmente, em algumas linhas dentro de `CanalVenda`, onde o valor aparece **repetido e separado por vírgula** (ex.: `xptoLS, xptoLS`). Isso **não é um problema de leitura**: como o separador de campos é `;`, essas vírgulas ficam contidas no próprio campo. Trata-se de um problema de **conteúdo** do canal, registrado para a seção 7.5.

Para confirmar o formato numérico, vale olhar o **padrão** dos valores de `ValorVenda` (cada dígito vira `9`). Assim fica visível se há separador de milhar (ex.: `1.234,56`), que exigiria o parâmetro `thousands`.
""")

code("""
# Padrão textual dos valores monetários: cada dígito é substituído por '9'
pos_valor = cabecalho.index("ValorVenda")
valores_texto = [reg[pos_valor] for reg in registros_brutos]

padroes_valor = Counter(re.sub(r"\\d", "9", v) for v in valores_texto)
pd.DataFrame(padroes_valor.most_common(), columns=["padrao_ValorVenda", "quantidade"])
""")

md("""
Os padrões mostram que **não existe separador de milhar** (nenhum ponto aparece, nem em valores com cinco dígitos inteiros) e que a vírgula é sempre o decimal. Chama a atenção que alguns valores têm **três ou quatro casas decimais** (ex.: padrão `999,999`) — algo incomum para preços em reais. Isso não impede a leitura, mas fica registrado como ponto a investigar no *profiling* (seção 3).

O mesmo raciocínio aplicado às colunas de data mostra o formato usado:
""")

code("""
# Padrão textual das colunas de data (dígitos -> '9'; campo vazio -> '<vazio>')
for coluna in ["DataVenda", "Cliente_Data_Nascimento"]:
    pos = cabecalho.index(coluna)
    padroes = Counter(re.sub(r"\\d", "9", reg[pos]) or "<vazio>" for reg in registros_brutos)
    print(f"{coluna}: {dict(padroes)}")
""")

md("""
O formato de `DataVenda` é uniforme (`AAAA-MM-DD hh:mm:ss`) em todas as linhas. Já `Cliente_Data_Nascimento` revela algo importante: os nascimentos ausentes **não estão vazios** — estão preenchidos com o **texto literal `NULL`**.

## 1.4 Representação de ausentes: o que conta como "vazio"

Por padrão, o `pandas` converte silenciosamente para `NaN` uma lista de marcadores (`""`, `"NULL"`, `"NA"`, `"null"`, `"N/A"`, `"None"`, entre outros). Isso é conveniente, mas perigoso: um canal de venda legítimo chamado `"NA"` seria apagado sem aviso. Por isso, verificamos **quais marcadores de ausência existem de fato** no arquivo, coluna a coluna.
""")

code("""
# Marcadores que o pandas trataria como ausentes por padrão (lista de pd.read_csv)
MARCADORES_NA_PADRAO = ["", "#N/A", "#N/A N/A", "#NA", "-1.#IND", "-1.#QNAN", "-NaN", "-nan",
                        "1.#IND", "1.#QNAN", "<NA>", "N/A", "NA", "NULL", "NaN", "None",
                        "n/a", "nan", "null"]

ocorrencias_na = Counter(
    (col, valor if valor else "<vazio>")
    for reg in registros_brutos
    for col, valor in zip(cabecalho, reg)
    if valor in MARCADORES_NA_PADRAO
)
tabela_na = pd.DataFrame(
    [(col, marcador, qtd) for (col, marcador), qtd in ocorrencias_na.items()],
    columns=["coluna", "marcador_no_arquivo", "quantidade"],
).sort_values(["coluna", "quantidade"], ascending=[True, False])
tabela_na
""")

md("""
**Diagnóstico:** apenas **dois marcadores** existem no arquivo — o campo vazio e o texto `NULL`. Os dois têm o mesmo significado (informação não registrada) e aparecem, inclusive, **misturados na mesma coluna** (`CanalVenda`). Nenhum outro marcador da lista padrão ocorre, portanto não há risco de apagar um valor legítimo.

**Solução adotada:** declarar explicitamente, na leitura, que somente `""` e `"NULL"` representam ausência (`keep_default_na=False` + `na_values=["", "NULL"]`). O resultado é idêntico ao padrão nesta base, mas a regra passa a ser **documentada e controlada**: se uma carga futura trouxer um canal chamado `"NA"`, ele será preservado como texto.

## 1.5 Leitura com parâmetros explícitos e criação do `df_raw`

Com base nas evidências acima, a leitura usa os seguintes parâmetros, todos declarados explicitamente:

| Parâmetro | Valor | Justificativa |
|---|---|---|
| `sep` | `";"` | 9 ocorrências em todas as linhas → 10 colunas consistentes |
| `decimal` | `","` | `ValorVenda` usa vírgula decimal, sem separador de milhar |
| `encoding` | `"utf-8-sig"` | Arquivo em UTF-8 com BOM; o sufixo `-sig` remove o BOM do nome da primeira coluna |
| `header` | `0` | A primeira linha contém os nomes das variáveis |
| `keep_default_na` / `na_values` | `False` / `["", "NULL"]` | Apenas esses dois marcadores de ausência existem no arquivo (1.4) |

**Deliberadamente, nenhuma conversão de tipo é feita na leitura** (por exemplo, `parse_dates`). A leitura deve refletir o arquivo tal como ele é; as conversões são decisões de preparação e serão feitas — e justificadas — sobre a cópia de trabalho.

**O conceito de camada RAW:** o `df_raw` é a "fotografia fiel" da fonte. Ele **nunca é alterado** ao longo do notebook; toda limpeza acontece em uma cópia (`df_clean`, criada na seção 6). Isso permite: (i) auditar qualquer transformação comparando antes e depois; (ii) refazer decisões sem reler a fonte; e (iii) calcular os indicadores da seção 8 sobre os dados originais. Para garantir que o RAW permanece intocado, guardamos uma **impressão digital** (*hash*) do conteúdo, que será conferida ao final.
""")

code("""
PARAMETROS_LEITURA = {
    "sep": ";",
    "decimal": ",",
    "encoding": "utf-8-sig",
    "header": 0,
    "keep_default_na": False,
    "na_values": ["", "NULL"],
}

df_raw = pd.read_csv(URL_BASE, **PARAMETROS_LEITURA)

# Impressão digital do RAW para verificar, ao final, que ele não foi modificado
HASH_RAW = pd.util.hash_pandas_object(df_raw, index=True).sum()

print(f"df_raw criado: {df_raw.shape[0]:,} linhas x {df_raw.shape[1]} colunas")
print(f"Hash do conteúdo RAW: {HASH_RAW}")
""")

md("""
Uma verificação de sanidade confirma que: (i) todas as linhas do arquivo foram carregadas; (ii) o nome da primeira coluna não carrega o BOM; e (iii) a quantidade de ausentes por coluna é exatamente a contagem de marcadores encontrada em 1.4.
""")

code("""
assert len(df_raw) == len(linhas) - 1, "Número de linhas lidas difere do arquivo"
assert df_raw.columns[0] == "DataVenda", "Primeira coluna com caractere oculto (BOM)"
assert list(df_raw.columns) == cabecalho, "Colunas divergentes do cabeçalho bruto"
ausentes_esperados = tabela_na.groupby("coluna")["quantidade"].sum()
assert df_raw.isna().sum()[ausentes_esperados.index].equals(ausentes_esperados), "Ausentes divergentes"
print("Leitura consistente com o arquivo bruto: todas as linhas e colunas foram carregadas.")
df_raw.head()
""")

# =====================================================================
# 2. Inspeção inicial
# =====================================================================
md("""
# 2. Inspeção inicial
""")

md("""
## 2.1 Dimensões: registros e atributos

A primeira pergunta é o tamanho da base: quantas vendas (linhas) e quantas características de cada venda (colunas) estão disponíveis.
""")

code("""
n_registros, n_atributos = df_raw.shape
print(f"Número de registros : {n_registros:,}")
print(f"Número de atributos : {n_atributos}")
""")

md("""
## 2.2 Variáveis e tipos inferidos

A tabela abaixo reúne, para cada coluna, o tipo que o `pandas` inferiu automaticamente, a quantidade de valores preenchidos e um exemplo real. Ela é o ponto de partida para avaliar se a inferência automática foi adequada (subseção 2.5).
""")

code("""
visao_tipos = pd.DataFrame({
    "tipo_inferido": df_raw.dtypes.astype(str),
    "preenchidos": df_raw.notna().sum(),
    "ausentes": df_raw.isna().sum(),
    "distintos": df_raw.nunique(dropna=True),
    "exemplo": df_raw.iloc[0],
})
visao_tipos.index.name = "variavel"
visao_tipos
""")

md("""
## 2.3 Memória utilizada

O consumo de memória é medido com `deep=True`, que contabiliza o conteúdo real das strings. Em versões do `pandas` anteriores à 3.0, colunas de texto (`object`) guardam apenas ponteiros, e sem `deep=True` o consumo fica subestimado; a partir da 3.0, o texto é armazenado em formato colunar (Arrow) e as duas medidas tendem a coincidir. Por isso, o valor exato depende da versão impressa em 0.1 — o que importa aqui é a **proporção** entre colunas.
""")

code("""
memoria = df_raw.memory_usage(deep=True).drop("Index")
tabela_memoria = pd.DataFrame({
    "tipo": df_raw.dtypes.astype(str),
    "memoria_KB": (memoria / 1024).round(1),
    "participacao_%": (memoria / memoria.sum() * 100).round(1),
}).sort_values("memoria_KB", ascending=False)

print(f"Memória total (deep=True) : {memoria.sum() / 1024**2:.2f} MB")
print(f"Memória total (deep=False): {df_raw.memory_usage(deep=False).drop('Index').sum() / 1024**2:.2f} MB")
tabela_memoria
""")

md("""
## 2.4 Período temporal da base

Como `DataVenda` foi lida como texto, o período é medido convertendo a coluna **em uma variável temporária**, sem alterar o `df_raw`. O parâmetro `format` é explícito (o padrão `9999-99-99 99:99:99` foi confirmado em 1.3) e `errors="coerce"` transforma qualquer valor inválido em `NaT`, permitindo contá-los em vez de interromper a execução.
""")

code("""
# Conversão temporária, apenas para medir o período (df_raw permanece como texto)
data_venda_tmp = pd.to_datetime(df_raw["DataVenda"], format="%Y-%m-%d %H:%M:%S", errors="coerce")

print(f"Datas inválidas (NaT)  : {data_venda_tmp.isna().sum()}")
print(f"Primeira venda         : {data_venda_tmp.min()}")
print(f"Última venda           : {data_venda_tmp.max()}")
print(f"Amplitude do período   : {(data_venda_tmp.max() - data_venda_tmp.min()).days} dias")
""")

md("""
A contagem mensal ajuda a verificar se todos os meses estão completos — informação importante para não comparar um mês parcial com um mês cheio na análise de evolução das vendas (seção 9.1).
""")

code("""
vendas_mes = pd.DataFrame({
    "vendas": data_venda_tmp.dt.to_period("M").value_counts().sort_index(),
    "primeiro_dia": data_venda_tmp.groupby(data_venda_tmp.dt.to_period("M")).min().dt.day,
    "ultimo_dia": data_venda_tmp.groupby(data_venda_tmp.dt.to_period("M")).max().dt.day,
})
vendas_mes.index.name = "mes"
vendas_mes
""")

md("""
**Leitura do resultado:** a base cobre **oito meses de 2011**, de janeiro a agosto, sem nenhuma data inválida. Porém, **dois meses são parciais**: janeiro começa no dia 10 e agosto termina no dia 28. Comparar volumes mensais brutos sem considerar isso subestimaria esses meses; a análise de evolução (9.1) deverá usar uma medida normalizada, como a média de vendas por dia.
""")

md("""
## 2.5 Diagnóstico: a leitura automática produziu tipos adequados?

**Não.** A leitura acertou os tipos de apenas parte das colunas. O tipo inferido pelo `pandas` reflete a **aparência** dos valores (só dígitos → inteiro; qualquer letra → texto), e não o **significado** de cada variável. A célula abaixo reúne as evidências que sustentam cada correção proposta.
""")

code("""
# Evidências para a revisão de tipos
print("Colunas de data lidas como texto:")
print(f"  DataVenda               -> tipo {df_raw['DataVenda'].dtype}, exemplo {df_raw['DataVenda'].iloc[0]!r}")
print(f"  Cliente_Data_Nascimento -> tipo {df_raw['Cliente_Data_Nascimento'].dtype}, exemplo {df_raw['Cliente_Data_Nascimento'].iloc[0]!r}")

print("\\nCódigos lidos como números (operações aritméticas não fazem sentido):")
print(f"  Cliente_Codigo     -> tipo {df_raw['Cliente_Codigo'].dtype}, 'média' = {df_raw['Cliente_Codigo'].mean():,.1f} (sem significado)")
print(f"  IdFormaDePagamento -> tipo {df_raw['IdFormaDePagamento'].dtype}, valores {sorted(df_raw['IdFormaDePagamento'].unique().tolist())}")

print("\\nTexto com poucas categorias (candidatas a 'category'):")
for c in ["FormaPagamento", "TipoFormaPagamento", "UF_Cliente"]:
    print(f"  {c:<19}-> {df_raw[c].nunique()} categorias distintas em {len(df_raw):,} linhas")

print(f"\\nCanalVenda -> {df_raw['CanalVenda'].nunique()} valores distintos (texto livre, exige normalização)")
""")

md("""
| Variável | Tipo inferido | Tipo adequado | Precisa corrigir? | Justificativa |
|---|---|---|---|---|
| `DataVenda` | texto | `datetime64` | **Sim** | Sem conversão não é possível ordenar cronologicamente, extrair mês/hora ou calcular idade na data da compra |
| `ValorVenda` | `float64` | `float64` | Não (tipo correto) | O parâmetro `decimal=","` garantiu a leitura numérica; as casas decimais excedentes são questão de **conteúdo**, tratada no *profiling* |
| `IdFormaDePagamento` | `int64` | `category` | **Sim** | É um **código**, não uma quantidade: somar ou tirar a média de IDs não tem significado |
| `FormaPagamento` | texto | `category` | **Sim** (otimização) | Domínio pequeno e fechado; `category` reduz memória e explicita o domínio |
| `TipoFormaPagamento` | texto | `category` | **Sim** (otimização) | Mesmo motivo de `FormaPagamento` |
| `NumeroParcelas` | `int64` | `int64` | Não (tipo correto) | É uma contagem; o valor `0` observado na distribuição será investigado como problema de **conteúdo** |
| `Cliente_Codigo` | `int64` | texto / `category` | **Sim** | Identificador: a "média" calculada acima não significa nada; tratá-lo como texto impede agregações indevidas |
| `Cliente_Data_Nascimento` | texto | `datetime64` | **Sim** | Necessário para calcular idade; os ausentes viram `NaT` |
| `UF_Cliente` | texto | `category` | **Sim** (otimização) | Domínio fechado (unidades federativas) |
| `CanalVenda` | texto | texto | Não (tipo correto) | O tipo é adequado, mas o **conteúdo** é texto livre com alta cardinalidade; o tratamento é de normalização (seção 7.5), não de tipo |

**Conclusão:** das 10 variáveis, **2 datas** precisam ser convertidas obrigatoriamente, **2 códigos** estão com tipo numérico enganoso e **3 colunas categóricas** se beneficiam do tipo `category`. Apenas `ValorVenda`, `NumeroParcelas` e `CanalVenda` têm tipo adequado — e mesmo nelas o **conteúdo** traz sinais que serão investigados na seção 3. As conversões serão aplicadas no `df_clean` (seções 6 e 7), nunca no `df_raw`.
""")

exec(open(os.path.join(PASTA_FERRAMENTAS, "secoes_03_05.py"), encoding="utf-8").read())
exec(open(os.path.join(PASTA_FERRAMENTAS, "secoes_06_07.py"), encoding="utf-8").read())
exec(open(os.path.join(PASTA_FERRAMENTAS, "secoes_08_11.py"), encoding="utf-8").read())

nb = nbf.v4.new_notebook()
nb["cells"] = cells
nb["metadata"] = {
    "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
    "language_info": {"name": "python"},
    "colab": {"provenance": []},
}
nbf.write(nb, os.path.join(PASTA_PROJETO, f"XPTO_Preparacao_Dados_{NOME}.ipynb"))
print(f"Notebook gerado com {len(cells)} células.")
