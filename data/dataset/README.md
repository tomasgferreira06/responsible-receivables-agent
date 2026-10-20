# Dataset estático (T03, v2.1.0, congelado)

510 mensagens sintéticas em PT-PT, redigidas diretamente por IA (sem gerador) e anotadas segundo o protocolo 2.1.0. Descrição, processo de criação, distribuições, estado de validação e limitações: [`docs/DATASET_CARD.md`](../../docs/DATASET_CARD.md).

| Ficheiro | Conteúdo |
| --- | --- |
| `cases.jsonl` | Entradas (7 campos): ids, montante pendente, vencimento, data de receção, mensagem. Sem etiquetas |
| `annotations.jsonl` | Referência (4 campos): `message_label`, `needs_additional_review`, `review_reasons` |
| `adjudications.jsonl` | Casos ambíguos e decisão provisória (mesmo acesso restrito que as anotações) |
| `splits.json` | Seed / pool / validação / teste, divididos por cliente com semente fixa |
| `manifest.json` | Versões, estado, *hashes* e contagens |

**Não ler `annotations.jsonl` nem `adjudications.jsonl` em código de experiências.** Usar `responsible_receivables_agent.dataset`:

- `load_inputs(split)`: entradas do classificador e do seletor;
- `Oracle().query(ids)`: etiquetas da *pool*, só para ids selecionados;
- `load_gold("seed_stock" | "validation")` / `load_gold("test", unlock_test=True)`: só para memória inicial e avaliação.

Estado: **congelado** desde 2026-10-20 (D18; `test_frozen: true`). Auditado por IA e com os casos de fronteira decididos pelo responsável do projeto; sem dupla anotação humana (desvio declarado). Estes ficheiros não são gerados por código e não se alteram durante E1/E2. Qualquer correção exige uma nova versão do dataset, documentada em `docs/DECISIONS.md`. Com `dataset.FROZEN`, `build` só regenera `manifest.json` e nunca reescreve `splits.json`.
