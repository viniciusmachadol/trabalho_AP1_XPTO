# Seções 6 e 7 do notebook. Executado por build_notebook.py (usa md() e code() de lá).

# =====================================================================
# 6. Limpeza e transformação
# =====================================================================
md(r"""
# 6. Limpeza e transformação
""")

md(r"""
## 6.1 Contexto: cópia de trabalho e rastreabilidade

A limpeza acontece sobre o `df_clean`, uma **cópia independente** do `df_raw` (`copy(deep=True)`). Alterar a cópia não afeta o original, e o *hash* calculado em 1.5 é conferido no fim da seção 7 para provar isso.

Cada registro recebe um identificador, `id_registro`, igual à sua posição no RAW. É ele que permite rastrear qualquer linha da base limpa até a linha de origem, mesmo depois de remoções.

Dois *logs* documentam o processo:

- **`log_etapas`:** uma linha por etapa, com a quantidade de linhas antes e depois e a quantidade de registros afetados.
- **`log_registros`:** uma linha por **valor alterado ou registro removido**, com `id_registro`, coluna, valor anterior, valor novo e motivo.

As *flags* de qualidade não alteram valores, apenas acrescentam informação. Por isso ficam registradas no `log_etapas`, e não no `log_registros`.
""")

code(r"""
df_clean = df_raw.copy(deep=True)
df_clean.insert(0, "id_registro", df_raw.index)

log_etapas = []
log_registros = []


def registrar_etapa(etapa, decisao, linhas_antes, linhas_depois, afetados, descricao):
    # Registra o resumo de uma etapa do pipeline
    log_etapas.append({"etapa": etapa, "decisao": decisao, "linhas_antes": linhas_antes,
                       "linhas_depois": linhas_depois, "registros_afetados": int(afetados),
                       "descricao": descricao})


def registrar_registros(df, mascara, etapa, acao, coluna, depois, motivo):
    # Registra, linha a linha, os valores alterados (ou os registros removidos)
    afetados = df.loc[mascara]
    antes = afetados[coluna].astype(str) if coluna else "-"
    novos = depois[mascara].astype(str) if isinstance(depois, pd.Series) else depois
    log_registros.append(pd.DataFrame({
        "id_registro": afetados["id_registro"].values, "etapa": etapa, "acao": acao,
        "coluna": coluna or "(linha inteira)", "valor_antes": np.asarray(antes),
        "valor_depois": np.asarray(novos), "motivo": motivo,
    }))


print(f"df_clean criado: {df_clean.shape[0]:,} linhas x {df_clean.shape[1]} colunas "
      f"(10 originais + id_registro)")
print(f"df_clean é um objeto diferente do df_raw: {df_clean is not df_raw}")
""")

md(r"""
## 6.2 Duplicata exata: remoção (decisão B)

A regra é aplicada sobre as **colunas originais**. O `id_registro` fica de fora da comparação, porque é diferente por definição. A primeira ocorrência é mantida e a cópia é removida.
""")

code(r"""
colunas_originais = list(df_raw.columns)
linhas_antes = len(df_clean)

mascara_dup = df_clean.duplicated(subset=colunas_originais, keep="first")
registrar_registros(df_clean, mascara_dup, "6.2", "removido", None, "-",
                    "Duplicata exata de outro registro (todas as colunas originais iguais)")
df_clean = df_clean.loc[~mascara_dup]

registrar_etapa("6.2", "B. Remover", linhas_antes, len(df_clean), mascara_dup.sum(),
                "Remoção de duplicatas exatas (mantida a primeira ocorrência)")
print(f"Linhas antes: {linhas_antes:,} | removidas: {mascara_dup.sum()} | linhas depois: {len(df_clean):,}")
""")

md(r"""
## 6.3 Tipos de dados: conversão (decisão D)

As conversões seguem o diagnóstico de 2.5. Os formatos de data são os mesmos confirmados em 1.3 (`FORMATOS_DATA`). O parâmetro `errors="coerce"` garante que um valor fora do formato vire `NaT` em vez de interromper o *pipeline*. A contagem de `NaT` antes e depois mostra que **nenhuma data válida foi perdida**.
""")

code(r"""
ausentes_antes = df_clean[["DataVenda", "Cliente_Data_Nascimento"]].isna().sum()

df_clean["DataVenda"] = pd.to_datetime(df_clean["DataVenda"], format=FORMATOS_DATA["DataVenda"], errors="coerce")
df_clean["Cliente_Data_Nascimento"] = pd.to_datetime(df_clean["Cliente_Data_Nascimento"],
                                                     format=FORMATOS_DATA["Cliente_Data_Nascimento"],
                                                     errors="coerce")
df_clean["Cliente_Codigo"] = df_clean["Cliente_Codigo"].astype(str)
for coluna in ["IdFormaDePagamento", "FormaPagamento", "TipoFormaPagamento", "UF_Cliente"]:
    df_clean[coluna] = df_clean[coluna].astype("category")

ausentes_depois = df_clean[["DataVenda", "Cliente_Data_Nascimento"]].isna().sum()
assert ausentes_antes.equals(ausentes_depois), "A conversão de datas gerou ausentes novos"

registrar_etapa("6.3", "D. Transformar", len(df_clean), len(df_clean), len(df_clean),
                "Conversão de tipos: datas para datetime64, Cliente_Codigo para texto, 4 colunas para category")

comparacao_tipos = pd.DataFrame({"tipo_RAW": df_raw.dtypes.astype(str),
                                 "tipo_CLEAN": df_clean[colunas_originais].dtypes.astype(str)})
comparacao_tipos["ausentes_RAW"] = df_raw.isna().sum()
comparacao_tipos["ausentes_CLEAN"] = df_clean[colunas_originais].isna().sum()
comparacao_tipos
""")

md(r"""
## 6.4 Nascimentos inválidos: correção para ausente (decisão A)

Duas regras identificam datas de nascimento **comprovadamente falsas**:

- **Sentinela:** ano ≤ `PARAMETROS_REGRAS["ano_max_sentinela_nascimento"]` (1900).
- **Posterior à compra:** nascimento depois da `DataVenda` da mesma linha.

O valor é substituído por `NaT`, e a *flag* `flag_nascimento_invalido` guarda o **motivo**. Assim a análise sabe *por que* a data está ausente: "não informado na origem" é diferente de "informado, mas inválido".
""")

code(r"""
nasc = df_clean["Cliente_Data_Nascimento"]
eh_sentinela = nasc.dt.year <= PARAMETROS_REGRAS["ano_max_sentinela_nascimento"]
eh_posterior = nasc > df_clean["DataVenda"]

df_clean["flag_nascimento_invalido"] = np.select([eh_sentinela, eh_posterior],
                                                 ["sentinela", "posterior_compra"], default="")
df_clean["flag_nascimento_invalido"] = df_clean["flag_nascimento_invalido"].replace("", np.nan)

invalido = eh_sentinela | eh_posterior
registrar_registros(df_clean, eh_sentinela, "6.4", "modificado", "Cliente_Data_Nascimento", "NaT",
                    "Data sentinela (ano <= 1900) substituída por ausente")
registrar_registros(df_clean, eh_posterior, "6.4", "modificado", "Cliente_Data_Nascimento", "NaT",
                    "Nascimento posterior à data da compra substituído por ausente")

ausentes_antes = nasc.isna().sum()
df_clean.loc[invalido, "Cliente_Data_Nascimento"] = pd.NaT
ausentes_depois = df_clean["Cliente_Data_Nascimento"].isna().sum()

registrar_etapa("6.4", "A. Corrigir", len(df_clean), len(df_clean), invalido.sum(),
                "Nascimentos sentinela ou posteriores à compra substituídos por NaT + flag_nascimento_invalido")

print(f"Sentinelas corrigidos           : {eh_sentinela.sum()}")
print(f"Posteriores à compra corrigidos : {eh_posterior.sum()}")
print(f"Nascimentos ausentes: antes {ausentes_antes:,} -> depois {ausentes_depois:,}")
print(f"Nascimento mínimo após a correção: {df_clean['Cliente_Data_Nascimento'].min().date()}")
print(f"Nascimento máximo após a correção: {df_clean['Cliente_Data_Nascimento'].max().date()}")
""")

md(r"""
## 6.5 Centavos fracionados: arredondamento (decisão A)

O arredondamento usa a regra **comercial** (meio centavo arredonda para cima), aplicada com `decimal.Decimal`. Por que não `round()` ou `np.round()`? Porque um número como `431,275` não tem representação exata em ponto flutuante: internamente é `431,27499999...`, e o arredondamento binário daria `431,27`. A conversão via texto (`Decimal(str(x))`) preserva o valor como está escrito no arquivo.
""")

code(r"""
from decimal import Decimal, ROUND_HALF_UP

CASAS = PARAMETROS_REGRAS["casas_decimais_valor"]
QUANTUM = Decimal(1).scaleb(-CASAS)  # 0.01 para 2 casas


def arredondar_comercial(x):
    # Arredonda meio centavo para cima, a partir da representação textual do número
    return float(Decimal(str(x)).quantize(QUANTUM, rounding=ROUND_HALF_UP))


valor_antes = df_clean["ValorVenda"].copy()
valor_depois = valor_antes.map(arredondar_comercial)
alterado = valor_antes.ne(valor_depois)

registrar_registros(df_clean, alterado, "6.5", "modificado", "ValorVenda", valor_depois,
                    "Valor com mais de 2 casas decimais arredondado para centavos")
df_clean["ValorVenda"] = valor_depois
registrar_etapa("6.5", "A. Corrigir", len(df_clean), len(df_clean), alterado.sum(),
                "ValorVenda arredondado para 2 casas (arredondamento comercial)")

print(f"Valores alterados : {alterado.sum()}")
print(f"Soma antes        : {valor_antes.sum():,.4f}")
print(f"Soma depois       : {valor_depois.sum():,.4f}")
print(f"Diferença total   : {valor_depois.sum() - valor_antes.sum():,.4f}")
with pd.option_context("display.float_format", "{:,.4f}".format):
    display(pd.DataFrame({"antes": valor_antes[alterado], "depois": valor_depois[alterado]}).head(6))
""")

md(r"""
## 6.6 Granularidade e clientes: *flags* de análise (decisões E e C)

Quatro *flags* registram situações que **não são erros comprovados**, mas que podem afetar indicadores:

- **`flag_possivel_repeticao`:** a venda repete cliente e valor de outra feita até `janela_repeticao_min` (60) minutos antes. A primeira venda do par **não** recebe a *flag*, apenas as repetições, para que filtrar a *flag* mantenha uma venda de cada par.
- **`flag_cliente_atipico`:** o cliente tem mais compras que o percentil 99,9 da base.
- **`flag_cliente_multi_uf`:** o cliente aparece com mais de uma UF.
- **`flag_rajada_compras`:** o cliente fez `compras_mesmo_dia_rajada` (5) ou mais compras no mesmo dia (3.12). A motivação detalhada desta regra, e o seu efeito sobre o canal HiMidia, estão na descoberta livre (9.6).

As regras são funções genéricas, sem códigos de cliente ou índices fixos.
""")

code(r"""
def marcar_repeticoes(df, janela_min):
    # True para vendas que repetem cliente e valor de uma venda anterior dentro da janela
    ordenado = df.sort_values(["Cliente_Codigo", "ValorVenda", "DataVenda"])
    intervalo = ordenado.groupby(["Cliente_Codigo", "ValorVenda"])["DataVenda"].diff()
    repete = intervalo.notna() & (intervalo > pd.Timedelta(0)) & (intervalo <= pd.Timedelta(minutes=janela_min))
    return repete.reindex(df.index)


def marcar_clientes_atipicos(df, percentil):
    # True para vendas de clientes cujo número de compras supera o percentil informado
    compras = df["Cliente_Codigo"].map(df["Cliente_Codigo"].value_counts())
    limite = df["Cliente_Codigo"].value_counts().quantile(percentil)
    return compras > limite


def marcar_clientes_multi_uf(df):
    # True para vendas de clientes que aparecem com mais de uma UF
    return df.groupby("Cliente_Codigo")["UF_Cliente"].transform("nunique") > 1


def marcar_rajadas(df, minimo_compras):
    # True para vendas de clientes com pelo menos minimo_compras compras no mesmo dia
    compras_dia = df.groupby(["Cliente_Codigo", df["DataVenda"].dt.normalize()])["id_registro"].transform("size")
    return compras_dia >= minimo_compras


df_clean["flag_possivel_repeticao"] = marcar_repeticoes(df_clean, PARAMETROS_REGRAS["janela_repeticao_min"])
df_clean["flag_cliente_atipico"] = marcar_clientes_atipicos(df_clean, PARAMETROS_REGRAS["percentil_cliente_atipico"])
df_clean["flag_cliente_multi_uf"] = marcar_clientes_multi_uf(df_clean)
df_clean["flag_rajada_compras"] = marcar_rajadas(df_clean, PARAMETROS_REGRAS["compras_mesmo_dia_rajada"])

for flag, decisao in [("flag_possivel_repeticao", "E. Marcar"), ("flag_cliente_atipico", "E. Marcar"),
                      ("flag_cliente_multi_uf", "C. Manter"), ("flag_rajada_compras", "E. Marcar")]:
    registrar_etapa("6.6", decisao, len(df_clean), len(df_clean), df_clean[flag].sum(), f"Criação de {flag}")
    print(f"{flag:<26}: {df_clean[flag].sum():,} vendas")
""")

md(r"""
**Leitura:** as quantidades coincidem com o diagnóstico da seção 3 (891 possíveis repetições, 877 vendas de clientes atípicos, 223 de clientes com várias UFs e as vendas em rajada). A remoção da duplicata exata não alterou esses números, porque o par duplicado tinha intervalo zero e já estava excluído da regra de repetição.

As demais decisões da seção 5 (idade improvável, valor zero e extremo, parcelas zero e canal) dependem de atributos derivados. Por isso são aplicadas na seção 7, com o mesmo registro em *log*.
""")

# =====================================================================
# 7. Criação de atributos
# =====================================================================
md(r"""
# 7. Criação de atributos
""")

md(r"""
## 7.1 Datas: componentes temporais da venda

A partir de `DataVenda`, já convertida para `datetime64` em 6.3, são derivados os atributos abaixo. A utilidade de cada um foi avaliada:

| Atributo | Regra | Utilidade |
|---|---|---|
| `Ano` | `dt.year` | **Baixa nesta base** (só 2011), mas mantido para o *pipeline* funcionar em cargas com vários anos |
| `Mes` / `AnoMes` | `dt.month` / `dt.to_period("M")` | **Alta:** evolução mensal (9.1). `AnoMes` evita misturar o mesmo mês de anos diferentes |
| `Dia` | `dt.day` | **Média:** permite estudar efeitos de início e fim de mês (dia de pagamento de salário) |
| `DiaSemana` | `dt.dayofweek` + dicionário em português | **Alta:** padrão semanal de compra e planejamento de campanhas |
| `FimDeSemana` | sábado ou domingo | **Média:** atalho binário para comparar dias úteis e fins de semana |
| `Hora` | `dt.hour` | **Alta:** horário de pico, janela de disparo de e-mails |
| `PeriodoDia` | faixas de hora | **Alta:** versão agregada e legível da hora |

O nome do dia da semana vem de um **dicionário próprio**, e não de `dt.day_name(locale=...)`, porque a disponibilidade de *locales* em português varia entre ambientes (o Colab, por exemplo, não garante `pt_BR`).

**Regra de `PeriodoDia`:** Madrugada [0h, 6h), Manhã [6h, 12h), Tarde [12h, 18h) e Noite [18h, 24h). São intervalos fechados à esquerda, sem sobreposição.
""")

code(r"""
DIAS_SEMANA = {0: "Segunda", 1: "Terça", 2: "Quarta", 3: "Quinta", 4: "Sexta", 5: "Sábado", 6: "Domingo"}
PERIODOS_DIA = {"limites": [0, 6, 12, 18, 24], "rotulos": ["Madrugada", "Manhã", "Tarde", "Noite"]}

data = df_clean["DataVenda"]
df_clean["Ano"] = data.dt.year
df_clean["Mes"] = data.dt.month
df_clean["AnoMes"] = data.dt.to_period("M").astype(str)
df_clean["Dia"] = data.dt.day
df_clean["DiaSemana"] = pd.Categorical(data.dt.dayofweek.map(DIAS_SEMANA),
                                       categories=list(DIAS_SEMANA.values()), ordered=True)
df_clean["FimDeSemana"] = data.dt.dayofweek >= 5
df_clean["Hora"] = data.dt.hour
df_clean["PeriodoDia"] = pd.cut(data.dt.hour, bins=PERIODOS_DIA["limites"], labels=PERIODOS_DIA["rotulos"],
                                right=False)

registrar_etapa("7.1", "D. Transformar", len(df_clean), len(df_clean), len(df_clean),
                "Derivação de Ano, Mes, AnoMes, Dia, DiaSemana, FimDeSemana, Hora e PeriodoDia")

assert df_clean["PeriodoDia"].notna().all() and df_clean["DiaSemana"].notna().all()
df_clean[["DataVenda", "Ano", "Mes", "AnoMes", "Dia", "DiaSemana", "FimDeSemana", "Hora", "PeriodoDia"]].head()
""")

code(r"""
# Conferência das distribuições derivadas
print(frequencias(df_clean["DiaSemana"]).sort_index().to_string(), "\n")
print(frequencias(df_clean["PeriodoDia"]).sort_index().to_string())
""")

md(r"""
**Leitura:** a distribuição por dia da semana e por período confirma que as derivações fazem sentido: as vendas se concentram em dias úteis e à tarde. A madrugada tem volume pequeno, mas não nulo, o que é esperado no comércio eletrônico. Esses padrões são explorados na seção 9.
""")

md(r"""
## 7.2 Dados do cliente: idade na data da compra e faixa etária

**A idade é calculada na data da compra, não na data de hoje.** Um cliente que comprou em 2011 com 30 anos deve ser analisado como "30 anos", e não com a idade que teria hoje, que dependeria do dia em que o notebook foi executado e tornaria o resultado **não reprodutível**.

O cálculo é **exato**: a diferença de anos é reduzida em 1 quando o aniversário ainda não tinha acontecido naquele ano. Uma aproximação como `dias / 365,25` erraria perto da data de aniversário (um cliente nascido em `1910-10-10` apareceria com "100,1 anos" numa compra feita quando ele tinha exatamente 100). A função `idade_na_data` foi definida em 3.1 e é a **mesma** usada no diagnóstico do RAW, de modo que a comparação RAW × CLEAN da seção 8 mede só o efeito da limpeza, e não uma mudança de método.
""")

code(r"""
# idade_na_data foi definida em 3.1 e já foi usada no diagnóstico: o mesmo método vale para RAW e CLEAN
df_clean["IdadeNaCompra"] = idade_na_data(df_clean["Cliente_Data_Nascimento"], df_clean["DataVenda"])

# Verificação em um caso controlado: aniversário um dia depois e um dia antes da compra
teste_nasc = pd.Series(pd.to_datetime(["1980-05-11", "1980-05-09"]))
teste_ref = pd.Series(pd.to_datetime(["2011-05-10", "2011-05-10"]))
assert idade_na_data(teste_nasc, teste_ref).tolist() == [30, 31]

print(df_clean["IdadeNaCompra"].describe().round(2).to_string())
""")

md(r"""
Com a idade calculada, investigamos os quatro tipos de situação exigidos. As idades **impossíveis** e os **sentinelas** já foram corrigidos em 6.4. Aqui eles aparecem como ausentes com motivo registrado.
""")

code(r"""
idade = df_clean["IdadeNaCompra"]
improvavel = (idade < PARAMETROS_REGRAS["idade_min_provavel"]) | (idade > PARAMETROS_REGRAS["idade_max_provavel"])
df_clean["flag_idade_improvavel"] = improvavel.fillna(False).astype(bool)

situacao_idade = pd.Series({
    "Nascimento ausente na origem (NULL)": df_raw["Cliente_Data_Nascimento"].isna().sum(),
    "Sentinela corrigido para ausente (6.4)": (df_clean["flag_nascimento_invalido"] == "sentinela").sum(),
    "Impossível: posterior à compra, corrigido (6.4)": (df_clean["flag_nascimento_invalido"] == "posterior_compra").sum(),
    f"Improvável: < {PARAMETROS_REGRAS['idade_min_provavel']} anos": (idade < PARAMETROS_REGRAS["idade_min_provavel"]).sum(),
    f"Improvável: > {PARAMETROS_REGRAS['idade_max_provavel']} anos": (idade > PARAMETROS_REGRAS["idade_max_provavel"]).sum(),
    "Idade plausível": (idade.notna() & ~improvavel.fillna(False)).sum(),
}, name="vendas").to_frame()
situacao_idade["percentual"] = (situacao_idade["vendas"] / len(df_clean) * 100).round(2)

registrar_etapa("7.2", "E. Marcar", len(df_clean), len(df_clean), df_clean["flag_idade_improvavel"].sum(),
                "Criação de IdadeNaCompra e flag_idade_improvavel")
situacao_idade
""")

md(r"""
**Leitura:** as quantidades coincidem com o diagnóstico de 3.6 e com a Tabela de Qualidade (4.1): 172 vendas de clientes com menos de 16 anos e nenhuma acima de 100. O cliente mais velho, nascido em `1910-10-10`, tinha **exatamente 100 anos** nas 7 compras e fica dentro do limite (ver a ressalva em 3.5).
""")

md(r"""
**Faixa etária: regra das faixas.** As faixas seguem cortes usuais em pesquisas de mercado, com amplitude de 10 anos na fase adulta e uma faixa inicial mais estreita (18 a 24) para separar o público jovem. Os limites são fechados à esquerda (`right=False`): 25 anos pertence a "25–34", e não a "18–24".

A primeira faixa começa em **16**, e não em 0, porque idades abaixo de `idade_min_provavel` (16) já são tratadas como improváveis. O rótulo "16–17" descreve exatamente quem está nela, enquanto "Menor de 18" sugeriria que há crianças na base.

Dois rótulos especiais evitam que dados sem qualidade se misturem às faixas:

- **`Não informado`:** nascimento ausente na origem ou corrigido para ausente.
- **`Idade improvável`:** idade marcada pela *flag*. Assim, um "cliente de 5 anos" não entra em nenhuma faixa de idade real e um de 101 anos não vai para "65 ou mais".
""")

code(r"""
FAIXAS_ETARIAS = {
    "limites": [PARAMETROS_REGRAS["idade_min_provavel"], 18, 25, 35, 45, 55, 65, np.inf],
    "rotulos": ["16–17", "18–24", "25–34", "35–44", "45–54", "55–64", "65 ou mais"],
}
ROTULOS_ESPECIAIS = ["Idade improvável", "Não informado"]

faixa = pd.cut(df_clean["IdadeNaCompra"].astype(float), bins=FAIXAS_ETARIAS["limites"],
               labels=FAIXAS_ETARIAS["rotulos"], right=False).astype(str)
faixa = faixa.mask(df_clean["flag_idade_improvavel"], "Idade improvável")
faixa = faixa.mask(df_clean["IdadeNaCompra"].isna(), "Não informado")
df_clean["FaixaEtaria"] = pd.Categorical(faixa, categories=FAIXAS_ETARIAS["rotulos"] + ROTULOS_ESPECIAIS,
                                         ordered=True)

assert df_clean["FaixaEtaria"].notna().all(), "Alguma venda ficou sem faixa etária"
registrar_etapa("7.2", "D. Transformar", len(df_clean), len(df_clean), len(df_clean), "Criação de FaixaEtaria")
frequencias(df_clean["FaixaEtaria"], n=20).sort_index()
""")

code(r"""
# Efeito das correções na idade média: RAW (com sentinelas e datas impossíveis) x CLEAN (sem inválidos)
idade_raw = aux_idade  # calculada em 3.1 sobre o RAW, com a mesma função idade_na_data
idade_clean_valida = df_clean.loc[~df_clean["flag_idade_improvavel"], "IdadeNaCompra"]

print(f"Idade média RAW (todas as datas preenchidas)         : {idade_raw.mean():.2f} anos")
print(f"Idade média CLEAN (sem inválidos, sem improváveis)   : {idade_clean_valida.mean():.2f} anos")
print(f"Idade mediana RAW / CLEAN                            : {idade_raw.median():.1f} / {idade_clean_valida.median():.1f}")
""")

md(r"""
**Leitura:** a correção dos sentinelas e das datas impossíveis, e a exclusão das idades improváveis, **reduz a idade média** do cliente (de 32,62 para 31,98 anos). A mediana não muda (29 anos), porque é robusta a extremos. A diferença mostra por que a média calculada sobre o RAW seria enganosa, e esse efeito é quantificado como indicador na seção 8.
""")

md(r"""
## 7.3 Valores monetários: extremos, valores zero e comportamento das vendas

`ValorVenda` já é numérica desde a leitura (`decimal=","`) e foi arredondada para centavos em 6.5. Falta aplicar as decisões de 5.6 e verificar se os extremos têm algum padrão que indique erro: concentração em uma forma de pagamento, em um mês ou em um cliente.
""")

code(r"""
valor = df_clean["ValorVenda"]
q1, q3 = valor.quantile([0.25, 0.75])
iqr = q3 - q1
limite_extremo = q3 + PARAMETROS_REGRAS["fator_iqr_extremo"] * iqr

df_clean["flag_valor_zero"] = valor.eq(0)
df_clean["flag_valor_extremo"] = valor.gt(limite_extremo)

registrar_etapa("7.3", "E. Marcar", len(df_clean), len(df_clean), df_clean["flag_valor_zero"].sum(),
                "Criação de flag_valor_zero")
registrar_etapa("7.3", "C. Manter", len(df_clean), len(df_clean), df_clean["flag_valor_extremo"].sum(),
                f"Criação de flag_valor_extremo (acima de {limite_extremo:,.2f})")

print(f"Q1 = {q1:,.2f} | Q3 = {q3:,.2f} | IQR = {iqr:,.2f} | limite superior = {limite_extremo:,.2f}")
print(f"flag_valor_zero    : {df_clean['flag_valor_zero'].sum()} vendas")
print(f"flag_valor_extremo : {df_clean['flag_valor_extremo'].sum():,} vendas "
      f"({df_clean['flag_valor_extremo'].mean() * 100:.1f}%) | "
      f"{valor[df_clean['flag_valor_extremo']].sum() / valor.sum() * 100:.1f}% do faturamento")
""")

code(r"""
# Os extremos se concentram em alguma forma de pagamento? (participação nos extremos x na base)
extremos_forma = pd.DataFrame({
    "%_da_base": df_clean["FormaPagamento"].value_counts(normalize=True) * 100,
    "%_dos_extremos": df_clean.loc[df_clean["flag_valor_extremo"], "FormaPagamento"].value_counts(normalize=True) * 100,
}).round(1)
display(extremos_forma)

# E ao longo do tempo? (proporção de vendas extremas por mês)
print("Proporção de vendas extremas por mês (%):")
print((df_clean.groupby("AnoMes")["flag_valor_extremo"].mean() * 100).round(1).to_string())

print(f"\nClientes distintos entre as vendas extremas: "
      f"{df_clean.loc[df_clean['flag_valor_extremo'], 'Cliente_Codigo'].nunique():,}")
""")

md(r"""
**Diagnóstico dos extremos:** a participação das formas de pagamento nas vendas extremas é **próxima** da participação na base, a proporção de extremos é **estável** entre os meses e as vendas extremas estão espalhadas por muitos clientes diferentes. Um erro de sistema (por exemplo, um valor multiplicado por 100) costuma se concentrar em um período, um canal ou uma forma de pagamento. Aqui não há nada disso. Os extremos são **vendas legítimas de valor alto**, e a decisão de 5.6 (C. Manter) se confirma.

O comportamento dos valores também mostra **preços psicológicos**: os valores mais frequentes terminam em 9 (R$ 199,00, R$ 99,00, R$ 89,00, vistos em 3.2). Isso reforça que `ValorVenda` representa o preço de etiqueta do pedido.
""")

code(r"""
# Valores incompatíveis: valor zero por forma de pagamento
display(pd.crosstab(df_clean["FormaPagamento"], df_clean["flag_valor_zero"], margins=True)
        .rename(columns={False: "valor > 0", True: "valor = 0"}))
""")

md(r"""
**Valores zero:** 14 das 16 vendas zeradas foram pagas com **cupom**, o que é compatível com um desconto integral. As 2 zeradas em **boleto** são incompatíveis, porque não se emite boleto de R$ 0,00. Todas foram mantidas com `flag_valor_zero`, e a *flag* permite excluí-las do cálculo de ticket médio.
""")

md(r"""
## 7.4 Pagamento: consistência entre Id, forma, tipo e parcelas

As quatro colunas são validadas contra um **dicionário de referência** do domínio de pagamento. Em produção, esse dicionário viria de uma tabela cadastral. As regras verificam:

1. **Id × descrição:** o Id corresponde à forma e ao tipo esperados? Um Id que não está no dicionário também é marcado, o que protege o *pipeline* contra formas novas.
2. **Parcelas × forma:** formas que não são cartão de crédito devem ter exatamente 1 parcela. Cartão deve ter de 1 a 10 parcelas. Zero parcelas é marcado à parte (decisão 5.7).
3. **Valor da parcela:** o valor de cada parcela deve ser positivo e compatível com um parcelamento real.
""")

code(r"""
DOMINIO_PAGAMENTO = {
    1: ("Boleto Bancário", "Boleto Bancário"),
    2: ("Visa", "Cartão de Crédito"),
    3: ("MasterCard", "Cartão de Crédito"),
    4: ("Diners", "Cartão de Crédito"),
    6: ("Cupom de Desconto", "Cupom"),
    7: ("Glamour VIP", "Pagamentos Glamour"),
}
TIPOS_PARCELAVEIS = {"Cartão de Crédito"}
PARCELAS_MAX = 10

id_pag = df_clean["IdFormaDePagamento"].astype(int)
forma_esperada = id_pag.map({k: v[0] for k, v in DOMINIO_PAGAMENTO.items()})
tipo_esperado = id_pag.map({k: v[1] for k, v in DOMINIO_PAGAMENTO.items()})
tipo = df_clean["TipoFormaPagamento"].astype(str)
parcelas = df_clean["NumeroParcelas"]

regras_pagamento = pd.DataFrame({
    "id_desconhecido": forma_esperada.isna(),
    "forma_diverge_do_id": forma_esperada.notna() & forma_esperada.ne(df_clean["FormaPagamento"].astype(str)),
    "tipo_diverge_do_id": tipo_esperado.notna() & tipo_esperado.ne(tipo),
    "nao_parcelavel_com_parcelas_diferente_de_1": ~tipo.isin(TIPOS_PARCELAVEIS) & parcelas.ne(1),
    "parcelas_acima_do_maximo": parcelas.gt(PARCELAS_MAX),
    "parcelas_negativas": parcelas.lt(0),
})
regras_pagamento.sum().rename("vendas_violando").to_frame()
""")

md(r"""
Nenhuma das regras estruturais é violada. A relação Id × forma × tipo é íntegra, e boleto, cupom e Glamour VIP sempre têm 1 parcela. As regras continuam no *pipeline* como **testes de qualidade**: numa carga futura, qualquer violação será marcada automaticamente em `flag_pagamento_inconsistente`.

A única anomalia é o **cartão com 0 parcelas**, que recebe uma *flag* própria por ter um padrão específico (3.8).
""")

code(r"""
cartao = tipo.isin(TIPOS_PARCELAVEIS)
df_clean["flag_pagamento_inconsistente"] = regras_pagamento.any(axis=1)
df_clean["flag_parcelas_zero"] = cartao & parcelas.eq(0)

# Modalidade legível: à vista, parcelado ou não informado (cartão com 0 parcelas)
df_clean["ModalidadePagamento"] = np.select(
    [cartao & parcelas.eq(0), cartao & parcelas.gt(1)],
    ["Não informado", "Parcelado"], default="À vista")

# Valor de cada parcela (indefinido quando o número de parcelas é 0)
df_clean["ValorParcela"] = (df_clean["ValorVenda"] / parcelas.where(parcelas > 0)).round(2)

for flag in ["flag_pagamento_inconsistente", "flag_parcelas_zero"]:
    registrar_etapa("7.4", "E. Marcar", len(df_clean), len(df_clean), df_clean[flag].sum(), f"Criação de {flag}")
registrar_etapa("7.4", "D. Transformar", len(df_clean), len(df_clean), len(df_clean),
                "Criação de ModalidadePagamento e ValorParcela")

print(f"flag_pagamento_inconsistente: {df_clean['flag_pagamento_inconsistente'].sum()}")
print(f"flag_parcelas_zero          : {df_clean['flag_parcelas_zero'].sum()}")
display(pd.crosstab(df_clean["FormaPagamento"], df_clean["ModalidadePagamento"], margins=True))
""")

code(r"""
# Valor da parcela em vendas parceladas: há parcelas de valor irrisório?
parcelado = df_clean["ModalidadePagamento"].eq("Parcelado")
print(df_clean.loc[parcelado, "ValorParcela"].describe().round(2).to_string())
print(f"\nMenor valor de parcela por número de parcelas:")
print(df_clean[parcelado].groupby("NumeroParcelas")["ValorParcela"].min().to_string())
""")

md(r"""
**Leitura:** em todas as quantidades de parcelas (de 2 a 10), a menor parcela fica em torno de **R$ 20,00**, com mínimo exato de R$ 20,00. Um piso tão regular sugere uma **regra de parcela mínima** no *checkout*: a loja só permite parcelar quando cada parcela é de pelo menos R$ 20. Não há parcelamentos incompatíveis com o valor da venda.

Resumo das *flags* de pagamento:

- **`flag_pagamento_inconsistente`:** nenhuma ocorrência nesta base; funciona como teste para cargas futuras.
- **`flag_parcelas_zero`:** 585 vendas, preservadas com `ModalidadePagamento = "Não informado"`, para não serem tratadas nem como "à vista" nem como "parceladas" sem evidência.
""")

md(r"""
## 7.5 Canal de venda: normalização e taxonomia (principal desafio)
""")

md(r"""
### 7.5.1 Contexto: o que o campo realmente contém

A investigação de 3.13 mostrou que `CanalVenda` não é uma lista de canais, e sim um **texto de rastreamento** que mistura três informações:

- **Origem externa:** `google`, `yahoo`, `HiMidia`, `buscape`, parceiros diversos.
- **Campanha interna:** 513 códigos com prefixo `xpto`, como `xptoourMasc1` e `xptockjH`. Parecem combinar peça, marca e público, mas a codificação interna não é documentada.
- **Parâmetro de mídia:** `utm_medium=Newsletter`, um parâmetro de URL que identifica o **meio** (e-mail), e não o canal.

Antes de normalizar, a célula abaixo quantifica **famílias** de valores pelo prefixo. Isso mostra que a variedade tem estrutura: poucos prefixos respondem pela maior parte dos valores distintos.
""")

code(r"""
canal_original = df_raw["CanalVenda"]
canal_preenchido = canal_original.dropna()

familias = canal_preenchido.str.lower().str.extract(r"^(xpto|uol|coluna|extra)", expand=False).fillna("(outros)")
resumo_familias = pd.DataFrame({
    "valores_distintos": canal_preenchido.groupby(familias).nunique(),
    "vendas": canal_preenchido.groupby(familias).size(),
}).sort_values("vendas", ascending=False)
resumo_familias.loc["(ausente)"] = [0, canal_original.isna().sum()]
resumo_familias
""")

md(r"""
### 7.5.2 Normalização: regras aplicadas em sequência

O `CanalVenda_Normalizado` é produzido por uma sequência de regras **genéricas**. Cada regra resolve um tipo de variação e nenhuma depende de valores específicos desta base, exceto o pequeno dicionário de grafias da última etapa, que é explícito e fácil de manter.

1. **Espaços e caixa:** `strip()` e `lower()`.
2. **Acentos:** remoção via `unicodedata` (`calçaecinto` → `calcaecinto`).
3. **Parâmetros de rastreamento:** remoção de `utm_*=...` e de *query strings* (`?`, `&`). Antes da remoção, o valor de `utm_medium` é **extraído** para a coluna `CanalVenda_Midia`, para não perder a informação.
4. **Listas:** o texto é dividido pela vírgula, as partes repetidas são eliminadas e **fica a primeira**. A *flag* `flag_canal_multiplo` marca as vendas com duas origens *distintas*.
5. **Pontuação nas bordas:** remoção de `/` e espaços no início e no fim (`xptosBanner/` → `xptosbanner`).
6. **Grafias conhecidas:** um dicionário corrige erros de digitação e abreviações (`twitte` → `twitter`, `fb` → `facebook`).

**Por que manter a primeira origem nas listas?** A base não informa se a ordem representa o primeiro ou o último contato. Manter a primeira é uma convenção declarada, e não uma verdade. O impacto é pequeno, e a *flag* deixa os casos identificáveis.
""")

code(r"""
import unicodedata

CORRECOES_GRAFIA = {        # valor inteiro -> forma canônica
    "twitte": "twitter",
    "fb": "facebook",
    "bradock": "braddock",
}
CORRECOES_TRECHO = {        # trecho dentro do valor -> forma canônica
    "calaecinto": "calcaecinto",   # 'calça' que perdeu o 'ç' em algum sistema de origem
}
PADRAO_RASTREAMENTO = r"(utm_\w+=[^,\s&]*|[?&]\S*)"
ROTULO_AUSENTE = "nao informado"


def remover_acentos(texto):
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


def partes_canal(texto):
    # Aplica as regras 1-6 e devolve a lista de origens distintas (na ordem original)
    partes = []
    for parte in texto.split(","):
        p = remover_acentos(parte.strip().lower())
        p = re.sub(PADRAO_RASTREAMENTO, "", p).strip(" /")
        for errado, certo in CORRECOES_TRECHO.items():
            p = p.replace(errado, certo)
        p = CORRECOES_GRAFIA.get(p, p)
        if p and p not in partes:
            partes.append(p)
    return partes


def normalizar_canal(valor):
    if pd.isna(valor):
        return ROTULO_AUSENTE
    partes = partes_canal(valor)
    return partes[0] if partes else ROTULO_AUSENTE


def extrair_midia(valor):
    if pd.isna(valor):
        return np.nan
    achado = re.search(r"utm_medium=([^,\s&]+)", valor, flags=re.IGNORECASE)
    return achado.group(1).lower() if achado else np.nan


# Demonstração: quantos valores distintos restam após cada regra (aplicadas cumulativamente)
etapas_normalizacao = [
    ("0. Original", lambda s: s),
    ("1. strip + minúsculas", lambda s: s.str.strip().str.lower()),
    ("2. sem acentos", lambda s: s.map(remover_acentos)),
    ("3. sem parâmetros de rastreamento", lambda s: s.str.replace(PADRAO_RASTREAMENTO, "", regex=True)),
    ("4. listas: primeira origem distinta", lambda s: s.map(lambda t: t.split(",")[0].strip())),
    ("5. sem '/' e espaços nas bordas", lambda s: s.str.strip(" /")),
    ("6. dicionário de grafias", lambda s: s.map(normalizar_canal)),
]
serie, evolucao = canal_preenchido.copy(), []
for nome, funcao in etapas_normalizacao:
    serie = funcao(serie)
    evolucao.append((nome, serie.nunique()))
pd.DataFrame(evolucao, columns=["regra aplicada", "valores_distintos"])
""")

md(r"""
A normalização reduz a quantidade de grafias distintas, mas **o que resta não é erro**. São centenas de **códigos de campanha legítimos**, que continuam distintos no `CanalVenda_Normalizado`: normalizar é padronizar a escrita, não apagar informação. A agregação em poucas categorias analisáveis é papel de outra coluna, o `GrupoCanal`.

A célula abaixo cria as três colunas exigidas, mais a mídia extraída e a *flag* de múltiplas origens.
""")

code(r"""
df_clean["CanalVenda_Original"] = df_clean["CanalVenda"]
df_clean["CanalVenda_Normalizado"] = df_clean["CanalVenda"].map(normalizar_canal)
df_clean["CanalVenda_Midia"] = df_clean["CanalVenda"].map(extrair_midia)
df_clean["flag_canal_multiplo"] = df_clean["CanalVenda"].map(
    lambda v: False if pd.isna(v) else len(partes_canal(v)) > 1)
df_clean = df_clean.drop(columns="CanalVenda")  # substituída por CanalVenda_Original (conteúdo idêntico)

assert df_clean["CanalVenda_Original"].equals(df_raw.loc[df_clean.index, "CanalVenda"]), "Original alterado"

print(f"Distintos no original   : {df_clean['CanalVenda_Original'].nunique()} (+ ausentes)")
print(f"Distintos no normalizado: {df_clean['CanalVenda_Normalizado'].nunique()} (incluindo '{ROTULO_AUSENTE}')")
print(f"Vendas com mídia extraída (utm_medium): {df_clean['CanalVenda_Midia'].notna().sum()} "
      f"-> {df_clean['CanalVenda_Midia'].value_counts().to_dict()}")
print(f"Vendas com mais de uma origem distinta: {df_clean['flag_canal_multiplo'].sum()}")
""")

md(r"""
### 7.5.3 Taxonomia: `GrupoCanal`

A taxonomia agrupa os canais pela **natureza do tráfego**, que é a pergunta que o marketing faz ("quanto vem de busca? de parcerias? de campanhas próprias?"). Ela é aplicada por **regras ordenadas**, e a primeira que casa define o grupo:

| Ordem | Grupo | Regra | Justificativa |
|---|---|---|---|
| 1 | Não informado | canal ausente | Ausência explícita, nunca misturada a outra categoria |
| 2 | E-mail e CRM | `CanalVenda_Midia = newsletter` ou `aviseme` | O parâmetro UTM identifica o meio e-mail; `AviseMe` é, pelo nome, o alerta de disponibilidade enviado ao cliente |
| 3 | Campanhas próprias XPTO | contém `xpto` ou começa com `campanha` | Prefixo com o nome da empresa: vitrines, banners e ações internas |
| 4 | Busca | `google`, `googleadwords`, `yahoo`, `bing` | Buscadores (orgânico e pago); ex.: google → Busca, yahoo → Busca |
| 5 | Portais e mídia display | começa com `uol` ou `himidia` | Portal UOL (formatos de banner, *newsletter* do portal) e rede de anúncios |
| 6 | Redes sociais e blogs | `twitter`, `facebook`, `redessociais`, `blog` | Mídias sociais e conteúdo |
| 7 | Bancos, cartões e fidelidade | bancos, bandeiras, seguradoras e programas de pontos (`visavale`, `dotz`, `unibanco`, `citi`, `hsbc`...) | Parcerias com bases de clientes de instituições financeiras |
| 8 | Comparadores e marketplaces | `buscape`, `mercadolivre` | Sites que listam ofertas de várias lojas |
| 9 | Outros parceiros | lista explícita de parceiros conhecidos sem categoria clara | Canais externos identificados, mas cuja natureza não se deduz com segurança pelo nome |
| 10 | Não mapeado | nenhuma regra casou | **Rede de segurança:** um canal novo em carga futura cai aqui, em vez de ser classificado errado ou gerar erro |

**Limites desta taxonomia:** os grupos 2, 5, 7 e 9 dependem da interpretação do nome. Por exemplo, `Coluna*` e `STB` foram mantidos em "Outros parceiros" justamente porque o nome não permite inferir a natureza do canal. Em um projeto real, a tabela deve ser validada com a equipe de marketing. Por isso ela está isolada em uma estrutura de dados, e não espalhada pelo código.
""")

code(r"""
REGRAS_GRUPO_CANAL = [
    ("Não informado",                 r"^nao informado$"),
    ("E-mail e CRM",                  r"^aviseme$"),
    ("Campanhas próprias XPTO",       r"xpto|^campanha"),
    ("Busca",                         r"^(google|googleadwords|yahoo|bing)$"),
    ("Portais e mídia display",       r"^(uol|himidia)"),
    ("Redes sociais e blogs",         r"^(twitter|facebook|redessociais|blog)$"),
    ("Bancos, cartões e fidelidade",  r"^(visavale|dotz|unicard|unibanco|citi|credicard|hsbc|americanasitaucard"
                                      r"|cartaopetrobras|bbseguro|clubmapfre|portoseguro)"),
    ("Comparadores e marketplaces",   r"^(buscape|mercadolivre)$"),
    ("Outros parceiros",              r"^(coluna|extra|muccashop|muccaclub|stb|descontobrabo|cotacota|braddock"
                                      r"|compra3|lg|fashionismo|calvin_klein|faslhe|depoisdosquinze|inclub"
                                      r"|gourmet_travel|nautico|vasco|elike|opote|t-shirt|cvg|sergio_k|gola)"),
]
GRUPO_NAO_MAPEADO = "Não mapeado"
MIDIAS_EMAIL = {"newsletter", "email", "e-mail"}


def classificar_canal(normalizado, midia):
    # Mídia de e-mail tem precedência: o parâmetro UTM informa o meio, independentemente do nome
    if normalizado != ROTULO_AUSENTE and isinstance(midia, str) and midia in MIDIAS_EMAIL:
        return "E-mail e CRM"
    for grupo, padrao in REGRAS_GRUPO_CANAL:
        if re.search(padrao, normalizado):
            return grupo
    return GRUPO_NAO_MAPEADO


df_clean["GrupoCanal"] = [classificar_canal(n, m) for n, m in
                          zip(df_clean["CanalVenda_Normalizado"], df_clean["CanalVenda_Midia"])]

registrar_etapa("7.5", "D. Transformar", len(df_clean), len(df_clean), len(df_clean),
                "Criação de CanalVenda_Original, CanalVenda_Normalizado, CanalVenda_Midia, GrupoCanal "
                "e flag_canal_multiplo")

resumo_grupos = (df_clean.groupby("GrupoCanal")
                 .agg(vendas=("id_registro", "size"),
                      canais_normalizados=("CanalVenda_Normalizado", "nunique"),
                      grafias_originais=("CanalVenda_Original", "nunique"),
                      faturamento=("ValorVenda", "sum"))
                 .sort_values("vendas", ascending=False))
resumo_grupos["%_vendas"] = (resumo_grupos["vendas"] / len(df_clean) * 100).round(2)
resumo_grupos
""")

code(r"""
# Quais canais caíram em "Não mapeado"? (deve ser uma lista curta e justificável)
nao_mapeados = df_clean.loc[df_clean["GrupoCanal"].eq(GRUPO_NAO_MAPEADO), "CanalVenda_Original"].value_counts()
print(f"Canais não mapeados: {len(nao_mapeados)} valor(es), {nao_mapeados.sum()} vendas")
print(nao_mapeados.to_string())
""")

md(r"""
O único valor sem grupo é `E`, uma **letra isolada**. Ela não identifica nenhum canal e pode ser um valor truncado. Classificá-la em qualquer grupo seria adivinhação, por isso ela fica em "Não mapeado". O fato de a regra de segurança capturar apenas esse caso mostra que a taxonomia cobre todos os demais valores da base.
""")

md(r"""
### 7.5.4 Tabela de mapeamento: original → normalizado → grupo

A tabela completa tem uma linha por grafia original. Abaixo aparecem as mais frequentes e, em seguida, exemplos que mostram as regras em ação (caixa, UTM, listas, grafias).
""")

code(r"""
tabela_mapeamento_canal = (df_clean
    .assign(CanalVenda_Original=df_clean["CanalVenda_Original"].fillna("<ausente>"))
    .groupby(["CanalVenda_Original", "CanalVenda_Normalizado", "GrupoCanal"])
    .size().rename("vendas").reset_index()
    .sort_values("vendas", ascending=False, ignore_index=True))

print(f"Linhas na tabela de mapeamento (grafias originais distintas): {len(tabela_mapeamento_canal)}")
with pd.option_context("display.max_rows", 30):
    display(tabela_mapeamento_canal.head(25))
""")

code(r"""
# Exemplos de cada regra: grafias originais diferentes que convergem para o mesmo canal normalizado
exemplos = ["twitter", "facebook", "braddock", "xptoourmasc1", "xptoourncl", "xptols",
            "xptoourfemcalcaecintockj", "xptosbanner"]
convergencia = tabela_mapeamento_canal[tabela_mapeamento_canal["CanalVenda_Normalizado"].isin(exemplos)]
with pd.option_context("display.max_rows", 60, "display.max_colwidth", 70):
    display(convergencia.sort_values(["CanalVenda_Normalizado", "vendas"], ascending=[True, False]))
""")

code(r"""
# Participação das vendas por grupo de canal
dados_grafico = resumo_grupos["vendas"].sort_values()

fig, ax = plt.subplots(figsize=(10, 5))
barras = ax.barh(dados_grafico.index, dados_grafico.values, color="#2a78d6", height=0.65)
for barra, qtd in zip(barras, dados_grafico.values):
    ax.text(barra.get_width() + 80, barra.get_y() + barra.get_height() / 2,
            f"{qtd:,}".replace(",", ".") + f"  ({qtd / len(df_clean) * 100:.1f}%)".replace(".", ","),
            va="center", color="#52514e", fontsize=9)
ax.set_title("Vendas por grupo de canal (base CLEAN)")
ax.set_xlabel("Quantidade de vendas")
ax.set_ylabel("")
ax.set_xlim(0, dados_grafico.max() * 1.22)
ax.grid(axis="x", color="#e5e5e3")
ax.set_axisbelow(True)
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
plt.show()
""")

md(r"""
### 7.5.5 Síntese do canal de venda

**Solução adotada:** o campo bruto foi preservado em `CanalVenda_Original` e decomposto em informações analisáveis:

- **`CanalVenda_Normalizado`:** grafia padronizada, sem parâmetros e sem duplicação. Os códigos de campanha foram mantidos.
- **`CanalVenda_Midia`:** o meio de comunicação extraído do parâmetro UTM, antes descartado ou "colado" ao nome do canal.
- **`GrupoCanal`:** a taxonomia de negócio, com regras ordenadas, explícitas e com uma rede de segurança para canais novos.
- **`flag_canal_multiplo`:** as vendas com mais de uma origem.

Nenhuma venda foi removida por problema de canal, e a ausência passou a ser uma **categoria explícita**, e não um valor que some silenciosamente de agregações. A seção 9.4 mostra como essa transformação muda a leitura de quais canais mais vendem.

**Por que o `CanalVenda_Normalizado` ainda tem centenas de valores?** Porque a normalização foi feita em **dois níveis**, cada um com um papel:

| Nível | Coluna | Cardinalidade | Pergunta que responde |
|---|---|---|---|
| Grafia | `CanalVenda_Normalizado` | 519 canais + "nao informado" | "Qual campanha ou origem específica gerou a venda?" |
| Negócio | `GrupoCanal` | 10 grupos | "Quanto vem de busca, parceiros, campanhas próprias, e-mail?" |

Todas as grafias **equivalentes** foram unificadas: caixa, acentos, parâmetros UTM, listas repetidas, barras e erros de digitação (602 → 519). O que sobrou são **códigos de campanha diferentes entre si** (433 deles no grupo de campanhas próprias XPTO), e não o mesmo canal escrito de formas diferentes. Juntar `xptoourmasc1` e `xptoourfem2` na coluna normalizada destruiria a informação de qual peça de campanha vendeu. O agrupamento de canais que "deveriam ser agrupados" (ex.: `google` e `yahoo` em Busca) é justamente o papel do `GrupoCanal`.
""")

md(r"""
## 7.6 Geografia: região do cliente

A UF tem 27 valores, o que dificulta comparações com poucas vendas por estado. A coluna `Regiao` agrega as UFs nas cinco grandes regiões, a partir de um **dicionário de domínio** (divisão regional do IBGE, o Instituto Brasileiro de Geografia e Estatística). Ela é usada na seção 9.5 e fica disponível na base final. O `assert` garante que nenhuma UF fique sem região, o que protegeria o *pipeline* contra um código de UF inválido em uma carga futura.
""")

code(r"""
REGIOES = {
    "Norte": ["AC", "AM", "AP", "PA", "RO", "RR", "TO"],
    "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Centro-Oeste": ["DF", "GO", "MS", "MT"],
    "Sudeste": ["ES", "MG", "RJ", "SP"],
    "Sul": ["PR", "RS", "SC"],
}
UF_PARA_REGIAO = {uf: regiao for regiao, ufs in REGIOES.items() for uf in ufs}
assert set(UF_PARA_REGIAO) == UFS_VALIDAS, "Dicionário de regiões diferente do domínio de UFs (3.9)"

df_clean["Regiao"] = df_clean["UF_Cliente"].astype(str).map(UF_PARA_REGIAO).astype("category")
assert df_clean["Regiao"].notna().all(), "UF sem região"
registrar_etapa("7.6", "D. Transformar", len(df_clean), len(df_clean), len(df_clean), "Criação de Regiao")
frequencias(df_clean["Regiao"])
""")

md(r"""
## 7.7 Resumo das transformações

As células a seguir consolidam o que foi feito nas seções 6 e 7: o *log* de etapas, a contagem de registros modificados e removidos, e a lista de novas variáveis. Por último, confirmamos que o `df_raw` **permanece intocado**.
""")

code(r"""
log_etapas_df = pd.DataFrame(log_etapas)
log_etapas_df.index = log_etapas_df.index + 1
with pd.option_context("display.max_colwidth", 110):
    display(log_etapas_df)
""")

code(r"""
log_registros_df = pd.concat(log_registros, ignore_index=True)

resumo_log = (log_registros_df.groupby(["etapa", "acao", "coluna", "motivo"])
              .agg(registros=("id_registro", "nunique")).reset_index())
with pd.option_context("display.max_colwidth", 90):
    display(resumo_log)

print(f"Registros removidos                  : {log_registros_df.loc[log_registros_df['acao'].eq('removido'), 'id_registro'].nunique()}")
print(f"Registros com algum valor modificado : {log_registros_df.loc[log_registros_df['acao'].eq('modificado'), 'id_registro'].nunique()}")
print(f"Linhas: RAW {len(df_raw):,} -> CLEAN {len(df_clean):,}")
""")

code(r"""
# Exemplo de rastreabilidade: as primeiras entradas do log, linha a linha
log_registros_df.head(8)
""")

code(r"""
colunas_novas = [c for c in df_clean.columns if c not in df_raw.columns]
DESCRICAO_NOVAS = {
    "id_registro": "Posição do registro no RAW (rastreabilidade)",
    "flag_nascimento_invalido": "Motivo da correção do nascimento: 'sentinela' ou 'posterior_compra'",
    "flag_possivel_repeticao": "Repete cliente e valor de venda anterior em até 60 min",
    "flag_cliente_atipico": "Cliente acima do percentil 99,9 de compras",
    "flag_cliente_multi_uf": "Cliente aparece com mais de uma UF",
    "Ano": "Ano da venda", "Mes": "Mês da venda (1-12)", "AnoMes": "Ano e mês (AAAA-MM)",
    "Dia": "Dia do mês", "DiaSemana": "Dia da semana em português (ordenado)",
    "FimDeSemana": "Venda no sábado ou domingo", "Hora": "Hora da venda (0-23)",
    "PeriodoDia": "Madrugada, Manhã, Tarde ou Noite",
    "IdadeNaCompra": "Idade exata do cliente na data da compra",
    "flag_idade_improvavel": "Idade < 16 ou > 100 anos",
    "FaixaEtaria": "Faixa etária (com 'Idade improvável' e 'Não informado')",
    "flag_valor_zero": "Venda com valor R$ 0,00",
    "flag_valor_extremo": "Valor acima de Q3 + 1,5 IQR (informativa)",
    "flag_pagamento_inconsistente": "Violação do domínio de pagamento (Id, tipo ou parcelas)",
    "flag_parcelas_zero": "Cartão de crédito com 0 parcelas",
    "ModalidadePagamento": "À vista, Parcelado ou Não informado",
    "ValorParcela": "Valor de cada parcela",
    "CanalVenda_Original": "Texto bruto do canal (preservado)",
    "CanalVenda_Normalizado": "Canal com grafia padronizada",
    "CanalVenda_Midia": "Mídia extraída do parâmetro utm_medium",
    "flag_canal_multiplo": "Venda com mais de uma origem distinta no canal",
    "GrupoCanal": "Taxonomia de negócio do canal",
    "Regiao": "Região do IBGE correspondente à UF",
    "flag_rajada_compras": "Cliente com 5+ compras no mesmo dia",
}
assert set(colunas_novas) == set(DESCRICAO_NOVAS), set(colunas_novas) ^ set(DESCRICAO_NOVAS)

novas = pd.DataFrame({"tipo": df_clean[colunas_novas].dtypes.astype(str),
                      "descricao": pd.Series(DESCRICAO_NOVAS)}).loc[colunas_novas]
print(f"Novas variáveis: {len(colunas_novas)} | colunas no df_clean: {df_clean.shape[1]}")
with pd.option_context("display.max_colwidth", 90, "display.max_rows", 40):
    display(novas)
""")

code(r"""
# Garantia final: o RAW não foi modificado em nenhuma etapa
hash_atual = pd.util.hash_pandas_object(df_raw, index=True).sum()
assert hash_atual == HASH_RAW, "O df_raw foi alterado!"
print(f"df_raw intacto: hash {hash_atual} idêntico ao calculado na leitura.")

# Resumo das flags de qualidade
flags = [c for c in df_clean.columns if c.startswith("flag_")]
# Flags booleanas: soma dos True; flag de motivo (texto): quantidade de preenchidos
resumo_flags = pd.Series({f: int(df_clean[f].sum() if pd.api.types.is_bool_dtype(df_clean[f])
                                 else df_clean[f].notna().sum())
                          for f in flags}, name="vendas_marcadas").to_frame()
resumo_flags["%"] = (resumo_flags["vendas_marcadas"] / len(df_clean) * 100).round(2)
resumo_flags
""")

md(r"""
**Síntese das seções 6 e 7:**

- **Registros removidos:** apenas 1 (duplicata exata). A base CLEAN mantém 28.504 das 28.505 vendas.
- **Registros modificados:** nascimentos inválidos convertidos em ausentes e valores arredondados para centavos, todos rastreáveis no `log_registros_df` pelo `id_registro`.
- **Novas variáveis:** 29 colunas que não existiam no RAW com esse nome. Uma delas, `CanalVenda_Original`, é a `CanalVenda` renomeada, então são **28 variáveis realmente novas**: componentes de data, idade e faixa etária, região, atributos de pagamento, as colunas derivadas do canal, o `id_registro` e **11 *flags* de qualidade**. Com as 10 originais, a base final tem 38 colunas. Nenhuma coluna original teve seu conteúdo perdido: `CanalVenda` vive em `CanalVenda_Original`, e os valores originais de nascimento e de valor continuam no RAW.
- **Princípio seguido:** das anomalias encontradas, a maioria foi **marcada**, e não corrigida nem removida. A base CLEAN entrega **mais informação que a RAW**, não menos: além de cada dado, ela diz o quanto se pode confiar nele.
""")
