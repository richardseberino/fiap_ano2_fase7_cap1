# Relatório — Assistente Cardiológico Conversacional

**Disciplina:** PCV — Processamento Cognitivo e Visão (FIAP, 2º ano, Fase 5)
**Entrega 1 — Protótipo funcional de chatbot para triagem inicial em cardiologia**

---

## 1. Objetivo

Construir um protótipo de assistente conversacional que simula o **atendimento
inicial (triagem)** de um paciente com queixa cardiológica. O assistente
conversa em linguagem natural, identifica a intenção do usuário, extrai
informações clínicas relevantes (sintoma, intensidade, duração, irradiação,
fatores de risco), aplica **regras de sinal de alarme** ("red flags") e
apresenta um **resumo clínico estruturado** com uma classificação de risco e
uma conduta sugerida.

O projeto foi modelado no **IBM Watson Assistant** (arquivo de exportação em
`watson/skill-assistente-cardiologico.json`) e integrado a um **backend Flask**.
Para permitir a execução e a demonstração sem credenciais da IBM Cloud, o
backend também traz um **motor de NLP local** que reproduz a mesma taxonomia de
intents e entities.

## 2. Arquitetura

```
┌────────────┐   HTTP/JSON   ┌──────────────────────────┐
│  Frontend  │ ────────────► │        Backend Flask      │
│ HTML/CSS/JS│ ◄──────────── │  /api/message /api/reset  │
└────────────┘               │                          │
                             │  ┌────────────────────┐  │
                             │  │  Seleção de motor  │  │
                             │  └─────────┬──────────┘  │
                             │     ┌──────┴───────┐     │
                             │     ▼              ▼     │
                             │  Watson        NLP local │
                             │  Assistant   (offline)   │
                             │  (API v2)                │
                             └──────────────────────────┘
```

- **Frontend** (`frontend/`): página única de chat. Envia as mensagens do
  usuário para `POST /api/message` e renderiza as respostas, os *quick replies*
  e o cartão de resumo clínico. Mostra também o intent/entidades detectados
  (útil para a banca).
- **Backend** (`backend/`):
  - `app.py` — rotas Flask e escolha do motor em tempo de execução.
  - `local_nlp.py` — classificação de *intents* por pontuação de palavras‑chave
    e extração de *entities* por dicionário de sinônimos + expressões regulares.
  - `dialog.py` — **gerenciador de diálogo**: mantém o estado da conversa por
    `conversation_id`, conduz a coleta de informações, avalia os sinais de
    alarme e monta o resumo clínico.
  - `watson_client.py` — cliente da API v2 do Watson Assistant; adapta a
    resposta ao mesmo formato do motor local.
  - `config.py` — leitura de variáveis de ambiente (`.env`).

A troca entre motores é feita pela variável `USE_WATSON`. Se o Watson estiver
habilitado mas indisponível (credenciais ausentes, erro de rede), a aplicação
**cai automaticamente** para o motor local — o protótipo nunca fica sem
resposta.

## 3. Modelagem conversacional

### 3.1 Intents (intenções)

| Intent | Exemplo de enunciado |
|---|---|
| `saudacao` | "oi, bom dia" |
| `informar_sintoma` | "estou com dor no peito há 1 hora" |
| `informar_dados_pessoais` | "meu nome é João, tenho 58 anos" |
| `duvida_medicamento` | "posso parar de tomar o remédio da pressão?" |
| `duvida_exame` | "para que serve o eletrocardiograma?" |
| `duvida_fatores_risco` | "quais os fatores de risco para infarto?" |
| `agendar_consulta` | "quero marcar uma consulta com cardiologista" |
| `agradecimento` | "obrigado pela ajuda" |
| `despedida` | "pode encerrar o atendimento" |
| `emergencia` | "não consigo respirar e tenho dor muito forte no peito" |

### 3.2 Entities (entidades)

- `sintoma_cardiaco`: dor no peito, dor no braço, falta de ar, palpitação,
  tontura, desmaio, inchaço nas pernas, sudorese fria, fadiga, náusea.
- `intensidade`: leve, moderada, forte, muito forte.
- `irradiacao`: braço esquerdo, mandíbula, costas, pescoço, ombro.
- `duracao`: extraída por regex (`10 minutos`, `2 horas`, `3 dias`) ou por
  expressões ("começou agora", "de repente", "há meses").
- `idade` e `nome`: extraídas por regex do enunciado.

### 3.3 Fluxo de diálogo (dialog nodes)

```
início
  └─ saudação ─────────────► "O que você está sentindo?"
        │
        ▼
  coleta da queixa  (intent informar_sintoma / entity sintoma_cardiaco)
        │
        ▼
  coleta de detalhes  (slots)
        ├─ intensidade?
        ├─ duração?
        ├─ irradiação?   (apenas se dor torácica)
        └─ fatores de risco?
        │   cada pergunta é feita no máximo uma vez
        ▼
  triagem ──► classificação de risco + resumo clínico estruturado
        │
        ▼
  encerramento (intent despedida) ──► repete o resumo + disclaimer
```

**Avaliação de sinais de alarme** ocorre a **cada turno**, antes do fluxo
normal. Se qualquer red flag for detectada (ou o intent `emergencia` for
reconhecido), o assistente interrompe a coleta e orienta procura **imediata**
por emergência (192 / SAMU).

Regras de red flag implementadas:

| Regra | Condição |
|---|---|
| Dor torácica de forte intensidade | `dor no peito` + intensidade forte/muito forte |
| Dor torácica + sudorese fria | `dor no peito` + `sudorese fria` |
| Dor torácica + falta de ar | `dor no peito` + `falta de ar` |
| Dor torácica com irradiação | `dor no peito` + qualquer `irradiacao` |
| Dor torácica prolongada | `dor no peito` + duração ≥ 20 min |
| Falta de ar + palpitação | ambos os sintomas presentes |
| Síncope | sintoma `desmaio` |

### 3.4 Classificação de risco

| Classificação | Critério | Conduta |
|---|---|---|
| **EMERGÊNCIA** | qualquer red flag | Pronto-socorro / 192 imediatamente |
| **PRIORIDADE ALTA** | dor torácica sem red flag, falta de ar nova ou síncope prévia | Atendimento no mesmo dia + ECG |
| **AVALIAÇÃO ELETIVA** | sintomas leves/intermitentes | Consulta com cardiologista em dias |
| **ORIENTAÇÃO / PREVENÇÃO** | sem sintomas, apenas fatores de risco | Avaliação de rotina |
| **ORIENTAÇÃO GERAL** | apenas dúvidas | Acompanhamento de rotina |

## 4. Tratamento de exceções

- **Mensagem não compreendida** (`fora_de_escopo`): o assistente pede
  reformulação; após **duas** falhas seguidas, explica o escopo (triagem
  cardiológica) e reforça o canal de emergência.
- **Respostas curtas durante a coleta** ("leve", "3 dias", "nenhum desses")
  são interpretadas como resposta ao slot corrente, e não como erro.
- **Perguntas repetidas**: cada slot é perguntado no máximo uma vez; depois
  disso o fluxo avança para a triagem mesmo sem a informação.
- **Falha do Watson**: *fallback* transparente para o motor local.
- **Campo `message` vazio**: `HTTP 400`.
- **Disclaimer**: toda resposta de emergência, triagem e encerramento inclui o
  aviso de que o protótipo não substitui avaliação médica.

## 5. Integração com o Watson Assistant

1. Criar um serviço **Watson Assistant** na IBM Cloud.
2. Em *Assistants → Actions/Dialog*, importar
   `watson/skill-assistente-cardiologico.json`.
3. Copiar *API key*, *Service URL* e *Assistant ID* para o arquivo `.env`
   (ver `.env.example`) e definir `USE_WATSON=true`.
4. O backend cria uma sessão por `conversation_id`
   (`AssistantV2.create_session`), envia cada mensagem com
   `AssistantV2.message` e converte a resposta (`output.generic`,
   `output.intents`, `output.entities`) para o formato consumido pelo frontend.

## 6. Testes

`tests/test_local_nlp.py` cobre (17 casos, `pytest`):

- classificação das 10 intents;
- extração de entidades combinadas (sintoma + intensidade + irradiação +
  idade + duração);
- rejeição de texto fora de escopo;
- fluxo completo até a triagem;
- disparo de emergência por combinação de sintomas e por síncope;
- fallback progressivo e presença do disclaimer.

## 7. Limitações e trabalhos futuros

- Base de conhecimento textual simples; um modelo de intents treinado
  (Watson ou embeddings) generalizaria melhor a linguagem coloquial.
- Estado da conversa em memória (não persiste entre reinícios do servidor).
- Não há autenticação nem armazenamento de histórico do paciente.
- O conteúdo clínico é **educacional** e simplificado; não deve ser usado em
  atendimento real.

## 8. Divisão de tarefas da equipe

| Integrante | Responsabilidade principal |
|---|---|
| Integrante 1 | Modelagem no Watson Assistant (intents, entities, dialog nodes) |
| Integrante 2 | Backend Flask e integração com a API do Watson |
| Integrante 3 | Motor de NLP local, regras de red flag e testes |
| Integrante 4 | Frontend (interface de chat) e integração com o backend |
| Integrante 5 | Relatório, roteiro do vídeo e organização do repositório |

> Preencher com os nomes reais dos integrantes antes da entrega.
