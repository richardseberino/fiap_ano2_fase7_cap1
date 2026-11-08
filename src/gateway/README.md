# CardioIA Gateway (BFF)

Serviço FastAPI que é o **único ponto de entrada** do app web/mobile. Ele esconde a topologia interna do cluster e junta, sob `/api`, os sinais do IoT (InfluxDB), o multiagente, o chatbot e o modelo de visão.

- **Sem estado:** escala horizontalmente (HPA de 2 a 6 réplicas no Kubernetes).
- **Integração IoT → IA:** `GET /api/analise/sugestao/{paciente}` calcula as médias recentes de FC, SpO2, temperatura e PAS e conta os episódios de alerta das últimas 24 h, para pré-preencher a análise multiagente.
- **Chat unificado:** `POST /api/chat` vai ao chatbot de triagem. Com `analise_id`, a pergunta vai ao Orquestrador do multiagente, que responde com o contexto daquela análise.
- **Resiliência:** timeouts por tipo de chamada (LLM: 180 s), erros dos serviços internos convertidos em 503 ou 504 com mensagem legível e saúde agregada em `/api/health`.
- **Segurança:** o identificador do paciente é validado antes de entrar em consultas Flux (evita injeção), há limite de tamanho de upload, CORS configurável (`CORS_ORIGINS`, `CORS_ORIGIN_REGEX`) e o container roda como usuário não-root.

| Variável | Padrão | Descrição |
|---|---|---|
| `MULTIAGENTE_URL` / `CHATBOT_URL` / `VISION_URL` | `http://localhost:8001` / `:5001` / `:5002` | Serviços internos |
| `INFLUX_URL`, `INFLUX_TOKEN`, `INFLUX_ORG`, `INFLUX_BUCKET` | `http://localhost:8086`, —, `fiap`, `dados-medicos` | InfluxDB |
| `CORS_ORIGINS` | `*` | Origens permitidas (ex.: `https://cardioia.vercel.app`) |
| `TIMEOUT_LLM` | `180` | Tempo máximo das chamadas ao multiagente |

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080   # docs em http://localhost:8080/api/docs
pytest -q                                   # 12 testes
```
