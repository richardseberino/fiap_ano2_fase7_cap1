#!/usr/bin/env bash
# Implanta a plataforma no cluster do contexto atual do kubectl.
#   scripts/deploy-k8s.sh            # usa as imagens :latest (locais no Docker Desktop ou do GHCR)
#   TAG=v2.0.0 scripts/deploy-k8s.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f config/secrets.env ]; then
  cp config/.env.example config/secrets.env
  echo "Criado config/secrets.env a partir do exemplo. Revise tokens e senhas antes de usar em produção."
fi

echo "Contexto: $(kubectl config current-context)"
if [ -n "${TAG:-}" ]; then
  # fixa a versão das imagens geradas pelo pipeline (ex.: TAG=sha-1a2b3c4)
  sed -i.bak "s/newTag: .*/newTag: $TAG/" config/kustomization.yaml && rm -f config/kustomization.yaml.bak
fi

kubectl apply -k config/
echo "Aguardando os deployments..."
for d in mosquitto telegraf grafana multiagente chatbot gateway iot-simulador vision; do
  kubectl -n cardioia rollout status deploy/$d --timeout=600s
done
kubectl -n cardioia rollout status statefulset/influxdb --timeout=300s

kubectl -n cardioia get pods,svc
cat <<MSG

Acesso (Docker Desktop: localhost; nuvem: EXTERNAL-IP dos Services *-externo):
  Gateway/API : http://localhost:8080/api/docs
  Grafana     : http://localhost:3000
  MQTT        : localhost:1883  (tópico cardioia/sinais-vitais/<paciente>)
Teste rápido: scripts/teste-integracao.sh http://localhost:8080
MSG
