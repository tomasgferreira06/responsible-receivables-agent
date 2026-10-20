# Dataset Card — Responsible Receivables Agent (v2.1.0, congelado)

**Protocolo:** `docs/EXPERIMENT_PROTOCOL.md` v2.1.0 · **Decisões:** `docs/DECISIONS.md` D16, D17, D18 · **Criado em:** 2026-10-19 (T03, refeita) · **Congelado em:** 2026-10-20 (D18)
**Estado:** **congelado** (`manifest.json → test_frozen: true`). Auditado por IA (`docs/audits/DATASET_AI_REVIEW_V2.md`) e com os casos divergentes ou de fronteira decididos pelo responsável do projeto. **Não** houve dupla anotação humana nem κ de Cohen (desvio declarado ao protocolo 8.2(7), D18).

**Alterações face a 2.0.0-candidate (D18):** RRA-0347 e RRA-0264 passam a ter RV3 (adiamento indeterminado); RRA-0351 passa a `PAYMENT_CLAIM` + RV2; RRA-0490 (teste) passa a `INVOICE_DISPUTE` + RV1. Mensagens e `splits.json` inalterados.

Substitui integralmente o dataset 1.0.0-candidate (mesmo número de mensagens, esquema e conteúdo novos). Nada do dataset anterior nem do gerador abandonado foi reutilizado.

## 1. Objetivo

Dados para as duas experiências do protocolo:

- **E1 (RQ1):** classificar a mensagem numa de cinco classes (`message_label`), com memória ICL obtida por seleção ativa;
- **E2 (RQ2):** decidir se o caso precisa de revisão humana adicional (`needs_additional_review`), com as razões (`review_reasons`).

O dataset é **fixo**: não se geram mensagens durante as experiências.

## 2. Domínio, língua e natureza sintética

Cobranças de um fornecedor fictício (manutenção, equipamentos, consumíveis e serviços) a PME e instituições portuguesas: restauração, hotelaria, saúde, construção, comércio, associações, IPSS, entidades públicas. Mensagens em **português de Portugal**, com registos variados: administrativo formal, coloquial, SMS sem acentos nem pontuação, mensagens muito curtas («Paguei.», «??»), respostas automáticas, citações e reencaminhamentos, mistura de inglês ou italiano e português de falante não nativo.

**Tudo é fictício**: clientes, pessoas, faturas, NIF (`500 000 00x`), IBAN (`PT50 0000 …`, marcados como fictícios), telefones e endereços (`*.example`). As proporções de classes e de revisão são **escolhas de desenho**, não estimativas de prevalência real.

## 3. Processo real de criação

1. **Redação direta.** As 510 mensagens foram escritas uma a uma pelo assistente de IA **Claude Opus 5.5** (`claude-opus-5-5`, no Claude Code), a 2026-10-19, em 10 lotes organizados por cliente. **Não foi usado gerador, *template*, motor de cenários nem preenchimento automático de texto.**
2. **Formato de trabalho.** A redação foi feita num formato compacto (uma linha por mensagem com cliente, fatura, montante, datas, classe, razões e texto). Um script descartável, fora do repositório, **só reformatou** esses registos: numerou os `case_id` por ordem, escreveu `needs_additional_review = bool(review_reasons)` e separou entradas e etiquetas nos dois ficheiros. Não alterou nenhum texto nem nenhuma etiqueta.
3. **Etiquetas propostas pelo mesmo assistente**, aplicando as regras do protocolo 2.0.0 (secções 3–4). Os 14 casos que o autor considerou genuinamente ambíguos foram registados em `adjudications.jsonl`, com a decisão provisória e a regra usada.
4. **Controlo de qualidade durante a redação** (verificação automática pelo autor, não validação): coerência dia da semana/data face a `received_date`, mesma fatura → mesmo cliente/montante/vencimento, vencimento anterior à receção e pesquisa de formulações repetidas. Os pares com Jaccard de 5-gramas ≥ 0,35 foram reescritos; o valor máximo final entre quaisquer duas mensagens é < 0,40.
5. **Auditoria e decisões finais (2026-10-20, D18):** revisão cega das 510 mensagens por Claude Opus 5.5, o mesmo modelo autor (concordância IA–IA de 99,2 % na classe; não é validação independente). O responsável do projeto decidiu os casos divergentes ou de fronteira (RRA-0228, 0264, 0288, 0347, 0351, 0440, 0490). `adjudications.jsonl` tem 19 registos: os marcados «Decisão do responsável do projeto» são humanos; os restantes ficam como decisões provisórias do autor, congeladas.
6. **Dupla anotação humana com κ:** **não realizada** (desvio declarado, D18).

O facto de o mesmo modelo ter escrito, etiquetado e auditado **não** equivale a anotação independente. Passar nos testes automáticos significa coerência interna com as regras, **não** que as etiquetas estejam cientificamente validadas.

## 4. Esquema

Ficheiros em `data/dataset/`, UTF-8, uma linha JSON por caso.

**`cases.jsonl`** — entradas; é a única coisa que o LLM e o seletor veem:

| Campo | Tipo | Função |
| --- | --- | --- |
| `case_id` | str `RRA-0001`…`RRA-0510` | identificação única |
| `customer_id` | str `CLI-NNN` | cliente; unidade de divisão (anti-*leakage*) |
| `invoice_id` | str `FT-NNN` | fatura; pertence a um só cliente |
| `pending_amount_eur` | str decimal exato (`"2000.00"`) | contexto financeiro (RV2, RV3) |
| `due_date` | str ISO | vencimento; sempre anterior a `received_date` |
| `received_date` | str ISO | data da mensagem; referência de «ontem», «sexta», «30 dias» |
| `message_text` | str | texto a classificar |

```json
{"case_id": "RRA-0001", "customer_id": "CLI-001", "invoice_id": "FT-101", "pending_amount_eur": "2000.00", "due_date": "2026-09-30", "received_date": "2026-10-12", "message_text": "Já pagámos 800 €, mas o restante valor da fatura está errado."}
```

**`annotations.jsonl`** — referência (nunca entra no prompt de inferência):

| Campo | Tipo | Função |
| --- | --- | --- |
| `case_id` | str | ligação ao caso |
| `message_label` | uma das 5 classes | alvo de E1 |
| `needs_additional_review` | bool, sempre `= bool(review_reasons)` | alvo de E2 |
| `review_reasons` | lista ordenada ⊆ {RV1, RV2, RV3, RV5, RV6, RV7, RV8} | razões; RV4 não existe; RV3 inclui adiamento indeterminado desde 2.1.0 |

```json
{"case_id": "RRA-0001", "message_label": "INVOICE_DISPUTE", "needs_additional_review": true, "review_reasons": ["RV1", "RV2"]}
```

(RV1 pela contestação; RV2 porque a alegação de 800 € não tem data nem meio.)

**`adjudications.jsonl`** — `case_id`, `issue`, `decision`, só para os casos problemáticos. Contém informação sobre as etiquetas: aplica-se a mesma restrição de acesso que a `annotations.jsonl`.

**`splits.json`** — semente e lista de `case_id` por conjunto. **`manifest.json`** — versões, estado, *hashes* SHA-256 de todos os ficheiros e de `protocol.json`, contagens.

## 5. Dimensão e distribuições

510 casos, 468 clientes (426 com 1 mensagem, 42 com 2), 494 faturas (16 com duas mensagens: seguimento da mesma fatura). Montantes de 75 € a 32 500 € (mediana 1 460 €; 78 casos ≥ 5 000 €). Receção entre 2026-08-24 e 2026-10-19. Mensagens de 1 a 64 palavras (mediana 23).

**Classe × revisão (todo o dataset):**

| Classe | Com revisão | Sem revisão | Total |
| --- | ---: | ---: | ---: |
| `PAYMENT_PROMISE` | 7 | 84 | 91 |
| `PAYMENT_CLAIM` | 49 | 63 | 112 |
| `PAYMENT_PLAN_REQUEST` | 45 | 45 | 90 |
| `INVOICE_DISPUTE` | 110 | 0 | 110 |
| `OTHER_OR_UNCLEAR` | 43 | 64 | 107 |
| **Total** | **254** | **256** | **510** |

**Razões:** RV1 113 · RV2 44 · RV3 43 · RV5 14 · RV6 19 · RV7 23 · RV8 16 (18 casos com mais de uma razão). Casos com regra obrigatória (RV5–RV7): 56; subconjunto discricionário: 454, dos quais 198 com revisão.

**Por conjunto** (classe: com revisão / total):

| Conjunto | Casos | PP | PC | PR | ID | OU | Revisão | Discricionários c/ revisão |
| --- | ---: | --- | --- | --- | --- | --- | ---: | ---: |
| `seed_stock` | 30 | 1/6 | 3/6 | 2/5 | 6/6 | 3/7 | 15 | 10 |
| `pool` | 300 | 3/52 | 30/68 | 27/52 | 65/65 | 25/63 | 150 | 113 |
| `validation` | 60 | 1/11 | 5/12 | 5/11 | 13/13 | 5/13 | 29 | 23 |
| `test` | 120 | 2/22 | 11/26 | 11/22 | 26/26 | 10/24 | 60 | 52 |

Mínimos do teste: ≥ 12 por classe (mínimo observado 22) e ≥ 40 críticos `PAYMENT_CLAIM` + `INVOICE_DISPUTE` (observado 52). Os números exatos estão em `manifest.json → counts`.

**Porque a E2 não é trivial.** `needs_additional_review` não é função da classe: há alegações com e sem revisão (RV2: incompleta, inconsistente, terceiro pagador ou destino não confirmado), planos com e sem revisão (RV3: ≥ 5 000 €, > 6 meses ou adiamento sem data), `OTHER_OR_UNCLEAR` com e sem revisão (RV8 e regras obrigatórias vs. pedidos de documentos, respostas vagas, respostas automáticas) e promessas com revisão apenas por regras obrigatórias. A maioria dos casos com revisão está no subconjunto discricionário, não nas regras obrigatórias. Em contrapartida, `INVOICE_DISPUTE` tem sempre revisão (RV1), por construção do protocolo (D11): a correlação classe→revisão continua alta e é reportada (protocolo 10.5).

## 6. Dificuldade

Não existe um campo de dificuldade (não é usado em nenhuma métrica). Qualitativamente:

- **simples:** promessa com data, alegação completa, pedido de cópia, resposta automática;
- **intermédios:** alegação parcial com promessa do resto, plano curto vs. longo, pedido de aceitação de uma data («pode ser?»), compensação com um crédito, mensagens sobre duas faturas;
- **difíceis:** contradições (incluindo entre o cliente e um sócio), «agendada» vs. «ordenada hoje», pergunta vs. recusa da fatura, terceiro pagador discreto (factoring, conta pessoal), declaração de liquidação com valor diferente do pendente, instruções ao agente escondidas em rodapés, citações ou comentários HTML, e **armadilhas lexicais** para os detetores obrigatórios (assinatura «Sociedade de Advogados», «Tribunal de Contas», «RGPD», perguntas sobre o IBAN do credor, pagamento devolvido por «erro no IBAN»), cuja referência **não** tem RV5/RV7.

## 7. Divisões

`dataset.assign_splits`, semente `20261019`. Unidade indivisível: **cliente** (logo também a fatura). Clientes ordenados por tamanho (maiores primeiro), ordem aleatória por semente dentro do mesmo tamanho, cada cliente atribuído ao conjunto com maior défice relativo face ao perfil global de classe × revisão, respeitando os tamanhos 30/300/60/120. A divisão foi calculada com as etiquetas 2.0.0-candidate e **congelada** em 2.1.0 (D18): as correções de etiquetas posteriores não a recalculam (recalcular trocaria 39 casos de teste), pelo que a estratificação por classe × revisão é aproximada e não exatamente a do algoritmo. `splits.json` fica protegido pelo *hash* no manifesto.

## 8. Utilização e isolamento das etiquetas

Usar sempre `responsible_receivables_agent.dataset`, nunca ler `annotations.jsonl` diretamente em código de experiências:

| Função | Para quê | Etiquetas |
| --- | --- | --- |
| `load_inputs(split)` | entradas do classificador/seletor | nenhuma |
| `Oracle().query(ids)` | anotação simulada da *pool* | só os ids pedidos; regista as consultas; recusa ids fora da *pool* |
| `load_gold("seed_stock" \| "validation")` | memória inicial; piloto e configuração | sim |
| `load_gold("test", unlock_test=True)` | avaliação final | só com desbloqueio explícito |

`load_gold("pool")` é recusado. O *policy gate* (T09) **não** usa nenhuma destas funções: decide a partir do texto bruto.

## 9. Verificações automáticas

`uv run --locked python -m responsible_receivables_agent.dataset check` (e `tests/test_dataset.py`) verificam: campos exatos dos dois esquemas (nenhum campo antigo); formatos de ids, montantes e datas; `needs_additional_review = bool(review_reasons)`; razões dentro do protocolo (sem RV4); cobertura caso↔anotação; coerência de cada fatura; duplicados exatos (texto normalizado); tamanhos dos conjuntos; nenhum caso em dois conjuntos; nenhum cliente ou fatura em dois conjuntos; quase-duplicados entre conjuntos (Jaccard de 5-gramas ≥ 0,80); mínimos do teste; reprodutibilidade da divisão (só enquanto o dataset não está congelado); e manifesto atualizado (*hashes*, versões, contagens). Com o dataset congelado (`dataset.FROZEN`), `build` só regenera `manifest.json` e nunca reescreve `splits.json`.

## 10. Limitações

- **Um só autor** (modelo de IA) escreveu todas as mensagens e propôs todas as etiquetas: risco de estilo e de vieses comuns a todos os conjuntos; sem concordância entre anotadores.
- Etiquetas **sem dupla anotação humana** nem κ; só os casos divergentes ou de fronteira da auditoria foram decididos por um humano. As restantes adjudicações são decisões provisórias do autor, congeladas.
- Riscos identificados na auditoria (`docs/audits/DATASET_AI_REVIEW_V2.md`): separabilidade lexical elevada (um Naive Bayes trivial obtém macro-F1 ≈ 0,85 na validação, risco de efeito teto em E1); em E2, revisão constante por classe no subconjunto discricionário (`PAYMENT_PROMISE` nunca, `INVOICE_DISPUTE` sempre); contradições (RV8) pouco realistas.
- **Quase-duplicados semânticos** (cosseno de *embeddings* ≥ 0,92) ainda não verificados: dependem do *encoder* fixado em T12.
- Algumas classes têm marcadores lexicais naturais (p. ex. «prestações» em planos); o autor variou a formulação, mas não se mediu o desempenho de um classificador lexical simples.
- Contexto mínimo: sem histórico de pagamentos ou promessas (RV4 retirada), pelo que o incumprimento repetido não é estudado.
- `INVOICE_DISPUTE` tem sempre revisão; promessas raramente.
- GAP-09 (cliente que reporta um IBAN suspeito) continua sem regra; esses casos não existem no dataset.
- Pequena dimensão da validação (60) e do teste (120): intervalos de confiança largos.

## 11. Estado após o congelamento

O teste está congelado desde 2026-10-20 (D18): as mensagens, as etiquetas e `splits.json` não se alteram durante E1/E2. Ficaram por fazer, e são limitações a reportar: dupla anotação humana com κ de Cohen (protocolo 8.2(7)); a verificação por *embeddings* (cosseno ≥ 0,92), que depende do *encoder* fixado em T12; e uma regra para GAP-09. Qualquer correção futura exige uma nova versão do dataset e do manifesto.
