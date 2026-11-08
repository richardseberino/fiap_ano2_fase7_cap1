# -*- coding: utf-8 -*-
"""Integracao com o IBM Watson Assistant (API v2).

Usado quando ``USE_WATSON=true`` e as credenciais estao configuradas. O
Watson e responsavel por classificar intents/entities e produzir a resposta
(conforme os *dialog nodes* modelados). Este modulo apenas adapta a resposta
da API para o mesmo formato devolvido pelo motor local.

Se o SDK ``ibm-watson`` nao estiver instalado ou as credenciais faltarem, a
criacao do :class:`WatsonEngine` levanta excecao e a aplicacao cai
automaticamente para o motor local.
"""
from __future__ import annotations

from typing import Any

from .config import Settings


class WatsonEngine:
    def __init__(self, settings: Settings) -> None:
        if not settings.watson_ready:
            raise RuntimeError(
                "Credenciais do Watson ausentes (WATSON_APIKEY / WATSON_URL / "
                "WATSON_ASSISTANT_ID)."
            )
        try:
            from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
            from ibm_watson import AssistantV2
        except ImportError as exc:  # pragma: no cover - depende do ambiente
            raise RuntimeError(
                "Pacote 'ibm-watson' nao instalado. Rode: pip install ibm-watson"
            ) from exc

        authenticator = IAMAuthenticator(settings.watson_apikey)
        self._assistant = AssistantV2(
            version=settings.watson_version, authenticator=authenticator
        )
        self._assistant.set_service_url(settings.watson_url)
        self._assistant_id = settings.watson_assistant_id
        self._sessions: dict[str, str] = {}

    # ------------------------------------------------------------------ #

    def _session_id(self, conversation_id: str) -> str:
        if conversation_id not in self._sessions:
            resp = self._assistant.create_session(
                assistant_id=self._assistant_id
            ).get_result()
            self._sessions[conversation_id] = resp["session_id"]
        return self._sessions[conversation_id]

    def reset(self, conversation_id: str) -> None:
        session_id = self._sessions.pop(conversation_id, None)
        if session_id:
            try:
                self._assistant.delete_session(
                    assistant_id=self._assistant_id, session_id=session_id
                )
            except Exception:  # pragma: no cover - best effort
                pass

    def message(self, conversation_id: str, text: str) -> dict[str, Any]:
        session_id = self._session_id(conversation_id)
        resp = self._assistant.message(
            assistant_id=self._assistant_id,
            session_id=session_id,
            input={
                "message_type": "text",
                "text": text,
                "options": {"return_context": True},
            },
        ).get_result()

        output = resp.get("output", {})
        textos = [
            item.get("text", "")
            for item in output.get("generic", [])
            if item.get("response_type") == "text" and item.get("text")
        ]
        intents = output.get("intents", [])
        entities = output.get("entities", [])

        return {
            "reply": "\n".join(textos) or "Desculpe, nao entendi. Pode reformular?",
            "intent": intents[0]["intent"] if intents else "fora_de_escopo",
            "confidence": round(intents[0]["confidence"], 2) if intents else 0.0,
            "entities": [
                {"entity": e.get("entity"), "value": e.get("value")} for e in entities
            ],
            "summary": None,
            "stage": "watson",
            "options": [],
            "engine": "watson",
        }
