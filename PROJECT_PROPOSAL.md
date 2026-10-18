# PROJECT PROPOSAL V2 — Responsible Receivables Agent

**UC:** Trustworthy and Responsible Artificial Intelligence (TRAI), 2026/2027  
**Projeto:** Lab Project 1 — *Trustworthy-aware Human in the Loop*  
**Docente:** Luís Macedo  
**Título científico provisório:** *Risk-Aware Active In-Context Learning for Human Oversight in an LLM-Based Receivables Agent*  
**Estado:** proposta para validação; sem implementação ou resultados experimentais nesta fase.

## 1. Problema, objetivo e contributo

Propõe-se um **agente LLM de apoio à gestão de cobranças em PMEs portuguesas**, inspirado num processo empresarial em que os **pendentes** são acompanhados através de um ficheiro Excel, eventualmente exportado do Cegid Primavera. Identificar datas de vencimento é uma operação determinística; a dificuldade está em **interpretar comunicações dos clientes**, identificar pagamentos alegados, contestações ou pedidos de prazo e decidir **quando solicitar intervenção humana**.

O objetivo científico **não** é construir um software de faturação, mas estudar **como a seleção ativa de feedback humano influencia a qualidade e o esforço da supervisão de um agente LLM**.

Serão investigados **Human Agency & Oversight** e **Safety**, com **Accountability** e **Privacy** como requisitos de desenho. O contributo pretendido é uma **análise empírica** da relação entre seleção de exemplos, erros com consequências relevantes, qualidade dos encaminhamentos e esforço humano. A originalidade proposta está na **combinação e avaliação contextualizada** de técnicas existentes, não na criação de uma nova família de algoritmos.

## 2. Questões de investigação

**RQ1 — Active Learning.** Com o mesmo orçamento de anotações, uma estratégia orientada pelo risco melhora a identificação de situações críticas face à seleção aleatória, por incerteza e por similaridade?

**RQ2 — Human Oversight.** Melhorar a classificação através de exemplos anotados permite **encaminhar corretamente casos para revisão humana adicional**, reduzindo revisões desnecessárias sem aumentar os erros críticos?

As hipóteses são falsificáveis: a seleção orientada pelo risco pode ser inferior às alternativas, e melhor classificação pode não produzir melhor triagem. Não se assumem resultados antecipadamente.

## 3. Workflow operacional proposto

O sistema será **orientado por eventos**, e não executado periodicamente de X em X minutos:

1. **Importação do Excel:** validação dos documentos e criação de casos de acompanhamento. O ficheiro é uma **fotografia dos saldos registados** numa determinada data; não confirma transferências bancárias.
2. **Agente LLM:** consulta ferramentas de leitura (pendentes e histórico), pode pedir esclarecimentos, redigir uma proposta, registar acompanhamento ou encaminhar o caso. O LLM escolhe entre ações permitidas; não controla diretamente as autorizações.
3. **Comunicação:** qualquer e-mail externo requer **aprovação humana prévia**. No protótipo o envio e a resposta serão **simulados**.
4. **Interpretação da resposta:** o agente classifica a mensagem com auxílio de demonstrações humanas e sugere **acompanhamento interno**, **pedido de esclarecimento** ou **revisão humana adicional**.
5. **Controlo:** políticas determinísticas impõem revisões obrigatórias em situações críticas, impedem alteração de saldos e tratam as instruções presentes nos e-mails como dados não fiáveis.
6. **Feedback:** o humano pode corrigir a classificação e indicar se o caso necessita de revisão. Um seletor de Active Learning escolhe estrategicamente **quais os casos a anotar**; essas anotações enriquecem a memória utilizada nas inferências futuras.

**Exemplo:** uma empresa alega ter pago 1 000 € de uma renda com 2 000 € registados como pendentes e contesta o restante por causa de uma nota de crédito. O agente distingue o pagamento **alegado** de um pagamento confirmado, consulta o contexto e encaminha a contestação. A eventual **anotação para aprendizagem** é distinta da **aprovação de uma ação**.

**Distinção essencial:** a supervisão é *graduada* na **triagem/investigação adicional de casos**; **não** serve para dispensar a autorização obrigatória de comunicações externas.

## 4. Arquitetura e implementação

| Componente | Solução prevista |
| --- | --- |
| **Dados** | Excel `.xlsx` sintético; importação e validação em Python (`pandas`/`openpyxl`); valores financeiros apenas de leitura. |
| **Agente** | Um LLM, orquestrado com **LangGraph**, capaz de escolher ferramentas para consultar, redigir, pedir esclarecimento, registar e escalar. |
| **Active In-Context Learning (ICL)** | Memória versionada de exemplos classificados por humanos; seleção ativa para anotação; recuperação de até `k` demonstrações por regra idêntica entre condições. |
| **Human-in-the-Loop** | Interrupção/retoma para revisão; controlador de segurança independente do LLM; aprovações vinculadas ao conteúdo, destinatário e versão dos dados. |
| **Avaliação** | Simulador de clientes/e-mails, ambiente isolado, registos auditáveis, testes automatizados e interface mínima de anotação/aprovação. |

**Fora do âmbito:** integração com ERP ou correio reais, alterações contabilísticas, pagamentos, decisões contratuais, *fine-tuning* e utilização de dados confidenciais. Não será reivindicada conformidade jurídica integral com RGPD ou AI Act.

## 5. Metodologia: Active In-Context Learning

Será utilizado um protocolo **pool-based**: conjunto inicial anotado → seleção de exemplos não anotados → anotação humana → atualização da memória → avaliação independente. **Os pesos do LLM não são alterados**; mudam os exemplos supervisionados disponibilizados no contexto. Trata-se de *active example selection for ICL*, distinta da Active Learning clássica com treino de parâmetros [1–4].

Compararemos **Random**, **Uncertainty**, **Similarity/Representativeness** e **Risk-Aware**. Para a última, propõe-se inicialmente:

`S(x) = α × U(x) + β × R(x) + γ × D(x)`

- **U:** incerteza estimada pela discordância entre classificações de execuções controladas; não será interpretada como probabilidade calibrada.
- **R:** custo esperado do erro, a partir de **matriz de custos definida previamente** e previsões disponíveis **sem consultar a etiqueta verdadeira**.
- **D:** diversidade/cobertura face aos exemplos já anotados.

Os pesos e normalizações serão pré-definidos ou escolhidos exclusivamente com dados de validação. Serão realizadas **ablações** para testar o contributo de cada componente. O *prompt*, o LLM, `k` e a regra de recuperação serão mantidos constantes nas comparações.

## 6. Dados e experiências de validação

Prevê-se construir mensagens **sintéticas em PT-PT**, ligadas a pendentes fictícios: promessas, pagamentos alegados, planos de pagamento, contestações e casos ambíguos. Cada cenário terá referências separadas para **classe da mensagem**, **necessidade de revisão adicional** e **ação permitida/proibida**.

**Dimensão preliminar, sujeita a piloto:** aproximadamente **20–30 exemplos iniciais**, *pool* de **300** e teste reservado de **100–150** casos; até **40 novas anotações** por execução. Estes valores serão ajustados à distribuição das classes e à capacidade de validação das etiquetas. A separação será feita por **cenário/cliente e família de formulações**, removendo quase-duplicados para reduzir contaminação. Um **piloto zero-shot** verificará se existe espaço para melhoria.

### E1 — Seleção ativa de exemplos

**Comparação:** Zero-shot; ICL inicial/fixo; Random; Uncertainty; Similarity; Risk-Aware. Como referência complementar, poderá incluir-se um classificador treinável simples (embeddings + regressão logística), **sem substituir o agente LLM**.

**Métricas:** *Macro F1*, *recall* dos casos críticos/contestações, **custo ponderado dos erros**, desempenho por orçamento de anotações, latência e custo. Serão usadas várias sementes, análise pareada e intervalos de confiança quando suportados pela dimensão da amostra, além de ablações da estratégia proposta.

**Controlo experimental:** mesmo modelo/versão, *prompt*, recuperação, `k` e conjunto de teste. Nenhuma etiqueta do teste poderá entrar na seleção ou na memória.

### E2 — Aprendizagem e supervisão humana

**Comparação no mesmo conjunto de casos:**

- **S0 — Revisão universal:** todos os casos recebem investigação humana adicional (*baseline* de esforço).
- **S1 — Triagem seletiva inicial:** encaminhamentos propostos pelo LLM sem novas demonstrações ativamente selecionadas, sujeitos às políticas obrigatórias.
- **S2 — Triagem seletiva com Active ICL:** mesmas políticas, mas com as demonstrações anotadas e selecionadas em E1.

**Métricas:** *recall* de encaminhamento crítico, **casos críticos não encaminhados**, taxa de revisões adicionais, custo ponderado das decisões e sucesso das tarefas internas. Serão comparadas **curvas risco–carga de revisão**, incluindo condições com o mesmo orçamento de revisões. A aprovação de e-mails externos continua obrigatória nas três configurações.

### Verificação e demonstração

Uma *suite* `pytest` verificará *prompt injection*, associação errada de documentos, dados desatualizados, importações duplicadas, aprovações inválidas e ausência de resposta humana. Uma pequena demonstração permitirá rever e anotar casos. Nas experiências repetidas, as etiquetas previamente validadas poderão simular o oráculo humano; **isto não equivale a um estudo com utilizadores reais**.

## 7. Fundamentação científica e decisões de desenho

| Publicação | Decisão sustentada |
| --- | --- |
| **[1] Xia et al., ACL 2025** — *From Selection to Generation: A Survey of LLM-based Active Learning* | Enquadrar seleção e anotação ativa com LLMs e identificar limitações do uso de anotadores automáticos. |
| **[2] Margatina et al., EMNLP 2023** — *Active Learning Principles for In-Context Learning with Large Language Models* | Comparar incerteza com **similaridade**, que se mostrou uma referência forte nas tarefas estudadas. |
| **[3] Su et al., ICLR 2023** — *Selective Annotation Makes Language Models Better Few-Shot Learners* | Separar **seleção para anotação** de **recuperação de demonstrações** na inferência. |
| **[4] Zhang et al., EMNLP 2022** — *Active Example Selection for In-Context Learning* | Reconhecer investigação anterior e delimitar a originalidade da nossa combinação. |
| **[5] Mozannar & Sontag, ICML 2020** — *Consistent Estimators for Learning to Defer to an Expert* | Fundamentar a decisão de **quando pedir ajuda humana**, sem reivindicar implementação do algoritmo. |
| **[6] Amershi et al., CHI 2019** — *Guidelines for Human-AI Interaction* | Fundamentar mecanismos de correção, aprovação e gestão de erros na interação humano–IA. |

**Fontes verificáveis:** [1] https://aclanthology.org/2025.acl-long.708/ · [2] https://aclanthology.org/2023.findings-emnlp.334/ · [3] https://openreview.net/pdf?id=qY1hlv7gwg · [4] https://aclanthology.org/2022.emnlp-main.622/ · [5] https://proceedings.mlr.press/v119/mozannar20b.html · [6] https://doi.org/10.1145/3290605.3300233

## 8. Entregáveis e perguntas para validação

**Entregáveis (até 5/11/2026):** software e artigo científico no **GitHub e Inforestudante**, dataset sintético e proveniência, código de experiências, resultados reproduzíveis, README de execução e defesa oral. O artigo seguirá as orientações do enunciado: **até 8 páginas, duas colunas, formato IJCAI**, excluindo referências, com reflexão sobre TRAI e declaração de utilização de ferramentas de IA. A data da defesa apresenta um aparente lapso no documento oficial.

**Questões para o docente:**

1. A **seleção ativa de exemplos humanos para ICL**, sem atualização dos pesos do LLM, é considerada adequada ao Projeto 1? É necessário um modelo treinável no núcleo do sistema?
2. A avaliação conjunta de **Active ICL e triagem para supervisão humana adicional**, mantendo as aprovações externas obrigatórias, corresponde à cooperação humano–IA pretendida?
3. **Human Oversight e Safety**, sustentados por Accountability e Privacy, são suficientes, ou é esperada uma experiência explícita de *fairness/bias*?
4. São aceitáveis **dados sintéticos PT-PT** com etiquetas revistas e um **oráculo simulado** nas experiências repetidas, complementados por uma demonstração humana limitada?
5. Pode confirmar a **data da defesa**, indicada como 6/11/2025 no enunciado de 2026/2027?

---

*Documento para discussão e validação do desenho do projeto. Os resultados, a dimensão final do dataset e quaisquer ganhos de desempenho permanecem por demonstrar.*
