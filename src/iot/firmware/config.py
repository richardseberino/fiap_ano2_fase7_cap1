# Configuração do monitor de sinais vitais.
# Em Linux/container, cada valor pode ser sobrescrito por variável de ambiente
# com o mesmo nome (ex.: MQTT_BROKER=mosquitto python main.py).

WIFI_SSID = "Wokwi-GUEST"
WIFI_SENHA = ""

# Broker MQTT.
#  - Wokwi web (sem gateway): broker público; o Mosquitto do cluster faz bridge
#    do tópico abaixo (config/mosquitto/mosquitto.conf).
#  - Wokwi com Private Gateway / dispositivo físico na mesma rede: IP do Mosquitto
#    (ou "host.wokwi.internal" no gateway local do Wokwi).
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORTA = 1883
MQTT_USUARIO = ""
MQTT_SENHA = ""
MQTT_PREFIXO = "fiap-drell/cardioia/sinais-vitais"   # tópico final: <prefixo>/<paciente_id>

PACIENTE_ID = "PAC-WOKWI-01"
SETOR = "UTI_02"

AMOSTRAGEM_MS = 1000        # leitura dos sensores a cada 1 s
JANELA_AMOSTRAS = 10        # média móvel de 10 leituras (edge: filtra ruído)
ENVIO_MS = 10000            # publica a média a cada 10 s
CAPACIDADE_FILA = 60        # mensagens guardadas offline (~10 min a 1 msg/10 s)
RECONEXAO_MS = 5000         # intervalo mínimo entre tentativas de reconexão

# Faixas fisiológicas dos potenciômetros (simulação dos sensores no Wokwi)
FAIXA_BPM = (40, 180)
FAIXA_SPO2 = (80, 100)
FAIXA_PA_SISTOLICA = (70, 200)

# Perfil clínico do sensor simulado em Linux (estavel, taquicardia, hipoxemia, febril, choque)
PERFIL_SIMULADO = "estavel"


def _aplicar_ambiente():
    try:
        import os
        ambiente = os.environ
    except (ImportError, AttributeError):
        return  # MicroPython: sem variáveis de ambiente
    g = globals()
    for nome in list(g):
        if nome.isupper() and nome in ambiente:
            atual = g[nome]
            bruto = ambiente[nome]
            if isinstance(atual, bool):
                g[nome] = bruto.lower() in ("1", "true", "sim", "yes")
            elif isinstance(atual, int):
                g[nome] = int(bruto)
            elif isinstance(atual, tuple):
                g[nome] = tuple(float(x) for x in bruto.split(","))
            else:
                g[nome] = bruto


_aplicar_ambiente()
