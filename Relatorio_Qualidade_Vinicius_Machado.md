# Relatório de Qualidade dos Dados — Base de Vendas XPTO

**Objetivo deste relatório:** resumir, de forma objetiva, os problemas de qualidade encontrados na base `BaseVendasXPTO.csv`, as evidências que os sustentam, as decisões tomadas, os tratamentos aplicados e o impacto das correções nos indicadores de negócio.

**Autor:** Vinicius Machado
**Notebook de referência:** `XPTO_Preparacao_Dados_Vinicius_Machado.ipynb` (as seções citadas entre parênteses remetem a ele)
**Base tratada:** `BaseVendasXPTO_CLEAN_Vinicius_Machado.csv`

1. Visão geral da base
2. Problemas encontrados e evidências
3. Decisões e tratamentos
4. Impacto das correções
5. Recomendações à área de negócio

---

## 1. Visão geral da base

| Item | Valor |
|---|---|
| Registros (RAW) | 28.505 |
| Atributos (RAW) | 10 |
| Período | 10/01/2011 a 28/08/2011 (janeiro e agosto parciais) |
| Leitura | `sep=";"`, `decimal=","`, `encoding="utf-8-sig"` (arquivo com BOM), ausentes = `""` e `"NULL"` |
| Registros (CLEAN) | 28.504 (1 removido) |
| Atributos (CLEAN) | 38 (10 originais tratados + 28 novos, sendo 11 *flags* de qualidade) |

**Leitura geral:** os **valores monetários** e as **datas de venda** estão íntegros. Os problemas se concentram nos atributos **descritivos**: canal de venda e dados do cliente. A relação entre Id, forma e tipo de pagamento é perfeitamente consistente, e as 27 UFs estão corretas. O *profiling* também confirmou o que está certo, e não só o que está errado.

---

## 2. Problemas encontrados e evidências

| # | Campo | Problema | Evidência | Quantidade | Severidade |
|---|---|---|---|---|---|
| 1 | `CanalVenda` | Canal ausente, em dois formatos (vazio e `NULL`) | Maior "categoria" da coluna (3.4, 3.13) | 9.482 (33,26%) | Alta |
| 2 | `CanalVenda` | Texto livre: caixa, parâmetros UTM, listas com vírgula, grafias diferentes | 602 valores distintos; 585 ignorando a caixa (3.13) | 10.805 vendas com texto fora do padrão | Alta |
| 3 | `Cliente_Data_Nascimento` | Data sentinela (ano ≤ 1900) | `1900-01-01` compartilhada por 141 clientes distintos; a próxima data mais comum tem 13 (3.5) | 270 | Alta |
| 4 | `Cliente_Data_Nascimento` | Nascimento posterior à data da compra | Idade negativa; um caso em `2011-12-16`, depois do fim da base (3.6) | 12 | Média |
| 5 | `Cliente_Data_Nascimento` | Idade improvável na compra (< 16 anos) | Cálculo exato da idade (7.2) | 172 | Média |
| 6 | `Cliente_Data_Nascimento` | Ausente na origem (literal `NULL`) | Ausência consistente por cliente, sem como recuperar (3.4) | 2.633 (9,24%) | Média |
| 7 | `NumeroParcelas` | Cartão de crédito com 0 parcelas | Surge só a partir de 10/06/2011; mediana de R$ 69 contra R$ 240 (3.8) | 585 | Média |
| 8 | Linha inteira | Possível repetição (mesmo cliente e valor em até 60 min) | Intervalo mediano de 10 min; 201 com troca da forma de pagamento (3.10) | 891 | Média |
| 9 | `Cliente_Codigo` | Volume atípico de compras (acima do percentil 99,9) | Um cliente com 236 compras, 100% pelo mesmo canal (3.12) | 877 vendas de 14 clientes | Média |
| 10 | `Cliente_Codigo` | Rajada de compras (5+ no mesmo dia) | Só 0,4% dos pares cliente-dia; boleto e repetição acima da média (3.12, 9.6) | 742 vendas de 64 clientes | Média |
| 11 | Várias | Tipos inadequados na leitura | Datas lidas como texto; códigos como inteiros (2.5) | Todas as linhas | Média |
| 12 | `ValorVenda` | Valor zero | 14 com cupom (plausível); 2 com boleto (incoerente) (3.7) | 16 | Baixa |
| 13 | `ValorVenda` | Mais de 2 casas decimais | Ex.: `431,275`; diferença máxima de meio centavo (3.7) | 77 | Baixa |
| 14 | `ValorVenda` | Extremos (acima de Q3 + 1,5 IQR = R$ 711) | Distribuição contínua e assimétrica; máximo de R$ 17.016,25 (3.7, 7.3) | 2.083 (7,3%) | Baixa |
| 15 | Linha inteira | Duplicata exata | Todas as colunas iguais, no mesmo minuto (3.10) | 1 | Baixa |
| 16 | `UF_Cliente` | Cliente com mais de uma UF | 53 clientes; possivelmente UF de entrega (3.11) | 223 | Baixa |

**Ponto de atenção, sem tratamento:** existem nascimentos com formato "bonito", como `1910-10-10` (7 vendas, 1 cliente, exatamente 100 anos na compra) e `1912-12-12` (1 venda). Eles são suspeitos, mas não foram tratados como sentinela: a regra de sentinela é objetiva (ano ≤ 1900) e, ao contrário de `1900-01-01`, não há concentração entre clientes que prove preenchimento automático (3.5).

---

## 3. Decisões e tratamentos

Cada problema recebeu uma de cinco decisões: **A. Corrigir**, **B. Remover**, **C. Manter**, **D. Transformar** ou **E. Marcar para análise**. O princípio seguido foi **"excluir dados não é limpar dados"**: a remoção ficou restrita ao único caso sem dúvida razoável.

| Problema | Decisão | Tratamento aplicado |
|---|---|---|
| Duplicata exata | **B. Remover** | Remoção da cópia excedente, registrada no *log* |
| Nascimento sentinela | **A. Corrigir** | Substituído por ausente + `flag_nascimento_invalido = "sentinela"` |
| Nascimento posterior à compra | **A. Corrigir** | Substituído por ausente + `flag_nascimento_invalido = "posterior_compra"` |
| Centavos fracionados | **A. Corrigir** | Arredondamento comercial para 2 casas (`Decimal`, `ROUND_HALF_UP`) |
| Idade improvável | **E. Marcar** | `flag_idade_improvavel`; faixa etária própria "Idade improvável" (por isso a primeira faixa real é "16–17") |
| Valor zero | **E. Marcar** | `flag_valor_zero`; excluído do cálculo de ticket |
| Valores extremos | **C. Manter** | `flag_valor_extremo`, apenas informativa |
| Cartão com 0 parcelas | **E. Marcar** | `flag_parcelas_zero`; `ModalidadePagamento = "Não informado"` |
| Possível repetição | **E. Marcar** | `flag_possivel_repeticao` (a primeira venda do par não é marcada) |
| Cliente atípico | **E. Marcar** | `flag_cliente_atipico` |
| Rajada de compras | **E. Marcar** | `flag_rajada_compras` (detectada em 3.12, aplicada em 6.6 e aprofundada na descoberta da seção 9.6) |
| Cliente com várias UFs | **C. Manter** | `flag_cliente_multi_uf` |
| Canal ausente ou em texto livre | **D. Transformar** | `CanalVenda_Original` (preservado), `CanalVenda_Normalizado`, `CanalVenda_Midia`, `GrupoCanal` e `flag_canal_multiplo` |
| Tipos inadequados | **D. Transformar** | Datas para `datetime64`; `Cliente_Codigo` para texto; 4 colunas para `category` |

**Normalização do canal:** seis regras genéricas aplicadas em sequência:

1. `strip` e minúsculas.
2. Remoção de acentos.
3. Remoção de parâmetros UTM e *query strings*, com extração da mídia antes.
4. Listas com vírgula: fica a primeira origem distinta.
5. Remoção de `/` nas bordas.
6. Dicionário de grafias (`twitte` → `twitter`, `fb` → `facebook`).

**Taxonomia do canal:** o `GrupoCanal` organiza os canais em 10 grupos por natureza do tráfego, com regras ordenadas. Um grupo de segurança, "Não mapeado", recebe canais novos em cargas futuras. Nesta base, só o valor `E`, uma letra isolada, caiu nele (30 vendas).

**Rastreabilidade:** o `log_registros` guarda cada valor alterado e cada registro removido, com `id_registro`, valor anterior, valor novo e motivo. No total, **1 registro foi removido e 358 tiveram algum valor corrigido**. O `df_raw` permaneceu intocado, o que foi verificado por *hash* no início e no fim do processo.

---

## 4. Impacto das correções

| Indicador | Base RAW | Base CLEAN | Diferença |
|---|---|---|---|
| Quantidade de canais distintos | 602 | 519 normalizados / 8 grupos de origem conhecida | −83 grafias |
| Participação do google (mesmo canal) | 29,40% | 19,62% | −9,78 p.p. |
| Principal origem de vendas (CLEAN por `GrupoCanal`) | google: 29,40% | Campanhas próprias XPTO: 32,00% | O líder muda (limpeza + taxonomia); busca = 20,31% |
| Idade média do cliente | 32,62 anos | 31,98 anos | −0,64 ano |
| Clientes com 65 anos ou mais | 2,41% | 1,39% | −1,02 p.p. (−42,3%) |
| Ticket médio | R$ 314,61 | R$ 314,80 | +R$ 0,18 |

**Interpretação:**

- **Canais — a decisão muda (impacto mais relevante):** a base bruta supervaloriza o `google` (29,40% contra 19,62% do total real de vendas) porque o `value_counts()` descarta o terço de vendas sem canal. Ela também esconde as campanhas próprias, que são o maior grupo (32,00%), mas estão fragmentadas em centenas de códigos. Com os dados tratados, a prioridade passa a ser **melhorar o rastreamento de origem**.
- **Público — a decisão muda:** o sentinela `1900-01-01` infla a participação de clientes com 65 anos ou mais em cerca de 1,7 vez. As duas bases usam o mesmo cálculo exato de idade, então a diferença vem só da limpeza.
- **Ticket — a decisão não muda:** o valor das vendas estava íntegro, e a variação é de R$ 0,18. Os problemas desta base estão nos atributos descritivos, não no valor.
- **Descoberta com impacto direto (9.6):** um único cliente responde por 51,5% das vendas do canal HiMidia em agosto. Pelo total, o canal parece crescer 49% de julho para agosto. Sem esse cliente, as vendas dos demais **caem 24%**.

---

## 5. Recomendações à área de negócio

1. **Incluir o status do pedido e do pagamento na extração.** Sem ele, não é possível saber se as possíveis repetições e as rajadas de boletos viraram receita.
2. **Tornar obrigatório o registro de origem da venda:** 33,26% das vendas não têm canal, e esse é hoje o maior ponto cego da análise de marketing.
3. **Padronizar a nomenclatura de campanhas** (letras minúsculas, sem parâmetros no nome, uma origem por venda) e documentar os códigos `xpto*`.
4. **Validar com o marketing** a taxonomia `GrupoCanal`, em especial os grupos "Outros parceiros" e "E-mail e CRM", que dependem da interpretação dos nomes.
5. **Investigar a mudança de 10/06/2011** que fez surgirem vendas em cartão com 0 parcelas: nova modalidade, alteração de sistema ou falha na captura.
6. **Remover do cadastro o preenchimento automático** de data de nascimento (`1900-01-01`) e validar que a data seja anterior à compra.
7. **Analisar os clientes com rajadas de compras**, a começar pelo cliente `618107`, para distinguir revenda, teste, integração ou fraude, antes de remunerar parceiros por volume.
