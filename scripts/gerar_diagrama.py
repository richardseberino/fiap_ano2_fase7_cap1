"""Gera assets/arquitetura.svg (e .png via Chrome headless em scripts/gerar-documentos.sh)."""
from pathlib import Path

W, H = 1680, 1060
out = []
a = out.append

a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
  'font-family="Inter, Segoe UI, Helvetica, Arial, sans-serif">')
a('<defs>' + ''.join(
    f'<marker id="{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
    f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
    for i, c in [("m-cinza", "#3D4B52"), ("m-teal", "#0B7A84"), ("m-ocre", "#8A5A00"), ("m-azul", "#2F6FD0"),
                 ("m-roxo", "#6B3FA0"), ("m-neutro", "#5B6B73"), ("m-preto", "#0E1A1F")]) + '</defs>')
a(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>')
a('<text x="40" y="52" font-size="30" font-weight="700" fill="#0E1A1F">CardioIA · Arquitetura integrada</text>')
a('<text x="40" y="82" font-size="16" fill="#5B6B73">IoT (MicroPython) → MQTT → InfluxDB · Gateway único → '
  'Multiagente, Chatbot e Visão · App web (Vercel) e Android (EAS) · Kubernetes</text>')

MARC = {"#3D4B52": "m-cinza", "#0B7A84": "m-teal", "#8A5A00": "m-ocre", "#2F6FD0": "m-azul",
        "#6B3FA0": "m-roxo", "#5B6B73": "m-neutro", "#0E1A1F": "m-preto"}


def grupo(x, y, w, h, titulo, cor, fundo, tracejado=False):
    t = 'stroke-dasharray="8 6"' if tracejado else ""
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{fundo}" stroke="{cor}" stroke-width="2" {t}/>')
    a(f'<text x="{x+18}" y="{y+30}" font-size="15" font-weight="700" fill="{cor}" letter-spacing="0.6">{titulo}</text>')


def caixa(x, y, w, h, titulo, sub=(), cor="#0B7A84", fundo="#FFFFFF", tam=16):
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fundo}" stroke="{cor}" stroke-width="1.6"/>')
    linhas = [titulo, *sub]
    y0 = y + h / 2 - (len(linhas) - 1) * 10 + 5
    for i, linha in enumerate(linhas):
        a(f'<text x="{x+w/2}" y="{y0+i*20}" text-anchor="middle" font-size="{tam if i == 0 else 13}" '
          f'font-weight="{700 if i == 0 else 400}" fill="{"#0E1A1F" if i == 0 else "#5B6B73"}">{linha}</text>')


def seta(pts, cor="#3D4B52", tracejado=False, rotulo=None, rx=0, ry=0, anc="middle"):
    d = "M" + " L".join(f"{x},{y}" for x, y in pts)
    t = 'stroke-dasharray="6 5"' if tracejado else ""
    a(f'<path d="{d}" fill="none" stroke="{cor}" stroke-width="2" marker-end="url(#{MARC[cor]})" {t}/>')
    if rotulo:
        a(f'<text x="{rx}" y="{ry}" text-anchor="{anc}" font-size="12.5" fill="{cor}" font-weight="600">{rotulo}</text>')


OCRE, AZUL, TEAL, ROXO, NEUTRO, PRETO = "#8A5A00", "#2F6FD0", "#0B7A84", "#6B3FA0", "#5B6B73", "#0E1A1F"

# ---- Edge
grupo(30, 110, 330, 610, "EDGE · DISPOSITIVOS IoT", OCRE, "#FFF9EC")
caixa(55, 155, 280, 110, "ESP32-S3 / Pico W / ESP32", ["MicroPython (Wokwi)", "FC · SpO2 · PA · DHT22 · OLED"], cor=OCRE)
caixa(55, 285, 280, 95, "Edge computing", ["média móvel · alerta local", "fila offline (store-and-forward)"], cor=OCRE, tam=15)
caixa(55, 410, 280, 90, "broker.hivemq.com", ["MQTT público (rede Wokwi-GUEST)"], cor=OCRE, tam=15)
caixa(55, 560, 280, 110, "Dispositivo Linux", ["mesmo firmware em CPython", "Raspberry Pi / container"], cor=OCRE)
seta([(195, 265), (195, 285)], OCRE)
seta([(195, 380), (195, 410)], OCRE, rotulo="MQTT 1883", rx=255, ry=400)

# ---- Cluster
grupo(400, 110, 880, 860, "CLUSTER KUBERNETES · namespace cardioia", TEAL, "#F2F9FA")
grupo(425, 150, 830, 250, "Ingestão e observabilidade", AZUL, "#F4F8FF", tracejado=True)
caixa(450, 200, 170, 90, "Mosquitto", ["broker MQTT", "bridge Wokwi"], cor=AZUL)
caixa(655, 200, 170, 90, "Telegraf", ["MQTT → Influx", "json_v2"], cor=AZUL)
caixa(860, 200, 170, 90, "InfluxDB 2.7", ["StatefulSet + PVC", "séries temporais"], cor=AZUL)
caixa(1065, 200, 170, 90, "Grafana", ["dashboard", "provisionado"], cor=AZUL)
seta([(620, 245), (655, 245)])
seta([(825, 245), (860, 245)])
seta([(1030, 245), (1065, 245)], rotulo="Flux", rx=1048, ry=236)
caixa(450, 315, 170, 65, "iot-simulador", ["5 pacientes virtuais"], cor=OCRE, tam=14)
seta([(535, 315), (535, 290)], OCRE)

caixa(640, 470, 400, 110, "CardioIA Gateway (BFF)",
      ["FastAPI · /api/* · CORS · HPA 2–6 réplicas", "sinais IoT · sugestão p/ análise · roteamento"],
      cor=TEAL, fundo="#DDF0F1", tam=19)
seta([(945, 290), (945, 380), (900, 380), (900, 470)], AZUL, rotulo="consulta Flux", rx=955, ry=440, anc="start")

grupo(425, 640, 830, 300, "Motores de IA", ROXO, "#F8F4FD", tracejado=True)
caixa(450, 690, 250, 140, "Multiagente",
      ["OpenAI Agents SDK", "Orquestrador → Analista →", "Protocolos → Planejador", "Random Forest (pico de risco)"], cor=ROXO)
caixa(715, 690, 250, 140, "Chatbot de triagem", ["Flask · NLP local", "IBM Watson (opcional)", "red flags · resumo clínico"], cor=ROXO)
caixa(980, 690, 250, 140, "Visão computacional", ["Flask · TensorFlow", "CNN ECG · 4 classes", "97,6% de acurácia"], cor=ROXO)
seta([(740, 580), (740, 615), (575, 615), (575, 690)], ROXO, rotulo="POST /analisar", rx=590, ry=607, anc="start")
seta([(840, 580), (840, 690)], ROXO, rotulo="POST /api/message", rx=832, ry=670, anc="end")
seta([(940, 580), (940, 615), (1105, 615), (1105, 690)], ROXO, rotulo="POST /api/predict", rx=1000, ry=607, anc="start")
a(f'<text x="840" y="958" text-anchor="middle" font-size="12" fill="{NEUTRO}">Services ClusterIP · probes · '
  'requests/limits · runAsNonRoot · Secrets e ConfigMaps gerados pelo Kustomize</text>')

# setas da borda desenhadas depois do cluster para ficarem por cima
seta([(335, 455), (380, 455), (380, 230), (450, 230)], OCRE, rotulo="bridge", rx=340, ry=447, anc="start")
seta([(335, 615), (390, 615), (390, 262), (450, 262)], OCRE, tracejado=True, rotulo="MQTT", rx=340, ry=607, anc="start")

# ---- Canais do usuário
grupo(1320, 110, 330, 420, "CANAIS DO USUÁRIO", PRETO, "#F6F7F8")
caixa(1345, 160, 280, 85, "Profissional de saúde", ["Grafana (painel IoT)"], cor=PRETO, tam=15)
caixa(1345, 265, 280, 110, "App web (Expo Web)", ["Vercel · HTTPS", "layout mobile-first"], cor=PRETO)
caixa(1345, 395, 280, 110, "App Android (.apk)", ["EAS Build · Expo SDK 58", "mesmo código React Native"], cor=PRETO)
seta([(1345, 202), (1235, 245)], AZUL)
seta([(1345, 320), (1300, 320), (1300, 505), (1040, 505)], TEAL, rotulo="HTTPS /api/*", rx=1170, ry=497)
seta([(1345, 450), (1300, 450)], TEAL)

# ---- Serviços externos (LLM opcionais)
grupo(1320, 570, 330, 190, "SERVIÇOS EXTERNOS", NEUTRO, "#FAFAFA", tracejado=True)
caixa(1345, 610, 280, 55, "OpenAI API", ["gpt-4.1-mini (opcional)"], cor=NEUTRO, tam=15)
caixa(1345, 685, 280, 55, "IBM Watson Assistant", ["opcional"], cor=NEUTRO, tam=15)
seta([(575, 830), (575, 895), (1292, 895), (1292, 637), (1345, 637)], NEUTRO, tracejado=True,
     rotulo="sem chave → modo offline (ML + protocolos)", rx=1060, ry=914)
seta([(840, 830), (840, 868), (1272, 868), (1272, 712), (1345, 712)], NEUTRO, tracejado=True)

# ---- CI/CD
grupo(30, 750, 330, 290, "CI/CD · GITHUB ACTIONS", PRETO, "#F6F7F8")
for i, (t, s) in enumerate([("CI", "testes · lint · kubeconform"), ("Build de imagens", "GHCR · amd64 + arm64"),
                            ("Deploy Kubernetes", "kubectl apply -k config/"), ("Vercel + EAS Build", "web (produção) · .apk")]):
    caixa(55, 795 + i * 58, 280, 48, t, [s], cor=PRETO, tam=14)
seta([(360, 940), (400, 940)], PRETO)
a(f'<text x="1660" y="1045" text-anchor="end" font-size="12" fill="#93A4AB">Grupo DRELL · FIAP · Fase 7</text>')
a("</svg>")

destino = Path(__file__).resolve().parents[1] / "assets" / "arquitetura.svg"
destino.write_text("\n".join(out), encoding="utf-8")
print(f"Gerado {destino}")
