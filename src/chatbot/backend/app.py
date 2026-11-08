# -*- coding: utf-8 -*-
"""Aplicacao Flask do Assistente Cardiologico Conversacional.

Expoe uma API REST simples consumida pela interface web (``frontend/``):

    GET  /                -> pagina do chat
    GET  /api/health      -> status e motor ativo
    POST /api/message     -> {message, conversation_id} -> resposta do assistente
    POST /api/reset       -> reinicia a conversa

O motor de conversacao e escolhido em tempo de execucao:
  * IBM Watson Assistant, se ``USE_WATSON=true`` e credenciais validas;
  * caso contrario (ou em caso de falha), o motor de NLP local (offline).
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from . import local_nlp
from .config import settings
from .dialog import DialogManager, Session

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("assistente-cardio")

FRONTEND_DIR = (Path(__file__).resolve().parent.parent / "frontend").resolve()

app = Flask(__name__, static_folder=None)
CORS(app)

_dialog = DialogManager()
_sessions: dict[str, Session] = {}
_watson_engine = None

if settings.use_watson:
    try:
        from .watson_client import WatsonEngine

        _watson_engine = WatsonEngine(settings)
        log.info("Motor ativo: IBM Watson Assistant")
    except Exception as exc:  # noqa: BLE001
        log.warning("Watson indisponivel (%s). Usando motor local.", exc)
else:
    log.info("Motor ativo: NLP local (USE_WATSON=false)")


def _get_session(conversation_id: str) -> Session:
    if conversation_id not in _sessions:
        _sessions[conversation_id] = Session(conversation_id=conversation_id)
    return _sessions[conversation_id]


def _active_engine() -> str:
    return "watson" if _watson_engine is not None else "local"


# ---------------------------------------------------------------------------
# Frontend estatico
# ---------------------------------------------------------------------------


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:filename>")
def static_files(filename: str):
    return send_from_directory(FRONTEND_DIR, filename)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "engine": _active_engine(),
            "use_watson_flag": settings.use_watson,
            "watson_ready": settings.watson_ready,
        }
    )


@app.post("/api/message")
def message():
    data = request.get_json(silent=True) or {}
    texto = (data.get("message") or "").strip()
    conversation_id = data.get("conversation_id") or str(uuid.uuid4())

    if not texto:
        return jsonify({"error": "campo 'message' vazio"}), 400

    # 1) tenta Watson
    if _watson_engine is not None:
        try:
            result = _watson_engine.message(conversation_id, texto)
            result["conversation_id"] = conversation_id
            return jsonify(result)
        except Exception as exc:  # noqa: BLE001
            log.exception("Falha ao chamar o Watson; caindo para o motor local: %s", exc)

    # 2) motor local
    nlu = local_nlp.analyze(texto)
    session = _get_session(conversation_id)
    out = _dialog.handle(session, nlu)

    return jsonify(
        {
            "conversation_id": conversation_id,
            "reply": out["reply"],
            "intent": nlu["intent"]["intent"],
            "confidence": nlu["intent"]["confidence"],
            "entities": [
                {"entity": e["entity"], "value": e["value"]} for e in nlu["entities"]
            ],
            "stage": out["stage"],
            "summary": out["summary"],
            "options": out["options"],
            "engine": "local",
        }
    )


@app.post("/api/reset")
def reset():
    data = request.get_json(silent=True) or {}
    conversation_id = data.get("conversation_id")
    if conversation_id:
        _sessions.pop(conversation_id, None)
        if _watson_engine is not None:
            _watson_engine.reset(conversation_id)
    return jsonify({"status": "reset", "conversation_id": conversation_id})


def main() -> None:
    log.info("Servindo frontend de %s", FRONTEND_DIR)
    app.run(host=settings.host, port=settings.port, debug=settings.debug)


if __name__ == "__main__":
    main()
