#!/usr/bin/env bash
# Gera as imagens de contêiner de todos os serviços.
#   scripts/build-images.sh                 # tag latest, só local
#   scripts/build-images.sh v2.0.0 --push   # publica no registro (padrão ghcr.io/richardseberino)
set -euo pipefail
cd "$(dirname "$0")/.."
TAG="${1:-latest}"
PUSH="${2:-}"
REGISTRY="${REGISTRY:-ghcr.io/richardseberino}"
SERVICOS=(gateway multiagente chatbot vision iot)

for s in "${SERVICOS[@]}"; do
  nome="cardioia-$s"; [ "$s" = iot ] && nome="cardioia-iot-simulador"
  echo "==> $REGISTRY/$nome:$TAG"
  if [ "$PUSH" = "--push" ]; then
    docker buildx build --platform linux/amd64,linux/arm64 -t "$REGISTRY/$nome:$TAG" --push "src/$s"
  else
    docker build -t "$REGISTRY/$nome:$TAG" "src/$s"
  fi
done
echo "Imagens geradas com a tag $TAG"
