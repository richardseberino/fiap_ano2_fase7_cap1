"""Testes do firmware em CPython: edge computing, fila offline e ciclo do dispositivo."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "firmware"))

import config  # noqa: E402
from edge import ATENCAO, CRITICO, NORMAL, FilaEnvio, JanelaMovel, avaliar_sinais, mapear, montar_payload  # noqa: E402
from main import Dispositivo  # noqa: E402
from placa import PERFIS, PlacaLinux  # noqa: E402


def test_janela_movel_descarta_valores_antigos():
    j = JanelaMovel(3)
    for v in (10, 20, 30, 40):
        j.adicionar(v)
    assert j.media() == 30 and len(j) == 3
    j.adicionar(None)  # leitura falha é ignorada
    assert len(j) == 3


def test_sinais_normais():
    assert avaliar_sinais({"bpm": 75, "oxigenacao": 98, "temperatura": 36.5, "pa_sistolica": 120}) == (NORMAL, [])


def test_zona_de_atencao():
    nivel, motivos = avaliar_sinais({"bpm": 115, "oxigenacao": 97, "temperatura": 36.8, "pa_sistolica": 120})
    assert nivel == ATENCAO and motivos == ["Taquicardia (115)"]


def test_critico_alinhado_aos_protocolos():
    # Mesmo paciente do enunciado do multiagente: FC 118, SpO2 89 -> SpO2 aciona atenção; PAS 100 no limite
    nivel, _ = avaliar_sinais({"bpm": 125, "oxigenacao": 87, "temperatura": 38.4, "pa_sistolica": 85})
    assert nivel == CRITICO


def test_valor_ausente_nao_quebra():
    assert avaliar_sinais({"bpm": None, "oxigenacao": 97})[0] == NORMAL


def test_fila_offline_limitada():
    f = FilaEnvio(2)
    for i in range(3):
        f.adicionar(i)
    assert f.itens == [1, 2] and f.descartadas == 1


def test_mapear_adc():
    assert mapear(0, 65535, 40, 180) == 40
    assert mapear(65535, 65535, 40, 180) == 180


def test_payload_contrato_telegraf():
    p = montar_payload("PAC-1", "UTI", "dev", "wokwi",
                       {"bpm": 80.4, "oxigenacao": 96.66, "temperatura": 36.55, "pa_sistolica": 119.6},
                       NORMAL, [], False, 7)
    assert p["bpm"] == 80 and p["oxigenacao"] == 96.7 and p["pa_sistolica"] == 120
    assert p["nivel_alerta"] == 0 and p["alerta"] == "NORMAL" and p["seq"] == 7
    json.dumps(p)


class ClienteFalso:
    def __init__(self):
        self.mensagens, self.online = [], True

    def connect(self):
        if not self.online:
            raise OSError("broker fora")

    def publish(self, topico, msg):
        if not self.online:
            raise OSError("broker fora")
        self.mensagens.append((topico, json.loads(msg)))

    def disconnect(self):
        pass


def _dispositivo(perfil, cliente):
    placa = PlacaLinux(perfil)
    placa.criar_cliente_mqtt = lambda *a: cliente
    return Dispositivo(placa, "PAC-T", "UTI")


def test_dispositivo_publica_e_classifica_perfil_choque(monkeypatch):
    monkeypatch.setattr(config, "ENVIO_MS", 0)
    cliente = ClienteFalso()
    d = _dispositivo("choque", cliente)
    d.rede.iniciar()
    for _ in range(15):
        d.ciclo()
    assert cliente.mensagens, "nenhuma mensagem publicada"
    topico, ultima = cliente.mensagens[-1]
    assert topico.endswith("/PAC-T")
    assert ultima["nivel_alerta"] == CRITICO and ultima["origem"] == "simulador"


def test_store_and_forward(monkeypatch):
    monkeypatch.setattr(config, "ENVIO_MS", 0)
    monkeypatch.setattr(config, "RECONEXAO_MS", 0)
    cliente = ClienteFalso()
    d = _dispositivo("estavel", cliente)
    d.rede.iniciar()
    cliente.online = False
    for _ in range(6):
        d.ciclo()
    pendentes = len(d.rede.fila)
    assert pendentes > 0 and not cliente.mensagens
    cliente.online = True
    d.ciclo()
    assert len(d.rede.fila) == 0
    seqs = [m["seq"] for _, m in cliente.mensagens]
    assert seqs == sorted(seqs) and len(seqs) == pendentes + 1


def test_todos_os_perfis_validos():
    for perfil in PERFIS:
        leitura = PlacaLinux(perfil).ler()
        assert set(leitura) == {"bpm", "oxigenacao", "temperatura", "pa_sistolica"}
