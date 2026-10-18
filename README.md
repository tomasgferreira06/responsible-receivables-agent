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

## Organização

```text
src/responsible_receivables_agent/   pacote Python
tests/                               testes (pytest)
scripts/  data/  experiments/        scripts, dados sintéticos, experiências
docs/  paper/                        documentação e artigo
pyproject.toml  uv.lock              dependências e lock reprodutível (uv)
```

## Estado atual

T01 (bootstrap do repositório e qualidade base) implementada, aguarda revisão. Ainda não existe
agente, dados nem lógica de negócio.
