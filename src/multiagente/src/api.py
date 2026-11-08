"""API HTTP do Sistema Preditivo Multiagente (serviço `multiagente` da arquitetura integrada).

Expõe o mesmo pipeline do `main.py` para o gateway e para o app móvel:

    GET  /health                       status, modo disponível (llm/offline) e modelo de ML
    GET  /exemplos                     pacientes de exemplo (data/pacientes)
    POST /analisar                     executa o fluxo multiagente e devolve a RecomendacaoFinal
    POST /analises/{id}/perguntar      pergunta de acompanhamento sobre uma análise (modo llm)

Modo de execução:
- ``llm``: os 4 agentes (OpenAI Agents SDK) com handoffs, tools e guardrails;
- ``offline``: as mesmas etapas sem LLM (modelo de ML + base de protocolos);
- ``auto`` (padrão): usa ``llm`` quando há OPENAI_API_KEY e cai para ``offline`` se o LLM falhar.

Execução local:  uvicorn api:app --app-dir src --port 8001
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from collections import OrderedDict
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from multiagente import preditor
from multiagente.config import CAMINHO_HISTORICO, MODELO_LLM, PASTA_PACIENTES
from multiagente.contexto import ContextoAtendimento
from multiagente.esquemas import DadosPaciente, RecomendacaoFinal
from multiagente.sistema import executar_atendimento, executar_offline, perguntar

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("multiagente.api")

MAX_ANALISES_EM_MEMORIA = 200

@asynccontextmanager
async def _ciclo_de_vida(_app):
    # Carrega o Random Forest na subida para a primeira análise não pagar o custo.
    preditor.carregar_modelo()
    log.info("Modelo de ML carregado. LLM disponível: %s (%s)", llm_disponivel(), MODELO_LLM)
    yield


app = FastAPI(
    lifespan=_ciclo_de_vida,
    title="CardioIA · Multiagente",
    version="2.0.0",
    description="Pipeline multiagente (Orquestrador, Analista de Risco, Especialista em Protocolos, "
                "Planejador de Resposta) para apoio à decisão em eventos cardíacos.",
)


class PedidoAnalise(BaseModel):
    paciente_id: str | None = Field(default=None, description="Identificador do paciente")
    dados: DadosPaciente
    modo: Literal["auto", "llm", "offline"] = "auto"


class RespostaAnalise(BaseModel):
    analise_id: str
    paciente_id: str
    modo: Literal["llm", "offline"]
    recomendacao: RecomendacaoFinal
    trilha: list[str]
    guardrail_bloqueou: bool = False
    problemas: list[str] = []
    observacao: str | None = None
    duracao_ms: int


class PedidoPergunta(BaseModel):
    pergunta: str = Field(min_length=1, max_length=2000)


class _Analise:
    def __init__(self, ctx: ContextoAtendimento, session, modo: str):
        self.ctx, self.session, self.modo = ctx, session, modo


# Contexto e sessão de cada análise, para as perguntas de acompanhamento (LRU simples em memória).
_analises: OrderedDict[str, _Analise] = OrderedDict()


def _guardar(analise_id: str, analise: _Analise) -> None:
    _analises[analise_id] = analise
    while len(_analises) > MAX_ANALISES_EM_MEMORIA:
        _analises.popitem(last=False)


def llm_disponivel() -> bool:
    chave = os.getenv("OPENAI_API_KEY", "").strip()
    return bool(chave) and chave != "sk-..."


@app.get("/health")
def health() -> dict:
    pacote = preditor.carregar_modelo()
    return {
        "status": "ok",
        "servico": "multiagente",
        "llm_disponivel": llm_disponivel(),
        "modelo_llm": MODELO_LLM if llm_disponivel() else None,
        "modelo_ml": pacote.get("algoritmo"),
    }


@app.get("/exemplos")
def exemplos() -> list[dict]:
    saida = []
    for arquivo in sorted(PASTA_PACIENTES.glob("*.json")):
        bruto = json.loads(arquivo.read_text(encoding="utf-8"))
        paciente_id = bruto.pop("paciente_id", arquivo.stem)
        saida.append({"paciente_id": paciente_id, "dados": DadosPaciente.model_validate(bruto).model_dump()})
    return saida


@app.post("/analisar", response_model=RespostaAnalise)
async def analisar(pedido: PedidoAnalise) -> RespostaAnalise:
    inicio = time.perf_counter()
    paciente_id = pedido.paciente_id or f"PAC-{uuid.uuid4().hex[:6].upper()}"
    analise_id = uuid.uuid4().hex
    observacao = None

    usar_llm = pedido.modo == "llm" or (pedido.modo == "auto" and llm_disponivel())
    if pedido.modo == "llm" and not llm_disponivel():
        raise HTTPException(409, "Modo llm solicitado, mas OPENAI_API_KEY não está configurada no serviço.")

    if usar_llm:
        from agents import SQLiteSession

        CAMINHO_HISTORICO.parent.mkdir(parents=True, exist_ok=True)
        session = SQLiteSession(f"{paciente_id}-{analise_id[:8]}", CAMINHO_HISTORICO)
        try:
            recomendacao, ctx, meta = await executar_atendimento(pedido.dados, paciente_id, session=session)
            _guardar(analise_id, _Analise(ctx, session, "llm"))
            return RespostaAnalise(
                analise_id=analise_id, paciente_id=paciente_id, modo="llm", recomendacao=recomendacao,
                trilha=ctx.trilha, guardrail_bloqueou=meta["guardrail_bloqueou"], problemas=meta["problemas"],
                duracao_ms=int((time.perf_counter() - inicio) * 1000),
            )
        except Exception as erro:  # noqa: BLE001
            if pedido.modo == "llm":
                raise HTTPException(502, f"Falha no pipeline com LLM: {erro}") from erro
            log.exception("Falha no pipeline com LLM; usando o modo offline")
            observacao = f"LLM indisponível ({type(erro).__name__}); resultado gerado no modo offline."

    recomendacao, ctx = executar_offline(pedido.dados, paciente_id)
    _guardar(analise_id, _Analise(ctx, None, "offline"))
    return RespostaAnalise(
        analise_id=analise_id, paciente_id=paciente_id, modo="offline", recomendacao=recomendacao,
        trilha=ctx.trilha, observacao=observacao, duracao_ms=int((time.perf_counter() - inicio) * 1000),
    )


@app.post("/analises/{analise_id}/perguntar")
async def perguntar_analise(analise_id: str, pedido: PedidoPergunta) -> dict:
    analise = _analises.get(analise_id)
    if analise is None:
        raise HTTPException(404, "Análise não encontrada (pode ter expirado). Execute uma nova análise.")
    if analise.modo != "llm" or analise.session is None:
        raise HTTPException(409, "Perguntas de acompanhamento exigem uma análise feita no modo llm.")
    resposta = await perguntar(pedido.pergunta, analise.ctx, analise.session)
    return {"analise_id": analise_id, "resposta": resposta}
