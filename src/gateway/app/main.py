"""CardioIA Gateway (BFF) — ponto único de entrada do app web/mobile.

Unifica, sob o prefixo /api, os serviços da arquitetura:

    IoT (InfluxDB)   GET  /api/pacientes                      pacientes com leituras recentes
                     GET  /api/sinais-vitais                  última leitura de cada paciente
                     GET  /api/sinais-vitais/{paciente_id}    última leitura + série temporal
    Multiagente      GET  /api/analise/exemplos               pacientes de exemplo
                     GET  /api/analise/sugestao/{paciente_id} dados do IoT pré-preenchidos p/ análise
                     POST /api/analise                        executa o pipeline multiagente
    Chatbot          POST /api/chat                           mensagem ao assistente de triagem
                     POST /api/chat/reset                     reinicia a conversa
    Vision           POST /api/ecg                            classifica imagem de ECG (multipart)
    Plataforma       GET  /api/health                         saúde agregada de todos os serviços
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from statistics import mean
from typing import Any

import httpx
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from influxdb_client.client.exceptions import InfluxDBError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import settings
from .influx import RepositorioSinais, contar_subidas

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("gateway")

_http: httpx.AsyncClient | None = None
_sinais = RepositorioSinais(settings)


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    global _http
    _http = httpx.AsyncClient(timeout=httpx.Timeout(settings.timeout_padrao, connect=5.0))
    log.info("Gateway iniciado: multiagente=%s chatbot=%s vision=%s influx=%s",
             settings.multiagente_url, settings.chatbot_url, settings.vision_url, settings.influx_url)
    yield
    await _http.aclose()
    _sinais.fechar()


app = FastAPI(title="CardioIA Gateway", version="2.0.0", lifespan=ciclo_de_vida,
              docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def _erro_validacao(_req: Request, erro: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(erro)})


@app.exception_handler(InfluxDBError)
async def _erro_influx(_req: Request, erro: InfluxDBError):
    log.warning("Falha ao consultar o InfluxDB: %s", erro)
    return JSONResponse(status_code=503, content={"detail": "InfluxDB indisponível ou sem permissão"})


# ---------------------------------------------------------------------------
# utilitários HTTP
# ---------------------------------------------------------------------------

async def _chamar(metodo: str, url: str, *, timeout: float | None = None, **kwargs) -> Any:
    """Chama um serviço interno e converte falhas em erros HTTP compreensíveis para o app."""
    assert _http is not None
    try:
        resp = await _http.request(metodo, url, timeout=timeout or settings.timeout_padrao, **kwargs)
    except httpx.TimeoutException as erro:
        raise HTTPException(504, f"Tempo esgotado ao chamar {url}") from erro
    except httpx.HTTPError as erro:
        raise HTTPException(503, f"Serviço indisponível: {url}") from erro
    if resp.status_code >= 400:
        try:
            detalhe = resp.json()
            detalhe = detalhe.get("detail") or detalhe.get("error") or detalhe
        except ValueError:
            detalhe = resp.text[:300]
        raise HTTPException(resp.status_code, detalhe)
    return resp.json()


async def _saude(nome: str, url: str) -> dict:
    try:
        dados = await _chamar("GET", url, timeout=4)
        return {"servico": nome, "ok": True, **({"detalhes": dados} if isinstance(dados, dict) else {})}
    except HTTPException as erro:
        return {"servico": nome, "ok": False, "erro": str(erro.detail)}


# ---------------------------------------------------------------------------
# plataforma
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health() -> dict:
    resultados = await asyncio.gather(
        _saude("multiagente", f"{settings.multiagente_url}/health"),
        _saude("chatbot", f"{settings.chatbot_url}/api/health"),
        _saude("vision", f"{settings.vision_url}/health"),
        asyncio.to_thread(_sinais.saude),
    )
    return {
        "status": "ok" if all(r["ok"] for r in resultados) else "degradado",
        "horario": datetime.now(timezone.utc).isoformat(),
        "servicos": resultados,
    }


@app.get("/")
async def raiz() -> dict:
    return {"servico": "cardioia-gateway", "docs": "/api/docs", "health": "/api/health"}


# ---------------------------------------------------------------------------
# IoT · sinais vitais (InfluxDB)
# ---------------------------------------------------------------------------

@app.get("/api/pacientes")
async def pacientes(horas: int = Query(24, ge=1, le=720)) -> list[dict]:
    return await asyncio.to_thread(_sinais.ultimas_leituras, horas)


@app.get("/api/sinais-vitais")
async def sinais_todos(horas: int = Query(24, ge=1, le=720)) -> list[dict]:
    return await asyncio.to_thread(_sinais.ultimas_leituras, horas)


@app.get("/api/sinais-vitais/{paciente_id}")
async def sinais_paciente(paciente_id: str, minutos: int = Query(60, ge=5, le=10080)) -> dict:
    serie = await asyncio.to_thread(_sinais.serie, paciente_id, minutos)
    ultimas = await asyncio.to_thread(_sinais.ultimas_leituras, max(1, minutos // 60 + 1))
    ultimo = next((u for u in ultimas if u["paciente_id"] == paciente_id), None)
    if ultimo is None and not serie:
        raise HTTPException(404, f"Sem leituras do paciente {paciente_id} nos últimos {minutos} min")
    return {"paciente_id": paciente_id, "minutos": minutos, "ultimo": ultimo, "serie": serie}


# ---------------------------------------------------------------------------
# Multiagente
# ---------------------------------------------------------------------------

class PedidoAnalise(BaseModel):
    paciente_id: str | None = None
    dados: dict[str, Any]
    modo: str = "auto"


@app.get("/api/analise/exemplos")
async def exemplos() -> Any:
    return await _chamar("GET", f"{settings.multiagente_url}/exemplos")


@app.get("/api/analise/sugestao/{paciente_id}")
async def sugestao(paciente_id: str, minutos: int = Query(30, ge=5, le=1440)) -> dict:
    """Pré-preenche os campos clínicos da análise com as médias recentes coletadas pelo IoT.

    Campos operacionais (carga do sistema, tempo de espera, recursos) não vêm dos sensores
    e são devolvidos como None para o usuário completar no app.
    """
    serie = await asyncio.to_thread(_sinais.serie, paciente_id, minutos)
    if not serie:
        raise HTTPException(404, f"Sem leituras do paciente {paciente_id} nos últimos {minutos} min")

    def media(campo: str) -> float | None:
        valores = [p[campo] for p in serie if p.get(campo) is not None]
        return round(mean(valores), 1) if valores else None

    eventos_24h = await asyncio.to_thread(_sinais.contar_episodios_alerta, paciente_id, 24 * 60)
    eventos_janela = contar_subidas([p.get("nivel_alerta") or 0 for p in serie])
    return {
        "paciente_id": paciente_id,
        "janela_minutos": minutos,
        "amostras": len(serie),
        "dados": {
            "fc_media": media("bpm"),
            "spo2_media": media("oxigenacao"),
            "temperatura": media("temperatura"),
            "pa_sistolica": media("pa_sistolica"),
            "eventos_24h": eventos_24h,
            "densidade_eventos": eventos_janela,
            "idade_media": None,
            "carga_sistema": None,
            "tempo_espera": None,
            "disponibilidade_recursos": None,
        },
    }


@app.post("/api/analise")
async def analise(pedido: PedidoAnalise) -> Any:
    return await _chamar("POST", f"{settings.multiagente_url}/analisar",
                         json=pedido.model_dump(), timeout=settings.timeout_llm)


# ---------------------------------------------------------------------------
# Chatbot (com opção de perguntar ao multiagente sobre a última análise)
# ---------------------------------------------------------------------------

class PedidoChat(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None
    analise_id: str | None = Field(default=None, description="Se informado, a pergunta vai ao "
                                   "Orquestrador do multiagente sobre essa análise")


@app.post("/api/chat")
async def chat(pedido: PedidoChat) -> Any:
    if pedido.analise_id:
        dados = await _chamar("POST", f"{settings.multiagente_url}/analises/{pedido.analise_id}/perguntar",
                              json={"pergunta": pedido.message}, timeout=settings.timeout_llm)
        return {"reply": dados["resposta"], "engine": "multiagente", "conversation_id": pedido.conversation_id,
                "options": [], "summary": None, "stage": "acompanhamento"}
    return await _chamar("POST", f"{settings.chatbot_url}/api/message",
                         json={"message": pedido.message, "conversation_id": pedido.conversation_id})


class PedidoReset(BaseModel):
    conversation_id: str | None = None


@app.post("/api/chat/reset")
async def chat_reset(pedido: PedidoReset) -> Any:
    return await _chamar("POST", f"{settings.chatbot_url}/api/reset", json=pedido.model_dump())


# ---------------------------------------------------------------------------
# Vision (ECG)
# ---------------------------------------------------------------------------

@app.post("/api/ecg")
async def ecg(image: UploadFile = File(...)) -> Any:
    conteudo = await image.read()
    if len(conteudo) > settings.max_upload_bytes:
        raise HTTPException(413, "Imagem maior que o limite permitido")
    arquivos = {"image": (image.filename or "ecg.jpg", conteudo, image.content_type or "image/jpeg")}
    return await _chamar("POST", f"{settings.vision_url}/api/predict", files=arquivos, timeout=120)
