# Camada de abstração de hardware (HAL).
#
# O mesmo firmware roda em:
#   ESP32 (DevKitC v4)       -> projeto Wokwi wokwi/esp32
#   ESP32-S3 (DevKitC-1)     -> projeto Wokwi wokwi/esp32-s3 (dual core 240 MHz, 512 KB SRAM + PSRAM)
#   Raspberry Pi Pico W/2 W  -> projeto Wokwi wokwi/pico-w (RP2040/RP2350)
#   Linux (Raspberry Pi 4/5, PC, container) -> sensores simulados, MQTT via paho-mqtt
#
# Só este arquivo conhece pinos e periféricos; main.py e edge.py não mudam entre placas.

import random

import config
from compat import MICROPYTHON, plataforma, sleep_ms, ticks_diff, ticks_ms
from edge import ATENCAO, CRITICO, NIVEL_TEXTO, mapear

# Mapa de pinos por placa (ADC: potenciômetros simulando os sensores analógicos)
PINOS = {
    "ESP32": dict(bpm=34, spo2=35, pa=32, dht=15, led_vermelho=23, led_verde=19,
                  buzzer=18, botao=4, sda=21, scl=22),
    "ESP32S3": dict(bpm=4, spo2=5, pa=6, dht=15, led_vermelho=16, led_verde=17,
                    buzzer=18, botao=21, sda=8, scl=9),
    "RP2": dict(bpm=26, spo2=27, pa=28, dht=15, led_vermelho=14, led_verde=13,
                buzzer=12, botao=16, sda=4, scl=5),
}


def identificar_placa():
    p = plataforma()
    if p == "rp2":
        return "RP2"
    if p == "esp32":
        import os
        maquina = os.uname().machine.upper().replace("-", "")
        return "ESP32S3" if "ESP32S3" in maquina else "ESP32"
    return "LINUX"


def criar_placa():
    modelo = identificar_placa()
    if modelo == "LINUX":
        return PlacaLinux(config.PERFIL_SIMULADO)
    return PlacaMicro(modelo)


# ---------------------------------------------------------------------------
# Placas MicroPython (ESP32 / ESP32-S3 / Pico W)
# ---------------------------------------------------------------------------

class PlacaMicro:
    origem = "wokwi"

    def __init__(self, modelo):
        from machine import ADC, I2C, PWM, Pin
        import dht

        self.modelo = modelo
        pinos = PINOS[modelo]
        self.adc_bpm = self._adc(ADC, Pin, pinos["bpm"])
        self.adc_spo2 = self._adc(ADC, Pin, pinos["spo2"])
        self.adc_pa = self._adc(ADC, Pin, pinos["pa"])
        self.dht = dht.DHT22(Pin(pinos["dht"]))
        self.led_vermelho = Pin(pinos["led_vermelho"], Pin.OUT)
        self.led_verde = Pin(pinos["led_verde"], Pin.OUT)
        self.buzzer = PWM(Pin(pinos["buzzer"]))
        self.buzzer.freq(2000)
        self.buzzer.duty_u16(0)
        self._panico = False
        self.botao = Pin(pinos["botao"], Pin.IN, Pin.PULL_UP)
        self.botao.irq(trigger=Pin.IRQ_FALLING, handler=self._ao_pressionar)
        self._temp = None
        self._ultima_leitura_dht = None
        self._piscar = False
        self.oled = None
        try:
            from ssd1306 import SSD1306_I2C
            i2c = I2C(0, sda=Pin(pinos["sda"]), scl=Pin(pinos["scl"]), freq=400000)
            if 0x3C in i2c.scan():
                self.oled = SSD1306_I2C(128, 64, i2c)
        except Exception as erro:  # display é opcional
            print("OLED indisponivel:", erro)
        import machine
        self.id_dispositivo = "%s-%s" % (modelo.lower(), "".join("%02x" % b for b in machine.unique_id()))
        self.wlan = None

    @staticmethod
    def _adc(ADC, Pin, numero):
        adc = ADC(Pin(numero))
        try:
            adc.atten(ADC.ATTN_11DB)  # ESP32: faixa completa 0..3,3 V
        except AttributeError:
            pass  # RP2 não tem atenuação
        return adc

    def _ao_pressionar(self, _pino):
        self._panico = True

    # --- rede -------------------------------------------------------------
    def conectar_rede(self, timeout_ms=15000):
        import network
        if self.wlan is None:
            self.wlan = network.WLAN(network.STA_IF)
            self.wlan.active(True)
        if self.wlan.isconnected():
            return True
        print("Conectando ao Wi-Fi", config.WIFI_SSID, end="")
        self.wlan.connect(config.WIFI_SSID, config.WIFI_SENHA)
        inicio = ticks_ms()
        while not self.wlan.isconnected() and ticks_diff(ticks_ms(), inicio) < timeout_ms:
            print(".", end="")
            sleep_ms(200)
        ok = self.wlan.isconnected()
        print(" IP:", self.wlan.ifconfig()[0] if ok else "sem conexao")
        return ok

    def rede_conectada(self):
        return self.wlan is not None and self.wlan.isconnected()

    def criar_cliente_mqtt(self, cliente_id, broker, porta, usuario, senha):
        from umqtt.simple import MQTTClient
        return MQTTClient(cliente_id, broker, port=porta, user=usuario or None,
                          password=senha or None, keepalive=60)

    # --- sensores ----------------------------------------------------------
    def ler(self):
        maximo = 65535
        leitura = {
            "bpm": mapear(self.adc_bpm.read_u16(), maximo, *config.FAIXA_BPM),
            "oxigenacao": mapear(self.adc_spo2.read_u16(), maximo, *config.FAIXA_SPO2),
            "pa_sistolica": mapear(self.adc_pa.read_u16(), maximo, *config.FAIXA_PA_SISTOLICA),
        }
        # DHT22 aceita no máximo uma leitura a cada 2 s
        agora = ticks_ms()
        if self._ultima_leitura_dht is None or ticks_diff(agora, self._ultima_leitura_dht) >= 2000:
            self._ultima_leitura_dht = agora
            try:
                self.dht.measure()
                self._temp = self.dht.temperature()
            except OSError as erro:
                print("Falha no DHT22:", erro)
        leitura["temperatura"] = self._temp
        return leitura

    def panico_pressionado(self):
        estado, self._panico = self._panico, False
        return estado

    # --- atuadores ---------------------------------------------------------
    def sinalizar(self, nivel, panico=False):
        self._piscar = not self._piscar
        self.led_verde.value(1 if nivel < ATENCAO else 0)
        if nivel >= CRITICO:
            self.led_vermelho.value(1 if self._piscar else 0)   # pisca no crítico
        else:
            self.led_vermelho.value(1 if nivel >= ATENCAO else 0)
        tocar = panico or (nivel >= CRITICO and self._piscar)
        self.buzzer.duty_u16(32768 if tocar else 0)

    def exibir(self, paciente_id, sinais, nivel, conectado, pendentes):
        if self.oled is None:
            return
        o = self.oled
        o.fill(0)
        o.text(paciente_id[:16], 0, 0)
        o.hline(0, 9, 128, 1)
        o.text("FC   %s bpm" % _txt(sinais.get("bpm"), "%d"), 0, 12)
        o.text("SpO2 %s %%" % _txt(sinais.get("oxigenacao"), "%.1f"), 0, 22)
        o.text("Temp %s C" % _txt(sinais.get("temperatura"), "%.1f"), 0, 32)
        o.text("PAS  %s mmHg" % _txt(sinais.get("pa_sistolica"), "%d"), 0, 42)
        if nivel >= ATENCAO:
            o.fill_rect(0, 53, 128, 11, 1)
            o.text(NIVEL_TEXTO[nivel], 2, 55, 0)
            o.text("Q%d" % pendentes if pendentes else ("ON" if conectado else "OFF"), 104, 55, 0)
        else:
            o.text("NORMAL", 0, 55)
            o.text(("MQTT ok" if conectado else "offline Q%d" % pendentes), 64, 55)
        o.show()


def _txt(valor, formato):
    if valor is None:
        return "--"
    return formato % (int(round(valor)) if formato == "%d" else valor)


# ---------------------------------------------------------------------------
# Linux: Raspberry Pi / PC / container (sensores simulados por perfil clínico)
# ---------------------------------------------------------------------------

PERFIS = {
    #              bpm   spo2  temp  pas
    "estavel":     (76, 97.5, 36.6, 122),
    "taquicardia": (116, 95.0, 37.2, 112),
    "hipoxemia":   (104, 89.5, 37.0, 118),
    "febril":      (102, 95.5, 38.3, 116),
    "choque":      (126, 87.5, 37.6, 86),
}
_RUIDO = {"bpm": 2.5, "oxigenacao": 0.35, "temperatura": 0.04, "pa_sistolica": 2.0}
_CAMPOS = ("bpm", "oxigenacao", "temperatura", "pa_sistolica")


class _ClientePaho:
    """Adapta o paho-mqtt à interface do umqtt.simple (connect/publish/disconnect)."""

    def __init__(self, cliente_id, broker, porta, usuario, senha):
        import paho.mqtt.client as mqtt
        self.broker, self.porta = broker, porta
        self.c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cliente_id)
        if usuario:
            self.c.username_pw_set(usuario, senha)

    def connect(self):
        self.c.connect(self.broker, self.porta, keepalive=60)
        self.c.loop_start()
        inicio = ticks_ms()
        while not self.c.is_connected():
            if ticks_diff(ticks_ms(), inicio) > 5000:
                self.c.loop_stop()
                raise OSError("timeout ao conectar no broker %s" % self.broker)
            sleep_ms(50)

    def publish(self, topico, mensagem):
        if not self.c.is_connected():
            raise OSError("MQTT desconectado")
        info = self.c.publish(topico, mensagem, qos=1)
        if info.rc != 0:
            raise OSError("falha ao publicar (rc=%s)" % info.rc)

    def disconnect(self):
        self.c.loop_stop()
        self.c.disconnect()


class PlacaLinux:
    origem = "simulador"

    def __init__(self, perfil="estavel", id_dispositivo=None):
        if perfil not in PERFIS:
            raise ValueError("perfil desconhecido: %s (use %s)" % (perfil, ", ".join(PERFIS)))
        self.modelo = "LINUX"
        self.perfil = perfil
        self.base = dict(zip(_CAMPOS, PERFIS[perfil]))
        self.atual = dict(self.base)
        self.episodio = 0          # amostras restantes de um episódio transitório
        self.id_dispositivo = id_dispositivo or "linux-%s" % perfil
        self._ultimo_nivel = None

    def conectar_rede(self, timeout_ms=0):
        return True

    def rede_conectada(self):
        return True

    def criar_cliente_mqtt(self, cliente_id, broker, porta, usuario, senha):
        return _ClientePaho(cliente_id, broker, porta, usuario, senha)

    def ler(self):
        # Passeio aleatório com reversão à média do perfil + episódios transitórios ocasionais.
        if self.episodio == 0 and random.random() < 0.004:
            self.episodio = random.randint(30, 90)
        alvo = dict(self.base)
        if self.episodio:
            self.episodio -= 1
            alvo["bpm"] += 22
            alvo["oxigenacao"] -= 4
        for campo in _CAMPOS:
            v = self.atual[campo]
            v += (alvo[campo] - v) * 0.15 + random.gauss(0, _RUIDO[campo])
            self.atual[campo] = v
        self.atual["oxigenacao"] = min(100.0, self.atual["oxigenacao"])
        return dict(self.atual)

    def panico_pressionado(self):
        return False

    def sinalizar(self, nivel, panico=False):
        if nivel != self._ultimo_nivel:
            print("[%s] LED: %s" % (self.id_dispositivo, NIVEL_TEXTO[nivel]))
            self._ultimo_nivel = nivel

    def exibir(self, paciente_id, sinais, nivel, conectado, pendentes):
        pass  # sem display; a publicação já é registrada no log
