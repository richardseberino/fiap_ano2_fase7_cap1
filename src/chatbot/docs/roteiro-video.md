# Roteiro do vídeo de demonstração (até 3 minutos)

> Objetivo: mostrar a interação usuário ↔ assistente e o funcionamento do fluxo.

| Tempo | Cena | O que mostrar / falar |
|---|---|---|
| 0:00–0:20 | Abertura | Nome do projeto, disciplina, integrantes. "Assistente de triagem inicial em cardiologia." |
| 0:20–0:40 | Arquitetura | Mostrar o diagrama do README: frontend → Flask → Watson / motor local. Citar `USE_WATSON`. |
| 0:40–1:00 | Watson Assistant | Tela do Watson com intents, entities e dialog nodes importados do JSON. |
| 1:00–1:20 | Subir o projeto | Terminal: `python run.py`. Abrir `http://127.0.0.1:5000`. Mostrar o badge "motor: local/watson". |
| 1:20–1:55 | Conversa feliz | "Oi" → "Estou com palpitação" → responder intensidade e duração → mostrar o **resumo clínico** e a classificação. |
| 1:55–2:25 | Sinal de alarme | "Estou com dor no peito muito forte, suando frio e com falta de ar" → resposta de EMERGÊNCIA + orientação 192. |
| 2:25–2:45 | Exceção | Mensagem sem sentido → pedido de reformulação → segunda falha → mensagem de escopo. |
| 2:45–3:00 | Encerramento | "Pode encerrar" → resumo final + disclaimer. GitHub do projeto na tela. |

Dicas:
- Gravar a tela em 1280×720, fonte do terminal legível.
- Ter o `.env` já configurado antes de gravar.
- Se for demonstrar o Watson real, testar a conexão minutos antes.
