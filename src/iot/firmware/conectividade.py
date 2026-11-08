# Wi-Fi + MQTT com reconexão automática e store-and-forward (fila offline).
import config
from compat import json, ticks_diff, ticks_ms
from edge import FilaEnvio


class Conectividade:
    def __init__(self, placa, cliente_id):
        self.placa = placa
        self.cliente_id = cliente_id
        self.fila = FilaEnvio(config.CAPACIDADE_FILA)
        self.cliente = None
        self.conectado = False
        self.ultima_tentativa = None

    def iniciar(self):
        self.placa.conectar_rede()
        self._conectar_mqtt()

    def _conectar_mqtt(self):
        self.ultima_tentativa = ticks_ms()
        try:
            if self.cliente is not None:
                try:
                    self.cliente.disconnect()
                except Exception:
                    pass
            self.cliente = self.placa.criar_cliente_mqtt(
                self.cliente_id, config.MQTT_BROKER, config.MQTT_PORTA,
                config.MQTT_USUARIO, config.MQTT_SENHA)
            self.cliente.connect()
            self.conectado = True
            print("MQTT conectado em %s:%d como %s" % (config.MQTT_BROKER, config.MQTT_PORTA, self.cliente_id))
        except Exception as erro:
            self.conectado = False
            print("MQTT indisponivel (%s); mensagens ficam na fila local" % erro)

    def enviar(self, topico, payload):
        self.fila.adicionar((topico, json.dumps(payload)))
        self.descarregar()

    def descarregar(self):
        """Envia as mensagens pendentes na ordem em que foram geradas."""
        while self.conectado and len(self.fila):
            topico, mensagem = self.fila.primeira()
            try:
                self.cliente.publish(topico, mensagem)
                self.fila.remover_primeira()
            except Exception as erro:
                self.conectado = False
                print("Falha ao publicar (%s); %d na fila" % (erro, len(self.fila)))

    def manter(self):
        """Chamado a cada ciclo: reconecta quando necessário e esvazia a fila."""
        if not self.conectado and (
                self.ultima_tentativa is None
                or ticks_diff(ticks_ms(), self.ultima_tentativa) >= config.RECONEXAO_MS):
            if not self.placa.rede_conectada():
                self.placa.conectar_rede(5000)
            self._conectar_mqtt()
        self.descarregar()
