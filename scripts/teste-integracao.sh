#!/usr/bin/env bash
# Testes de fumaça ponta a ponta contra o gateway (compose ou Kubernetes).
#   scripts/teste-integracao.sh [http://localhost:8080]
set -uo pipefail
BASE="${1:-http://localhost:8080}"
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
falhas=0

checar() {  # nome, comando que deve imprimir algo não vazio
  local nome="$1"; shift
  if saida=$("$@" 2>/dev/null) && [ -n "$saida" ]; then
    printf "  \033[32mOK\033[0m   %-38s %s\n" "$nome" "$saida"
  else
    printf "  \033[31mFALHA\033[0m %-37s\n" "$nome"; falhas=$((falhas+1))
  fi
}
py() { python3 -c "import json,sys; d=json.load(sys.stdin); $1"; }

echo "Gateway: $BASE"
checar "saúde agregada"            sh -c "curl -sf $BASE/api/health | python3 -c \"import json,sys;d=json.load(sys.stdin);print(d['status'],[s['servico'] for s in d['servicos'] if s['ok']])\""
checar "IoT: pacientes monitorados" sh -c "curl -sf $BASE/api/sinais-vitais | python3 -c \"import json,sys;d=json.load(sys.stdin);assert d;print(len(d),'pacientes')\""
PAC=$(curl -sf "$BASE/api/sinais-vitais" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d[0]['paciente_id'])" 2>/dev/null)
checar "IoT: série do paciente $PAC" sh -c "curl -sf '$BASE/api/sinais-vitais/$PAC?minutos=30' | python3 -c \"import json,sys;d=json.load(sys.stdin);print(len(d['serie']),'pontos')\""
checar "IoT → análise (sugestão)"   sh -c "curl -sf $BASE/api/analise/sugestao/$PAC | python3 -c \"import json,sys;d=json.load(sys.stdin);print('FC',d['dados']['fc_media'],'SpO2',d['dados']['spo2_media'])\""
checar "multiagente: análise"       sh -c "curl -sf -X POST $BASE/api/analise -H 'content-type: application/json' -d '{\"paciente_id\":\"SMOKE\",\"dados\":{\"idade_media\":62,\"carga_sistema\":92,\"tempo_espera\":75,\"fc_media\":118,\"spo2_media\":89,\"pa_sistolica\":100,\"temperatura\":37.5,\"densidade_eventos\":7,\"eventos_24h\":5,\"disponibilidade_recursos\":25}}' | python3 -c \"import json,sys;d=json.load(sys.stdin);r=d['recomendacao'];print(d['modo'],r['probabilidade_pico_risco'],r['classificacao_risco'])\""
checar "chatbot: triagem"           sh -c "curl -sf -X POST $BASE/api/chat -H 'content-type: application/json' -d '{\"message\":\"dor no peito forte\",\"conversation_id\":\"smoke\"}' | python3 -c \"import json,sys;d=json.load(sys.stdin);print(d['engine'],d['stage'])\""
IMG="$RAIZ/src/vision/assets/dados_exemplo1.png"
checar "vision: ECG"                sh -c "curl -sf -X POST $BASE/api/ecg -F image=@$IMG | python3 -c \"import json,sys;d=json.load(sys.stdin);print(d['rotulo'],round(d['confianca'],3))\""

[ $falhas -eq 0 ] && echo "Todos os testes passaram." || { echo "$falhas teste(s) falharam."; exit 1; }
