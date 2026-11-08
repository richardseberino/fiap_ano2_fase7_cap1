"""Testes do gateway com os serviços internos e o InfluxDB simulados."""
import pytest
from fastapi.testclient import TestClient

from app import main
from app.influx import _validar_id, contar_subidas

SERIE = [
    {"horario": "t1", "bpm": 120.0, "oxigenacao": 88.0, "temperatura": 37.0, "pa_sistolica": 95.0, "nivel_alerta": 0.0},
    {"horario": "t2", "bpm": 130.0, "oxigenacao": 86.0, "temperatura": 37.4, "pa_sistolica": 85.0, "nivel_alerta": 2.0},
    {"horario": "t3", "bpm": 125.0, "oxigenacao": 87.0, "temperatura": 37.2, "pa_sistolica": 90.0, "nivel_alerta": 0.0},
    {"horario": "t4", "bpm": 125.0, "oxigenacao": 87.0, "temperatura": 37.2, "pa_sistolica": 90.0, "nivel_alerta": 1.0},
]


class SinaisFalsos:
    def serie(self, pid, minutos):
        return SERIE if pid == "PAC-1" else []

    def ultimas_leituras(self, horas):
        return [{"paciente_id": "PAC-1", "bpm": 125.0, "nivel_alerta": 1}]

    def contar_episodios_alerta(self, pid, minutos):
        return 4

    def saude(self):
        return {"servico": "influxdb", "ok": True}

    def fechar(self):
        pass


@pytest.fixture
def cliente(monkeypatch):
    chamadas = []

    async def chamar(metodo, url, **kw):
        chamadas.append((metodo, url, kw))
        if url.endswith("/analisar"):
            return {"modo": "offline", "recebido": kw["json"]}
        if "/perguntar" in url:
            return {"resposta": "resposta do orquestrador"}
        if url.endswith("/api/message"):
            return {"reply": "oi", "engine": "local"}
        if url.endswith("/api/predict"):
            return {"classe": "normal", "nome_arquivo": kw["files"]["image"][0]}
        return {"status": "ok"}

    monkeypatch.setattr(main, "_chamar", chamar)
    monkeypatch.setattr(main, "_sinais", SinaisFalsos())
    with TestClient(main.app) as c:
        c.chamadas = chamadas
        yield c


def test_contar_subidas():
    assert contar_subidas([0, 2, 2, 0, 1, 0, 0]) == 2
    assert contar_subidas([]) == 0


@pytest.mark.parametrize("pid", ['x") or (1', "a b", "", "x" * 65])
def test_id_invalido_rejeitado(pid):
    with pytest.raises(ValueError):
        _validar_id(pid)


def test_saude_agregada(cliente):
    r = cliente.get("/api/health").json()
    assert r["status"] == "ok" and len(r["servicos"]) == 4


def test_sinais_paciente(cliente):
    r = cliente.get("/api/sinais-vitais/PAC-1?minutos=30").json()
    assert r["ultimo"]["bpm"] == 125.0 and len(r["serie"]) == 4


def test_sinais_paciente_inexistente(cliente):
    assert cliente.get("/api/sinais-vitais/PAC-9").status_code == 404


def test_sugestao_usa_medias_do_iot(cliente):
    r = cliente.get("/api/analise/sugestao/PAC-1").json()
    d = r["dados"]
    assert d["fc_media"] == 125.0 and d["spo2_media"] == 87.0
    assert d["eventos_24h"] == 4 and d["densidade_eventos"] == 2
    assert d["carga_sistema"] is None  # campo operacional fica para o usuário


def test_analise_encaminhada_ao_multiagente(cliente):
    r = cliente.post("/api/analise", json={"paciente_id": "P", "dados": {"fc_media": 100}}).json()
    assert r["recebido"]["paciente_id"] == "P" and r["recebido"]["modo"] == "auto"


def test_chat_vai_ao_chatbot_ou_ao_multiagente(cliente):
    assert cliente.post("/api/chat", json={"message": "oi"}).json()["engine"] == "local"
    r = cliente.post("/api/chat", json={"message": "por quê?", "analise_id": "abc"}).json()
    assert r["engine"] == "multiagente" and r["reply"] == "resposta do orquestrador"
    assert cliente.chamadas[-1][1].endswith("/analises/abc/perguntar")


def test_ecg_repassa_imagem(cliente):
    r = cliente.post("/api/ecg", files={"image": ("exame.png", b"\x89PNG", "image/png")}).json()
    assert r["nome_arquivo"] == "exame.png"
