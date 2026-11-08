> **Fase 7 · Plataforma integrada.** Este componente agora faz parte do CardioIA integrado. Arquitetura, execução com Docker Compose/Kubernetes e o app estão no [README principal](../../README.md). Novidades desta fase: execução em container com Gunicorn (Dockerfile), consumido pelo gateway em `/api/chat`; a interface original continua disponível na raiz do serviço.

# FIAP - Faculdade de Informática e Administração Paulista

<p align="center">
<a href= "https://www.fiap.com.br/"><img src="assets/logo-fiap.png" alt="FIAP - Faculdade de Informática e Administração Paulista" border="0" width=40% height=40%></a>
</p>

<br>

# Ano 2 - Fase 5

## Grupo DRELL

## 👨‍🎓 Integrantes: 
- <a href="https://www.linkedin.com/in/richard-marques-26b3a14/">Richard</a>
- <a href="https://www.linkedin.com/in/luis-fernando-dos-santos-costa-b69894365/">Luis</a>

## 👩‍🏫 Professores:
### Tutor(a) 
- <a href="https://github.com/leoruiz197">Leo Ruiz</a>
### Coordenador(a)
- <a href="https://www.linkedin.com/in/andregodoichiovato/">Andre Godoi</a>


## 📜 Descrição

Este repositório mantém os assets solicitados para esta etapa: a construção de um **Assistente Cardiológico Conversacional (Chatbot)** que simula um atendimento inicial em saúde. O usuário interage em linguagem natural e o assistente identifica a intenção, extrai as informações clínicas relevantes (sintoma, intensidade, duração, irradiação e fatores de risco), aplica regras de **sinal de alarme** ("red flags") e devolve um **resumo clínico estruturado** com uma classificação de risco e uma conduta sugerida.

O assistente foi modelado na plataforma **IBM Watson Assistant** (arquivo de exportação em `watson/skill-assistente-cardiologico.json`), com **intents**, **entities** e **dialog nodes** voltados para a triagem cardiológica, e integrado a um **backend em Flask** que consome a API do serviço. Para que o protótipo possa ser executado e demonstrado sem credenciais da IBM Cloud, o backend também inclui um **motor de NLP local (offline)** que reproduz a mesma taxonomia de intents e entities — a troca entre os dois é feita pela variável de ambiente `USE_WATSON`, e há *fallback* automático para o motor local caso o Watson esteja indisponível.

A interface de interação é uma página de **chat em HTML/CSS/JS puro**, servida pelo próprio Flask e integrada ao backend.

> ⚠️ **Aviso:** projeto acadêmico/educacional. O conteúdo clínico é simplificado e **não substitui avaliação médica**. Em emergência, ligue **192 (SAMU)**.

## Video demonstrativo

No link abaixo tem um video explicando a solução e demonstrando suas duas variações (como motor local e com o uso do Watsonx Assistant da IBM)

<a href="https://www.youtube.com/watch?v=s3It0NV1fsY" ><img src="./assets/youtube.png" width="400"></a>


### Arquitetura

```
Frontend (HTML/CSS/JS)  ──HTTP/JSON──►  Backend Flask  ──►  IBM Watson Assistant (API v2)
                                              │
                                              └──►  Motor de NLP local (offline, fallback)
```

## Parte 1: Assistente Conversacional com NLP

### Etapa 1.1 - Modelagem no IBM Watson Assistant

O assistente foi modelado com foco em um fluxo de atendimento inicial no contexto de saúde. As instruções em como configurar o serviço estão em  [`watson/COMO-IMPORTAR.md`](./watson/COMO-IMPORTAR.md)):

- [`watson/skill-assistente-cardiologico.json`](./watson/skill-assistente-cardiologico.json) — *dialog skill* (workspace v1): **10 intents**, **6 entities** e **18 dialog nodes** (Watson Assistant clássico).

**Intents (intenções):**

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

**Entities (entidades):** `sintoma_cardiaco` (dor no peito, dor no braço, falta de ar, palpitação, tontura, desmaio, inchaço nas pernas, sudorese fria, fadiga, náusea), `intensidade` (leve, moderada, forte, muito forte), `irradiacao` (braço esquerdo, mandíbula, costas, pescoço, ombro), `duracao` (regex: `10 minutos`, `2 horas`, `3 dias`), além de `idade` e `nome`.

### Etapa 1.2 - Fluxo de diálogo

```
início
  └─ saudação ─────────────► "O que você está sentindo?"
        │
        ▼
  coleta da queixa   (intent informar_sintoma / entity sintoma_cardiaco)
        │
        ▼
  coleta de detalhes (slots)
        ├─ intensidade?
        ├─ duração?
        ├─ irradiação?        (apenas se dor torácica)
        └─ fatores de risco?
        │   cada pergunta é feita no máximo uma vez
        ▼
  triagem ──► classificação de risco + resumo clínico estruturado
        │
        ▼
  encerramento (intent despedida) ──► repete o resumo + disclaimer
```

A avaliação de **sinais de alarme** ocorre a cada turno, **antes** do fluxo normal. Se qualquer red flag for detectada (ou o intent `emergencia` for reconhecido), o assistente interrompe a coleta e orienta procura imediata por emergência (192 / SAMU).

| Regra de red flag | Condição |
|---|---|
| Dor torácica de forte intensidade | `dor no peito` + intensidade forte/muito forte |
| Dor torácica + sudorese fria | `dor no peito` + `sudorese fria` |
| Dor torácica + falta de ar | `dor no peito` + `falta de ar` |
| Dor torácica com irradiação | `dor no peito` + qualquer `irradiacao` |
| Dor torácica prolongada | `dor no peito` + duração ≥ 20 min |
| Falta de ar + palpitação | ambos os sintomas presentes |
| Síncope | sintoma `desmaio` |

**Classificação de risco resultante:** `EMERGÊNCIA`, `PRIORIDADE ALTA`, `AVALIAÇÃO ELETIVA`, `ORIENTAÇÃO / PREVENÇÃO` ou `ORIENTAÇÃO GERAL`, cada uma com a respectiva conduta sugerida.

**Tratamento de exceções:** mensagem não compreendida pede reformulação e, após duas falhas seguidas, explica o escopo; respostas curtas durante a coleta ("leve", "3 dias", "sou fumante") são interpretadas como resposta ao slot corrente; cada slot é perguntado uma única vez; falha do Watson faz *fallback* transparente para o motor local; `message` vazio retorna `HTTP 400`.

### Etapa 1.3 - Integração backend (Flask + API do Watson)

O backend seleciona o motor em tempo de execução e adapta a resposta do Watson (`output.generic`, `output.intents`, `output.entities`) ao mesmo formato consumido pelo frontend.

| Método | Rota | Corpo | Descrição |
|---|---|---|---|
| `GET` | `/` | — | Página do chat |
| `GET` | `/api/health` | — | Status e motor ativo |
| `POST` | `/api/message` | `{"message": "...", "conversation_id": "..."}` | Mensagem do usuário → resposta do assistente |
| `POST` | `/api/reset` | `{"conversation_id": "..."}` | Reinicia a conversa |

Exemplo de resposta de `/api/message`:

```json
{
  "reply": "🚨 Os sinais que você descreveu podem indicar uma EMERGÊNCIA cardíaca...",
  "intent": "emergencia",
  "confidence": 0.99,
  "entities": [{"entity": "sintoma_cardiaco", "value": "dor no peito"}],
  "stage": "emergencia",
  "summary": {
    "classificacao": "EMERGENCIA",
    "conduta_sugerida": "Procure imediatamente um pronto-socorro ou ligue 192 (SAMU).",
    "sintomas": ["dor no peito", "falta de ar", "sudorese fria"],
    "sinais_de_alarme": ["Dor toracica de forte intensidade", "..."]
  },
  "engine": "local"
}
```

## Parte 2: Interface de Interação com o Usuário

Interface simples de chat em **HTML/CSS/JS puro** (pasta `frontend/`), servida pelo próprio Flask e integrada ao backend. Permite ao usuário enviar mensagens e visualizar as respostas do assistente, com *quick replies*, cartão de **resumo clínico** e um *badge* indicando o motor ativo (`local` ou `watson`).

<img src="./watson/assets/assistente2.png" alt="Interface de chat do assistente" width="700"> 

## ▶️ Executando o projeto

### Pré-requisitos
- Python 3.10+

### Passos

```bash
# 1. clonar e entrar na pasta
git clone <URL-do-seu-repositorio>
cd entrega1

# 2. ambiente virtual
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # Linux/Mac

# 3. dependências
pip install -r requirements.txt

# 4. configuração
copy .env.example .env           # Windows  (cp no Linux/Mac)
#    deixe USE_WATSON=false para rodar offline

# 5. subir a aplicação
python run.py
```

Abra **http://127.0.0.1:5000** no navegador.

### Testes

```bash
pytest -q
```

17 testes cobrindo a classificação das intents, a extração de entidades combinadas, a rejeição de texto fora de escopo, o fluxo completo até a triagem, o disparo de emergência e o *fallback* progressivo.

### Usando o IBM Watson Assistant (opcional)

1. Crie um serviço **Watson Assistant** na IBM Cloud.
2. Importe `watson/skill-assistente-cardiologico.json` no assistente.
3. No `.env`, preencha e ajuste:
   ```
   USE_WATSON=true
   WATSON_APIKEY=...
   WATSON_URL=https://api.<região>.assistant.watson.cloud.ibm.com
   WATSON_ASSISTANT_ID=...
   ```
4. Reinicie `python run.py`. O *badge* da interface passa a exibir `motor: watson`. Se as credenciais faltarem ou o serviço falhar, o backend volta automaticamente para o motor local.

### Frases para testar

- `oi` → saudação e início da triagem
- `estou com palpitação` → coleta de intensidade/duração → resumo
- `estou com dor no peito muito forte, suando frio e com falta de ar` → **emergência**
- `eu desmaiei agora há pouco` → **emergência** (síncope)
- `para que serve o eletrocardiograma?` → dúvida sobre exame
- `posso parar de tomar o remédio da pressão?` → dúvida sobre medicamento
- `quais os fatores de risco para infarto?` → fatores de risco
- `asdfghjkl` (2x) → tratamento de exceção


## 📁 Estrutura de pastas

Dentre os arquivos e pastas presentes na raiz do projeto, definem-se:

- <b>backend</b>: código-fonte do backend em Python (Flask). `app.py` (rotas e seleção de motor), `local_nlp.py` (motor de NLP local), `dialog.py` (gerenciador de diálogo, red flags e resumo clínico), `watson_client.py` (integração com a API do Watson Assistant) e `config.py` (variáveis de ambiente).

- <b>frontend</b>: interface de chat em HTML/CSS/JS puro (`index.html`, `styles.css`, `app.js`).

- <b>watson</b>: exportações do assistente — `skill-assistente-cardiologico.json` (dialog skill / workspace v1, para o Watson Assistant clássico) e `watsonx-actions-assistente-cardiologico.json` (action skill, para o watsonx Assistant novo). Instruções em `watson/COMO-IMPORTAR.md`.

- <b>tests</b>: testes automatizados (`pytest`) do motor de NLP e do gerenciador de diálogo.

- <b>assets</b>: arquivos não-estruturados do repositório, como imagens.

- <b>run.py</b>: atalho de execução (`python run.py`).

- <b>requirements.txt</b>: dependências do projeto.

- <b>.env.example</b>: modelo de configuração de ambiente.

- <b>README.md</b>: arquivo que serve como guia e explicação geral sobre o projeto (o mesmo que você está lendo agora).


## 🗃 Histórico de lançamentos

* 0.1.0 - 06/09/2026
    * Versão inicial

## 📋 Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/agodoi/template">MODELO GIT FIAP</a> por <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://fiap.com.br">Fiap</a> está licenciado sobre <a href="http://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Attribution 4.0 International</a>.</p>
