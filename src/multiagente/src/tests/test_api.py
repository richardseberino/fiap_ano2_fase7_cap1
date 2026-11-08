"""Testes da API HTTP do multiagente (modo offline, sem chave da OpenAI)."""
import pytest
from fastapi.testclient import TestClient

import api

CASO = {"idade_media": 62, "carga_sistema": 92, "tempo_espera": 75, "fc_media": 118, "spo2_media": 89,
        "pa_sistolica": 100, "temperatura": 37.5, "densidade_eventos": 7, "eventos_24h": 5,
        "disponibilidade_recursos": 25}


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with TestClient(api.app) as c:
        yield c


def test_health(cliente):
    r = cliente.get("/health").json()
    assert r["status"] == "ok" and r["llm_disponivel"] is False and r["modelo_ml"]


def test_exemplos(cliente):
    exemplos = cliente.get("/exemplos").json()
    assert {e["paciente_id"] for e in exemplos} >= {"PAC-001-enunciado"}


def test_analise_offline_caso_do_enunciado(cliente):
    r = cliente.post("/analisar", json={"paciente_id": "PAC-001", "dados": CASO}).json()
    assert r["modo"] == "offline"
    assert r["recomendacao"]["classificacao_risco"] == "ALTO"
    assert r["recomendacao"]["acoes_operacionais"] and len(r["trilha"]) == 3


def test_dados_invalidos_rejeitados(cliente):
    assert cliente.post("/analisar", json={"dados": {**CASO, "spo2_media": 140}}).status_code == 422


def test_modo_llm_sem_chave_retorna_409(cliente):
    assert cliente.post("/analisar", json={"dados": CASO, "modo": "llm"}).status_code == 409


def test_pergunta_exige_analise_llm(cliente):
    analise_id = cliente.post("/analisar", json={"dados": CASO}).json()["analise_id"]
    assert cliente.post(f"/analises/{analise_id}/perguntar", json={"pergunta": "por quê?"}).status_code == 409
    assert cliente.post("/analises/inexistente/perguntar", json={"pergunta": "?"}).status_code == 404
