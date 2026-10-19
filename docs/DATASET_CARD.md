# Dataset Card — Responsible Receivables Agent (v1.0.0-candidate)

**Protocolo:** `docs/EXPERIMENT_PROTOCOL.md` v1.0.0 · **Decisão:** `docs/DECISIONS.md` D16 · **Criado em:** 2026-10-19 (T03)
**Estado:** **candidato**. A validação humana independente **ainda não foi feita** (ver §13). O teste **não está congelado**.

## 1. Objetivo

Dataset de investigação para as experiências E1 (Active In-Context Learning, RQ1) e E2 (triagem para revisão humana adicional, RQ2) do protocolo T02. Fornece:

- o *seed stock* da memória inicial;
- a *pool* de candidatos à anotação ativa;
- uma validação para piloto, pesos e limiares;
- um teste reservado.

Cada observação é uma mensagem de um cliente sobre um pendente, com o contexto financeiro e as etiquetas de referência. **O dataset é fixo**: não se geram mensagens novas durante as experiências.

## 2. Domínio e língua

Acompanhamento de faturas vencidas de um fornecedor fictício, uma PME portuguesa de equipamentos, consumíveis, manutenção e aluguer de máquinas para hotelaria, restauração e instituições. Os 180 clientes fictícios incluem restaurantes, hotéis, pastelarias, IPSS, escolas, bares, catering e outros. As mensagens estão em **português de Portugal**, com registos variados: formal e administrativo, coloquial, regional, sem pontuação ou acentos, com emojis, com mistura de inglês e italiano, e português de falante não nativo.

## 3. Natureza sintética

**Todas as mensagens, nomes, empresas, NIF, IBAN e valores são fictícios.** Os IBAN usam o padrão `PT50 0000 …`. Nenhum dado vem de empresas reais. O dataset **não representa a distribuição real** dos e-mails de cobrança das PME portuguesas: as proporções de classes, de casos críticos e de situações são **escolhas de desenho** para cobrir as regras do protocolo, não estimativas de prevalência.

## 4. Processo real de criação

1. **Redação:** as 510 mensagens foram escritas uma a uma pelo assistente de IA **Claude Opus 5.5** (`claude-opus-5-5`, Claude Code) a 2026-10-19, em 10 lotes (A–J). Cada lote foi organizado por cliente, com estilo próprio de cada cliente, para que o estilo dependa do autor e não da classe. **Não foi usado nenhum gerador, *template* programático nem preenchimento automático.** A abordagem anterior de geração programática foi abandonada e não foi reutilizada (D16).
2. **Etiquetas propostas:** o mesmo assistente atribuiu, a cada mensagem, a etiqueta, as intenções secundárias, as *flags*, as razões RV, os factos RV (`rv_facts`), a situação e a justificação.
3. **Verificação automática:** `dataset.validate_records` recalcula as razões RV esperadas a partir das intenções, das *flags*, dos factos e do contexto; recalcula também o perfil `action_policy` por *first match* e verifica schema, datas e dias da semana. Todos os erros encontrados foram corrigidos na fonte, por exemplo duas justificações curtas e duas menções de dias da semana.
4. **Revisão editorial/semântica por IA:** o mesmo modelo reviu os lotes (Etapa C), sem independência:
   - definiu as lacunas GAP-01…GAP-09 e reescreveu casos ambíguos, entre eles os planos de cerca de 6 meses e as auto-correções;
   - excluiu casos sem regra suficiente (GAP-09);
   - fundiu formulações reutilizadas em famílias;
   - ajustou campos de contexto que criavam correlações espúrias (valores de OU, incumprimentos em ID), sem mexer no texto.
5. **Revisão humana independente:** **não realizada**.
6. **Adjudicação:** **não realizada**; prevista na T04.

Uma segunda leitura pelo mesmo modelo **não equivale** a um segundo anotador humano.

## 5. Dimensão

510 observações: 30 *seed stock*, 300 *pool*, 60 validação, 120 teste (protocolo 8.1). Nenhuma observação é preenchimento: não há duplicados exatos nem quase-duplicados (§11).

## 6. Schema

Ficheiros em `data/dataset/`, em JSONL UTF-8, uma linha por caso, ordenados por `case_id`.

**`cases.jsonl`** (entrada, sem ground truth):

| Campo | Tipo | Nota |
| --- | --- | --- |
| `case_id` | str | `RRA-0001`…`RRA-0510`, único |
| `customer_id` | str | `CLI-001`…`CLI-180` |
| `invoice_id` | str | `FT 2026/NNNN`; pertence a um só cliente (pode haver vários casos sobre a mesma fatura) |
| `scenario_id` | str | fio de seguimento sobre a mesma fatura (`SCN-NNNN`); interno |
| `family_id` | str | família de formulação; interno |
| `pending_amount_eur` | str | decimal exato, `"1840.00"` |
| `due_date`, `snapshot_date` | str | ISO 8601; `due_date < snapshot_date` (todas as faturas estão vencidas) |
| `broken_promises_count` | int | ≥ 0 |
| `received_at` | str | ISO 8601; `snapshot_date ≤ received_at` |
| `message_subject` | str | pode ser vazio (297/510) |
| `message_text` | str | texto integral |

**`annotations.jsonl`** (ground truth e proveniência, mesma ordem):

| Campo | Nota |
| --- | --- |
| `message_label`, `secondary_intents`, `needs_additional_review`, `review_reasons`, `risk_flags`, `action_policy` | etiquetas de referência (protocolo 4) |
| `rv_facts` | `claimed_amount_eur`, `claim_has_date`, `claim_has_means`, `claim_third_party` (só com intenção PAYMENT_CLAIM), `plan_total_months` (só com PAYMENT_PLAN_REQUEST): factos usados para verificar RV2/RV3 |
| `situation` | subtipo descritivo (41 valores); não é etiqueta experimental |
| `rationale` | justificação textual da etiqueta |
| `needs_adjudication` | sempre `false` (os casos sem regra suficiente foram excluídos) |
| `annotation_status` | `ai_proposed_rule_checked_ai_reviewed` |
| `authoring_batch` | lote de redação (`A`…`J`) |

**`splits.json`**: atribuição dos `case_id` a cada conjunto + semente. **`manifest.json`**: versão, estado, *hashes*, estatísticas e verificações.

## 7. Distribuição das classes

| Classe | Total | Seed | Pool | Validação | Teste |
| --- | ---: | ---: | ---: | ---: | ---: |
| PAYMENT_PROMISE | 95 | 6 | 55 | 11 | 23 |
| PAYMENT_CLAIM | 110 | 6 | 66 | 11 | 27 |
| PAYMENT_PLAN_REQUEST | 84 | 5 | 50 | 11 | 18 |
| INVOICE_DISPUTE | 115 | 6 | 69 | 14 | 26 |
| OTHER_OR_UNCLEAR | 106 | 7 | 60 | 13 | 26 |
| **Total** | **510** | **30** | **300** | **60** | **120** |

O teste tem ≥ 12 casos por classe e 53 das classes críticas de E1 (PC + ID ≥ 40).

## 8. Distribuição da revisão humana adicional

`needs_additional_review = true` em **245/510** (48 %). Por classe:

| Classe | Com revisão | Sem revisão |
| --- | ---: | ---: |
| PAYMENT_PROMISE | 22 | 73 |
| PAYMENT_CLAIM | 33 | 77 |
| PAYMENT_PLAN_REQUEST | 41 | 43 |
| INVOICE_DISPUTE | 115 | 0 |
| OTHER_OR_UNCLEAR | 34 | 72 |

INVOICE_DISPUTE implica sempre RV1 (protocolo 4.2); as restantes classes têm ambos os resultados, por isso a revisão **não** é função da classe. Subconjunto discricionário (sem RV5–RV7): 465 casos, 200 com revisão; **no teste: 107 casos, 44 com revisão e 63 sem**.

| Conjunto | Revisão (sim/não) | Discricionário (n / com revisão) |
| --- | --- | --- |
| Seed | 14 / 16 | 27 / 11 |
| Pool | 145 / 155 | 275 / 120 |
| Validação | 29 / 31 | 56 / 25 |
| Teste | 57 / 63 | 107 / 44 |

## 9. Cobertura RV1–RV8 e políticas

| Regra | Casos | Teste |  | Perfil | Casos |
| --- | ---: | ---: | --- | --- | ---: |
| RV1 contestação | 118 | 26 |  | AP_STANDARD | 416 |
| RV2 alegação não verificável | 30 | 7 |  | AP_CLARIFY_FIRST | 49 |
| RV3 valor elevado / plano longo | 33 | 8 |  | AP_REVIEW_GATED | 20 |
| RV4 incumprimentos | 25 | 4 |  | AP_SECURITY_LOCKDOWN | 25 |
| RV5 alteração de dados bancários (MR1) | 11 | 4 |  |  |  |
| RV6 instrução ao agente (MR2) | 14 | 4 |  |  |  |
| RV7 legal / insolvência (MR3) | 20 | 5 |  |  |  |
| RV8 contradição | 12 | 1 |  |  |  |

Casos exigidos pelo pedido: a mesma classe com e sem revisão (todas exceto ID); instruções maliciosas junto de intenções legítimas (6 casos: PP e PC com RV6); casos críticos em OU (IBAN, *injection*, legal, insolvência, contradição); contestações sem bloqueio obrigatório (108 ID em AP_STANDARD); políticas que impõem revisão independentemente da classe (RV5–RV7 em PP, PC, PR, ID e OU). RV8 tem só 1 caso no teste: limitação para análises por regra.

## 10. Mensagens multi-intenção

**33** mensagens têm intenções secundárias: 21 sem contradição (ID+PC 7, ID+PP 6, PC+PP 5, PC+PR 2, ID+PR 1) e 12 contradições (OU com PC, PC+PP ou ID+PP). Por conjunto: seed 1, pool 19, validação 5, teste 8.

## 11. Critérios de qualidade e verificações efetuadas

- **Duplicados exatos** (texto normalizado, protocolo 8.2.3): 0.
- **Quase-duplicados** (Jaccard de 5-gramas ≥ 0,80, 8.2.4): 0 pares no dataset inteiro, não só entre conjuntos. O par mais semelhante tem Jaccard < 0,5.
- **Famílias de formulação:** 10 famílias com mais de um membro. Incluem 6 pares de contraste deliberados (p. ex. o mesmo pedido de prestações abaixo e acima de 5 000 €; a mesma promessa com e sem *injection*; «não reconhecemos» vs «enviem cópia») e 4 grupos de fórmulas reutilizadas pelo autor entre clientes (Jaccard ≥ 0,35, verificado por `family_audit`). As restantes 488 famílias são singulares: nenhuma relação de formulação foi encontrada. Isto é declarado, não é um id arbitrário para preencher o campo.
- **Coerência financeira e temporal:** valores positivos com 2 casas decimais; vencimento < *snapshot* ≤ receção; *snapshots* às segundas-feiras (7/9 a 12/10/2026); menções «dia da semana, dia N» verificadas contra o calendário.
- **Coerência das etiquetas:** razões RV recalculadas a partir de intenções, *flags*, factos e contexto; perfil derivado das *flags*; prioridade e regra de contradição verificadas.
- **Atalhos de classificação (verificados na Etapa C):** não há saudação nem primeira palavra típica de uma classe («bom dia»/«boa tarde» dominam em todas); 297 assuntos estão vazios e a maioria dos restantes é neutra («RE: FT …», «RE: Aviso», nome do equipamento). Ainda assim, uma minoria antecipa a etiqueta e é um sinal a considerar: 6 pedidos de plano («Pedido de prazo/plano/faseamento», «Proposta de pagamento/regularização») em 84 PR; 2 ID («divergência», «reconciliação»); respostas automáticas e insolvência em OU. Os assuntos sobre dados bancários repartem-se entre PP e OU, e «Pagamento» aparece também numa contestação; pendentes ≥ 5 000 € existem em todas as classes (PP 7, PC 6, PR 20, ID 10, OU 8); incumprimentos ≥ 2 aparecem em todas as classes.
- **Não verificado:** cosseno de *embedding* ≥ 0,92 (8.2.4), porque não há *encoder* local e não se fizeram downloads; qualidade linguística PT-PT por falante nativo independente.

## 12. Procedimento de anotação

Etiquetas segundo `docs/EXPERIMENT_PROTOCOL.md` (secções 3–4), usando `docs/protocol/reference_examples.json` como guia. **Nenhum dos 15 exemplos de referência foi copiado.** Interpretações operacionais adotadas onde o guia não decide: GAP-01…GAP-08 em `DECISIONS.md`. Resumo:

- PP vs PR em faturas já vencidas;
- completude de RV2 (valor, data identificável e meio explícitos; anexos não contam);
- erro de documento vs pedido de documento;
- só contam as intenções sobre a fatura do caso;
- o prazo de RV3 conta-se até ao último pagamento;
- RV2/RV3/RV4 não se aplicam dentro de uma contradição;
- sem auto-correções;
- âmbito de `insufficient_information`.

GAP-09 (cliente que relata uma possível fraude de IBAN) ficou **sem regra**, e esses casos foram excluídos.

## 13. Estado real da validação humana

| Etapa | Estado |
| --- | --- |
| Etiqueta proposta | Feita (IA, Claude Opus 5.5) |
| Verificação automática de consistência | Feita (`validate` e `pytest`, 0 erros) |
| Revisão editorial/semântica por IA | Feita pelo **mesmo** modelo; não independente |
| Revisão humana independente | **Não feita** |
| Dupla anotação humana + κ ≥ 0,70 (8.2.7) | **Não feita**: requisito científico pendente (T04) |
| Adjudicação | **Não feita** |

Consequência: as divisões são **candidatas**. O manifesto declara `"status": "candidate: …"` e `"test_frozen": false`. Os resultados obtidos antes da T04 não podem ser apresentados como avaliados sobre um teste validado.

## 14. Estratégia anti-*leakage*

- Unidade de divisão = componentes conexos do grafo cliente/cenário/família (8.2.1), mais as arestas de quase-duplicados (8.2.4). Há 168 componentes; a maior tem 12 casos.
- Nenhum cliente, cenário ou família aparece em dois conjuntos (verificado).
- Mensagens e etiquetas estão em ficheiros separados. `inference_view` / `inference_split` devolvem só `case_id`, `customer_id`, `invoice_id`, contexto e mensagem, sem etiquetas, razões, *flags*, política, `scenario_id` nem `family_id` (8.2.5).
- `Oracle` responde só a ids da *pool* pedidos explicitamente e regista as consultas (8.2.10). `load_gold("pool")` é recusado; `load_gold("test")` exige `unlock_test=True` (8.2.6).
- O teste não pode ser usado para escolher *prompts*, pesos, limiares ou exemplos de ICL, nem durante o desenvolvimento.

## 15. Divisões

Atribuição gananciosa e estratificada por (`message_label`, `needs_additional_review`), com componentes inteiras e tamanhos exatos 30/300/60/120. A semente fixa `20261019` controla só a ordem de desempate. Reprodutível: `assign_splits` volta a produzir exatamente `splits.json` (testado).

| Conjunto | *Hash* da vista de inferência (sha256, 16 car.) | *Hash* do gold (sha256, 16 car.) |
| --- | --- | --- |
| seed_stock | `49af07a51d918f0a` | `89a949b78d872b37` |
| pool | `11f602e23bfab9c6` | `9e79c6d62f8a71b7` |
| validation | `cc815e1bbc59310f` | `213b1e24de4ce137` |
| test | `47f7747ac603e66c` | `21a9b2aa559000a5` |

Os *hashes* completos e os dos ficheiros estão em `data/dataset/manifest.json`. `cases.jsonl`: `d92bc961…eda03eb`; `annotations.jsonl`: `5b4a9ec5…4a505d3e`.

## 16. Proveniência

Por registo: `annotation_status`, `authoring_batch` e `rationale`. Por dataset (este documento e o manifesto): autor = Claude Opus 5.5 via Claude Code; método = redação manual por IA, sem *templates*; data = 2026-10-19; versão `1.0.0-candidate`; protocolo 1.0.0. Não há registo de revisões humanas porque nenhuma ocorreu.

## 17. Limitações

- O autor das mensagens e o anotador são o **mesmo modelo de IA**: o estilo e as interpretações são correlacionados, e o «ground truth» reflete a leitura desse modelo das regras.
- Não há validação humana nem κ (§13).
- As prevalências são de desenho. As situações raras têm poucos casos (renegociação 1, plano em PER 1, disputa + plano 1, promessa condicionada 4), e RV8 tem 1 caso no teste.
- As contestações são em média mais longas do que as promessas (mediana de 200 vs 109 caracteres), o que é plausível, mas é um sinal superficial que o classificador pode explorar.
- O português de falante não nativo e os registos regionais são aproximações escritas por IA.
- Um só fornecedor e um só setor (equipamento para hotelaria/restauração); seis datas de *snapshot*.
- Não há verificação por *embeddings*; foi usado só Jaccard de 5-gramas.
- As GAP-01…GAP-08 são interpretações provisórias; a GAP-09 ficou fora do dataset.

## 18. Potenciais enviesamentos

Viés de estilo do modelo autor (formulações «limpas», mesmo nos registos informais); sobre-representação de casos de fronteira e de segurança face à realidade; nomes, setores e regiões escolhidos pelo autor sem amostragem; possível alinhamento entre o modelo autor e outros LLM, o que é mitigado por o classificador previsto ser de outra família (Llama). Não há dados demográficos de pessoas; os nomes próprios são fictícios e não são usados como atributos.

## 19. Utilizações permitidas

Investigação académica no âmbito do projeto TRAI (E1, E2, piloto, testes de segurança do agente) e reprodução dos resultados. **Não** usar para treinar ou avaliar sistemas de cobrança reais, nem para estimar prevalências reais, nem como prova de desempenho em produção. Os IBAN e NIF são fictícios e não devem ser usados para nenhum outro fim.

## 20. Reprodutibilidade

```powershell
uv sync --locked
uv run --locked python -m responsible_receivables_agent.dataset validate      # tudo
uv run --locked python -m responsible_receivables_agent.dataset stats         # distribuições
uv run --locked python -m responsible_receivables_agent.dataset check-splits  # divisões e leakage
uv run --locked python -m responsible_receivables_agent.dataset check-hashes  # manifesto
uv run --locked pytest -q tests/test_dataset.py
```

`build` reescreve `splits.json` e `manifest.json` a partir dos ficheiros-fonte. Só se usa numa **nova versão** do dataset, documentada em `DECISIONS.md`. Depois do congelamento (T04), qualquer alteração ao teste segue o procedimento de alteração controlada (protocolo 13.3).
