# CardioIA · Monitor de sinais vitais (MicroPython / CPython)
#
# Ciclo de 1 s:
#   1. lê os sensores (FC, SpO2, PA sistólica nos potenciômetros; temperatura no DHT22)
#   2. edge: média móvel + classificação NORMAL/ATENCAO/CRITICO no próprio dispositivo
#   3. alarme local (LEDs, buzzer, OLED) — funciona mesmo sem rede
#   4. publica no MQTT a cada ENVIO_MS, ou imediatamente se o nível piorar
#      ou se o botão de pânico for pressionado (fila offline se o broker cair)
import config
from compat import MICROPYTHON, sleep_ms, ticks_diff, ticks_ms
from conectividade import Conectividade
from edge import NIVEL_TEXTO, JanelaMovel, avaliar_sinais, montar_payload
from placa import criar_placa

CAMPOS = ("bpm", "oxigenacao", "temperatura", "pa_sistolica")


class Dispositivo:
    def __init__(self, placa, paciente_id=None, setor=None):
        self.placa = placa
        self.paciente_id = paciente_id or config.PACIENTE_ID
        self.setor = setor or config.SETOR
        self.topico = "%s/%s" % (config.MQTT_PREFIXO, self.paciente_id)
        self.janelas = {c: JanelaMovel(config.JANELA_AMOSTRAS) for c in CAMPOS}
        self.rede = Conectividade(placa, "cardioia-%s-%s" % (placa.id_dispositivo, self.paciente_id))
        self.ultimo_envio = None
        self.nivel_enviado = 0
        self.seq = 0

    def medias(self):
        return {c: j.media() for c, j in self.janelas.items()}

    def ciclo(self):
        for campo, valor in self.placa.ler().items():
            self.janelas[campo].adicionar(valor)
        sinais = self.medias()
        nivel, motivos = avaliar_sinais(sinais)
        panico = self.placa.panico_pressionado()
        if panico:
            motivos.append("Botao de panico acionado")

        self.placa.sinalizar(nivel, panico)
        self.placa.exibir(self.paciente_id, sinais, nivel, self.rede.conectado, len(self.rede.fila))

        agora = ticks_ms()
        vencido = self.ultimo_envio is None or ticks_diff(agora, self.ultimo_envio) >= config.ENVIO_MS
        piorou = nivel > self.nivel_enviado
        pronto = len(self.janelas["bpm"]) >= min(3, config.JANELA_AMOSTRAS)
        if pronto and (vencido or piorou or panico):
            self.seq += 1
            payload = montar_payload(self.paciente_id, self.setor, self.placa.id_dispositivo,
                                     self.placa.origem, sinais, nivel, motivos, panico, self.seq)
            self.rede.enviar(self.topico, payload)
            self.ultimo_envio = agora
            self.nivel_enviado = nivel
            print("[%s #%d] FC=%s SpO2=%s T=%s PAS=%s -> %s %s" % (
                self.paciente_id, self.seq, payload["bpm"], payload["oxigenacao"], payload["temperatura"],
                payload["pa_sistolica"], NIVEL_TEXTO[nivel], payload["motivos"]))
        self.rede.manter()

    def executar(self, ciclos=None):
        self.rede.iniciar()
        n = 0
        while ciclos is None or n < ciclos:
            inicio = ticks_ms()
            try:
                self.ciclo()
            except Exception as erro:  # o monitor nunca deve parar por uma falha pontual
                print("Erro no ciclo:", erro)
            n += 1
            sleep_ms(max(0, config.AMOSTRAGEM_MS - ticks_diff(ticks_ms(), inicio)))


def iniciar():
    placa = criar_placa()
    print("CardioIA monitor | placa=%s | paciente=%s | broker=%s" % (
        placa.modelo, config.PACIENTE_ID, config.MQTT_BROKER))
    Dispositivo(placa).executar()


if MICROPYTHON or __name__ == "__main__":
    iniciar()
