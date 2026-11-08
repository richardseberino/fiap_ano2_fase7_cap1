# -*- coding: utf-8 -*-
"""Testes do motor de NLP local e do gerenciador de dialogo."""
import pytest

from backend import local_nlp
from backend.dialog import DialogManager, Session


# ---------------------------------------------------------------------------
# NLU
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "texto,intent_esperado",
    [
        ("Oi, bom dia", "saudacao"),
        ("Muito obrigado pela ajuda", "agradecimento"),
        ("pode encerrar o atendimento", "despedida"),
        ("estou com dor no peito ha 1 hora", "informar_sintoma"),
        ("posso parar de tomar o remedio da pressao?", "duvida_medicamento"),
        ("para que serve o eletrocardiograma?", "duvida_exame"),
        ("quais os fatores de risco para infarto?", "duvida_fatores_risco"),
        ("quero marcar uma consulta com cardiologista", "agendar_consulta"),
        ("nao consigo respirar e tenho dor muito forte no peito", "emergencia"),
    ],
)
def test_classificacao_de_intents(texto, intent_esperado):
    resultado = local_nlp.analyze(texto)
    assert resultado["intent"]["intent"] == intent_esperado


def test_extracao_de_entities():
    resultado = local_nlp.analyze(
        "tenho 58 anos, sinto dor no peito forte ha 30 minutos que irradia para o braco esquerdo"
    )
    entidades = {(e["entity"], e["value"]) for e in resultado["entities"]}
    assert ("sintoma_cardiaco", "dor no peito") in entidades
    assert ("intensidade", "forte") in entidades
    assert ("irradiacao", "braco esquerdo") in entidades
    assert ("idade", "58") in entidades
    assert any(e["entity"] == "duracao" for e in resultado["entities"])


def test_texto_fora_de_escopo():
    resultado = local_nlp.analyze("qual a previsao do tempo para amanha?")
    assert resultado["intent"]["intent"] == "fora_de_escopo"


# ---------------------------------------------------------------------------
# Dialogo
# ---------------------------------------------------------------------------


def _conversa():
    return DialogManager(), Session(conversation_id="teste")


def test_saudacao_inicia_coleta():
    dm, s = _conversa()
    out = dm.handle(s, local_nlp.analyze("ola"))
    assert s.stage == "coleta_sintomas"
    assert out["options"]


def test_fluxo_completo_ate_triagem():
    dm, s = _conversa()
    dm.handle(s, local_nlp.analyze("ola"))
    dm.handle(s, local_nlp.analyze("estou com palpitacao"))
    dm.handle(s, local_nlp.analyze("e leve"))
    out = dm.handle(s, local_nlp.analyze("comecou ha 3 dias"))
    # sem dor toracica -> proximo passo pergunta fatores de risco
    dm.handle(s, local_nlp.analyze("nenhum desses"))
    out = dm.handle(s, local_nlp.analyze("estou com palpitacao"))
    assert out["summary"] is not None
    assert out["summary"]["classificacao"] in {
        "AVALIACAO ELETIVA",
        "PRIORIDADE ALTA",
        "ORIENTACAO GERAL",
    }


def test_red_flag_dispara_emergencia():
    dm, s = _conversa()
    dm.handle(s, local_nlp.analyze("ola"))
    out = dm.handle(
        s,
        local_nlp.analyze(
            "estou com dor no peito muito forte, suando frio e com falta de ar"
        ),
    )
    assert s.stage == "emergencia"
    assert out["summary"]["classificacao"] == "EMERGENCIA"
    assert out["summary"]["sinais_de_alarme"]
    assert "192" in out["reply"]


def test_desmaio_e_red_flag():
    dm, s = _conversa()
    out = dm.handle(s, local_nlp.analyze("eu desmaiei agora ha pouco"))
    assert s.stage == "emergencia"
    assert any("sincope" in f.lower() for f in out["summary"]["sinais_de_alarme"])


def test_fallback_progressivo():
    dm, s = _conversa()
    dm.handle(s, local_nlp.analyze("xyz abc"))
    out = dm.handle(s, local_nlp.analyze("asdf qwer"))
    assert "reformular" in out["reply"].lower() or "reformular" in out["reply"]


def test_disclaimer_presente_na_emergencia():
    dm, s = _conversa()
    out = dm.handle(s, local_nlp.analyze("dor no peito muito forte irradiando para o braco"))
    assert "nao substitui" in out["reply"].lower()
