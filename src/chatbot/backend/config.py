# -*- coding: utf-8 -*-
"""Carregamento de configuracao a partir de variaveis de ambiente / arquivo .env."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "sim"}


@dataclass(frozen=True)
class Settings:
    """Configuracoes da aplicacao."""

    host: str = os.getenv("FLASK_HOST", "127.0.0.1")
    port: int = int(os.getenv("FLASK_PORT", "5000"))
    debug: bool = _as_bool(os.getenv("FLASK_DEBUG"), True)

    use_watson: bool = _as_bool(os.getenv("USE_WATSON"), False)
    watson_apikey: str = os.getenv("WATSON_APIKEY", "")
    watson_url: str = os.getenv("WATSON_URL", "")
    watson_assistant_id: str = os.getenv("WATSON_ASSISTANT_ID", "")
    watson_version: str = os.getenv("WATSON_VERSION", "2021-11-27")

    @property
    def watson_ready(self) -> bool:
        return bool(self.watson_apikey and self.watson_url and self.watson_assistant_id)


settings = Settings()
