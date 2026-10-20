# Responsible Receivables Agent

Agente baseado em LLM para a gestão de contas a receber de PME, combinando supervisão humana
(human-in-the-loop), *active learning* sensível ao risco e decisões auditáveis.

## Contexto académico

Projeto da unidade curricular **Trustworthy and Responsible Artificial Intelligence (TRAI)**
2026/2027, Mestrado em Inteligência Artificial, Universidade de Coimbra.

## Objetivo científico

Ver [`PROJECT_PROPOSAL.md`](PROJECT_PROPOSAL.md) (V2) para as questões de investigação, hipóteses e
metodologia, e [`IMPLEMENTATION_TASKS.md`](IMPLEMENTATION_TASKS.md) para o plano de tarefas.

## Aviso

O projeto usa **apenas simulação**: funciona offline por omissão, **não envia comunicações reais**
(e-mail ou outras), não altera dados financeiros e não executa operações pagas. Os dados são
sintéticos.

## Requisitos

- [uv](https://docs.astral.sh/uv/) (gestor único de Python/ambiente/dependências). Instalação
  oficial: <https://docs.astral.sh/uv/getting-started/installation/>
  (Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`).
- Python 3.12 (instalado pelo uv; versão fixada em `.python-version`).

## Instalação

```powershell
uv --version
uv python install 3.12
uv sync --locked
```

Copie `.env.example` para `.env` apenas se necessário (não é preciso para os testes).

## Testes, lint e type checking

```powershell
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy src tests
```

## Dataset (T03)

Dataset estático de 510 mensagens sintéticas PT-PT em `data/dataset/` (v2.1.0, congelado, esquema mínimo, D17/D18). Descrição, estado de validação e limitações: [`docs/DATASET_CARD.md`](docs/DATASET_CARD.md).

```powershell
uv run --locked python -m responsible_receivables_agent.dataset check   # esquema, regras, divisões, leakage, hashes; mostra contagens
```

`build` reescreve `splits.json` e `manifest.json`; só se usa ao criar uma nova versão do dataset.

## Classificador Llama local (T05.1)

`src/responsible_receivables_agent/classifier.py`: classificador zero-shot de uma classe principal, via API local do Ollama (sem rede externa nem chaves). Saída `{"message_label": <uma das 5 classes>}`; sem `needs_additional_review` nem `review_reasons` (tarefas posteriores).

```powershell
ollama serve                      # se ainda não estiver a correr
ollama list                       # deve listar llama3.2:latest
uv run --locked python -m responsible_receivables_agent.classifier --message "Pagamos na sexta-feira."
```

- **Entrada:** exatamente os 7 campos de `cases.jsonl`; qualquer outra chave (p. ex. etiquetas gold) é rejeitada. Só `invoice_id`, `pending_amount_eur`, `due_date`, `received_date` e `message_text` entram no prompt; o texto vai como string JSON, marcado como dados não fiáveis.
- **Configuração** (`OllamaConfig`): `llama3.2:latest`, `temperature=0`, `num_ctx=4096`, `num_predict=32`, `seed=0`, timeout 120 s, saída estruturada (JSON schema com enum). `latest` é mutável: `--expected-digest a80c4f17acd5` aborta se o modelo instalado for outro. O resultado inclui latência, digest e opções.
- **Falhas:** `OllamaUnavailable`, `OllamaTimeout`, `InvalidModelOutput`; nunca se devolve uma classe por defeito.
- **Limitações:** zero-shot, uma chamada por caso, sem cache nem votos; o smoke test valida a integração técnica, não o desempenho semântico (não avaliado na validação nem no teste).
- **Falta para a T05.2:** interface LLM com mock/replay, cache de respostas, registo de execuções, piloto zero-shot nas 60 mensagens de validação e nota *go/no-go*.

## Organização

```text
src/responsible_receivables_agent/   pacote Python
tests/                               testes (pytest)
scripts/  data/  experiments/        scripts, dados sintéticos, experiências
docs/  paper/                        documentação e artigo
pyproject.toml  uv.lock              dependências e lock reprodutível (uv)
```

## Estado atual

T01–T02 concluídas (protocolo revisto para 2.0.0 em D17 e para 2.1.0 em D18). T03 (dataset estático
anotado, divisões, manifesto) reconstruída com esquema mínimo, auditada por IA e **congelada** em D18
(`test_frozen: true`). A dupla anotação humana com κ (T04) não foi feita: desvio declarado em D18.
T05.1 (classificador Llama local via Ollama, sem avaliação) implementada. Ainda não existe agente nem lógica de negócio.
