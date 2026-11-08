# Lógica de Edge Computing do monitor de sinais vitais.
#
# Este módulo é Python puro: roda igual em MicroPython (ESP32, ESP32-S3, Pico W)
# e em CPython (Raspberry Pi, PC, container). Por isso ele não importa `machine`.
#
#  - JanelaMovel   : média móvel que filtra ruído dos sensores antes de enviar
#  - avaliar_sinais: classifica a leitura em NORMAL / ATENCAO / CRITICO no próprio
#                    dispositivo (o alarme local funciona mesmo sem rede)
#  - FilaEnvio     : store-and-forward; guarda mensagens enquanto o MQTT está fora
#  - montar_payload: JSON enviado ao broker (contrato com o Telegraf/InfluxDB)

NORMAL = 0
ATENCAO = 1
CRITICO = 2
NIVEL_TEXTO = ("NORMAL", "ATENCAO", "CRITICO")

# Limites alinhados à base de protocolos do serviço multiagente:
# CRITICO = valor que aciona um protocolo; ATENCAO = zona de margem antes dele.
# (campo, operador, limite_atencao, limite_critico, descricao)
LIMITES = (
    ("oxigenacao", "<", 92, 88, "SpO2 baixa"),
    ("bpm", ">", 110, 120, "Taquicardia"),
    ("bpm", "<", 55, 45, "Bradicardia"),
    ("temperatura", ">", 37.5, 38.0, "Febre"),
    ("temperatura", "<", 35.5, 35.0, "Hipotermia"),
    ("pa_sistolica", "<", 100, 90, "Hipotensao"),
    ("pa_sistolica", ">", 160, 180, "Hipertensao"),
)


class JanelaMovel:
    """Média móvel de tamanho fixo (sem alocar listas novas a cada amostra)."""

    def __init__(self, tamanho):
        self.tamanho = tamanho
        self.valores = []
        self.indice = 0

    def adicionar(self, valor):
        if valor is None:
            return
        if len(self.valores) < self.tamanho:
            self.valores.append(valor)
        else:
            self.valores[self.indice] = valor
        self.indice = (self.indice + 1) % self.tamanho

    def media(self):
        if not self.valores:
            return None
        return sum(self.valores) / len(self.valores)

    def __len__(self):
        return len(self.valores)


def _ultrapassa(valor, operador, limite):
    return valor > limite if operador == ">" else valor < limite


def avaliar_sinais(sinais, limites=LIMITES):
    """Retorna (nivel, motivos) para um dicionário de sinais vitais."""
    nivel = NORMAL
    motivos = []
    for campo, operador, lim_atencao, lim_critico, descricao in limites:
        valor = sinais.get(campo)
        if valor is None:
            continue
        if _ultrapassa(valor, operador, lim_critico):
            nivel = CRITICO
            motivos.append("%s critica (%s)" % (descricao, _fmt(valor)))
        elif _ultrapassa(valor, operador, lim_atencao):
            nivel = max(nivel, ATENCAO)
            motivos.append("%s (%s)" % (descricao, _fmt(valor)))
    return nivel, motivos


def _fmt(valor):
    return ("%.1f" % valor) if isinstance(valor, float) else str(valor)


class FilaEnvio:
    """Fila limitada de mensagens pendentes (descarta as mais antigas se encher)."""

    def __init__(self, capacidade):
        self.capacidade = capacidade
        self.itens = []
        self.descartadas = 0

    def adicionar(self, mensagem):
        if len(self.itens) >= self.capacidade:
            self.itens.pop(0)
            self.descartadas += 1
        self.itens.append(mensagem)

    def primeira(self):
        return self.itens[0] if self.itens else None

    def remover_primeira(self):
        if self.itens:
            self.itens.pop(0)

    def __len__(self):
        return len(self.itens)


def arredondar(sinais):
    return {
        "bpm": None if sinais.get("bpm") is None else int(round(sinais["bpm"])),
        "oxigenacao": None if sinais.get("oxigenacao") is None else round(sinais["oxigenacao"], 1),
        "temperatura": None if sinais.get("temperatura") is None else round(sinais["temperatura"], 1),
        "pa_sistolica": None if sinais.get("pa_sistolica") is None else int(round(sinais["pa_sistolica"])),
    }


def montar_payload(paciente_id, setor, dispositivo, origem, sinais, nivel, motivos, panico, seq):
    """Mensagem publicada em  <prefixo>/<paciente_id>  (consumida pelo Telegraf)."""
    payload = arredondar(sinais)
    payload.update({
        "paciente_id": paciente_id,
        "setor": setor,
        "dispositivo": dispositivo,
        "origem": origem,
        "nivel_alerta": nivel,
        "alerta": NIVEL_TEXTO[nivel],
        "motivos": "; ".join(motivos),
        "panico": 1 if panico else 0,
        "seq": seq,
    })
    return payload


def mapear(valor_bruto, maximo_bruto, minimo, maximo):
    """Converte a leitura do ADC (0..maximo_bruto) para a faixa fisiológica [minimo, maximo]."""
    return minimo + (valor_bruto / maximo_bruto) * (maximo - minimo)
