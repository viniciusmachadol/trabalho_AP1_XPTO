# Seções 3 a 5 do notebook. Executado por build_notebook.py (usa md() e code() de lá).

# =====================================================================
# 3. Data profiling
# =====================================================================
md(r"""
# 3. *Data profiling*
""")

md(r"""
## 3.1 Contexto: o que o *profiling* procura

*Data profiling* é a descrição sistemática de cada atributo: quanto está preenchido, quais valores assume, como se distribui. O objetivo não é "achar erros" de forma genérica, mas responder a perguntas concretas: há ausentes? Há valores sentinela, isto é, preenchimentos artificiais que imitam um dado real? As categorias equivalentes estão escritas do mesmo jeito? As colunas concordam entre si? A granularidade é a esperada?

A seção está dividida em duas partes:

- **Visão consolidada (3.2 e 3.3):** uma tabela com as estatísticas de todas as colunas e as frequências das principais categorias.
- **Busca ativa (3.4 a 3.13):** uma investigação dirigida para cada tipo de problema, sempre com o código que produz a evidência.

Nenhuma alteração é feita no `df_raw`. As conversões necessárias para medir datas e idades são feitas em **séries auxiliares**, descartáveis.
""")

code(r"""
# Séries auxiliares para o profiling (df_raw permanece intocado)
FORMATOS_DATA = {"DataVenda": "%Y-%m-%d %H:%M:%S", "Cliente_Data_Nascimento": "%Y-%m-%d"}

aux_venda = pd.to_datetime(df_raw["DataVenda"], format=FORMATOS_DATA["DataVenda"], errors="coerce")
aux_nasc = pd.to_datetime(df_raw["Cliente_Data_Nascimento"],
                          format=FORMATOS_DATA["Cliente_Data_Nascimento"], errors="coerce")


def idade_na_data(nascimento, referencia):
    # Idade completa em anos na data de referência (NaN se o nascimento for ausente)
    anos = referencia.dt.year - nascimento.dt.year
    ainda_nao_fez = (referencia.dt.month * 100 + referencia.dt.day) < (nascimento.dt.month * 100 + nascimento.dt.day)
    return (anos - ainda_nao_fez.astype(int)).where(nascimento.notna()).astype("Int64")


# Idade exata na data da compra, calculada sobre o RAW (sentinelas e datas impossíveis incluídas).
# A mesma função é usada na seção 7.2, para que RAW e CLEAN sejam comparáveis pelo mesmo método.
aux_idade = idade_na_data(aux_nasc, aux_venda)

print(f"Datas de venda não convertidas     : {aux_venda.isna().sum()}")
print(f"Nascimentos não convertidos        : {aux_nasc.isna().sum()} "
      f"(ausentes na origem: {df_raw['Cliente_Data_Nascimento'].isna().sum()})")
""")

md(r"""
A quantidade de nascimentos não convertidos é igual à de ausentes na origem: **todas as datas preenchidas estão em formato válido**. Os problemas de data, se existirem, serão de **conteúdo**, não de formato.
""")

md(r"""
## 3.2 Visão consolidada: perfil por coluna

O perfil depende do **tipo semântico** de cada coluna, definido na seção 2.5, e não do tipo que o `pandas` inferiu. Média e quartis só fazem sentido para medidas (`ValorVenda`, `NumeroParcelas`) e para datas; para códigos e categorias, o que interessa é o domínio e a frequência. A função `perfilar_coluna` aplica essa regra de forma genérica, e pode ser reutilizada em qualquer nova carga.
""")

code(r"""
TIPO_SEMANTICO = {
    "DataVenda": "data",
    "ValorVenda": "numérico",
    "IdFormaDePagamento": "código",
    "FormaPagamento": "categórico",
    "TipoFormaPagamento": "categórico",
    "NumeroParcelas": "numérico",
    "Cliente_Codigo": "código",
    "Cliente_Data_Nascimento": "data",
    "UF_Cliente": "categórico",
    "CanalVenda": "texto livre",
}


def perfilar_coluna(serie, tipo, formato_data=None, n_top=3):
    # Perfil de uma coluna conforme o seu tipo semântico
    n = len(serie)
    ausentes = int(serie.isna().sum())
    perfil = {
        "tipo_semantico": tipo,
        "tipo_pandas": str(serie.dtype),
        "preenchidos": n - ausentes,
        "ausentes": ausentes,
        "ausentes_%": round(ausentes / n * 100, 2),
        "distintos": serie.nunique(dropna=True),
    }
    if tipo == "numérico":
        q1, mediana, q3 = serie.quantile([0.25, 0.50, 0.75])
        iqr = q3 - q1
        extremos = ((serie < q1 - 1.5 * iqr) | (serie > q3 + 1.5 * iqr)).sum()
        perfil.update({"min": f"{serie.min():,.2f}", "q1": f"{q1:,.2f}", "mediana": f"{mediana:,.2f}",
                       "media": f"{serie.mean():,.2f}", "q3": f"{q3:,.2f}", "max": f"{serie.max():,.2f}",
                       "extremos_IQR": int(extremos)})
    elif tipo == "data":
        datas = pd.to_datetime(serie, format=formato_data, errors="coerce")
        q1, mediana, q3 = datas.quantile([0.25, 0.50, 0.75])
        fmt = lambda d: d.strftime("%Y-%m-%d")
        perfil.update({"min": fmt(datas.min()), "q1": fmt(q1), "mediana": fmt(mediana),
                       "media": fmt(datas.mean()), "q3": fmt(q3), "max": fmt(datas.max())})
    top = serie.value_counts().head(n_top)
    perfil["principais_valores (freq.)"] = "; ".join(f"{k} ({v:,})" for k, v in top.items())
    return perfil


perfil = pd.DataFrame({
    col: perfilar_coluna(df_raw[col], TIPO_SEMANTICO[col], FORMATOS_DATA.get(col))
    for col in df_raw.columns
}).T
perfil.index.name = "variavel"

with pd.option_context("display.max_colwidth", 80):
    display(perfil)
""")

md(r"""
**Primeiras leituras da tabela consolidada:**

- **Ausentes:** apenas `Cliente_Data_Nascimento` (9,24%) e `CanalVenda` (33,26%) têm lacunas. No canal, **um terço das vendas** não tem origem registrada.
- **`ValorVenda`:** a média (314,61) fica bem acima da mediana (217,90), sinal de **assimetria à direita**, com uma cauda de vendas altas. O mínimo é **0,00** e o máximo **17.016,25**. A regra do IQR (intervalo interquartil) aponta 2.083 valores extremos.
- **`Cliente_Data_Nascimento`:** o mínimo é **1900-01-01**, data típica de preenchimento automático, e o máximo **2011-12-16**, **posterior ao fim da base** (agosto de 2011).
- **`Cliente_Codigo`:** 13.737 clientes para 28.505 vendas, e um único cliente aparece 236 vezes.
- **`CanalVenda`:** 602 valores distintos em texto livre, um volume incompatível com a quantidade real de canais de uma operação de e-commerce.

Esses sinais orientam a busca ativa das subseções seguintes.
""")

md(r"""
## 3.3 Frequências: principais categorias

Para as colunas categóricas, a distribuição de frequências mostra o domínio efetivo e ajuda a identificar categorias raras, que podem ser erros ou casos especiais.
""")

code(r"""
def frequencias(serie, n=10):
    # Frequência absoluta e relativa das n categorias mais comuns (ausentes incluídos)
    contagem = serie.value_counts(dropna=False).head(n)
    return pd.DataFrame({"quantidade": contagem,
                         "percentual": (contagem / len(serie) * 100).round(2)})


for coluna in ["FormaPagamento", "TipoFormaPagamento", "NumeroParcelas"]:
    print(f"\n=== {coluna} ===")
    display(frequencias(df_raw[coluna], n=15))
""")

code(r"""
print("=== UF_Cliente (10 principais) ===")
display(frequencias(df_raw["UF_Cliente"]))
print("=== CanalVenda (10 principais) ===")
display(frequencias(df_raw["CanalVenda"]))
""")

md(r"""
Três pontos merecem atenção:

- **`Glamour VIP`** (forma de pagamento) aparece em apenas 3 vendas. É uma categoria rara, mas consistente (seu tipo é `Pagamentos Glamour`). Por isso **não é um erro**: é um meio de pagamento de baixo uso.
- **`NumeroParcelas = 0`** ocorre em 585 vendas (2,05%). "Zero parcelas" não é um valor natural e será investigado em 3.8.
- **O maior "canal" de `CanalVenda` é a ausência de canal** (`NaN`, 9.482 vendas), maior até que `google` (5.593). Qualquer ranking de canais que ignore esse fato será distorcido.
""")

# ---- Busca ativa ----
md(r"""
## 3.4 Ausentes: onde estão e se seguem um padrão

Não basta contar ausentes. É preciso entender **em que nível** está a lacuna. No caso da data de nascimento, um atributo do **cliente**, e não da venda, vale verificar se a ausência é consistente por cliente: se um mesmo cliente tivesse a data em algumas vendas e não em outras, daria para recuperá-la a partir das outras vendas.
""")

code(r"""
ausentes = pd.DataFrame({
    "ausentes": df_raw.isna().sum(),
    "ausentes_%": (df_raw.isna().mean() * 100).round(2),
})
display(ausentes[ausentes["ausentes"] > 0])

# O nascimento ausente é consistente por cliente? (algum cliente tem data em uma venda e não em outra?)
por_cliente = df_raw.groupby("Cliente_Codigo")["Cliente_Data_Nascimento"]
clientes_mistos = (por_cliente.apply(lambda s: s.isna().any() and s.notna().any())).sum()
clientes_sem_nasc = (por_cliente.apply(lambda s: s.isna().all())).sum()
datas_divergentes = (por_cliente.nunique() > 1).sum()

print(f"Clientes sem nenhuma data de nascimento           : {clientes_sem_nasc:,}")
print(f"Clientes com data em umas vendas e ausente em outras: {clientes_mistos}")
print(f"Clientes com mais de uma data de nascimento        : {datas_divergentes}")
""")

md(r"""
**Diagnóstico:** a ausência de nascimento é uma característica do **cadastro do cliente**. Nenhum cliente tem a data em uma venda e ausente em outra, e nenhum tem duas datas diferentes. Por isso **não há como recuperar** esses valores a partir da própria base, e a ausência deve ser mantida e tratada como "não informado". O mesmo raciocínio vale para `CanalVenda`: a origem da venda não se infere de outra coluna.
""")

md(r"""
## 3.5 Valores sentinela: datas de nascimento artificiais

Um **valor sentinela** é um preenchimento artificial que ocupa o lugar de um dado ausente. Por exemplo, sistemas que exigem uma data preenchida gravam `1900-01-01` quando o cliente não informa o nascimento. O sentinela é mais perigoso que o ausente, porque **parece um dado válido**: essa data produziria uma idade de 111 anos, e o cliente entraria no cálculo da idade média.

A evidência mais forte de um sentinela é a **concentração improvável**: muitos clientes *diferentes* compartilhando exatamente a mesma data.
""")

code(r"""
# Datas de nascimento compartilhadas pelo maior número de clientes distintos
clientes_por_nasc = (df_raw.groupby("Cliente_Data_Nascimento")
                     .agg(clientes_distintos=("Cliente_Codigo", "nunique"),
                          vendas=("Cliente_Codigo", "size"))
                     .sort_values("clientes_distintos", ascending=False))
display(clientes_por_nasc.head(8))

mediana_clientes = clientes_por_nasc["clientes_distintos"].median()
print(f"Mediana de clientes distintos por data de nascimento: {mediana_clientes:.0f}")
""")

code(r"""
# Distribuição dos anos de nascimento: o pico isolado em 1900 é visualmente evidente
nasc_por_ano = aux_nasc.dt.year.value_counts().sort_index()

fig, ax = plt.subplots(figsize=(11, 4))
ax.bar(nasc_por_ano.index, nasc_por_ano.values, width=0.8, color="#2a78d6")
ax.set_title("Vendas por ano de nascimento do cliente (base RAW)")
ax.set_xlabel("Ano de nascimento")
ax.set_ylabel("Quantidade de vendas")
ax.annotate(f"1900: {nasc_por_ano.get(1900, 0)} vendas", xy=(1900, nasc_por_ano.get(1900, 0)),
            xytext=(1905, nasc_por_ano.max() * 0.5), color="#52514e",
            arrowprops={"arrowstyle": "->", "color": "#52514e"})
ax.grid(axis="y", color="#e5e5e3")
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
plt.show()

anos_1900 = df_raw.loc[aux_nasc.dt.year <= 1900, "Cliente_Data_Nascimento"].value_counts()
print("Datas com ano <= 1900:")
print(anos_1900.to_string())
""")

md(r"""
**Diagnóstico:**

- **Caso 1 — `1900-01-01` (o mais relevante):** 141 clientes distintos compartilham essa data, enquanto a data seguinte mais comum reúne só 13 (a mediana é 1 cliente por data). No gráfico, o ano de 1900 aparece como um pico isolado, separado do restante da distribuição por décadas quase vazias. Isso **não é um cliente centenário**: é um preenchimento padrão de sistema.
- **Caso 2 — `1900-11-11`:** 4 vendas. O que a define como sentinela é o **ano de 1900**, o mesmo valor-padrão do caso 1: nenhum cliente nascido nesse ano teria 110 anos e compraria pela internet em 2011. A regra adotada é, portanto, **objetiva e baseada no ano (≤ 1900)**, e não no formato da data.
- **Por que datas "bonitas" de outros anos não entram na regra:** existem nascimentos como `1910-10-10` (7 vendas, 1 cliente) e `1912-12-12` (1 venda), com o mesmo formato repetitivo. Eles são **suspeitos**, mas pertencem a um único cliente cada e produzem idades possíveis (100 e 98 anos). Diferentemente de `1900-01-01`, não há concentração entre clientes que prove preenchimento automático. Por isso são mantidos, e registrados aqui como ponto de atenção.
- **Caso 3 — datas `01-01` concentradas, como `1985-01-01` (13 clientes) e `2010-01-01` (9 clientes):** são suspeitas, mas **não conclusivas**. O primeiro de janeiro é um preenchimento comum quando só o ano é conhecido, mas também é uma data de nascimento real. Sem evidência forte, esses casos não serão tratados como sentinela. A de 2010 reaparece como idade improvável em 3.6.
""")

md(r"""
## 3.6 Problemas em datas: idade na data da compra

A idade relevante para o negócio é a que o cliente tinha **no momento da compra**, não a idade atual. Cruzar `Cliente_Data_Nascimento` com `DataVenda` revela três situações: idades **impossíveis** (negativas), **improváveis** (crianças ou pessoas com mais de 100 anos comprando) e **plausíveis**.

Os limites usados no diagnóstico são **16 anos**, idade abaixo da qual uma compra autônoma com cartão ou boleto em nome próprio é pouco provável, e **100 anos**.
""")

code(r"""
sentinela_1900 = aux_nasc.dt.year <= 1900

diagnostico_idade = pd.DataFrame({
    "situacao": ["Nascimento posterior à compra (idade < 0)",
                 "Idade entre 0 e 16 anos (improvável)",
                 "Idade acima de 100 anos, sem sentinela 1900 (improvável)",
                 "Sentinela 1900 (idade artificial)"],
    "vendas": [(aux_idade < 0).sum(),
               ((aux_idade >= 0) & (aux_idade < 16)).sum(),
               ((aux_idade > 100) & ~sentinela_1900).sum(),
               sentinela_1900.sum()],
})
display(diagnostico_idade)

print("Vendas com nascimento posterior à compra:")
display(df_raw.loc[aux_idade < 0, ["DataVenda", "Cliente_Codigo", "Cliente_Data_Nascimento"]])
""")

md(r"""
**Diagnóstico:**

- **Caso 1 — nascimento posterior à compra (impossível):** 12 vendas de clientes que, pelo cadastro, "nasceram" meses depois de comprar. Um caso chega a `2011-12-16`, data posterior ao fim da própria base. Provavelmente alguém digitou a data do cadastro ou da compra no campo de nascimento, mas não há como saber a data correta.
- **Caso 2 — clientes com menos de 16 anos (improvável):** 172 vendas. Podem ser erros de digitação, cadastros feitos por um responsável ou datas preenchidas com o ano corrente. São **possíveis mas improváveis**. Não há como distinguir os casos com certeza.
- **Caso 3 — acima de 100 anos sem sentinela:** nenhuma venda. O cliente mais velho fora do sentinela nasceu em `1910-10-10` e tinha **exatamente 100 anos** na data das 7 compras, o que fica no limite do plausível (ver 3.5).

A `DataVenda`, por sua vez, **não apresenta problemas**: todas as datas são válidas e ficam dentro do período esperado (2.4).
""")

md(r"""
## 3.7 Valores monetários: zeros, precisão e extremos

A coluna `ValorVenda` foi investigada em três frentes: valores nulos ou negativos, precisão incompatível com a moeda (mais de 2 casas decimais) e valores extremos.
""")

code(r"""
valor = df_raw["ValorVenda"]

# Frente 1: valores zero ou negativos, por forma de pagamento
print(f"Vendas com valor negativo: {(valor < 0).sum()}")
print(f"Vendas com valor zero    : {(valor == 0).sum()}")
display(df_raw.loc[valor == 0, "FormaPagamento"].value_counts().rename("vendas_valor_zero").to_frame())
""")

code(r"""
# Frente 2: valores com mais de 2 casas decimais (centavos fracionados)
mais_de_2_casas = (valor * 100).round(6) % 1 != 0
print(f"Vendas com mais de 2 casas decimais: {mais_de_2_casas.sum()}")
print(f"Maior diferença em relação ao valor arredondado: "
      f"R$ {(valor[mais_de_2_casas] - valor[mais_de_2_casas].round(2)).abs().max():.4f}")
# Formato com 4 casas para que as frações de centavo fiquem visíveis
with pd.option_context("display.float_format", "{:,.4f}".format):
    display(df_raw.loc[mais_de_2_casas, ["ValorVenda", "FormaPagamento", "NumeroParcelas"]].head(8))
""")

code(r"""
# Frente 3: extremos pela regra do IQR (intervalo interquartil)
q1, q3 = valor.quantile([0.25, 0.75])
iqr = q3 - q1
limite_sup = q3 + 1.5 * iqr
limite_sup_extremo = q3 + 3 * iqr

print(f"Q1 = {q1:,.2f} | Q3 = {q3:,.2f} | IQR = {iqr:,.2f}")
print(f"Limite superior (Q3 + 1,5 IQR): {limite_sup:,.2f} -> {(valor > limite_sup).sum():,} vendas "
      f"({(valor > limite_sup).mean() * 100:.1f}%)")
print(f"Limite extremo  (Q3 + 3 IQR)  : {limite_sup_extremo:,.2f} -> {(valor > limite_sup_extremo).sum():,} vendas")
print(f"Limite inferior (Q1 - 1,5 IQR): {q1 - 1.5 * iqr:,.2f} -> nenhum valor abaixo (mínimo = {valor.min():.2f})")

print("\nAs 8 maiores vendas:")
with pd.option_context("display.float_format", "{:,.4f}".format):
    display(df_raw.nlargest(8, "ValorVenda")[["DataVenda", "ValorVenda", "FormaPagamento",
                                                "NumeroParcelas", "Cliente_Codigo", "UF_Cliente"]])
""")

code(r"""
# Distribuição de ValorVenda em escala logarítmica (a escala linear esconderia a cauda)
fig, ax = plt.subplots(figsize=(10, 4))
ax.hist(valor[valor > 0], bins=np.logspace(np.log10(valor[valor > 0].min()), np.log10(valor.max()), 60),
        color="#2a78d6", edgecolor="white", linewidth=0.5)
ax.set_xscale("log")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}".replace(",", ".")))
ax.axvline(limite_sup, color="#52514e", linestyle="--", linewidth=1.5)
ax.text(limite_sup * 1.08, ax.get_ylim()[1] * 0.9, f"Q3 + 1,5 IQR = {limite_sup:,.0f}", color="#52514e")
ax.set_title("Distribuição do valor das vendas (escala logarítmica, sem valores zero)")
ax.set_xlabel("Valor da venda (R$, escala log)")
ax.set_ylabel("Quantidade de vendas")
ax.grid(axis="y", color="#e5e5e3")
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
plt.show()
""")

md(r"""
**Diagnóstico:**

- **Caso 1 — valor zero:** 16 vendas, 14 delas pagas com `Cupom de Desconto`. Um cupom que cobre 100% do pedido é **plausível** (brinde, troca, promoção). Já os 2 casos de `Boleto Bancário` com valor zero são **incoerentes**, porque não se emite boleto de R$ 0,00.
- **Caso 2 — centavos fracionados:** 77 vendas têm 3 ou 4 casas decimais (ex.: `431,275`). Isso **não é um erro de leitura**: o valor está assim no arquivo. A hipótese mais provável é um cálculo (desconto percentual ou juros) que não foi arredondado para centavos. A diferença para o valor arredondado é de no máximo meio centavo, então o impacto financeiro é desprezível, mas o valor não é monetariamente válido.
- **Caso 3 — extremos:** o critério do IQR marca 2.083 vendas (7,3%) acima de R$ 711,00. Uma proporção tão alta **não é compatível com erro**: é o formato natural de uma distribuição assimétrica de preços, como mostra o histograma, que é contínuo e sem ruptura. Os valores mais altos (R$ 17.016,25 e R$ 16.662,68) estão isolados, mas são coerentes com as demais colunas: forma de pagamento válida, parcelamento compatível. Um valor extremo **não é, por si só, um erro**.
""")

md(r"""
## 3.8 Pagamento: consistência entre Id, forma, tipo e parcelas

As quatro colunas de pagamento descrevem a mesma realidade e devem concordar entre si. A verificação tem duas etapas: (i) cada `IdFormaDePagamento` corresponde a uma única forma e a um único tipo? (ii) o número de parcelas é compatível com a forma de pagamento?
""")

code(r"""
# (i) Relação entre Id, forma e tipo: deve ser 1 para 1
combinacoes = df_raw.groupby(["IdFormaDePagamento", "FormaPagamento", "TipoFormaPagamento"]).size()
display(combinacoes.rename("vendas").to_frame())

print(f"Formas por Id : {df_raw.groupby('IdFormaDePagamento')['FormaPagamento'].nunique().max()}")
print(f"Ids por forma : {df_raw.groupby('FormaPagamento')['IdFormaDePagamento'].nunique().max()}")
""")

code(r"""
# (ii) Parcelas por forma de pagamento
display(pd.crosstab(df_raw["FormaPagamento"], df_raw["NumeroParcelas"]))
""")

md(r"""
A relação Id × forma × tipo é **perfeitamente consistente**: cada Id tem uma única forma e cada forma um único Id. O Id `5` não existe na base, mas isso não é um problema, apenas um código não utilizado no período. Boleto, cupom e Glamour VIP estão sempre em 1 parcela, o que é coerente.

A anomalia está nos **cartões de crédito com 0 parcelas**. A pergunta é: o zero é um erro aleatório ou tem padrão?
""")

code(r"""
cartao = df_raw["TipoFormaPagamento"].eq("Cartão de Crédito")
parcela_zero = cartao & df_raw["NumeroParcelas"].eq(0)

print(f"Vendas em cartão com 0 parcelas: {parcela_zero.sum()}")
print(f"Primeira ocorrência            : {aux_venda[parcela_zero].min()}")
print("\nOcorrências por mês:")
print(aux_venda[parcela_zero].dt.to_period("M").value_counts().sort_index().to_string())

# Comparação de valor com as demais vendas em cartão do mesmo período
periodo = cartao & (aux_venda >= aux_venda[parcela_zero].min())
comparacao = (df_raw[periodo].groupby(df_raw["NumeroParcelas"].eq(0).map({True: "0 parcelas", False: "1+ parcelas"}))
              ["ValorVenda"].agg(["count", "median", "mean"]))
display(comparacao)
""")

md(r"""
**Diagnóstico:** o zero **não é aleatório**. As 585 ocorrências começam em **10/06/2011** e não há nenhuma antes disso. Além disso, concentram-se em vendas de **valor baixo** (mediana de R$ 69,00, contra R$ 240,00 nas demais vendas em cartão do mesmo período). O padrão sugere uma **mudança no sistema** a partir de junho, por exemplo uma nova modalidade (débito, cartão pré-pago ou "à vista" registrado como 0) ou uma falha na captura das parcelas. Isso **não é um erro de digitação**, e a base não permite afirmar qual das hipóteses é a correta. É uma pergunta para a área de negócio.
""")

md(r"""
## 3.9 Domínio: unidades federativas

`UF_Cliente` tem domínio fechado e conhecido: as 27 unidades federativas do Brasil. A verificação compara os valores da base com uma lista de referência, e essa regra é reutilizável em qualquer carga futura.
""")

code(r"""
UFS_VALIDAS = {"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
               "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"}

ufs_base = set(df_raw["UF_Cliente"].dropna().unique())
print(f"UFs distintas na base : {len(ufs_base)}")
print(f"UFs fora do domínio   : {sorted(ufs_base - UFS_VALIDAS) or 'nenhuma'}")
print(f"UFs sem nenhuma venda : {sorted(UFS_VALIDAS - ufs_base) or 'nenhuma'}")
""")

md(r"""
`UF_Cliente` está **íntegra**: as 27 UFs aparecem, todas escritas no padrão oficial, sem variações de caixa ou espaços. Um bom lembrete de que o *profiling* também serve para **confirmar** que algo está correto.
""")

md(r"""
## 3.10 Duplicidades e granularidade: o que é uma linha?

A granularidade esperada é **uma linha = uma venda**. A verificação tem dois níveis:

- **Duplicata exata:** todas as colunas iguais, incluindo data e hora ao minuto.
- **Possível repetição:** o mesmo cliente, com o mesmo valor, em um intervalo curto (até 60 minutos). Pode ser uma segunda compra legítima, mas também uma **nova tentativa de pagamento** (por exemplo, cartão recusado e depois boleto) registrada como uma nova venda.
""")

code(r"""
duplicatas = df_raw.duplicated(keep="first")
print(f"Duplicatas exatas (linhas excedentes): {duplicatas.sum()}")
display(df_raw[df_raw.duplicated(keep=False)])
""")

code(r"""
JANELA_REPETICAO = pd.Timedelta(minutes=60)

# Ordena por cliente, valor e horário; mede o intervalo até a venda anterior de mesmo cliente e valor
ordem = pd.DataFrame({"cliente": df_raw["Cliente_Codigo"], "valor": df_raw["ValorVenda"],
                      "data": aux_venda, "forma": df_raw["FormaPagamento"]}).sort_values(["cliente", "valor", "data"])
grupo = ordem.groupby(["cliente", "valor"])
intervalo = grupo["data"].diff()
forma_anterior = grupo["forma"].shift()

repeticao = intervalo.notna() & (intervalo <= JANELA_REPETICAO) & (intervalo > pd.Timedelta(0))
print(f"Vendas repetidas (mesmo cliente e valor, até 60 min após a anterior): {repeticao.sum()}")
print(f"  - com a mesma forma de pagamento da anterior    : {(repeticao & (forma_anterior == ordem['forma'])).sum()}")
print(f"  - com forma de pagamento diferente da anterior  : {(repeticao & (forma_anterior != ordem['forma'])).sum()}")
print(f"Mediana do intervalo entre as duas vendas: {intervalo[repeticao].median()}")
""")

md(r"""
**Diagnóstico:**

- **Caso 1 — duplicata exata:** 1 par de linhas idênticas (cliente `375678`, R$ 195,00, mesmo minuto, mesma forma de pagamento). Duas vendas legítimas iguais no mesmo minuto são improváveis: trata-se de um registro em duplicidade.
- **Caso 2 — possíveis repetições (o mais relevante para a granularidade):** 891 vendas repetem cliente e valor de outra venda feita até 60 minutos antes, com intervalo mediano de 10 minutos. Em 201 delas **a forma de pagamento mudou**, padrão típico de "cartão recusado, tentou boleto". Isso **não é duplicidade comprovada**: o cliente pode ter comprado o mesmo item duas vezes. Mas indica que **nem toda linha é necessariamente uma venda concluída**, e a base não tem uma coluna de status do pedido que permita confirmar.
""")

md(r"""
## 3.11 Inconsistências entre colunas: o cliente e sua UF

Atributos do cliente deveriam ser estáveis entre as vendas de um mesmo `Cliente_Codigo`. Em 3.4 vimos que o nascimento é estável. A UF, porém, apresenta divergências.
""")

code(r"""
ufs_por_cliente = df_raw.groupby("Cliente_Codigo")["UF_Cliente"].nunique()
clientes_multi_uf = ufs_por_cliente[ufs_por_cliente > 1].index
vendas_multi_uf = df_raw["Cliente_Codigo"].isin(clientes_multi_uf)

print(f"Clientes com mais de uma UF : {len(clientes_multi_uf)}")
print(f"Vendas desses clientes      : {vendas_multi_uf.sum()}")
display(df_raw[vendas_multi_uf].groupby("Cliente_Codigo")["UF_Cliente"].unique().head(8).to_frame())
""")

md(r"""
**Diagnóstico:** 53 clientes (223 vendas) aparecem com mais de uma UF, quase sempre duas. Isso **não é necessariamente um erro**: a UF pode refletir o **endereço de entrega** de cada pedido (presente para alguém em outro estado, mudança de endereço). Como a base não informa se `UF_Cliente` é do cadastro ou da entrega, a divergência é **mantida e sinalizada**.
""")

md(r"""
## 3.12 Concentração por cliente: compradores atípicos

A distribuição de compras por cliente é muito concentrada no valor 1. Clientes com dezenas ou centenas de compras em oito meses podem ser revendedores, contas corporativas, contas de teste ou comportamento suspeito. Para defini-los de forma **genérica**, sem citar códigos, usamos o **percentil 99,9** do número de compras por cliente.
""")

code(r"""
compras_por_cliente = df_raw["Cliente_Codigo"].value_counts()
print(compras_por_cliente.describe().round(2).to_string())

limite_atipico = compras_por_cliente.quantile(0.999)
clientes_atipicos = compras_por_cliente[compras_por_cliente > limite_atipico]
print(f"\nLimite (percentil 99,9): {limite_atipico:.1f} compras")
print(f"Clientes acima do limite: {len(clientes_atipicos)} ({clientes_atipicos.sum()} vendas)")

# Perfil dos 3 clientes mais frequentes
top3 = clientes_atipicos.head(3).index
perfil_top = df_raw[df_raw["Cliente_Codigo"].isin(top3)].groupby("Cliente_Codigo").agg(
    vendas=("ValorVenda", "size"),
    valor_total=("ValorVenda", "sum"),
    ufs=("UF_Cliente", "nunique"),
    canal_mais_comum=("CanalVenda", lambda s: s.value_counts(dropna=False).index[0]),
    pct_canal_mais_comum=("CanalVenda", lambda s: round(s.value_counts(dropna=False, normalize=True).iloc[0] * 100, 1)),
    forma_mais_comum=("FormaPagamento", lambda s: s.mode().iloc[0]),
    dias_com_compra=("DataVenda", lambda s: s.str[:10].nunique()),
).sort_values("vendas", ascending=False)
perfil_top
""")

md(r"""
**Diagnóstico:** metade dos clientes compra uma única vez (mediana = 1), e o percentil 99,9 é de cerca de 30 compras. Acima dele estão 14 clientes, que somam 877 vendas. O caso mais extremo tem **236 vendas**, **100% pelo canal `HiMidia`**, quase todas em boleto, distribuídas em 30 dias diferentes. Um padrão tão uniforme **não é típico de um consumidor final** e se parece mais com uma conta de revenda, de integração ou de teste. Isso **não prova erro**, mas esse único cliente responde por uma fração relevante do canal `HiMidia` e pode distorcer o *ranking* de canais.

O cliente mais extremo chegou a fazer dezenas de compras **em um mesmo dia**. Isso levanta uma segunda pergunta, sobre **granularidade**: quantas compras um mesmo cliente costuma fazer em um único dia, e quantos clientes têm esse comportamento de "rajada"?
""")

code(r"""
# Compras do mesmo cliente no mesmo dia (pares cliente-dia)
dia_venda = df_raw["DataVenda"].str[:10]
compras_cliente_dia = df_raw.groupby(["Cliente_Codigo", dia_venda]).size()
dist_cliente_dia = compras_cliente_dia.value_counts().sort_index()
display(pd.DataFrame({"pares_cliente_dia": dist_cliente_dia,
                      "%_acumulado": (dist_cliente_dia.cumsum() / dist_cliente_dia.sum() * 100).round(2)}).head(8).T)

LIMITE_RAJADA = 5
em_rajada = df_raw.groupby(["Cliente_Codigo", dia_venda])["Cliente_Codigo"].transform("size") >= LIMITE_RAJADA
print(f"Vendas em dias com {LIMITE_RAJADA}+ compras do mesmo cliente: {em_rajada.sum()} "
      f"| clientes: {df_raw.loc[em_rajada, 'Cliente_Codigo'].nunique()}")
print(f"Boleto nessas vendas: {(df_raw.loc[em_rajada, 'FormaPagamento'] == 'Boleto Bancário').mean() * 100:.1f}% "
      f"| na base: {(df_raw['FormaPagamento'] == 'Boleto Bancário').mean() * 100:.1f}%")
""")

md(r"""
**Diagnóstico:** 99,6% dos pares cliente-dia têm no máximo 4 compras. Comprar **5 ou mais vezes no mesmo dia** é raro, mas não é exclusivo do cliente mais extremo: há centenas de vendas de dezenas de clientes nessa situação, com uso de boleto bem acima da média da base. Pode ser revenda, reemissão de boletos não pagos, teste ou fraude, e a base não tem o status do pedido para decidir. A investigação completa desse comportamento está na descoberta livre (9.6).
""")

md(r"""
## 3.13 Canal de venda: sinais de texto livre

`CanalVenda` será tratado em profundidade na seção 7.5. Aqui registramos apenas as **evidências** de que o campo exige normalização, medindo padrões recorrentes no texto.
""")

code(r"""
canal = df_raw["CanalVenda"].dropna()

sinais_canal = pd.DataFrame([
    ("Valores distintos (texto original)", canal.nunique(), len(canal)),
    ("Valores distintos ignorando maiúsculas/minúsculas", canal.str.lower().nunique(), len(canal)),
    ("Contém parâmetro de URL (utm_ / '=')", canal[canal.str.contains("=|utm_", regex=True)].nunique(),
     canal.str.contains("=|utm_", regex=True).sum()),
    ("Contém lista separada por vírgula", canal[canal.str.contains(",")].nunique(), canal.str.contains(",").sum()),
    ("Termina com '/'", canal[canal.str.endswith("/")].nunique(), canal.str.endswith("/").sum()),
    ("Começa com o prefixo 'xpto' (campanhas próprias)", canal[canal.str.lower().str.startswith("xpto")].nunique(),
     canal.str.lower().str.startswith("xpto").sum()),
], columns=["padrao", "valores_distintos", "vendas"])
sinais_canal
""")

code(r"""
# Exemplos: variações de caixa, listas, parâmetros e grafias próximas
grupos_caixa = canal.groupby(canal.str.lower()).agg(lambda s: dict(s.value_counts()))
print("Mesmo canal, grafias com caixa diferente (exemplos):")
print(grupos_caixa[grupos_caixa.apply(len) > 1].head(6).to_string(), "\n")

print("Listas com vírgula (exemplos):", canal[canal.str.contains(",")].value_counts().head(4).index.tolist())
print("Parâmetros de URL (exemplos) :", canal[canal.str.contains("=")].value_counts().head(3).index.tolist())

# Grafias próximas: pares de canais externos que parecem ser o mesmo
for termo in ["twitt", "bradd|bradock", "calcaecinto|calaecinto|calçaecinto", "^fb$|facebook", "google"]:
    achados = canal[canal.str.lower().str.contains(termo, regex=True)].value_counts()
    print(f"  '{termo}': {achados.head(6).to_dict()}")
""")

md(r"""
**Diagnóstico:** o campo `CanalVenda` mistura **identificador de canal**, **identificador de campanha** e **parâmetros de rastreamento** em um único texto livre. As evidências:

- **Caso 1 — ausência (o mais relevante em volume):** 9.482 vendas (33,26%) sem canal, registradas de duas formas (vazio e `NULL`).
- **Caso 2 — maiúsculas/minúsculas:** 602 valores distintos caem para 585 ignorando a caixa (ex.: `twitter`/`Twitter`, `xptoourMasc1`/`xptoourmasc1`).
- **Caso 3 — parâmetros embutidos:** 222 vendas trazem `utm_medium=Newsletter` colado ao nome da campanha. É um parâmetro de rastreamento de URL, e **não faz parte do nome do canal**.
- **Caso 4 — listas:** 131 vendas têm dois valores separados por vírgula. Às vezes é o mesmo valor repetido (`xptoLS, xptoLS`), às vezes duas origens (`xptoourNcl, xptoourFem1`), indicando **atribuição múltipla**.
- **Caso 5 — grafias diferentes para o mesmo canal:** `twitte`/`twitter`, `bradock`/`braddock`, `Fb`/`Facebook`, e `calçaecinto`/`calcaecinto`/`calaecinto` (o mesmo texto com e sem cedilha, sinal de perda de acentuação em algum sistema de origem).
- **Caso 6 — campanhas próprias:** 9.321 vendas começam com `xpto`, o nome da própria empresa. São campanhas internas (newsletter, banners, vitrines), que respondem por 513 dos valores distintos.
""")

# =====================================================================
# 4. Diagnóstico da qualidade
# =====================================================================
md(r"""
# 4. Diagnóstico da qualidade
""")

md(r"""
## 4.1 Tabela de Qualidade dos Dados

A tabela consolida os problemas encontrados na seção 3. Ela é **montada por código**: cada quantidade vem de uma variável calculada na investigação, e não de um número digitado, para que a tabela continue correta se a base mudar.

A severidade combina o **volume afetado** com o **impacto na análise**:

- **Alta:** distorce indicadores centrais do negócio.
- **Média:** afeta análises específicas.
- **Baixa:** impacto pontual ou apenas formal.
""")

code(r"""
def brl(x):
    # Formata valor monetário no padrão brasileiro (1.234,56)
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


canal_bruto = df_raw["CanalVenda"]
# Vendas cujo texto não está em forma canônica: maiúsculas, parâmetros, listas ou barra final
n_variacoes_canal = canal.str.contains(r"[A-Z=,/]", regex=True).sum()

tabela_qualidade = pd.DataFrame([
    ("CanalVenda", "Ausência de canal, com dois marcadores (vazio e 'NULL')",
     "3.4 / 3.13: maior 'categoria' da coluna", canal_bruto.isna().sum(),
     "Preservar o original; criar a categoria 'Não informado' no normalizado", "Alta"),
    ("CanalVenda", "Texto livre: caixa, parâmetros UTM, listas com vírgula e grafias diferentes",
     f"3.13: {canal.nunique()} valores distintos; {canal.str.lower().nunique()} ignorando a caixa; "
     "contagem = vendas com maiúsculas, '=', ',' ou '/'",
     n_variacoes_canal, "Normalizar por regras genéricas e agrupar em taxonomia (7.5)", "Alta"),
    ("Cliente_Data_Nascimento", "Data sentinela (ano <= 1900)",
     "3.5: 1900-01-01 compartilhada por 141 clientes distintos", sentinela_1900.sum(),
     "Substituir por ausente e criar flag", "Alta"),
    ("Cliente_Data_Nascimento", "Nascimento posterior à data da compra",
     "3.6: idade negativa; máximo em 2011-12-16", (aux_idade < 0).sum(),
     "Substituir por ausente e criar flag", "Média"),
    ("Cliente_Data_Nascimento", "Idade improvável na compra (< 16 ou > 100 anos, sem sentinela)",
     "3.6: idade exata < 16 anos (ex.: nascimentos em 2008-2010); nenhuma acima de 100",
     (((aux_idade >= 0) & (aux_idade < 16)) | ((aux_idade > 100) & ~sentinela_1900)).sum(),
     "Manter e criar flag de idade improvável", "Média"),
    ("Cliente_Data_Nascimento", "Ausente (literal 'NULL')",
     "1.4 / 3.4: ausência consistente por cliente", df_raw["Cliente_Data_Nascimento"].isna().sum(),
     "Manter como ausente; faixa etária 'Não informado'", "Média"),
    ("NumeroParcelas", "Cartão de crédito com 0 parcelas",
     "3.8: surge em 10/06/2011; mediana R$ 69 vs R$ 240", parcela_zero.sum(),
     "Manter o valor original e criar flag para análise", "Média"),
    ("ValorVenda", "Valor zero", "3.7: 14 com cupom (plausível) e 2 com boleto (incoerente)",
     (valor == 0).sum(), "Manter e criar flag", "Baixa"),
    ("ValorVenda", "Mais de 2 casas decimais", "3.7: ex. 431,275; diferença máxima de meio centavo",
     mais_de_2_casas.sum(), "Arredondar para 2 casas (centavos)", "Baixa"),
    ("ValorVenda", "Valores extremos (acima de Q3 + 1,5 IQR)", f"3.7: limite de {brl(limite_sup)}; máximo de {brl(valor.max())}",
     (valor > limite_sup).sum(), "Manter (distribuição assimétrica legítima) e criar flag", "Baixa"),
    ("Linha inteira", "Duplicata exata", "3.10: cliente 375678, mesmo minuto e valor",
     duplicatas.sum(), "Remover a cópia excedente", "Baixa"),
    ("Cliente_Codigo / ValorVenda / DataVenda", "Possível repetição (mesmo cliente e valor em até 60 min)",
     "3.10: intervalo mediano de 10 min; 201 com troca de forma de pagamento", repeticao.sum(),
     "Manter e criar flag (sem status do pedido para confirmar)", "Média"),
    ("UF_Cliente", "Cliente com mais de uma UF", f"3.11: {len(clientes_multi_uf)} clientes",
     vendas_multi_uf.sum(), "Manter a UF de cada venda e criar flag", "Baixa"),
    ("Cliente_Codigo", "Cliente com volume atípico de compras (> percentil 99,9)",
     "3.12: máximo de 236 vendas, 100% em um único canal", clientes_atipicos.sum(),
     "Manter e criar flag para análise", "Média"),
    ("Cliente_Codigo / DataVenda", "Rajada de compras (5+ compras do mesmo cliente no mesmo dia)",
     "3.12: 99,6% dos pares cliente-dia têm até 4 compras; boleto acima da média", em_rajada.sum(),
     "Manter e criar flag para análise", "Média"),
    ("DataVenda, Cliente_Data_Nascimento, códigos", "Tipos inadequados na leitura automática",
     "2.5: datas como texto; códigos como inteiros", len(df_raw),
     "Converter os tipos no df_clean", "Média"),
], columns=["Campo", "Problema encontrado", "Evidência", "Quantidade afetada", "Regra proposta", "Severidade"])

tabela_qualidade["% da base"] = (tabela_qualidade["Quantidade afetada"] / len(df_raw) * 100).round(2)
ordem_sev = {"Alta": 0, "Média": 1, "Baixa": 2}
tabela_qualidade = (tabela_qualidade.sort_values("Severidade", key=lambda s: s.map(ordem_sev), kind="stable")
                    .reset_index(drop=True))
tabela_qualidade.index = tabela_qualidade.index + 1

with pd.option_context("display.max_colwidth", None):
    display(tabela_qualidade)
""")

md(r"""
## 4.2 Interpretação: o que mais pesa

- **O canal de venda é o problema mais grave.** Um terço das vendas não tem canal, e o restante está pulverizado em centenas de grafias. Sem tratamento, **qualquer análise de marketing fica comprometida**: o ranking de canais seria liderado pela ausência de informação, e canais relevantes apareceriam fragmentados em várias linhas.
- **O sentinela de nascimento é pequeno em volume (270 vendas), mas tem alto impacto.** Cada venda com `1900-01-01` soma uma "idade" de cerca de 110 anos. Poucas centenas desses valores bastam para deslocar a idade média e criar uma faixa etária de idosos que não existe.
- **As anomalias de pagamento e de granularidade são perguntas, não erros.** O zero em parcelas e as possíveis repetições têm padrão claro, mas a base não permite concluir a causa. Por isso a regra proposta é **sinalizar, não corrigir**.
- **Os extremos de valor não são problema.** Eles descrevem uma distribuição assimétrica real. Removê-los reduziria artificialmente o ticket médio.
- **Há boas notícias:** `UF_Cliente` está íntegra no domínio, a relação Id × forma × tipo de pagamento é perfeita e `DataVenda` não tem nenhum valor inválido.
""")

# =====================================================================
# 5. Decisões
# =====================================================================
md(r"""
# 5. Decisões sobre os problemas
""")

md(r"""
## 5.1 Contexto: as cinco decisões possíveis

Cada problema recebe uma de cinco decisões:

- **A. Corrigir:** o valor está errado e existe uma regra objetiva para substituí-lo, mesmo que por "ausente".
- **B. Remover:** a linha não representa um fato real.
- **C. Manter:** o valor é estranho, mas legítimo.
- **D. Transformar:** o dado está correto, mas em formato inadequado para análise.
- **E. Marcar para análise:** há indício de problema, mas não prova. O valor é preservado e uma *flag* de qualidade o identifica.

O princípio geral é **"excluir dados não é limpar dados"**: a remoção é reservada para quando há certeza de que a linha não é uma venda real. Nos demais casos, a preferência é por *flags*, que deixam a decisão de filtrar para quem faz a análise, com transparência.
""")

md(r"""
## 5.2 Duplicata exata: decisão B (Remover)

- **Problema:** duas linhas idênticas em todas as colunas.
- **Evidência:** 1 cópia excedente (3.10). Mesmo cliente, mesmo valor (R$ 195,00), mesmo minuto e mesma forma de pagamento.
- **Decisão:** **B. Remover** a cópia, mantendo a primeira ocorrência.
- **Por quê:** é a única situação da base em que não há dúvida razoável. Duas vendas idênticas no mesmo minuto, sem nenhuma diferença em nenhum atributo, correspondem a um registro gravado duas vezes. Mantê-la contaria a mesma venda em dobro.
- **Efeito:** −1 linha. A remoção fica registrada no *log* da seção 6.
""")

md(r"""
## 5.3 Nascimento sentinela e nascimento posterior à compra: decisão A (Corrigir)

- **Problema:** datas de nascimento que não representam o nascimento real: ano ≤ 1900 (sentinela) ou data posterior à compra (impossível).
- **Evidência:** 270 vendas com sentinela (3.5) e 12 com idade negativa (3.6).
- **Decisão:** **A. Corrigir**, substituindo por ausente (`NaT`) no `df_clean`, com uma *flag* que registra o motivo (`sentinela` ou `posterior_compra`).
- **Por quê:** o valor informado é comprovadamente falso, e não existe fonte para descobrir o verdadeiro. Transformá-lo em ausente é a correção honesta: a informação passa a dizer "não sabemos", em vez de afirmar algo errado. A **venda não é removida**, porque valor, pagamento e canal continuam válidos.
- **Efeito:** o número de nascimentos ausentes no CLEAN aumenta. A idade média deixa de ser inflada pelas "idades" de 110 anos. O valor original continua disponível no `df_raw`.
""")

md(r"""
## 5.4 Idades improváveis: decisão E (Marcar para análise)

- **Problema:** idades possíveis, mas improváveis, na data da compra: menos de 16 ou mais de 100 anos.
- **Evidência:** 172 vendas (3.6), todas de compradores com 0 a 15 anos na data da compra. Nenhuma venda passa de 100 anos, mas o limite superior fica na regra para cargas futuras.
- **Decisão:** **E. Marcar** com a *flag* `flag_idade_improvavel`, mantendo a data.
- **Por quê:** diferentemente do sentinela, **não há prova de erro**. Um cliente de 101 anos existe, e uma compra no cadastro de um adolescente também. Apagar esses valores seria substituir um dado possivelmente real por uma suposição.
- **Efeito:** nenhum valor é alterado. As análises de perfil etário (9.3) podem excluir os casos marcados, informando essa escolha.
""")

md(r"""
## 5.5 Centavos fracionados em `ValorVenda`: decisão A (Corrigir)

- **Problema:** valores com 3 ou 4 casas decimais.
- **Evidência:** 77 vendas (3.7). A diferença máxima para o valor arredondado é de meio centavo.
- **Decisão:** **A. Corrigir**, arredondando para 2 casas decimais.
- **Por quê:** o real não tem frações de centavo. O arredondamento restaura a validade monetária sem mudar o sentido do dado, e o impacto somado é desprezível.
- **Efeito:** 77 valores alterados em menos de R$ 0,01 cada, registrados no *log*.
""")

md(r"""
## 5.6 Valores zero e valores extremos: decisões E e C

- **Problema:** vendas de R$ 0,00 e vendas muito acima do padrão.
- **Evidência:** 16 vendas com valor zero, sendo 14 em cupom e 2 em boleto (3.7). Pela regra do IQR, 2.083 vendas acima de R$ 711,00, com máximo de R$ 17.016,25.
- **Decisão:**
  - **Valor zero, E. Marcar** (`flag_valor_zero`).
  - **Extremos, C. Manter** (com `flag_valor_extremo` apenas como informação).
- **Por quê:** o valor zero pago com cupom é plausível e o pago com boleto é suspeito, mas nos dois casos a venda existe. Os extremos somam 7,3% da base e formam a cauda contínua de uma distribuição assimétrica. **Não se remove um valor só por estar longe da média**, e retirá-los subestimaria o faturamento e o ticket médio.
- **Efeito:** nenhum valor alterado. As duas *flags* permitem análises com e sem esses casos.
""")

md(r"""
## 5.7 Cartão com 0 parcelas: decisão E (Marcar para análise)

- **Problema:** vendas em cartão de crédito registradas com 0 parcelas.
- **Evidência:** 585 vendas, todas a partir de 10/06/2011, com valor mediano bem menor (3.8).
- **Decisão:** **E. Marcar** com `flag_parcelas_zero`, mantendo o `0` original.
- **Por quê:** o padrão temporal indica uma mudança de sistema ou de modalidade, e não um erro aleatório. "Corrigir" para 1 parcela suporia que o zero significa "à vista", uma hipótese que a base não confirma. A causa deve ser validada com a área de negócio.
- **Efeito:** nenhum valor alterado. As análises de parcelamento devem tratar esses casos à parte.
""")

md(r"""
## 5.8 Possíveis repetições, rajadas, clientes atípicos e clientes com várias UFs: decisões E e C

- **Problema:** linhas que podem não ser vendas independentes (repetições em até 60 minutos e rajadas de 5+ compras no mesmo dia), clientes com volume de compras fora do padrão e clientes com mais de uma UF.
- **Evidência:** 891 possíveis repetições (3.10), rajadas de compras (3.12), 14 clientes atípicos com 877 vendas (3.12) e 53 clientes com várias UFs (3.11).
- **Decisão:**
  - **Repetições, E. Marcar** (`flag_possivel_repeticao`).
  - **Rajadas, E. Marcar** (`flag_rajada_compras`).
  - **Clientes atípicos, E. Marcar** (`flag_cliente_atipico`).
  - **UF múltipla, C. Manter** (`flag_cliente_multi_uf`).
- **Por quê:** em todos os casos há uma explicação legítima possível (segunda compra, revendedor, endereço de entrega diferente), e falta à base a informação que decidiria a questão, como o status do pedido ou o tipo de cliente. Remover as repetições, por exemplo, poderia apagar vendas reais.
- **Efeito:** nenhuma linha removida. As *flags* permitem medir a **sensibilidade** dos indicadores, por exemplo o ranking de canais com e sem o cliente atípico.
""")

md(r"""
## 5.9 Canal de venda: decisão D (Transformar)

- **Problema:** texto livre com ausências, variações de caixa, parâmetros UTM, listas e grafias diferentes.
- **Evidência:** 9.482 ausentes e 602 valores distintos (3.13).
- **Decisão:** **D. Transformar**, criando três colunas:
  - `CanalVenda_Original`: o texto bruto, preservado.
  - `CanalVenda_Normalizado`: minúsculas, sem parâmetros, sem duplicação, com as grafias unificadas.
  - `GrupoCanal`: uma taxonomia de negócio.

  As ausências viram a categoria explícita `Não informado`.
- **Por quê:** o conteúdo não está errado, apenas em formato impróprio para agregação. A normalização usa **regras genéricas** (funções, *regex* e dicionário de mapeamento), para funcionar com canais novos em cargas futuras.
- **Efeito:** nenhuma linha removida. A cardinalidade cai de centenas de valores para poucos grupos analisáveis (detalhes na seção 7.5).
""")

md(r"""
## 5.10 Tipos de dados: decisão D (Transformar)

- **Problema:** datas lidas como texto e códigos lidos como números.
- **Evidência:** seção 2.5.
- **Decisão:** **D. Transformar**:
  - `DataVenda` e `Cliente_Data_Nascimento` para `datetime64`.
  - `Cliente_Codigo` para texto.
  - `IdFormaDePagamento`, `FormaPagamento`, `TipoFormaPagamento` e `UF_Cliente` para `category`.
- **Por quê:** permite cálculos temporais, impede operações sem sentido sobre códigos e reduz a memória.
- **Efeito:** nenhum valor alterado, apenas a representação.
""")

md(r"""
## 5.11 Resumo das decisões

| Problema | Decisão | Justificativa | Tratamento aplicado |
|---|---|---|---|
| Duplicata exata | **B. Remover** | Registro idêntico no mesmo minuto; sem dúvida razoável | Remover a cópia excedente (`keep="first"`) e registrar no *log* |
| Nascimento sentinela (ano ≤ 1900) | **A. Corrigir** | Valor comprovadamente artificial | Substituir por `NaT` + `flag_nascimento_invalido = "sentinela"` |
| Nascimento posterior à compra | **A. Corrigir** | Valor impossível | Substituir por `NaT` + `flag_nascimento_invalido = "posterior_compra"` |
| Idade improvável (< 16 ou > 100) | **E. Marcar** | Possível, sem prova de erro | `flag_idade_improvavel` |
| Centavos fracionados | **A. Corrigir** | Frações de centavo não existem | Arredondar `ValorVenda` para 2 casas |
| Valor zero | **E. Marcar** | Cupom integral plausível; boleto zerado suspeito | `flag_valor_zero` |
| Valores extremos | **C. Manter** | Cauda natural de distribuição assimétrica | `flag_valor_extremo` (informativa) |
| Cartão com 0 parcelas | **E. Marcar** | Padrão temporal; causa desconhecida | `flag_parcelas_zero` |
| Possível repetição (≤ 60 min) | **E. Marcar** | Pode ser recompra ou nova tentativa de pagamento | `flag_possivel_repeticao` |
| Rajada de compras (5+ no mesmo dia) | **E. Marcar** | Pode ser revenda, reemissão de boleto, teste ou fraude | `flag_rajada_compras` |
| Cliente com volume atípico | **E. Marcar** | Pode ser revendedor ou conta de teste | `flag_cliente_atipico` |
| Cliente com várias UFs | **C. Manter** | UF pode ser a de entrega | `flag_cliente_multi_uf` |
| Canal ausente ou em texto livre | **D. Transformar** | Conteúdo válido em formato impróprio | `CanalVenda_Original`, `CanalVenda_Normalizado`, `GrupoCanal` |
| Tipos inadequados | **D. Transformar** | Datas como texto; códigos como números | Conversão de tipos no `df_clean` |

**Síntese:** das 14 decisões, apenas **uma remove linhas** (uma única cópia duplicada). Todas as outras preservam as vendas, e quatro delas alteram algum valor: nascimentos inválidos, arredondamento, canal e tipos.
""")

md(r"""
## 5.12 Parâmetros das regras

As regras de decisão dependem de alguns limites. Eles ficam centralizados em um único lugar, em vez de espalhados pelo código, para que a seção 6 os aplique de forma consistente e para que possam ser revistos sem editar a lógica. Nenhum deles é específico desta base (não há índices de linha nem códigos de cliente).
""")

code(r"""
PARAMETROS_REGRAS = {
    "ano_max_sentinela_nascimento": 1900,   # nascimento com ano <= 1900 é sentinela
    "idade_min_provavel": 16,               # abaixo disso: idade improvável
    "idade_max_provavel": 100,              # acima disso: idade improvável
    "casas_decimais_valor": 2,              # centavos
    "fator_iqr_extremo": 1.5,               # regra clássica do IQR
    "janela_repeticao_min": 60,             # minutos entre vendas de mesmo cliente e valor
    "percentil_cliente_atipico": 0.999,     # volume de compras por cliente
    "compras_mesmo_dia_rajada": LIMITE_RAJADA,  # compras do mesmo cliente no mesmo dia (3.12)
}
pd.Series({k: str(v) for k, v in PARAMETROS_REGRAS.items()}, name="valor").to_frame()
""")
