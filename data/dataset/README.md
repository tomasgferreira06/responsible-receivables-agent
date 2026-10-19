# Dataset estático (T03)

510 mensagens sintéticas em PT-PT, redigidas por IA e anotadas segundo o protocolo T02. Descrição completa, estado de validação e limitações: [`docs/DATASET_CARD.md`](../../docs/DATASET_CARD.md).

| Ficheiro | Conteúdo |
| --- | --- |
| `cases.jsonl` | Entradas: contexto financeiro e mensagem (sem ground truth) |
| `annotations.jsonl` | Ground truth, factos RV, justificação e proveniência |
| `splits.json` | Atribuição seed / pool / validação / teste (semente fixa) |
| `manifest.json` | Versão, estado, *hashes* e estatísticas |

**Não ler `annotations.jsonl` diretamente em código de experiências.** Usar `responsible_receivables_agent.dataset`:

- `inference_split(split)`: vista sem etiquetas nem ids de agrupamento (classificador e seletor);
- `Oracle().query(ids)`: etiquetas da *pool*, só para ids selecionados;
- `load_gold("validation")` / `load_gold("test", unlock_test=True)`: só para o código de avaliação.

Estado: **candidato**. A dupla anotação humana está pendente (T04) e o teste não está congelado. Estes ficheiros não são gerados por código: editá-los é criar uma nova versão do dataset, que tem de ser documentada em `docs/DECISIONS.md`.
