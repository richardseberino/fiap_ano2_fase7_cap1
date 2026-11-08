"""Configuração do gateway via variáveis de ambiente (ConfigMap/Secret no Kubernetes)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _lista(valor: str) -> list[str]:
    return [v.strip() for v in valor.split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    multiagente_url: str = os.getenv("MULTIAGENTE_URL", "http://localhost:8001").rstrip("/")
    chatbot_url: str = os.getenv("CHATBOT_URL", "http://localhost:5001").rstrip("/")
    vision_url: str = os.getenv("VISION_URL", "http://localhost:5002").rstrip("/")

    influx_url: str = os.getenv("INFLUX_URL", "http://localhost:8086")
    influx_token: str = os.getenv("INFLUX_TOKEN", "")
    influx_org: str = os.getenv("INFLUX_ORG", "fiap")
    influx_bucket: str = os.getenv("INFLUX_BUCKET", "dados-medicos")
    influx_measurement: str = os.getenv("INFLUX_MEASUREMENT", "sinais_vitais")

    # CORS: o app web roda na Vercel (*.vercel.app) e o app nativo não envia Origin.
    cors_origins: list[str] = field(default_factory=lambda: _lista(os.getenv("CORS_ORIGINS", "*")))
    cors_origin_regex: str | None = os.getenv("CORS_ORIGIN_REGEX") or None

    timeout_padrao: float = float(os.getenv("TIMEOUT_PADRAO", "30"))
    timeout_llm: float = float(os.getenv("TIMEOUT_LLM", "180"))
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_MB", "20")) * 1024 * 1024


settings = Settings()
