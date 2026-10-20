# Registo de Decisões Científicas e Técnicas

**Protocolo:** `docs/EXPERIMENT_PROTOCOL.md` v2.0.0 (D17; v1.0.0 em T02) · **Criado em:** 2026-10-18 (T02).

Convenções: **Estado** ∈ `Adotada` (em vigor), `Adotada — a validar` (pressuposto com validação experimental prevista), `Substituída`. Nenhuma decisão aqui é um resultado demonstrado: são escolhas ex ante com pressupostos explícitos. Não ficam decisões fundamentais em aberto por falta de validação externa; se o docente exigir alterações, aplica-se o procedimento da secção 13 do protocolo e regista-se na secção «Registo de alterações».

---

## D01 — Active ICL sem *fine-tuning*

- **Descrição:** como o feedback humano melhora o agente.
- **Alternativas:** (a) *fine-tuning*/classificador treinável; (b) *prompt engineering* manual; (c) ICL com memória de exemplos anotados.
- **Escolhida:** (c). Pesos do LLM inalterados; muda a memória de demonstrações.
- **Fundamentação:** a proposta V2 e as referências [2–4]; custo e prazo (entrega 5/11/2026); preserva a ligação direta entre anotação e comportamento.
- **Consequências:** o efeito de uma anotação depende da regra de recuperação (D08); não se generaliza a treino de parâmetros.
- **Impacto:** E1/E2 inteiros; O01 (baseline treinável) fica opcional.
- **Estado:** Adotada. Se o docente exigir um modelo treinável, promover O01 a essencial (nota em `IMPLEMENTATION_TASKS.md`).

## D02 — Cinco classes e regras de prioridade

- **Descrição:** taxonomia e etiqueta principal para mensagens com várias intenções.
- **Alternativas:** quatro classes (sem `OTHER_OR_UNCLEAR`); multirrótulo; prioridade por ordem de risco; prioridade por ordem temporal.
- **Escolhida:** cinco classes; etiqueta principal única por prioridade `ID ≻ PC ≻ PR ≻ PP`; intenções secundárias e *flags* guardadas à parte; contradição → `OTHER_OR_UNCLEAR`.
- **Fundamentação:** a ordem reflete a consequência de ignorar cada intenção (dívida contestada > cobrar quem já pagou > negociação perdida > promessa). Multirrótulo tornaria F1 e custos ambíguos com um teste de ≈ 120 itens.
- **Consequências:** perda de informação (limitações no protocolo 3.6); o LLM pode ser penalizado por acertar na intenção secundária.
- **Impacto:** alvo de E1; calibração de anotadores; T03.
- **Estado:** Adotada.

## D03 — Matrizes de custos

- **Descrição:** severidade dos erros de classificação (E1) e de encaminhamento (E2).
- **Alternativas:** custo uniforme 0/1; valores monetários estimados; matriz assimétrica normativa 0–10.
- **Escolhida:** matriz assimétrica normativa 5×5 (0–10), diagonal nula; custos de encaminhamento separados (FN 5–10, FP 1, TP/TN 0); violações executadas fora do custo (penalização de relatório 100).
- **Fundamentação:** não há dados empíricos de custo; escala *ex ante* evita ajustar custos aos resultados. Sensibilidade pré-registada (`uniform_01`, `symmetrized_mean`; FN constante em {3,5,10,20}) para detetar dependência da escolha. Evita duplicar penalizações (TP sem custo; bloqueios não contam como violação).
- **Consequências:** os valores são ordinais e discutíveis; conclusões só valem sob a escala declarada.
- **Impacto:** R(x), custo médio, custo de encaminhamento, classes críticas.
- **Estado:** Adotada — a validar (robustez às matrizes de sensibilidade).

## D04 — Definição de risco

- **Descrição:** $R(x)$ para o seletor.
- **Alternativas:** palavras-chave de classe; probabilidade verbalizada pelo LLM; custo esperado sob a distribuição de votos.
- **Escolhida:** $R(x)=\frac{1}{10}\sum_c q_c C[c,\hat y]$ com $q$ = frequência de votos suavizada (λ = 0,5).
- **Fundamentação:** não consulta etiquetas; é explicável; evita palavras-chave (enviesariam a comparação a favor da classe-alvo) e confiança verbalizada (não calibrada).
- **Consequências:** circularidade parcial com a matriz de avaliação (mitigada por métrica primária de *recall* e sensibilidade); viés para previsões `PAYMENT_PROMISE`, assumido e documentado.
- **Impacto:** RQ1 (ameaça de validade i).
- **Estado:** Adotada — a validar (ablação R vs U vs D).

## D05 — Definição de incerteza

- **Descrição:** $U(x)$.
- **Alternativas:** entropia de *logits* (indisponível em todos os fornecedores); confiança verbal; discordância entre votos amostrados; comité de prompts.
- **Escolhida:** entropia normalizada de $N=5$ votos a temperatura 0,7, mesmo prompt.
- **Fundamentação:** implementável com qualquer API; a proposta pede discordância entre execuções controladas; $N=5$ equilibra custo e resolução.
- **Consequências:** resolução baixa; não calibrada; custo ≈ 6 000 chamadas por corrida para UNCERTAINTY e RISK_AWARE.
- **Impacto:** orçamento computacional separado; contingência de subamostragem (M = 150).
- **Estado:** Adotada — a validar no piloto (custo e variabilidade dos votos).

## D06 — Estratégia de diversidade e normalização

- **Descrição:** $D(x)$ e como combinar componentes.
- **Alternativas:** distância mínima ao conjunto anotado; *k-center*; normalização *min-max*; percentil; valores brutos.
- **Escolhida:** $D=1-\max\cos$ face à memória; normalização por percentil na ronda; seleção gananciosa no lote; pesos iguais por omissão; ablação das 7 combinações; ajuste (exploratório) só na validação.
- **Fundamentação:** escalas diferentes tornam os pesos ininterpretáveis com valores brutos; percentis dão aos pesos o significado pretendido; empates resolvidos por *hash* comum a todas as estratégias.
- **Consequências:** o percentil depende do conjunto de candidatos da ronda; valores brutos também são registados.
- **Impacto:** RQ1; T15.
- **Estado:** Adotada.

## D07 — `SIMILARITY` como representatividade da *pool*

- **Descrição:** a estratégia «Similarity/Representativeness» da proposta.
- **Alternativas:** similaridade aos textos de teste (Margatina et al. [2]); *k-medoids*; *facility location* sobre a *pool*.
- **Escolhida:** *facility location* guloso sobre a *pool* (cobertura), sem teste nem etiquetas.
- **Fundamentação:** na implantação real não se conhecem as mensagens futuras; usar textos de teste na seleção contaminaria a comparação.
- **Consequências:** não replica exatamente a variante de [2]; o resultado não se estende a ela.
- **Impacto:** RQ1; T13.
- **Estado:** Adotada.

## D08 — Regras de recuperação ICL

- **Descrição:** que demonstrações entram no prompt.
- **Alternativas:** aleatórias; balanceadas por classe; vizinhos mais próximos por embedding; fixas.
- **Escolhida:** $k=6$ vizinhos mais próximos (cosseno) da memória, ordem crescente de similaridade, desempate por `example_id`; igual em todas as estratégias, S1 e S2. *Encoder* fixado em T12 antes de qualquer corrida.
- **Fundamentação:** separa seleção de recuperação [3]; mantém o contexto comparável; vizinhos mais próximos são a prática comum.
- **Consequências:** interação entre `SIMILARITY` e recuperação (mesmo *encoder*), reconhecida como ameaça; o *encoder* é um hiperparâmetro não ajustado no teste.
- **Impacto:** E1, E2; T12.
- **Estado:** Adotada — a validar (sensibilidade a $k$ na validação, se o custo o permitir).

## D09 — Orçamento de anotações

- **Descrição:** dimensão e ritmo das anotações.
- **Alternativas:** 20/30/40/60 anotações; lotes de 5/10/20.
- **Escolhida:** $n_0=24$ (de um *seed stock* de 30), $B=40$ em 4 rondas de 10, avaliação em $\{0,10,20,30,40\}$.
- **Fundamentação:** valores iniciais da proposta; 4 pontos de curva a custo viável; lote de 10 deixa a diversidade atuar.
- **Consequências:** o efeito de 40 anotações num prompt com $k=6$ pode ser pequeno (ver D13 e efeito teto).
- **Impacto:** E1, E2; custos.
- **Estado:** Adotada — a validar no piloto.

## D10 — Separação dos datasets

- **Descrição:** seed, pool, validação e teste.
- **Alternativas:** divisão aleatória por linha; por cliente; por componentes conexos cliente/cenário/família.
- **Escolhida:** componentes conexos; tamanhos 30 / 300 / 60 / 120; mínimos no teste (≥ 12 por classe; ≥ 40 críticos); deduplicação (exata e quase); etiquetas isoladas; duplo anotador em validação e teste; *hashes* e imutabilidade.
- **Fundamentação:** a divisão por linha causa fugas por paráfrase da mesma família; validação separada evita usar o teste para afinar (pesos, limiares, piloto).
- **Consequências:** exige gerador com identificadores de cenário/família (T03); validação de 60 itens é pequena (limitação).
- **Impacto:** todas as experiências; T03/T04.
- **Estado:** Adotada nos tamanhos, mínimos, deduplicação e isolamento. A unidade de divisão passou a ser o cliente (`customer_id`) por D17.

## D11 — Supervisão graduada para revisão adicional

- **Descrição:** o que o LLM gradua e o que não gradua.
- **Alternativas:** graduar também a aprovação de e-mails; tornar disputas obrigatórias; apenas revisão adicional discricionária.
- **Escolhida:** a aprovação externa é sempre obrigatória; MR1–MR3 obrigatórias e independentes do LLM (união monótona); RV1–RV4 e RV8 discricionárias (LLM). A referência `needs_additional_review` é «alguma regra RV dispara», com contexto além da classe.
- **Fundamentação:** responde à proposta («supervisão graduada na triagem, não na autorização»); disputas obrigatórias tornariam E2 trivial.
- **Consequências:** um produto real provavelmente tornaria as disputas obrigatórias (limitação); correlação classe→revisão elevada (diagnóstico `S_LBL`).
- **Impacto:** E2; T09, T18.
- **Estado:** Adotada. Desde 2.0.0 (D17) as discricionárias são RV1–RV3 e RV8 (RV4 retirada).

## D12 — Oráculo simulado e referência de anotação

- **Descrição:** quem responde às consultas de anotação.
- **Alternativas:** humano real; oráculo com ruído; oráculo simulado a partir de etiquetas validadas.
- **Escolhida:** oráculo simulado perfeito, só para consultas legítimas após a seleção; anotação humana em CLI mantida como modo alternativo (T16); ruído (O02) opcional.
- **Fundamentação:** repetibilidade e custo; a proposta já assume esta limitação.
- **Consequências:** sem erro, atraso ou fadiga humana; não equivale a um estudo com utilizadores.
- **Impacto:** E1, E2; secção de limitações do artigo.
- **Estado:** Adotada.

## D13 — Estratégia estatística

- **Descrição:** inferência com amostras pequenas.
- **Alternativas:** testes de significância clássicos; McNemar; *bootstrap* por itens; *bootstrap* por clusters.
- **Escolhida:** *bootstrap* pareado por clusters (10 000) para IC 95 % **não ajustados**; valores-p por teste de aleatorização com inversão de sinal ao nível do cluster (10 000), unilateral, com Holm sobre os valores-p das famílias confirmatórias (secção 12.3); 5 sementes (até 10 se barato), efeito mínimo de interesse 0,05, categorias de interpretação (suportado/parcial/equivalente/inferior/inconclusivo), sensibilidade às matrizes.
- **Fundamentação:** itens da mesma família não são independentes; sem alegar potência estatística.
- **Consequências:** IC largos; muitos resultados serão «inconclusivos» e serão reportados como tal.
- **Impacto:** T20.
- **Estado:** Adotada.

## D14 — Critérios de paragem

- **Descrição:** quando uma corrida termina ou se aborta.
- **Alternativas:** paragem por plateau de desempenho; apenas por orçamento.
- **Escolhida:** orçamento ou pool esgotados; limite de custo (1,5× a estimativa); respostas inválidas > 10 % numa ronda; falha anti-*leakage*; **nunca por desempenho**.
- **Fundamentação:** parar por desempenho exigiria olhar para o teste (*peeking*) e tornaria curvas incomparáveis.
- **Consequências:** pode gastar-se orçamento sem ganho; aceitável.
- **Impacto:** T16, T17.
- **Estado:** Adotada.

## D15 — Controlo de comparabilidade de E2 (S2 por fonte)

- **Descrição:** que memória usa S2.
- **Alternativas:** só RISK_AWARE; todas as estratégias de E1.
- **Escolhida:** S2 principal = RISK_AWARE; S2[RANDOM/UNCERTAINTY/SIMILARITY] como controlos; S1 usa só a memória inicial.
- **Fundamentação:** isola o efeito de «anotar mais» do de «selecionar ativamente»; evita superioridade por construção.
- **Consequências:** mais condições a avaliar (custo ≈ 15 000 chamadas de votos).
- **Impacto:** E2; T18.
- **Estado:** Adotada.

## D16 — Dataset estático (*dataset-first*) em vez de gerador programático

- **Data:** 2026-10-19 (T03).
- **Descrição:** forma de obter as 510 mensagens anotadas exigidas por D10 e pelo protocolo 8.1.
- **Alternativas:** (a) gerador determinístico por semente, com *templates* (plano original da T03); (b) LLM a gerar mensagens durante as experiências; (c) dataset estático, redigido uma única vez, versionado e validado por código.
- **Escolhida:** (c). A abordagem de geração programática foi **abandonada**: o código e os resultados dessa fase foram apagados de propósito e não são reutilizados. As 510 mensagens foram redigidas uma a uma pelo assistente de IA (Claude Opus 5.5, `claude-opus-5-5`, no Claude Code) e não por um programa que preencha *templates*. São conteúdo **sintético gerado por IA**, não anotações humanas independentes. O código do repositório (`dataset.py`) só lê, valida, divide e calcula *hashes*.
- **Fundamentação:** o gerador não é a contribuição científica do projeto. Um dataset fixo é mais fácil de rever linha a linha, elimina a variabilidade do gerador e permite auditar cada etiqueta.
- **Correspondência com o protocolo (sem o alterar):** 8.2.8/8.2.9 pedem «gerador/versão/semente». Num dataset estático, isso corresponde a: origem = redação por IA, modelo identificado, sem semente de geração. A única semente é a da divisão (`SPLIT_SEED = 20261019`), que só controla a atribuição de componentes aos conjuntos. Em 13.2.1, «regenerar» passa a «rever ou reescrever mensagens com nova versão do dataset». Na ameaça de validade 2.1 (iii), «gerador comum» passa a «autor comum (o mesmo modelo de IA) para todas as divisões». O modelo autor é de família diferente do classificador previsto (Llama), como recomenda 8.2.8.
- **Regras próprias do dataset (mais estritas do que o protocolo):** `family_id` agrupa formulações com origem partilhada real. Inclui pares de contraste deliberados e mensagens de clientes diferentes com Jaccard de 5-gramas ≥ 0,35 (auditoria automática `family_audit`). As restantes famílias são singulares e isso é declarado, não escondido. Datas de vencimento < *snapshot* ≤ receção. Valores monetários guardados como texto decimal exato. Menções «dia da semana + dia do mês» verificadas contra o calendário.
- **Consequências:** a validação humana dupla (protocolo 8.2.7) **continua por fazer** e passa a ser a T04. Até lá, as divisões são **candidatas** e o teste **não está congelado**. A verificação por *embeddings* (cosseno 0,92) não foi feita, por não haver *encoder* local; só a de Jaccard.
- **Impacto:** T03 (substituída), T04 (redefinida), T05–T18 passam a depender do dataset estático; D10 mantém-se nos tamanhos e nas regras de divisão.
- **Estado:** Adotada quanto à abordagem (dataset estático redigido diretamente, sem gerador). O dataset 1.0.0-candidate, o seu esquema e as «regras próprias do dataset» acima (`family_id`, *snapshot*, auditoria de famílias) foram **substituídos por D17**.

## D17 — Simplificação do dataset e do protocolo (v2.0.0)

- **Data:** 2026-10-19.
- **Gatilho (13.3 a):** objetivo — o dataset candidato 1.0.0 e o seu código (≈ 760 linhas, 12 campos por caso, 13 por anotação, famílias/cenários, perfis de política e factos RV por registo) tornaram-se desproporcionados face ao âmbito, ao prazo (5/11/2026) e ao que RQ1/RQ2 realmente medem. Nenhum resultado de teste existe nem foi consultado (o teste nunca foi desbloqueado), pelo que 13.3 (b)–(c) são satisfeitos.
- **Descrição:** reconstrução de raiz do dataset estático com um esquema mínimo e simplificação das regras de revisão e da política de execução.
- **Alternativas:** (a) manter o dataset 1.0.0 e só remover campos (as etiquetas dependiam de RV4, `snapshot_date` e famílias, que deixariam de ser verificáveis); (b) gerador ou *templates* (abandonados em D16); (c) dataset novo, escrito diretamente, com esquema mínimo.
- **Escolhida:** (c). Alterações:
  1. **Casos:** só `case_id`, `customer_id`, `invoice_id`, `pending_amount_eur`, `due_date`, `received_date`, `message_text`. Saem `broken_promises_count`, `snapshot_date`, `received_at` (passa a `received_date`, só data), `message_subject`, `scenario_id`, `family_id`.
  2. **Anotações:** só `case_id`, `message_label`, `needs_additional_review`, `review_reasons`. Saem `secondary_intents`, `risk_flags`, `action_policy`, `rv_facts`, `situation`, `rationale`, `needs_adjudication`, `annotation_status`, `authoring_batch`. A proveniência passa a ser documentada uma vez (`DATASET_CARD.md`, `manifest.json`); casos ambíguos vão para `adjudications.jsonl`.
  3. **RV4 retirada** (dependia do histórico de promessas). RV1–RV3 e RV5–RV8 mantêm os identificadores (sem renumeração). RV2 e RV3 ganham critérios objetivos no próprio protocolo (incorporando GAP-02 e GAP-05); a fronteira PP/PR passa a ser o limite explícito de 30 dias após `received_date` (incorpora GAP-01).
  4. **`action_policy`:** de quatro perfis calculados a partir de `risk_flags` para dois perfis explícitos (`AP_MANDATORY_REVIEW` se MR1–MR3 disparam; `AP_STANDARD` caso contrário), decididos pelo *policy gate* em execução a partir do texto bruto, nunca a partir das anotações. `AP_SECURITY_LOCKDOWN` e `AP_REVIEW_GATED` tinham as mesmas permissões; `AP_CLARIFY_FIRST` dependia de *flags* que só o LLM pode inferir. Saem `risk_flags`.
  5. **Divisão:** unidade = cliente (as faturas pertencem a um só cliente), estratificação gananciosa por classe com semente fixa; quase-duplicados verificados entre conjuntos (Jaccard ≥ 0,80).
  6. **Exemplos de referência:** removidos `secondary_intents`, `risk_flags` e `action_policy`; REF15 (RV4) retirado; REF16 (promessa + instrução ao agente) acrescentado.
- **Preservado sem alteração:** RQ1, RQ2, H0/H1, as cinco classes e a sua prioridade, matriz de custos e classes críticas, custos de encaminhamento, estratégias e Risk-Aware Sampling, orçamentos (n₀ = 24, B = 40, rondas de 10), tamanhos dos conjuntos (30/300/60/120) e mínimos do teste, métricas primárias (CR, CER), plano estatístico, invariantes de segurança e a separação entre seleção para anotação e recuperação ICL.
- **Alterações que afetam as experiências:** (i) **E2:** a referência `needs_additional_review` deixa de incluir o histórico de incumprimento; o subconjunto discricionário passa a ser RV1–RV3 e RV8; (ii) **TSR (E2):** as ações permitidas vêm de dois perfis em vez de quatro; (iii) **inferência estatística:** os clusters do *bootstrap*/aleatorização passam a ser os clientes; (iv) **E1:** nenhuma alteração ao alvo nem às métricas; o contexto no prompt passa a ser o esquema mínimo. Nenhum resultado anterior existe, pelo que não há resultados a invalidar.
- **Consequências:** o histórico de promessas deixa de ser estudado (limitação, secção 16); os detetores MR1–MR3 (T09) têm de ser avaliados contra a referência, incluindo armadilhas lexicais presentes no dataset. Validação humana independente continua pendente (T04); o teste não está congelado.
- **Impacto:** protocolo 1.0.0 → 2.0.0; dataset 1.0.0-candidate → 2.0.0-candidate; T03 (refeita), T04, T09, T12, T16–T18.
- **Estado:** Adotada.

## D18 — Correções após a auditoria por IA, RV3 para adiamentos indeterminados e congelamento do dataset (v2.1.0)

- **Data:** 2026-10-20.
- **Gatilho (13.3 a):** lacuna do guia, identificada na auditoria `docs/audits/DATASET_AI_REVIEW_V2.md` (revisão cega das 510 mensagens por Claude Opus 5.5). O teste nunca foi desbloqueado nem usado para experiências; nenhum modelo foi executado. As etiquetas do teste foram lidas só para auditar o dataset ainda não congelado.
- **Decisões do responsável do projeto** (revisão humana dos casos indicados, não dupla anotação):
  1. **RV2, critério do valor (esclarecimento, sem mudança de etiquetas):** quando o cliente identifica a fatura do caso como paga e indica data e meio («paguei a FT-632 a 5 de outubro, por MB Way»), a alegação é completa: `PAYMENT_CLAIM` sem RV2. Resolve a contradição entre a nota histórica de GAP-02 («"a fatura" sozinha não basta») e o protocolo 4.2. Confirmado em RRA-0288 e RRA-0440; abrange também RRA-0141, RRA-0213 e RRA-0343.
  2. **RV3 alargada (alteração normativa):** dispara também quando um pedido de plano adia o pagamento (total ou do remanescente) para um momento **indeterminado**, sem data nem prazo («peço que esperem», «quando chegar o donativo»). Prazos relativos («daqui a uma semana», «daqui a um mês», «60 dias após o visto») não disparam por este critério; medem-se pelo limiar dos 6 meses. Fronteira 3.3: pedido de espera sem data → `PAYMENT_PLAN_REQUEST` (sem pedido → `OTHER_OR_UNCLEAR`, como antes).
  3. **Etiquetas alteradas:** RRA-0347 (pool) `PAYMENT_PLAN_REQUEST` + RV3 (antes sem revisão); RRA-0264 (pool) `PAYMENT_CLAIM` + RV3 (antes sem revisão); RRA-0351 (pool) `OTHER_OR_UNCLEAR` → `PAYMENT_CLAIM` + RV2; RRA-0490 (teste) `OTHER_OR_UNCLEAR` → `INVOICE_DISPUTE` + RV1. RRA-0228 mantém-se sem RV3 (prazo relativo). Registos em `adjudications.jsonl`.
  4. **Congelamento:** o dataset passa a 2.1.0 e o teste fica congelado (`test_frozen: true`). `splits.json` mantém-se **exatamente** como estava. Recalcular a divisão com as etiquetas corrigidas trocaria 39 dos 120 casos de teste, por isso a divisão deixa de ser re-derivada das etiquetas e fica protegida pelo *hash* no manifesto. `build` deixa de reescrever `splits.json` (`dataset.FROZEN`).
- **Alternativas:** (a) recalcular a divisão (rejeitada: altera o teste depois de as suas etiquetas terem sido lidas na auditoria); (b) adiar o congelamento até à dupla anotação humana com κ (rejeitada pelo responsável do projeto).
- **Desvio declarado ao protocolo 8.2(7):** o teste é congelado **sem** dupla anotação humana nem κ de Cohen ≥ 0,70. A validação consistiu em: auditoria cega por IA, do mesmo modelo autor (concordância IA–IA de 99,2 % na classe, que não é validação independente), e decisão humana do responsável sobre os casos divergentes ou de fronteira acima. As restantes adjudicações provisórias do autor ficam congeladas tal como estão. Limitação a reportar nos resultados e na dissertação.
- **Impacto nas experiências:** E1 — 2 alterações de classe (1 no teste: +1 `INVOICE_DISPUTE`, −1 `OTHER_OR_UNCLEAR`). E2 — 4 casos passam a precisar de revisão (1 no teste). A estratificação classe × revisão por conjunto deixa de ser exatamente a do algoritmo; os mínimos do teste continuam cumpridos (`dataset check`).
- **Impacto:** protocolo 2.0.0 → 2.1.0; dataset 2.0.0-candidate → 2.1.0 (congelado); T04 (fechada com este desvio), T05 em diante.
- **Estado:** Adotada.

---

## Divergências e esclarecimentos face aos documentos de partida

| Origem | Divergência | Tratamento |
| --- | --- | --- |
| `IMPLEMENTATION_TASKS.md` refere `PROJECT_PROPOSAL_V2.md` | O ficheiro existente chama-se `PROJECT_PROPOSAL.md` | Considerado o mesmo documento; sem alterações. |
| T02: «quatro ou cinco classes a definir» | — | Cinco (D02). |
| Proposta: «*recall* dos casos críticos/contestações» | «Críticos» não estava definido | Classes com custo máximo de erro ≥ 7: `PAYMENT_CLAIM` e `INVOICE_DISPUTE` (secção 5); `INVOICE_DISPUTE` também é reportado isoladamente. |
| Proposta: «Similarity/Representativeness» | Pode significar similaridade ao teste | D07. |
| Proposta: curvas «com o mesmo orçamento de revisões» | Os votos geram poucos níveis de pontuação | Desempate por R(x) e *hash* (protocolo 10.3). |
| Proposta, questão 5: data da defesa | Aparente lapso no enunciado | Não afeta o protocolo; tratar em T22. |

## Pendente do docente (não bloqueia a implementação)

As cinco questões da secção 8 da proposta continuam por validar. Se alguma alterar a metodologia (aprendiz treinável, experiência de *fairness*, etc.), segue-se o procedimento de alteração (protocolo 13.3).

## Lacunas de anotação

Lacunas descobertas na adjudicação (protocolo 3.7) registam-se aqui com ID `GAP-nn`.

As lacunas abaixo foram identificadas **pelo assistente de IA durante a redação do dataset (T03)**, não numa adjudicação humana. Em cada uma registou-se a interpretação **provisória** usada nas etiquetas. Não alteram o protocolo e têm de ser confirmadas ou corrigidas pelos anotadores humanos na T04, antes de qualquer congelamento. As GAP-01 a GAP-06 foram implementadas em `dataset.expected_reasons`/`check_annotation` no código 1.0.0, que foi removido em D17; o estado atual de cada lacuna está na tabela seguinte.

| ID | Lacuna | Interpretação provisória usada |
| --- | --- | --- |
| GAP-01 | Todas as faturas do dataset estão vencidas, por isso «data posterior ao vencimento» (fronteira 3.3) não basta para separar PP de PR. | **PP**: compromisso firme de pagar o valor numa data próxima (até cerca de 3 semanas), sem pedir aceitação nem invocar incapacidade. **PR**: pede ou propõe prestações, extensão ou nova data; declara que só consegue pagar mais tarde (incapacidade, financiamento, orçamento); ou fixa unilateralmente uma data distante. |
| GAP-02 | Critérios de completude de RV2. | Valor explícito (número, ou «totalidade/valor total»; «a fatura» sozinha não basta, cf. REF03); data identificável («ontem», «dia 6», «sexta passada»; não contam «semana passada» nem «há uns dias»); meio ou referência. Anexos não contam, porque o agente não os lê. Terceiro pagador = pagamento feito por, ou para, uma entidade diferente (conta pessoal de sócio ou familiar, empresa-mãe, entidade pública, conta de destino não confirmada). Quem só transmite a informação (p. ex. o contabilista) não é terceiro. Valor alegado = soma do que foi alegadamente pago para este documento. |
| GAP-03 | Pedidos sobre o documento: contestação ou pedido neutro? | Erro de conteúdo imputado ao fornecedor que condiciona o pagamento (NIF, entidade, referência de compromisso, vencimento, IVA, mesmo a favor do cliente) → INVOICE_DISPUTE. Reenvio, cópia, guia, relatório, canal ou formato, sem condicionar o pagamento → OTHER_OR_UNCLEAR. Compensação com um crédito alegado → INVOICE_DISPUTE (recusa da obrigação na parte compensada). |
| GAP-04 | Mensagens que falam de várias faturas. | `message_label` e `secondary_intents` consideram só as intenções sobre o documento do caso (`invoice_id`). As *flags* de risco (RV5–RV7) aplicam-se ao texto inteiro, porque as regras obrigatórias atuam sobre o texto bruto (4.2). |
| GAP-05 | Medida do «prazo total» de RV3. | `plan_total_months` = meses entre a mensagem e o último pagamento proposto, arredondado; é usado só para o limiar > 6. Os casos de fronteira (≈ 6 meses) foram evitados ou reescritos. |
| GAP-06 | Interação das regras com a contradição e com intenções secundárias. | RV1 aplica-se sempre que haja contestação, incluindo numa contradição. RV2, RV3 e RV4 não se aplicam a intenções que fazem parte de uma contradição (como em REF12, que só tem RV8). RV3/RV4 aplicam-se a PR/PP principal ou secundária. |
| GAP-07 | Auto-correções («ou melhor», «afinal»). | Não foram usadas no dataset, para não alargar a regra de contradição. As contradições incluídas mantêm as duas afirmações (também quando vêm de fontes diferentes do cliente, p. ex. «o sócio diz que…»). |
| GAP-08 | Quando usar `insufficient_information`. | OU sem intenção nem pedido acionável: vago, ausência automática, reencaminhamento, não relacionado, dúvida sobre se pagou. Pedidos concretos de documento ou esclarecimento não a recebem (cf. REF11). |
| GAP-09 | Cliente que relata uma possível fraude de IBAN (p. ex. «recebi um email vosso com IBAN novo, é verdade?»). | **Sem regra suficiente**: RV5 exige um *pedido* de alteração, mas o risco é elevado. Seguindo 3.7, estes casos foram **excluídos** do dataset em vez de etiquetados arbitrariamente. Precisa de decisão (eventual nova versão do protocolo). |

**Estado das lacunas no protocolo 2.0.0 (D17)** — a tabela acima é histórica (dataset 1.0.0):

| ID | Estado em 2.0.0 |
| --- | --- |
| GAP-01 | Incorporada (3.1, 3.3): PP exige data até 30 dias após `received_date` e sem pedido de aceitação. |
| GAP-02 | Incorporada (4.2, critérios de RV2). Esclarecida em 2.1.0 (D18): identificar a fatura do caso como paga conta como valor total; a nota histórica «"a fatura" sozinha não basta» deixa de se aplicar quando a mensagem identifica a fatura. |
| GAP-03 | Incorporada (3.4, fronteira). |
| GAP-04 | Incorporada (secção 3, unidade anotada). |
| GAP-05 | Incorporada (4.2, RV3: prazo desde `received_date`). |
| GAP-06 | Incorporada (4.2), sem a parte de RV4, que foi retirada. |
| GAP-07 | Mantida: o dataset 2.0.0 continua sem auto-correções; um pagamento falhado explicado na mensagem não é contradição (3.6, regra 3). |
| GAP-08 | Obsoleta: `insufficient_information` deixou de existir. |
| GAP-09 | **Continua aberta**; os casos continuam excluídos do dataset 2.0.0 e 2.1.0. |
| GAP-10 | Nova (auditoria de 2026-10-20): pedido de espera ou adiamento sem data nem prazo. Resolvida em 2.1.0 (D18): `PAYMENT_PLAN_REQUEST` com RV3. |

Os casos ambíguos estão em `data/dataset/adjudications.jsonl`. Os marcados «Decisão do responsável do projeto (D18)» foram decididos por um humano; os restantes são decisões provisórias do autor (IA), congeladas tal como estão em 2.1.0.

## Registo de alterações ao protocolo

| Versão | Data | Gatilho | Alteração | Evidência (sem teste) | Hash antes → depois |
| --- | --- | --- | --- | --- | --- |
| 1.0.0 | 2026-10-18 | Criação (T02) | — | — | — |
| 2.0.0 | 2026-10-19 | Complexidade desproporcionada do dataset candidato (D17) | RV4 retirada; `risk_flags` retiradas; `action_policy` com 2 perfis decididos pelo *gate*; critérios objetivos de RV2/RV3 e fronteira PP/PR (30 dias); unidade de divisão = cliente; esquema mínimo do dataset; REF15 → REF16 | Revisão do dataset 1.0.0 (sem piloto, sem validação, sem teste) | `protocol.json` 54200902… → c1ed7180… |
| 2.1.0 | 2026-10-20 | Lacuna do guia identificada na auditoria por IA (D18) | RV3 também para adiamento indeterminado (sem data nem prazo); fronteira 3.3 para pedido de espera sem data; critério de valor de RV2 esclarecido (fatura identificada = totalidade) | Casos da *pool* (RRA-0347, RRA-0264) e auditoria; sem piloto; teste nunca desbloqueado | `protocol.json` c1ed7180… → d05aa9c9… |

## Registo *go/no-go* do piloto (T05)

Por preencher após o piloto, com os números da **validação** (nunca do teste).
