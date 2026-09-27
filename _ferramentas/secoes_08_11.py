# Seções 8 a 11 e checklist. Executado por build_notebook.py (usa md() e code() de lá).

# =====================================================================
# 8. Comparação RAW x CLEAN
# =====================================================================
md(r"""
# 8. Comparação RAW × CLEAN
""")

md(r"""
## 8.1 Contexto: o que um analista concluiria com a base bruta?

A pergunta desta seção é prática: **a preparação muda as respostas de negócio?** Para responder, os mesmos indicadores são calculados duas vezes:

- **RAW:** da forma como um analista faria se abrisse o arquivo e calculasse direto, com `value_counts()`, `mean()` e os valores como vieram.
- **CLEAN:** usando os atributos tratados e as *flags* de qualidade.

Foram escolhidos quatro indicadores, que cobrem as três frentes da preparação: canal, cliente e valor.

1. **Quantidade de canais de venda distintos:** o tamanho do "cardápio" de canais que o marketing enxerga.
2. **Participação dos canais nas vendas**, medida de duas formas:
   - **2a. Participação do `google`:** o **mesmo canal** medido nas duas bases. É a comparação mais justa, porque isola o efeito da limpeza (ausentes explícitos e grafias unificadas).
   - **2b. Principal origem de vendas:** o que cada base aponta como "líder". Aqui o CLEAN usa o `GrupoCanal`, então a diferença combina limpeza **e** taxonomia; o resultado é lido com essa ressalva.
3. **Idade média do cliente e participação de clientes com 65 anos ou mais:** o público-alvo. Nas duas bases a idade é calculada com a **mesma função exata** (`idade_na_data`, definida em 3.1), de modo que a diferença vem só da correção dos nascimentos inválidos e da exclusão das idades improváveis.
4. **Ticket médio:** indicador financeiro central.
""")

code(r"""
# Indicador 1: quantidade de canais distintos
canais_raw = df_raw["CanalVenda"].nunique()
canais_clean_norm = df_clean.loc[df_clean["CanalVenda_Normalizado"] != ROTULO_AUSENTE, "CanalVenda_Normalizado"].nunique()
grupos_clean = df_clean.loc[~df_clean["GrupoCanal"].isin(["Não informado", GRUPO_NAO_MAPEADO]), "GrupoCanal"].nunique()

print(f"RAW  : {canais_raw} valores distintos em CanalVenda")
print(f"CLEAN: {canais_clean_norm} canais normalizados, agrupados em {grupos_clean} grupos de origem conhecida")
""")

code(r"""
# Indicador 2: participação do principal canal
# RAW: value_counts() descarta os ausentes por padrão -> o percentual é calculado só sobre as vendas com canal
part_raw = df_raw["CanalVenda"].value_counts(normalize=True) * 100
principal_raw, pct_principal_raw = part_raw.index[0], part_raw.iloc[0]

# CLEAN: percentual sobre TODAS as vendas; 'Não informado' é uma categoria explícita
part_clean = df_clean["GrupoCanal"].value_counts(normalize=True) * 100
part_clean_conhecido = part_clean.drop(["Não informado", GRUPO_NAO_MAPEADO], errors="ignore")
principal_clean, pct_principal_clean = part_clean_conhecido.index[0], part_clean_conhecido.iloc[0]
pct_busca_clean = part_clean.get("Busca", 0)

# 2a. O mesmo canal nas duas bases: google
pct_google_raw = part_raw.get("google", 0)
pct_google_clean = df_clean["CanalVenda_Normalizado"].eq("google").mean() * 100
print(f"google -> RAW: {pct_google_raw:.2f}% (sobre vendas com canal) | CLEAN: {pct_google_clean:.2f}% (sobre todas as vendas)\n")

print(f"RAW  : principal canal = '{principal_raw}' com {pct_principal_raw:.2f}% das vendas")
print(f"CLEAN: principal grupo = '{principal_clean}' com {pct_principal_clean:.2f}% das vendas")
print(f"CLEAN: 'Busca' (google + yahoo + googleadwords) = {pct_busca_clean:.2f}% | "
      f"'Não informado' = {part_clean['Não informado']:.2f}%")
print("\nTop 5 RAW:")
print(part_raw.head(5).round(2).to_string())
print("\nTop 5 CLEAN (GrupoCanal):")
print(part_clean.head(5).round(2).to_string())
""")

code(r"""
# Indicador 3: idade média e participação de 65+
# RAW: idade exata (idade_na_data, 3.1) com todas as datas preenchidas, incluindo sentinelas e datas impossíveis
idade_raw = aux_idade.dropna().astype(float)
idade_media_raw = idade_raw.mean()
pct_65_raw = (idade_raw >= 65).mean() * 100

# CLEAN: mesma função, sem datas inválidas e sem idades improváveis
idade_valida = df_clean.loc[~df_clean["flag_idade_improvavel"], "IdadeNaCompra"].dropna().astype(float)
idade_media_clean = idade_valida.mean()
pct_65_clean = (idade_valida >= 65).mean() * 100

print(f"Idade média  -> RAW: {idade_media_raw:.2f} | CLEAN: {idade_media_clean:.2f}")
print(f"% 65 ou mais -> RAW: {pct_65_raw:.2f}% | CLEAN: {pct_65_clean:.2f}%")
""")

code(r"""
# Indicador 4: ticket médio
ticket_raw = df_raw["ValorVenda"].mean()
ticket_clean = df_clean.loc[~df_clean["flag_valor_zero"], "ValorVenda"].mean()
ticket_clean_sem_rep = df_clean.loc[~df_clean["flag_valor_zero"] & ~df_clean["flag_possivel_repeticao"], "ValorVenda"].mean()

print(f"Ticket médio -> RAW: {ticket_raw:,.2f} | CLEAN (sem valor zero): {ticket_clean:,.2f} | "
      f"CLEAN (sem valor zero e sem possíveis repetições): {ticket_clean_sem_rep:,.2f}")
""")

md(r"""
## 8.2 Tabela comparativa
""")

code(r"""
def fmt_pct(x):
    return f"{x:.2f}%".replace(".", ",")


def fmt_num(x, casas=2):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


comparacao_raw_clean = pd.DataFrame([
    ("Quantidade de canais distintos", f"{canais_raw}",
     f"{canais_clean_norm} normalizados / {grupos_clean} grupos",
     f"-{canais_raw - canais_clean_norm} grafias; {grupos_clean} grupos analisáveis"),
    ("Participação do google nas vendas (mesmo canal)", fmt_pct(pct_google_raw), fmt_pct(pct_google_clean),
     f"{fmt_num(pct_google_clean - pct_google_raw)} p.p. (ausentes passam a contar no denominador)"),
    ("Principal origem de vendas (CLEAN por GrupoCanal)", f"{principal_raw}: {fmt_pct(pct_principal_raw)}",
     f"{principal_clean}: {fmt_pct(pct_principal_clean)}",
     f"Líder muda (limpeza + taxonomia); Busca = {fmt_pct(pct_busca_clean)}"),
    ("Idade média do cliente (anos)", fmt_num(idade_media_raw), fmt_num(idade_media_clean),
     f"{fmt_num(idade_media_clean - idade_media_raw)} anos"),
    ("Clientes com 65 anos ou mais (% das vendas com idade)", fmt_pct(pct_65_raw), fmt_pct(pct_65_clean),
     f"{fmt_num(pct_65_clean - pct_65_raw)} p.p. ({fmt_num((pct_65_clean / pct_65_raw - 1) * 100, 1)}%)"),
    ("Ticket médio (R$)", fmt_num(ticket_raw), fmt_num(ticket_clean), f"{fmt_num(ticket_clean - ticket_raw)}"),
], columns=["Indicador", "Base RAW", "Base CLEAN", "Diferença"])

with pd.option_context("display.max_colwidth", None):
    display(comparacao_raw_clean)
""")

md(r"""
## 8.3 Interpretação: alguma decisão gerencial seria diferente?

**Sim, pelo menos duas decisões gerenciais seriam diferentes, e uma não mudaria.**

- **Caso 1 — investimento em canais (o mais relevante):** na base bruta, o `google` aparece com **29,40%** das vendas, e a conclusão natural seria concentrar a verba em busca. O número está inflado porque `value_counts()` descarta as 9.482 vendas sem canal. Medido na base tratada, o **mesmo canal** responde por **19,62%** do total (−9,78 p.p.), e a busca inteira (google, yahoo e googleadwords) por **20,31%**. Olhando os grupos de origem, o maior é o das **campanhas próprias XPTO (32,00%)**, que no RAW ficavam invisíveis por estar fragmentadas em centenas de códigos, nenhum acima de 3,3%. Além disso, **um terço das vendas (33,26%) não tem origem**. Com os dados limpos, a primeira decisão seria **investir em rastreamento**, e não redistribuir a verba entre canais.
- **Caso 2 — dimensionamento de público:** a base bruta indica que **2,41%** das vendas com idade são de clientes com 65 anos ou mais. A tratada mostra **1,39%**. O sentinela `1900-01-01` cria "clientes de 110 anos", e uma ação voltada à terceira idade seria planejada para um público cerca de **1,7 vez maior** que o real. A idade média cai de 32,62 para 31,98 anos (−0,64): como as duas bases usam a mesma função de idade, essa diferença vem **só** da limpeza. Parece pouco na média, mas a distorção se concentra justamente na faixa de idosos, como mostra o indicador anterior.
- **Caso 3 — ticket médio (não muda):** R$ 314,61 no RAW contra R$ 314,80 no CLEAN. Mesmo excluindo as possíveis repetições, o ticket vai a R$ 318,71, cerca de 1% acima. **Decisões de preço e de meta de faturamento seriam as mesmas.** Isso também é um resultado: os problemas desta base estão nos atributos **descritivos** (canal e cliente), e não no valor das vendas, que foi preservado. Nem toda limpeza muda todos os números, e mostrar onde ela **não** muda dá credibilidade às diferenças onde ela muda.
""")

# =====================================================================
# 9. Perguntas de negócio
# =====================================================================
md(r"""
# 9. Perguntas de negócio
""")

md(r"""
## 9.0 Contexto: regras usadas em todas as análises

Todas as análises usam **somente o `df_clean`**. Para que os resultados sejam comparáveis, três convenções valem para a seção inteira:

- **Ticket médio** exclui `flag_valor_zero`: uma venda de R$ 0,00 não representa preço pago.
- **Mediana ao lado da média:** a distribuição de valores é assimétrica (3.7), e a mediana mostra o valor "típico" sem a influência da cauda.
- **Grupos pequenos são sinalizados:** categorias com poucas vendas (por exemplo, `Glamour VIP`, com 3) aparecem nas tabelas, mas não sustentam conclusões.

A função `estilo_eixo` padroniza os gráficos: grade discreta atrás das barras e sem bordas superiores e direitas.
""")

code(r"""
COR_PRINCIPAL = "#2a78d6"
COR_SECUNDARIA = "#eb6834"
COR_TEXTO = "#52514e"
plt.rcParams["text.parse_math"] = False  # "R$" nos rótulos não deve virar fórmula matemática
vendas_validas = df_clean[~df_clean["flag_valor_zero"]]


def estilo_eixo(ax, titulo, xlabel, ylabel, eixo_grade="y"):
    ax.set_title(titulo)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(axis=eixo_grade, color="#e5e5e3")
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)


def formato_br(x, _=None):
    return f"{x:,.0f}".replace(",", ".")
""")

# ---- 9.1
md(r"""
## 9.1 Evolução das vendas ao longo do período

Como janeiro (a partir do dia 10) e agosto (até o dia 28) são meses **parciais** (2.4), comparar totais mensais seria injusto. A medida principal é a **média de vendas por dia com venda**, calculada dividindo o total do mês pelo número de dias em que houve vendas.
""")

code(r"""
evolucao = df_clean.groupby("AnoMes").agg(
    vendas=("id_registro", "size"),
    faturamento=("ValorVenda", "sum"),
    dias_com_venda=("DataVenda", lambda s: s.dt.normalize().nunique()),
)
evolucao["vendas_por_dia"] = (evolucao["vendas"] / evolucao["dias_com_venda"]).round(1)
evolucao["faturamento_por_dia"] = (evolucao["faturamento"] / evolucao["dias_com_venda"]).round(2)
evolucao["ticket_medio"] = vendas_validas.groupby("AnoMes")["ValorVenda"].mean().round(2)
evolucao["variacao_vendas_dia_%"] = (evolucao["vendas_por_dia"].pct_change() * 100).round(1)
evolucao
""")

code(r"""
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(evolucao.index, evolucao["vendas_por_dia"], color=COR_PRINCIPAL, linewidth=2, marker="o", markersize=7)
for mes, valor_mes in evolucao["vendas_por_dia"].items():
    ax.annotate(f"{valor_mes:.0f}", (mes, valor_mes), textcoords="offset points", xytext=(0, 9),
                ha="center", color=COR_TEXTO, fontsize=9)
ax.set_ylim(0, evolucao["vendas_por_dia"].max() * 1.2)
estilo_eixo(ax, "Média de vendas por dia, por mês (2011)", "Mês", "Vendas por dia")
plt.tight_layout()
plt.show()
""")

code(r"""
# Padrão semanal complementar: vendas médias por dia da semana
dias_por_semana = df_clean.groupby("DiaSemana", observed=True)["DataVenda"].apply(lambda s: s.dt.normalize().nunique())
vendas_semana = df_clean.groupby("DiaSemana", observed=True).size()
(vendas_semana / dias_por_semana).round(1).rename("vendas_por_dia").to_frame().T
""")

md(r"""
**Conclusão:**

- **Crescimento:** a média de vendas por dia cresce de **110** em janeiro para **161** em julho (+46%), com uma queda em março e abril (cerca de 100 por dia) e aceleração a partir de maio. O faturamento por dia acompanha: de R$ 35,1 mil para R$ 49,0 mil.
- **Origem do crescimento:** o ticket médio fica estável entre R$ 301 e R$ 333 ao longo dos meses. **O crescimento vem do volume de pedidos, não do preço.**
- **Agosto:** a queda para 136 vendas por dia (−15,6%) precisa ser lida com cuidado, porque parte do volume do mês vem de um único cliente (9.6). Sem ele, agosto fica em cerca de 128 vendas por dia. O pico de julho pode refletir sazonalidade (férias, liquidações), mas a base não tem o ano anterior para confirmar essa hipótese.
- **Padrão semanal:** de segunda a quinta, a loja vende entre 145 e 160 pedidos por dia. Na sexta, 117. No sábado e no domingo, cerca de 72 a 74, **metade de um dia útil**. O comportamento indica compras feitas principalmente em horário de trabalho, o que é relevante para agendar campanhas e disparos de e-mail.
""")

# ---- 9.2
md(r"""
## 9.2 Diferença de ticket entre formas de pagamento
""")

code(r"""
ticket_forma = vendas_validas.groupby("FormaPagamento", observed=True)["ValorVenda"].agg(
    vendas="size", ticket_medio="mean", ticket_mediano="median",
    q1=lambda s: s.quantile(0.25), q3=lambda s: s.quantile(0.75)).round(2)
ticket_forma["amostra"] = np.where(ticket_forma["vendas"] < 30, "insuficiente (< 30)", "ok")
ticket_forma.sort_values("ticket_mediano", ascending=False)
""")

code(r"""
# Ticket por modalidade e por número de parcelas
display(vendas_validas.groupby("ModalidadePagamento")["ValorVenda"]
        .agg(vendas="size", ticket_medio="mean", ticket_mediano="median").round(2))
display(vendas_validas.groupby("NumeroParcelas")["ValorVenda"]
        .agg(vendas="size", ticket_medio="mean", ticket_mediano="median").round(2).T)
""")

code(r"""
dados = ticket_forma[ticket_forma["amostra"] == "ok"].sort_values("ticket_mediano")
fig, ax = plt.subplots(figsize=(9, 3.8))
barras = ax.barh(dados.index.astype(str), dados["ticket_mediano"], color=COR_PRINCIPAL, height=0.6)
for barra, med, media in zip(barras, dados["ticket_mediano"], dados["ticket_medio"]):
    ax.text(barra.get_width() + 5, barra.get_y() + barra.get_height() / 2,
            f"mediana R$ {med:,.0f} | média R$ {media:,.0f}".replace(",", "."), va="center", color=COR_TEXTO, fontsize=9)
ax.set_xlim(0, dados["ticket_mediano"].max() * 1.6)
estilo_eixo(ax, "Ticket mediano por forma de pagamento (amostras com 30+ vendas)", "Ticket mediano (R$)", "", "x")
plt.tight_layout()
plt.show()
""")

md(r"""
**Conclusão:**

- **`Diners`** tem o maior ticket: mediana de R$ 332 e média de R$ 410. É uma bandeira tradicionalmente associada a clientes de maior renda, mas essa é uma hipótese que a base não permite confirmar.
- **`Visa` e `MasterCard`** são praticamente idênticos: mediana de R$ 230 e R$ 231, média de R$ 315.
- **`Boleto Bancário`** tem mediana **menor** (R$ 199), mas média **igual** à dos cartões (R$ 317). A distribuição é mais dispersa: muitas compras pequenas e algumas muito grandes. As maiores vendas da base, como a de R$ 17.016,25, foram em boleto, o que é coerente com compras de alto valor feitas por quem prefere não usar o limite do cartão.
- **`Cupom de Desconto`** tem o menor ticket entre as formas com amostra suficiente: mediana de R$ 164.
- **`Glamour VIP`** (3 vendas) não permite conclusão.

**A diferença mais forte, porém, não está na forma de pagamento, e sim no parcelamento.** O ticket mediano das vendas parceladas é R$ 249, contra R$ 196 à vista, e cresce com o número de parcelas: R$ 129 em 2x e R$ 456 em 10x. O parcelamento é o que viabiliza os pedidos de maior valor.
""")

# ---- 9.3
md(r"""
## 9.3 Perfil etário dos clientes

A análise usa `FaixaEtaria` e considera apenas as vendas com **idade válida**, ou seja, sem `Não informado` e sem `Idade improvável`. A participação desses dois grupos é informada à parte, para deixar claro sobre qual parcela da base a conclusão se apoia.

Como um cliente pode comprar várias vezes, o perfil é mostrado de duas formas: **por venda** (quem gera o volume) e **por cliente** (quem é a base de compradores).
""")

code(r"""
faixas_validas = FAIXAS_ETARIAS["rotulos"]
com_idade = df_clean[df_clean["FaixaEtaria"].isin(faixas_validas)]

print(f"Vendas com idade válida: {len(com_idade):,} ({len(com_idade) / len(df_clean) * 100:.1f}% da base)")
print(f"Não informado: {(df_clean['FaixaEtaria'] == 'Não informado').sum():,} | "
      f"Idade improvável: {(df_clean['FaixaEtaria'] == 'Idade improvável').sum():,}")

perfil_etario = pd.DataFrame({
    "%_vendas": com_idade["FaixaEtaria"].value_counts(normalize=True) * 100,
    "%_clientes": com_idade.drop_duplicates("Cliente_Codigo")["FaixaEtaria"].value_counts(normalize=True) * 100,
    "ticket_mediano": com_idade[~com_idade["flag_valor_zero"]].groupby("FaixaEtaria", observed=True)["ValorVenda"].median(),
    "%_parcelado": com_idade.groupby("FaixaEtaria", observed=True)["ModalidadePagamento"]
                   .apply(lambda s: (s == "Parcelado").mean() * 100),
}).loc[faixas_validas].round(1)
perfil_etario
""")

code(r"""
print(com_idade["IdadeNaCompra"].astype(float).describe().round(1).to_string())

fig, ax = plt.subplots(figsize=(9, 4))
ax.bar(perfil_etario.index, perfil_etario["%_clientes"], color=COR_PRINCIPAL, width=0.65)
for i, v in enumerate(perfil_etario["%_clientes"]):
    ax.text(i, v + 0.6, f"{v:.1f}%".replace(".", ","), ha="center", color=COR_TEXTO, fontsize=9)
estilo_eixo(ax, "Distribuição dos clientes por faixa etária (idade na data da compra)", "Faixa etária",
            "% dos clientes com idade válida")
plt.tight_layout()
plt.show()
""")

md(r"""
**Conclusão:** a base de clientes é **jovem**.

- **Concentração:** a faixa de **25 a 34 anos** reúne 39,0% dos clientes, e somada à de 18 a 24 chega a **67,2%**. A mediana de idade é 29 anos e a média, 32. Clientes com 55 anos ou mais somam apenas 5,4%.
- **Valor por faixa:** o ticket mediano **cresce com a idade**, de R$ 188 (18 a 24) para R$ 289 (55 a 64). O uso de parcelamento também, de 52,3% para 65,1%. Os clientes mais velhos são poucos, mas compram mais caro por pedido.
- **16 e 17 anos:** a faixa "16–17" (1,7%) tem o menor ticket (R$ 139) e o menor uso de parcelamento (34,4%), coerente com menos acesso a cartão de crédito.

**Ressalva:** 10,8% das vendas estão fora desta análise (não informado ou idade improvável). Se esses clientes tiverem perfil diferente, as proporções mudam. A base não permite avaliar esse viés.
""")

# ---- 9.4
md(r"""
## 9.4 Canais com maior volume de vendas

A resposta é dada em dois níveis: o **grupo de canal**, que mostra de onde vem o tráfego, e o **canal normalizado**, que mostra quais origens específicas mais vendem. Em seguida, o mesmo *ranking* é feito com o `CanalVenda_Original` para mostrar por que ele levaria a conclusões inadequadas.
""")

code(r"""
ranking_grupo = df_clean.groupby("GrupoCanal").agg(
    vendas=("id_registro", "size"), faturamento=("ValorVenda", "sum"),
    ticket_mediano=("ValorVenda", "median"), canais=("CanalVenda_Normalizado", "nunique"))
ranking_grupo["%_vendas"] = ranking_grupo["vendas"] / len(df_clean) * 100
ranking_grupo["%_faturamento"] = ranking_grupo["faturamento"] / df_clean["ValorVenda"].sum() * 100
ranking_grupo.sort_values("vendas", ascending=False).round(2)
""")

code(r"""
# Top 10 canais específicos (normalizados, com origem conhecida)
top_norm = (df_clean[df_clean["CanalVenda_Normalizado"] != ROTULO_AUSENTE]
            .groupby(["CanalVenda_Normalizado", "GrupoCanal"]).size().rename("vendas")
            .sort_values(ascending=False).head(10).reset_index())
top_norm["grafias_originais"] = top_norm["CanalVenda_Normalizado"].map(
    df_clean.groupby("CanalVenda_Normalizado")["CanalVenda_Original"].nunique())
top_norm
""")

md(r"""
**Por que o `CanalVenda` original levaria a uma conclusão inadequada?** O código abaixo compara o *ranking* ingênuo sobre o campo bruto com o *ranking* tratado, medindo quatro distorções.
""")

code(r"""
ranking_raw = df_raw["CanalVenda"].value_counts()

# Distorção 1: a ausência some do ranking bruto e infla a participação dos demais
print("Distorção 1 — ausência invisível")
print(f"  Vendas sem canal: {df_raw['CanalVenda'].isna().sum():,} "
      f"({df_raw['CanalVenda'].isna().mean() * 100:.1f}%) -> não aparecem em value_counts()")
print(f"  google: {pct_principal_raw:.1f}% no RAW (sobre vendas com canal) vs "
      f"{df_clean['CanalVenda_Normalizado'].eq('google').mean() * 100:.1f}% do total real de vendas\n")

# Distorção 2: fragmentação de um mesmo canal em várias grafias
print("Distorção 2 — fragmentação")
frag = (df_clean.groupby("CanalVenda_Normalizado")
        .agg(grafias=("CanalVenda_Original", "nunique"), vendas=("id_registro", "size"),
             maior_grafia=("CanalVenda_Original", lambda s: s.value_counts().iloc[0] if s.notna().any() else 0)))
frag = frag[frag["grafias"] > 1].sort_values("vendas", ascending=False)
print(f"  Canais normalizados com mais de uma grafia no original: {len(frag)}")
print(frag.head(6).to_string(), "\n")

# Distorção 3: um meio inteiro (e-mail) fica invisível
email = df_clean["GrupoCanal"].eq("E-mail e CRM")
maior_valor_email_raw = df_clean.loc[email, "CanalVenda_Original"].value_counts().iloc[0]
print("Distorção 3 — meio invisível")
print(f"  'E-mail e CRM' soma {email.sum()} vendas; no RAW está espalhado em "
      f"{df_clean.loc[email, 'CanalVenda_Original'].nunique()} grafias (a maior tem {maior_valor_email_raw})\n")

# Distorção 4: concentração em um único cliente
himidia = df_clean["CanalVenda_Normalizado"].eq("himidia")
atipico_himidia = df_clean.loc[himidia, "flag_cliente_atipico"].sum()
print("Distorção 4 — concentração")
print(f"  himidia: {himidia.sum():,} vendas, das quais {atipico_himidia} ({atipico_himidia / himidia.sum() * 100:.1f}%) "
      f"de clientes atípicos")
""")

code(r"""
# Visual: os 8 maiores do ranking bruto x os 8 maiores grupos tratados
fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
bruto = (ranking_raw / len(df_raw) * 100).head(8).sort_values()
tratado = (df_clean["GrupoCanal"].value_counts(normalize=True) * 100).head(8).sort_values()
for ax, dados_rank, titulo in [(axes[0], bruto, "RAW: CanalVenda original (top 8)"),
                               (axes[1], tratado, "CLEAN: GrupoCanal (top 8)")]:
    ax.barh(dados_rank.index, dados_rank.values, color=COR_PRINCIPAL, height=0.6)
    for i, v in enumerate(dados_rank.values):
        ax.text(v + 0.4, i, f"{v:.1f}%".replace(".", ","), va="center", color=COR_TEXTO, fontsize=9)
    ax.set_xlim(0, 40)
    estilo_eixo(ax, titulo, "% do total de vendas", "", "x")
plt.tight_layout()
plt.show()
""")

md(r"""
**Conclusão:**

- **Grupos de canal:** as vendas vêm, em ordem, de campanhas próprias XPTO (32,0%), busca (20,3%) e portais e mídia display (6,2%). Um terço (33,3%) não tem origem registrada, e o grupo "Não informado" fatura R$ 3,1 milhões, o maior volume individual.
- **Canais individuais:** `google` é o maior canal específico (5.593 vendas, 19,6% do total), seguido por `himidia` (1.578) e pela campanha `xptoourmasc1` (652).

**Por que o `CanalVenda` original levaria a uma conclusão inadequada:**

1. **Ausência invisível:** `value_counts()` descarta os 9.482 ausentes, e os percentuais passam a ser calculados sobre dois terços da base. O `google` sobe de 19,6% para 29,4%.
2. **Fragmentação:** 68 canais aparecem com mais de uma grafia. `xptoourncl` soma 267 vendas em **9 grafias**, e a maior delas tem só 150. Um ranking pelo campo bruto subestima esses canais.
3. **Meio invisível:** o e-mail (`utm_medium=Newsletter` e `AviseMe`) soma 666 vendas em 13 grafias. E as campanhas próprias, o **maior grupo da empresa**, não aparecem como relevantes no bruto, porque nenhum código isolado passa de 3,3%.
4. **Concentração:** 15,3% das vendas do `himidia` vêm de clientes atípicos. Sem essa informação, o canal parece mais forte do que é (9.6).

No gráfico, os dois painéis usam o mesmo denominador (total de vendas). Mesmo assim, o painel RAW **não mostra** o terço de vendas sem canal nem o peso das campanhas próprias.

Em resumo, o campo bruto responde "qual **grafia** aparece mais", e não "qual **canal** vende mais".
""")

# ---- 9.5
md(r"""
## 9.5 Diferenças relevantes entre estados brasileiros

Além das UFs, as vendas são agregadas por **região** (Norte, Nordeste, Centro-Oeste, Sudeste e Sul), usando a coluna `Regiao` criada na seção 7.6.

Os indicadores comparados são: volume, ticket (média e mediana), uso de boleto e uso de parcelamento. Como algumas UFs têm poucas vendas, as conclusões por UF consideram apenas as que têm **pelo menos 100 vendas**.
""")

code(r"""
def indicadores_geo(df, chave):
    base = df.groupby(chave, observed=True).agg(
        vendas=("id_registro", "size"), faturamento=("ValorVenda", "sum"),
        ticket_medio=("ValorVenda", "mean"), ticket_mediano=("ValorVenda", "median"),
        pct_boleto=("FormaPagamento", lambda s: (s == "Boleto Bancário").mean() * 100),
        pct_parcelado=("ModalidadePagamento", lambda s: (s == "Parcelado").mean() * 100))
    base["%_vendas"] = base["vendas"] / base["vendas"].sum() * 100
    return base.sort_values("vendas", ascending=False).round(2)


por_regiao = indicadores_geo(vendas_validas, "Regiao")
por_regiao
""")

code(r"""
por_uf = indicadores_geo(vendas_validas, "UF_Cliente")
por_uf["Regiao"] = por_uf.index.astype(str).map(UF_PARA_REGIAO)
uf_relevantes = por_uf[por_uf["vendas"] >= 100]
print(f"UFs com 100+ vendas: {len(uf_relevantes)} de {len(por_uf)}")

print("\nMaiores e menores tickets medianos (UFs com 100+ vendas):")
display(uf_relevantes.sort_values("ticket_mediano", ascending=False)
        [["Regiao", "vendas", "ticket_mediano", "ticket_medio", "pct_boleto", "pct_parcelado"]].iloc[[0, 1, 2, -3, -2, -1]])

print("Maior e menor uso de boleto (UFs com 100+ vendas):")
display(uf_relevantes.sort_values("pct_boleto", ascending=False)
        [["Regiao", "vendas", "pct_boleto", "pct_parcelado", "ticket_mediano"]].iloc[[0, 1, 2, -3, -2, -1]])
""")

code(r"""
dados = uf_relevantes.sort_values("ticket_mediano")
mediana_geral = vendas_validas["ValorVenda"].median()
fig, ax = plt.subplots(figsize=(10, 6.5))
ax.barh(dados.index.astype(str), dados["ticket_mediano"], color=COR_PRINCIPAL, height=0.65)
ax.axvline(mediana_geral, color=COR_TEXTO, linestyle="--", linewidth=1.2,
           label=f"Mediana geral: R$ {mediana_geral:,.2f}".replace(".", ","))
ax.legend(frameon=False, loc="lower right")
estilo_eixo(ax, "Ticket mediano por UF (UFs com 100+ vendas)", "Ticket mediano (R$)", "UF", "x")
plt.tight_layout()
plt.show()
""")

md(r"""
**Conclusão:**

- **Concentração de volume:** o Sudeste responde por **48,6%** das vendas, e São Paulo sozinho por 27%.
- **Ticket por região:** Sudeste e Sul têm ticket mediano de R$ 233, contra R$ 199 no Nordeste e R$ 208 no Norte e no Centro-Oeste.
- **A região esconde diferenças internas relevantes:** os três maiores tickets medianos são de estados fora do eixo Sul-Sudeste — **Alagoas (R$ 255,50), Paraíba (R$ 249) e Rondônia (R$ 247,50)** — enquanto Rio Grande do Norte, Sergipe e Tocantins têm os menores (cerca de R$ 180). Uma estratégia só por região trataria AL e RN da mesma forma, mas os tickets são muito diferentes.
- **Média engana em UFs pequenas:** Rondônia tem ticket **médio** de R$ 467, o maior do país, mas mediana de R$ 247,50. A diferença vem de poucas vendas de valor muito alto, o que mostra por que a mediana é a medida mais segura para comparar estados com pouco volume.
- **Meio de pagamento:** o uso de **boleto** é maior no Norte (34,0%) e no Nordeste (30,1%) do que no Sudeste (23,3%). Tocantins (39,6%) e Mato Grosso (36,8%) lideram, e o Rio Grande do Norte (20,0%) e São Paulo (22,5%) têm os menores índices. Onde o boleto pesa mais, o parcelamento pesa menos (Tocantins: 45,4% parcelado, contra 62,0% em São Paulo).

**Implicação:** condições de pagamento (desconto no boleto, número de parcelas) deveriam ser pensadas por **UF**, e não só por região. Uma hipótese a investigar com dados externos, que esta base não traz, é a relação entre renda e acesso a crédito.
""")

# ---- 9.6
md(r"""
## 9.6 Descoberta livre: um único cliente distorce agosto, o canal HiMidia e o indicador de repetições

### O que foi encontrado

Um **único cliente** (código `618107`, do Ceará) fez **236 compras em dois meses**, 221 delas em agosto de 2011. As compras seguem um padrão muito uniforme:

- **100% pelo canal HiMidia.**
- **233 de 236 em boleto.**
- **83% no mesmo valor**, R$ 109,00.
- **Até 33 compras em um único dia.**

Esse cliente sozinho responde por **51,5% das vendas do canal HiMidia em agosto**, **18,4% de todas as possíveis repetições** da base e **5,8% de todas as vendas de agosto**.
""")

md(r"""
### Como se chegou nele

A descoberta surgiu do **cruzamento de três *flags* independentes**, criadas por motivos diferentes:

- Na seção 3.12, um cliente se destacou pelo volume de compras (`flag_cliente_atipico`).
- Na seção 3.10, o mesmo código aparecia com frequência entre as possíveis repetições (`flag_possivel_repeticao`).
- Na seção 9.4, a concentração do canal HiMidia apontava para clientes atípicos.

A pergunta natural foi: **esses sinais são o mesmo fenômeno?** A investigação abaixo segue o cliente ao longo do tempo.
""")

code(r"""
# Cliente com maior número de compras (identificado por regra, sem código fixo)
cliente_top = df_clean["Cliente_Codigo"].value_counts().index[0]
compras_top = df_clean[df_clean["Cliente_Codigo"] == cliente_top]

print(f"Cliente: {cliente_top}")
print(f"Compras: {len(compras_top)} | de {compras_top['DataVenda'].min():%d/%m/%Y} a {compras_top['DataVenda'].max():%d/%m/%Y}")
print(f"UF: {compras_top['UF_Cliente'].astype(str).unique().tolist()} | "
      f"Canais: {compras_top['CanalVenda_Normalizado'].value_counts().to_dict()}")
print(f"Formas de pagamento: {compras_top['FormaPagamento'].astype(str).value_counts().to_dict()}")
print(f"Valor mais frequente: R$ {compras_top['ValorVenda'].mode().iloc[0]:.2f} "
      f"({(compras_top['ValorVenda'] == compras_top['ValorVenda'].mode().iloc[0]).mean() * 100:.0f}% das compras)")
print(f"Marcadas como possível repetição: {compras_top['flag_possivel_repeticao'].sum()} "
      f"({compras_top['flag_possivel_repeticao'].sum() / df_clean['flag_possivel_repeticao'].sum() * 100:.1f}% "
      f"de todas as repetições da base)")

print("\nCompras por mês:")
print(compras_top.groupby("AnoMes").size().to_string())
print("\nDias com mais compras:")
print(compras_top["DataVenda"].dt.date.value_counts().head(5).to_string())
""")

code(r"""
# Evidência 1: a evolução mensal do canal HiMidia, separando o cliente das demais vendas
himidia_mes = pd.crosstab(df_clean.loc[himidia, "AnoMes"],
                          np.where(df_clean.loc[himidia, "Cliente_Codigo"] == cliente_top,
                                   "Cliente atípico", "Demais clientes"))
himidia_mes.columns.name = None
himidia_mes["%_cliente_atipico"] = (himidia_mes["Cliente atípico"] / himidia_mes.sum(axis=1) * 100).round(1)
display(himidia_mes)

fig, ax = plt.subplots(figsize=(10, 4))
ax.bar(himidia_mes.index, himidia_mes["Demais clientes"], color=COR_PRINCIPAL, width=0.65, label="Demais clientes")
ax.bar(himidia_mes.index, himidia_mes["Cliente atípico"], bottom=himidia_mes["Demais clientes"],
       color=COR_SECUNDARIA, width=0.65, label=f"Cliente {cliente_top}", edgecolor="white", linewidth=1.5)
ax.legend(frameon=False, loc="upper left")
estilo_eixo(ax, "Vendas do canal HiMidia por mês: um único cliente responde pelo salto de agosto",
            "Mês", "Vendas")
plt.tight_layout()
plt.show()
""")

code(r"""
# Evidência 2: efeito sobre a evolução geral de agosto (9.1)
agosto = evolucao.index.max()
vendas_ago_sem = (df_clean["AnoMes"].eq(agosto) & df_clean["Cliente_Codigo"].ne(cliente_top)).sum()
print(f"{agosto}: {evolucao.loc[agosto, 'vendas_por_dia']:.1f} vendas/dia com o cliente | "
      f"{vendas_ago_sem / evolucao.loc[agosto, 'dias_com_venda']:.1f} sem o cliente")
print(f"Participação do cliente nas vendas de {agosto}: "
      f"{(compras_top['AnoMes'] == agosto).sum() / evolucao.loc[agosto, 'vendas'] * 100:.1f}%")
""")

md(r"""
### Da descoberta à regra: a *flag* de rajada de compras

Um achado só é útil para o *pipeline* se virar uma **regra genérica**, que funcione sem citar o código do cliente. Foi esta investigação que motivou a *flag* `flag_rajada_compras` (5 ou mais compras do mesmo cliente no mesmo dia). Para que a base preparada estivesse completa **antes** das análises, a regra foi registrada no *profiling* (3.12) e aplicada junto com as demais *flags* de cliente (6.6). Aqui ela é usada para verificar se o comportamento descoberto é isolado ou se repete em outros clientes.
""")

code(r"""
distribuicao = (df_clean.groupby(["Cliente_Codigo", df_clean["DataVenda"].dt.normalize()]).size()
                .value_counts().sort_index())
dist_tab = pd.DataFrame({"pares_cliente_dia": distribuicao,
                         "%_acumulado": (distribuicao.cumsum() / distribuicao.sum() * 100).round(3)})
display(dist_tab.head(8).T)

rajada = df_clean["flag_rajada_compras"]
print(f"Vendas em rajada: {rajada.sum()} | clientes: {df_clean.loc[rajada, 'Cliente_Codigo'].nunique()} | "
      f"das quais do cliente {cliente_top}: {(rajada & df_clean['Cliente_Codigo'].eq(cliente_top)).sum()}")
print(f"Boleto nas vendas em rajada: {(df_clean.loc[rajada, 'FormaPagamento'] == 'Boleto Bancário').mean() * 100:.1f}% "
      f"| na base: {(df_clean['FormaPagamento'] == 'Boleto Bancário').mean() * 100:.1f}%")
print(f"Possível repetição nas vendas em rajada: {df_clean.loc[rajada, 'flag_possivel_repeticao'].mean() * 100:.1f}% "
      f"| na base: {df_clean['flag_possivel_repeticao'].mean() * 100:.1f}%")
""")

md(r"""
**Evidência e interpretação:**

- **O "crescimento" do HiMidia em agosto é ilusório.** Pelo total, o canal sobe de 288 vendas em julho para 429 em agosto (+49%). Separando o cliente, as vendas dos **demais clientes caem** de 274 para 208 (−24%). As duas leituras levam a decisões opostas: ampliar ou rever o investimento no canal.
- **Agosto também muda:** sem esse cliente, a média do mês cai de 135,6 para 127,7 vendas por dia.
- **O padrão não é isolado.** Comprar 5 ou mais vezes no mesmo dia acontece em apenas 0,4% dos pares cliente-dia (99,6% ficam em até 4 compras). Mesmo assim, a regra encontra **742 vendas de 64 clientes**, 215 delas do cliente descoberto. Nessas "rajadas", o boleto sobe para 37,1% (contra 26,4% na base) e a possível repetição para 36,7% (contra 3,1%).

**Por que é relevante:**

- **Pode superestimar o faturamento.** Rajadas de boletos do mesmo valor sugerem boletos emitidos e não pagos, reemissões, contas de teste, revenda ou fraude. A base não tem **status de pagamento**, então não é possível saber quantas dessas vendas se converteram em receita. Esta é a principal recomendação à área de negócio: incluir o status do pedido na próxima extração.
- **Distorce a avaliação de parceiros.** Se o HiMidia for remunerado por venda, o parceiro estaria recebendo por um volume concentrado em um único comprador com comportamento atípico.
- **Virou regra do *pipeline*.** O achado foi transformado em `flag_rajada_compras` (aplicada em 6.6), genérica e parametrizada (`compras_mesmo_dia_rajada = 5`), que detecta o mesmo comportamento em qualquer carga futura, sem depender do código deste cliente.

A descoberta mostra o valor de **cruzar *flags*** criadas por motivos independentes: sozinhas, elas indicavam "um cliente que compra muito" e "algumas vendas repetidas". Juntas, revelaram um fenômeno que muda a leitura de um canal e de um mês.
""")

# =====================================================================
# 10. Base final
# =====================================================================
md(r"""
# 10. Geração da base final
""")

md(r"""
## 10.1 Seleção de colunas

A base final reúne, em blocos, tudo o que a análise precisa:

| Bloco | Colunas | Justificativa |
|---|---|---|
| Rastreabilidade | `id_registro` | Liga cada linha ao RAW e ao *log* de alterações |
| Originais tratadas | `DataVenda`, `ValorVenda`, `IdFormaDePagamento`, `FormaPagamento`, `TipoFormaPagamento`, `NumeroParcelas`, `Cliente_Codigo`, `Cliente_Data_Nascimento`, `UF_Cliente` | Os fatos da venda, já com tipos corrigidos, datas inválidas como ausentes e valores em centavos |
| Canal | `CanalVenda_Original`, `CanalVenda_Normalizado`, `CanalVenda_Midia`, `GrupoCanal` | O texto bruto é preservado ao lado das versões analisáveis, exigência do trabalho e garantia de auditoria |
| Datas derivadas | `Ano`, `Mes`, `AnoMes`, `Dia`, `DiaSemana`, `FimDeSemana`, `Hora`, `PeriodoDia` | Evita que cada usuário recalcule, com risco de regras diferentes |
| Cliente e geografia | `IdadeNaCompra`, `FaixaEtaria`, `Regiao` | Idade na data da compra, faixas documentadas (7.2) e região (7.6) |
| Pagamento | `ModalidadePagamento`, `ValorParcela` | Leitura direta do parcelamento |
| Qualidade | as 11 colunas `flag_*` | Permitem que cada análise decida o que filtrar, com transparência |

**Colunas excluídas:** nenhuma informação foi descartada. A coluna `CanalVenda` não aparece com esse nome porque foi **renomeada** para `CanalVenda_Original`, com conteúdo idêntico (verificado por `assert` em 7.5). As séries auxiliares de diagnóstico (`aux_*`) não fazem parte do `df_clean`.

**Registros eliminados:** apenas 1, a cópia da duplicata exata (6.2).
""")

code(r"""
COLUNAS_FINAIS = [
    "id_registro",
    "DataVenda", "ValorVenda", "IdFormaDePagamento", "FormaPagamento", "TipoFormaPagamento", "NumeroParcelas",
    "Cliente_Codigo", "Cliente_Data_Nascimento", "UF_Cliente", "Regiao",
    "CanalVenda_Original", "CanalVenda_Normalizado", "CanalVenda_Midia", "GrupoCanal",
    "Ano", "Mes", "AnoMes", "Dia", "DiaSemana", "FimDeSemana", "Hora", "PeriodoDia",
    "IdadeNaCompra", "FaixaEtaria",
    "ModalidadePagamento", "ValorParcela",
    "flag_nascimento_invalido", "flag_idade_improvavel", "flag_valor_zero", "flag_valor_extremo",
    "flag_pagamento_inconsistente", "flag_parcelas_zero", "flag_possivel_repeticao", "flag_rajada_compras",
    "flag_cliente_atipico", "flag_cliente_multi_uf", "flag_canal_multiplo",
]
faltando = set(df_clean.columns) - set(COLUNAS_FINAIS)
assert not faltando, f"Colunas do df_clean fora da base final: {faltando}"

df_final = df_clean[COLUNAS_FINAIS].reset_index(drop=True)
print(f"Base final: {df_final.shape[0]:,} linhas x {df_final.shape[1]} colunas")
print(f"Flags de qualidade: {sum(c.startswith('flag_') for c in COLUNAS_FINAIS)}")
""")

md(r"""
## 10.2 Gravação do arquivo

Os parâmetros de gravação são **explícitos**, e seguem o mesmo padrão do arquivo de origem para facilitar a abertura em planilhas configuradas em português:

- `sep=";"` e `decimal=","`: padrão brasileiro. Evita conflito entre a vírgula decimal e o separador de campos.
- `encoding="utf-8-sig"`: UTF-8 com BOM, para que os acentos apareçam corretamente no Excel.
- `date_format="%Y-%m-%d %H:%M:%S"`: formato ISO, sem ambiguidade entre dia e mês. A data de nascimento, que não tem hora, é gravada como `AAAA-MM-DD`.
- `index=False`: o índice do `pandas` não é informação da venda; a rastreabilidade está em `id_registro`.
""")

code(r"""
NOME_ARQUIVO_FINAL = "BaseVendasXPTO_CLEAN_Vinicius_Machado.csv"
PARAMETROS_GRAVACAO = {"sep": ";", "decimal": ",", "encoding": "utf-8-sig", "index": False,
                       "date_format": "%Y-%m-%d %H:%M:%S"}

# Nascimento é uma data sem hora: gravado como AAAA-MM-DD (as demais datas usam date_format)
saida = df_final.copy()
saida["Cliente_Data_Nascimento"] = saida["Cliente_Data_Nascimento"].dt.strftime("%Y-%m-%d")
saida.to_csv(NOME_ARQUIVO_FINAL, **PARAMETROS_GRAVACAO)
print(f"Arquivo gravado: {NOME_ARQUIVO_FINAL}")

# No Google Colab, descomente a linha abaixo para baixar o arquivo
# from google.colab import files; files.download(NOME_ARQUIVO_FINAL)
""")

md(r"""
## 10.3 Verificação: o arquivo relido é igual à base final?

Um arquivo gravado só é confiável se **relido com os mesmos parâmetros reproduzir a base**. A verificação compara quantidade de linhas e colunas, soma dos valores, ausentes por coluna e contagem das *flags*.
""")

code(r"""
releitura = pd.read_csv(NOME_ARQUIVO_FINAL, sep=";", decimal=",", encoding="utf-8-sig",
                        keep_default_na=False, na_values=[""])

assert releitura.shape == df_final.shape, "Dimensões divergentes"
assert list(releitura.columns) == COLUNAS_FINAIS, "Colunas divergentes"
assert np.isclose(releitura["ValorVenda"].sum(), df_final["ValorVenda"].sum()), "Soma de valores divergente"
assert releitura.isna().sum().equals(df_final.isna().sum()), "Ausentes divergentes"
flags_finais = [c for c in COLUNAS_FINAIS if c.startswith("flag_") and c != "flag_nascimento_invalido"]
assert (releitura[flags_finais].sum() == df_final[flags_finais].sum()).all(), "Flags divergentes"

import os
print(f"Releitura consistente: {releitura.shape[0]:,} linhas x {releitura.shape[1]} colunas | "
      f"tamanho {os.path.getsize(NOME_ARQUIVO_FINAL) / 1024**2:.2f} MB")
releitura.head(3)
""")

# =====================================================================
# 11. Produção
# =====================================================================
md(r"""
# 11. Pergunta final sobre produção
""")

md(r"""
## 11.1 "Se amanhã chegarem mais 1 milhão de registros no mesmo formato, o pipeline funciona sem intervenção manual?"

**Em grande parte sim, mas não com segurança suficiente para produção.** A resposta depende de separar o que já é genérico do que ainda depende de um analista.

**O que já funcionaria sem intervenção:**

- **Leitura:** os parâmetros são explícitos e os marcadores de ausência são declarados (1.4).
- **Regras parametrizadas:** ficam em `PARAMETROS_REGRAS`, sem índices de linha nem códigos de cliente fixos.
- **Limites estatísticos recalculados:** IQR e percentil de clientes atípicos se ajustam aos novos dados.
- **Canais novos:** caem em `Não mapeado`, em vez de gerar erro ou ser classificados errado.
- **Formas de pagamento novas:** um Id novo é marcado por `flag_pagamento_inconsistente`.

**O que exigiria intervenção ou poderia falhar em silêncio:**

- **Dicionários mantidos à mão:** `REGRAS_GRUPO_CANAL`, `CORRECOES_GRAFIA` e `DOMINIO_PAGAMENTO`. Um canal novo relevante ficaria em "Não mapeado" até alguém classificá-lo.
- **Limites que mudam a cada carga:** o limite de valor extremo e o de cliente atípico são recalculados em cada execução. Isso é bom para adaptação, mas **torna as *flags* incomparáveis entre cargas**. Em produção, os limites deveriam ser calculados sobre uma base de referência e versionados.
- **Regras que dependem do histórico:** repetições, rajadas e clientes atípicos olham para outras vendas do mesmo cliente. Se a carga for incremental, uma repetição que atravessa dois lotes não seria detectada.
- **Duplicatas entre cargas:** a remoção de duplicatas só compara registros do mesmo lote. Reprocessar um arquivo já carregado duplicaria vendas.
- **Células exploratórias:** as células de descoberta da seção 1 (leitura byte a byte, contagem de separadores) são diagnóstico, não *pipeline*. Em produção, os parâmetros descobertos viram **contrato**.
""")

md(r"""
## 11.2 O que mudaria em produção

- **Modularização em funções e scripts:** o notebook documenta a descoberta; a produção precisa de um pacote Python com uma função por etapa (`ler`, `validar`, `limpar`, `derivar`, `gravar`) e uma função `executar_pipeline(caminho_entrada)` que as encadeia. As funções deste notebook (`perfilar_coluna`, `normalizar_canal`, `classificar_canal`, `idade_na_data`, `marcar_repeticoes`) já são quase reutilizáveis.
- **Validação de *schema*:** antes de qualquer transformação, o arquivo seria validado contra um contrato (nomes e ordem das colunas, tipos, formatos de data, domínios de UF e pagamento), com bibliotecas como `pandera` ou `great_expectations`. Um arquivo fora do contrato é **rejeitado com mensagem clara**, em vez de processado de forma errada.
- **Testes de qualidade automatizados:** os `assert` deste notebook virariam testes (`pytest`), com dois tipos. **Testes de unidade**, como o do aniversário em 7.2, para as funções. **Testes de dados**, com limites de alerta, por exemplo "a proporção de canal ausente não pode passar de 40%" ou "nenhuma data de venda no futuro".
- **Categorias novas de canal:** a tabela de regras sairia do código para um arquivo de configuração (CSV ou YAML) mantido pelo marketing. A cada carga, a lista de valores em "Não mapeado" seria **enviada automaticamente** para classificação, com a participação nas vendas, para priorizar os canais mais relevantes.
- ***Logs*:** o `log_etapas` e o `log_registros` seriam gravados em arquivo ou tabela, com data da execução, versão do código e identificador da carga, trocando `print` pelo módulo `logging`.
- **Orquestração:** um orquestrador (Airflow, Prefect ou um agendador simples) executaria as etapas em ordem, com novas tentativas em caso de falha de rede na leitura, alertas e dependências entre tarefas.
- **Versionamento de dados:** o arquivo RAW de cada carga seria armazenado **imutável** (com *hash*, como em 1.5), e as bases CLEAN versionadas (DVC, *snapshots* de tabela). Qualquer número publicado poderia ser reproduzido a partir de uma versão específica dos dados e do código.
- **Performance e memória:** 1 milhão de linhas é cerca de 35 vezes esta base. Cabe na memória de uma máquina comum, mas três pontos pediriam ajuste:
  - As funções aplicadas linha a linha em Python (`normalizar_canal`, `classificar_canal`, `arredondar_comercial`) deveriam ser aplicadas **só aos valores distintos** e depois mapeadas de volta. Há centenas de canais distintos contra milhões de linhas.
  - A leitura deveria declarar `dtype` por coluna (e usar `category` desde o início), ou ser feita em blocos (`chunksize`).
  - Para volumes maiores, formatos colunares como Parquet e bibliotecas como `polars` ou `duckdb` substituiriam o CSV.
- **Monitoramento:** um painel acompanharia, por carga, os indicadores de qualidade: percentual de cada *flag*, volume em "Não mapeado", ausentes por coluna e distribuição de valores. Uma **mudança brusca** geraria alerta. O caso das parcelas zeradas a partir de 10/06/2011 (3.8) teria sido detectado no dia em que surgiu, e não meses depois, numa análise manual.
""")

# =====================================================================
# Checklist
# =====================================================================
md(r"""
# Checklist final do trabalho

| Requisito | Onde é atendido | Status |
|---|---|---|
| Leitura direta da URL, sem arquivos intermediários | 1.1, 1.5 | [x] |
| Parâmetros de leitura descobertos e justificados (separador, decimal, *encoding*, ausentes) | 1.2 a 1.5 | [x] |
| Camada RAW intocada (`df_raw`) e verificada por *hash* | 1.5, 7.7 | [x] |
| Nº de registros, atributos, nomes, tipos, memória e período | 2.1 a 2.4 | [x] |
| Resposta sobre a adequação dos tipos inferidos | 2.5 | [x] |
| *Profiling* por atributo consolidado em tabela | 3.2, 3.3 | [x] |
| Busca ativa: ausentes, sentinelas, domínio, datas, duplicidades, extremos, inconsistências entre colunas, granularidade | 3.4 a 3.13 | [x] |
| Tabela de Qualidade com pelo menos 8 ocorrências e severidade | 4.1 (16 ocorrências) | [x] |
| Pelo menos 5 decisões classificadas de A a E, com tabela resumo | 5.2 a 5.11 (14 decisões) | [x] |
| `df_clean` criado por cópia, com contagens antes e depois | 6.1 a 6.6 | [x] |
| *Log* de registros modificados e removidos, com motivo | 6.1, 7.7 | [x] |
| 7.1 Datas derivadas e justificadas | 7.1 | [x] |
| 7.2 Idade na data da compra, investigação e faixa etária documentada | 7.2 | [x] |
| 7.3 Valores monetários: extremos, IQR e decisões | 7.3 | [x] |
| 7.4 Pagamento: consistência e *flags* | 7.4 | [x] |
| 7.5 Canal: `CanalVenda_Original`, `CanalVenda_Normalizado`, `GrupoCanal` e tabela de mapeamento | 7.5 | [x] |
| Resumo de transformações, variáveis novas, modificados e removidos | 7.7 | [x] |
| Comparação RAW × CLEAN com 3+ indicadores e tabela | 8.1, 8.2 | [x] |
| Resposta: alguma decisão gerencial seria diferente? | 8.3 | [x] |
| Perguntas de negócio 9.1 a 9.5 usando somente `df_clean` | 9.1 a 9.5 | [x] |
| Descoberta livre com evidência e relevância | 9.6 | [x] |
| Base final com originais, transformados, derivados e *flags* | 10.1 | [x] |
| Arquivo `BaseVendasXPTO_CLEAN_Vinicius_Machado.csv` com separador e decimal explícitos | 10.2, 10.3 | [x] |
| Discussão sobre produção | 11.1, 11.2 | [x] |
| Execução do início ao fim em ambiente limpo, sem valores "chumbados" de linhas | Todo o notebook | [x] |
""")
