# CardioIA · App web e mobile (Expo)

Um único código React Native (Expo SDK 58 e Expo Router) gera:

- o **site** publicado na **Vercel** (`expo export -p web`, SPA estática em `dist/`), com layout mobile-first que fica centralizado com largura de celular no desktop;
- o **APK Android** gerado na nuvem pelo **EAS Build** (perfil `preview`).

## Telas

| Aba | Função | Endpoint do gateway |
|---|---|---|
| **Sinais** | Sinais vitais do IoT em tempo real (atualiza a cada 10 s), seletor de paciente, nível de alerta do edge e mini-gráficos de 15 min, 1 h ou 6 h | `GET /api/sinais-vitais`, `GET /api/sinais-vitais/{id}` |
| **Análise IA** | Formulário com validação das faixas fisiológicas; preenchimento pelos sinais do IoT ou por casos de exemplo; resultado do multiagente com risco, ações priorizadas, protocolos e trilha dos agentes | `GET /api/analise/sugestao/{id}`, `POST /api/analise` |
| **Assistente** | Chat de triagem com sugestões rápidas, resumo clínico e botão **Ligar 192** em emergência; modo *Minha análise* para perguntar ao Orquestrador sobre a última análise feita com LLM | `POST /api/chat` |
| **ECG** | Envio de imagem pela galeria ou pela câmera; classe prevista, severidade, confiança e probabilidade das 4 classes | `POST /api/ecg` |
| **Ajustes** | URL do gateway (salva no aparelho) e diagnóstico de todos os serviços | `GET /api/health` |

## Desenvolvimento

```bash
npm ci
cp .env.example .env              # EXPO_PUBLIC_API_URL=http://localhost:8080
npx expo start --web              # navegador
npx expo start                    # Expo Go / emulador (use o IP da máquina em Ajustes, não localhost)
npx tsc --noEmit && npx expo lint # verificação
```

## Publicação

| Destino | Manual | Pipeline |
|---|---|---|
| Vercel | `npx vercel --prod` (usa o [vercel.json](vercel.json)) | [.github/workflows/deploy-vercel.yml](../../.github/workflows/deploy-vercel.yml) |
| APK (EAS) | `npx eas-cli@latest build -p android --profile preview` | [.github/workflows/eas-build.yml](../../.github/workflows/eas-build.yml) |

`EXPO_PUBLIC_API_URL` é embutida no build: na Vercel, pela variável do projeto ou do repositório; no EAS, pelo `env` do perfil em [eas.json](eas.json). O usuário pode trocar a URL depois, na tela **Ajustes**.

O Android bloqueia HTTP sem TLS por padrão. O app libera esse tráfego (`expo-build-properties` → `usesCleartextTraffic`) para funcionar com um gateway de laboratório em `http://<ip>:8080`. Em produção, use HTTPS.
