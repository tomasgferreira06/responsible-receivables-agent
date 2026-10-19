# Registo de Decisões Científicas e Técnicas

**Protocolo:** `docs/EXPERIMENT_PROTOCOL.md` v1.0.0 · **Criado em:** 2026-10-18 (T02).

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
- **Estado:** Adotada.

## D11 — Supervisão graduada para revisão adicional

- **Descrição:** o que o LLM gradua e o que não gradua.
- **Alternativas:** graduar também a aprovação de e-mails; tornar disputas obrigatórias; apenas revisão adicional discricionária.
- **Escolhida:** a aprovação externa é sempre obrigatória; MR1–MR3 obrigatórias e independentes do LLM (união monótona); RV1–RV4 e RV8 discricionárias (LLM). A referência `needs_additional_review` é «alguma regra RV dispara», com contexto além da classe.
- **Fundamentação:** responde à proposta («supervisão graduada na triagem, não na autorização»); disputas obrigatórias tornariam E2 trivial.
- **Consequências:** um produto real provavelmente tornaria as disputas obrigatórias (limitação); correlação classe→revisão elevada (diagnóstico `S_LBL`).
- **Impacto:** E2; T09, T18.
- **Estado:** Adotada.

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

As lacunas abaixo foram identificadas **pelo assistente de IA durante a redação do dataset (T03)**, não numa adjudicação humana. Em cada uma registou-se a interpretação **provisória** usada nas etiquetas. Não alteram o protocolo e têm de ser confirmadas ou corrigidas pelos anotadores humanos na T04, antes de qualquer congelamento. As GAP-01 a GAP-06 estão implementadas e verificadas em `dataset.expected_reasons`/`check_annotation`, até onde é possível verificá-las automaticamente.

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

## Registo de alterações ao protocolo

| Versão | Data | Gatilho | Alteração | Evidência (sem teste) | Hash antes → depois |
| --- | --- | --- | --- | --- | --- |
| 1.0.0 | 2026-10-18 | Criação (T02) | — | — | — |

## Registo *go/no-go* do piloto (T05)

Por preencher após o piloto, com os números da **validação** (nunca do teste).
