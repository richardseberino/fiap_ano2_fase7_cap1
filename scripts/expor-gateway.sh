#!/usr/bin/env bash
# Expõe o gateway local em HTTPS público (Cloudflare Quick Tunnel), útil para a demonstração:
# o app na Vercel (HTTPS) e o APK passam a alcançar o backend rodando no cluster/compose local.
#   scripts/expor-gateway.sh [porta-local]   -> imprime https://<aleatorio>.trycloudflare.com
# Para produção, use o overlay config/k8s/ingress (domínio próprio + TLS).
set -euo pipefail
PORTA="${1:-8080}"
echo "Abrindo túnel para http://localhost:$PORTA ... (Ctrl+C encerra)"
docker run --rm cloudflare/cloudflared:2025.11.1 tunnel --no-autoupdate --url "http://host.docker.internal:$PORTA"
