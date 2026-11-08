# Roteiro do vídeo de demonstração · CardioIA (≈ 5 min)

Objetivo: mostrar a plataforma funcionando de ponta a ponta, cobrindo os critérios de avaliação: URLs e APK, unificação do backend, IoT no Wokwi, clareza do diagrama e do fluxo de dados, e documentação.

**Preparação antes de gravar**
- Stack no ar (`scripts/deploy-k8s.sh` ou `docker compose up -d`) e `scripts/teste-integracao.sh` todo verde.
- Gateway acessível por HTTPS (Ingress ou `scripts/expor-gateway.sh`) e URL salva no app.
- Abas abertas: app na Vercel, Grafana, projeto Wokwi (ESP32-S3), terminal com `kubectl -n cardioia get pods`.
- Celular com o APK instalado (espelhar a tela ou gravar à parte).

| Tempo | Cena | O que mostrar / falar |
|---|---|---|
| 0:00–0:25 | Abertura | Grupo DRELL, problema (cinco protótipos isolados) e proposta (plataforma integrada do sensor ao celular) |
| 0:25–1:05 | Diagrama | `assets/arquitetura.png`: edge MicroPython → MQTT → Telegraf → InfluxDB; gateway único; três motores de IA; Vercel e EAS; tudo no Kubernetes |
| 1:05–1:35 | Kubernetes | `kubectl -n cardioia get pods,svc,hpa`: Deployments, StatefulSet do InfluxDB, HPA do gateway; `kustomization.yaml` e as imagens `ghcr.io/.../cardioia-*` |
| 1:35–2:20 | IoT no Wokwi | Projeto ESP32-S3 em execução: monitor serial com "MQTT conectado"; girar o potenciômetro de SpO2 para menos de 88 → LED vermelho pisca, buzzer, OLED "CRITICO"; apertar o botão de pânico → envio imediato. Citar que o mesmo firmware roda no Pico W e em Linux |
| 2:20–2:45 | Fluxo de dados | Grafana: paciente PAC-WOKWI-01 aparecendo e a linha do tempo de alertas. No app (aba Sinais), o mesmo paciente em vermelho |
| 2:45–3:30 | Análise multiagente | No app: "Analisar com a IA multiagente" → campos preenchidos com as médias do IoT → completar os dados operacionais → resultado (risco, ações P1/P2, protocolos, trilha dos 4 agentes) |
| 3:30–4:00 | Assistente | "Estou com dor no peito forte e falta de ar" → emergência, botão Ligar 192 e resumo clínico. Se houver chave OpenAI: modo "Minha análise" com uma pergunta ao Orquestrador |
| 4:00–4:30 | ECG | Aba ECG no celular (APK): escolher uma imagem de exame → classe, confiança e barras por classe |
| 4:30–4:50 | Pipelines | GitHub Actions: CI verde, build de imagens, deploy na Vercel (URL) e build EAS (link do APK) |
| 4:50–5:00 | Encerramento | README no template FIAP, relatório PDF; aviso de uso acadêmico |
