# -*- coding: utf-8 -*-
"""Gerenciador de dialogo do motor local.

Orquestra o fluxo de atendimento inicial em cardiologia:

    inicio -> coleta da queixa -> coleta de detalhes -> triagem -> encerramento

Regras de "red flag" (sinais de alarme) sao avaliadas a cada turno e
interrompem o fluxo normal para orientar procura imediata por emergencia.

O gerenciador e propositalmente simples e deterministico -- ele existe para
que o prototipo funcione offline e espelha a logica que estaria distribuida
entre os *dialog nodes* do Watson Assistant (arquivo em ``watson/``).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

DISCLAIMER = (
    "⚠️ Este assistente e um prototipo educacional e NAO substitui "
    "avaliacao medica. Em caso de emergencia, ligue 192 (SAMU)."
)

_SINTOMAS_TORACICOS = {"dor no peito", "dor no braco"}


@dataclass
class Session:
    """Estado de uma conversa (mantido em memoria por ``conversation_id``)."""

    conversation_id: str
    stage: str = "inicio"
    nome: str | None = None
    idade: int | None = None
    sintomas: list[str] = field(default_factory=list)
    intensidade: str | None = None
    duracao: str | None = None
    irradiacao: list[str] = field(default_factory=list)
    fatores_risco: list[str] = field(default_factory=list)
    perguntas_feitas: set[str] = field(default_factory=set)
    emergencia_disparada: bool = False
    fallback_seguidos: int = 0
    turnos: int = 0

    def reset(self) -> None:
        keep = self.conversation_id
        self.__init__(conversation_id=keep)  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Atualizacao do estado a partir das entities
# ---------------------------------------------------------------------------


def _absorver_entities(session: Session, entities: list[dict[str, Any]]) -> None:
    for ent in entities:
        tipo, valor = ent["entity"], ent["value"]
        if tipo == "sintoma_cardiaco" and valor not in session.sintomas:
            session.sintomas.append(valor)
        elif tipo == "intensidade":
            session.intensidade = valor
        elif tipo == "duracao":
            session.duracao = valor
        elif tipo == "irradiacao" and valor not in session.irradiacao:
            session.irradiacao.append(valor)
        elif tipo == "idade":
            try:
                session.idade = int(valor)
            except ValueError:
                pass
        elif tipo == "nome":
            session.nome = valor


def _absorver_fatores_risco(session: Session, texto_norm: str) -> None:
    mapa = {
        "hipertensao": ["hipertensao", "pressao alta"],
        "diabetes": ["diabetes", "diabetico", "diabetica"],
        "colesterol alto": ["colesterol alto", "colesterol elevado"],
        "tabagismo": ["fumo", "fumante", "cigarro", "tabagismo"],
        "sedentarismo": ["sedentario", "sedentaria", "sedentarismo", "nao faco exercicio"],
        "obesidade": ["obesidade", "acima do peso", "sobrepeso"],
        "historico familiar": ["historico familiar", "pai teve infarto", "mae teve infarto"],
    }
    for fator, termos in mapa.items():
        if any(t in texto_norm for t in termos) and fator not in session.fatores_risco:
            session.fatores_risco.append(fator)


# ---------------------------------------------------------------------------
# Sinais de alarme e classificacao de risco
# ---------------------------------------------------------------------------


def _duracao_prolongada(duracao: str | None) -> bool:
    if not duracao:
        return False
    m = re.match(r"(\d+)\s*(minuto|minutos|min|hora|horas)", duracao)
    if not m:
        return False
    qtd = int(m.group(1))
    unidade = m.group(2)
    if unidade.startswith("min"):
        return qtd >= 20
    return True  # horas


def _red_flags(session: Session) -> list[str]:
    flags: list[str] = []
    dor_toracica = bool(_SINTOMAS_TORACICOS & set(session.sintomas))

    if "desmaio" in session.sintomas:
        flags.append("Episodio de desmaio / sincope")
    if dor_toracica and session.intensidade in {"forte", "muito forte"}:
        flags.append("Dor toracica de forte intensidade")
    if dor_toracica and "sudorese fria" in session.sintomas:
        flags.append("Dor toracica associada a sudorese fria")
    if dor_toracica and "falta de ar" in session.sintomas:
        flags.append("Dor toracica associada a falta de ar")
    if dor_toracica and session.irradiacao:
        flags.append("Dor toracica com irradiacao (" + ", ".join(session.irradiacao) + ")")
    if dor_toracica and _duracao_prolongada(session.duracao):
        flags.append("Dor toracica prolongada (>= 20 min)")
    if "falta de ar" in session.sintomas and "palpitacao" in session.sintomas:
        flags.append("Falta de ar associada a palpitacoes")
    return flags


def _classificar(session: Session, flags: list[str]) -> tuple[str, str]:
    if flags:
        return (
            "EMERGENCIA",
            "Procure imediatamente um pronto-socorro ou ligue 192 (SAMU). "
            "Nao dirija; peca ajuda.",
        )

    dor_toracica = bool(_SINTOMAS_TORACICOS & set(session.sintomas))
    if dor_toracica or {"falta de ar", "desmaio"} & set(session.sintomas):
        return (
            "PRIORIDADE ALTA",
            "Procure atendimento medico ainda hoje (pronto-atendimento ou "
            "unidade de urgencia) para avaliacao e eletrocardiograma.",
        )

    if session.sintomas:
        return (
            "AVALIACAO ELETIVA",
            "Agende consulta com cardiologista nos proximos dias. Se os "
            "sintomas piorarem ou surgir dor no peito, procure urgencia.",
        )

    if session.fatores_risco:
        return (
            "ORIENTACAO / PREVENCAO",
            "Sem sintomas agudos no momento. Agende avaliacao cardiologica de "
            "rotina para controle dos fatores de risco.",
        )

    return (
        "ORIENTACAO GERAL",
        "Sem sinais de alarme identificados. Mantenha acompanhamento de rotina.",
    )


def _montar_resumo(session: Session, flags: list[str]) -> dict[str, Any]:
    classificacao, conduta = _classificar(session, flags)
    return {
        "paciente": {"nome": session.nome, "idade": session.idade},
        "queixa_principal": session.sintomas[0] if session.sintomas else None,
        "sintomas": list(session.sintomas),
        "intensidade": session.intensidade,
        "duracao": session.duracao,
        "irradiacao": list(session.irradiacao),
        "fatores_risco": list(session.fatores_risco),
        "sinais_de_alarme": flags,
        "classificacao": classificacao,
        "conduta_sugerida": conduta,
    }


# ---------------------------------------------------------------------------
# Respostas de conteudo (perguntas frequentes)
# ---------------------------------------------------------------------------

_RESP_MEDICAMENTO = (
    "Sobre medicamentos: nao inicie, ajuste ou suspenda nenhum remedio do "
    "coracao ou da pressao por conta propria. Mudancas devem ser feitas pelo "
    "medico que acompanha voce. Se esqueceu uma dose, em geral tome assim que "
    "lembrar (a nao ser que ja esteja perto do proximo horario) — nunca "
    "dobre a dose. Se tiver dor no peito, falta de ar ou mal-estar agora, "
    "procure atendimento de urgencia."
)

_RESP_EXAME = (
    "Exames iniciais mais comuns em cardiologia: eletrocardiograma (ECG), que "
    "registra o ritmo do coracao; ecocardiograma, um ultrassom que avalia a "
    "estrutura e a funcao; Holter 24h para arritmias; e teste ergometrico "
    "(esteira) para sintomas ligados ao esforco. A indicacao depende da sua "
    "queixa e deve ser feita pelo cardiologista."
)

_RESP_FATORES_RISCO = (
    "Principais fatores de risco cardiovascular: hipertensao, diabetes, "
    "colesterol alto, tabagismo, sedentarismo, obesidade, historico familiar "
    "de doenca cardiaca precoce e idade. Controlar pressao, glicemia e "
    "colesterol, parar de fumar, praticar atividade fisica regular e manter "
    "peso saudavel reduzem bastante o risco."
)

_RESP_AGENDAR = (
    "Para agendar uma consulta com cardiologista: pela rede publica, procure a "
    "Unidade Basica de Saude (UBS) mais proxima para encaminhamento; por plano "
    "de saude ou particular, use a central de agendamento da operadora ou da "
    "clinica. Voce tem algum sintoma no momento?"
)


# ---------------------------------------------------------------------------
# Gerenciador
# ---------------------------------------------------------------------------


class DialogManager:
    """Recebe o resultado da NLU e devolve a resposta do assistente."""

    def handle(self, session: Session, nlu: dict[str, Any]) -> dict[str, Any]:
        session.turnos += 1
        intent = nlu["intent"]["intent"]
        entities = nlu.get("entities", [])
        texto_norm = nlu.get("normalized", "")

        _absorver_entities(session, entities)
        _absorver_fatores_risco(session, texto_norm)

        # ---- 1. Sinais de alarme tem prioridade sobre tudo -----------------
        flags = _red_flags(session)
        if intent == "emergencia" or flags:
            session.emergencia_disparada = True
            session.stage = "emergencia"
            session.fallback_seguidos = 0
            resumo = _montar_resumo(session, flags or ["Relato compativel com emergencia"])
            corpo = (
                "\U0001f6a8 Os sinais que voce descreveu podem indicar uma "
                "EMERGENCIA cardiaca.\n\n"
                "→ Ligue AGORA para o 192 (SAMU) ou va ao pronto-socorro "
                "mais proximo.\n"
                "→ Nao dirija sozinho e evite esforco.\n"
                "→ Se ja usa e foi orientado a isso, mastigar AAS pode ser "
                "recomendado — siga orientacao medica."
            )
            return _resposta(session, corpo, summary=resumo, options=[])

        # ---- 2. Fluxo por intencao ---------------------------------------
        handler = {
            "saudacao": self._saudacao,
            "informar_sintoma": self._sintoma,
            "informar_dados_pessoais": self._dados_pessoais,
            "duvida_medicamento": self._faq_medicamento,
            "duvida_exame": self._faq_exame,
            "duvida_fatores_risco": self._faq_fatores_risco,
            "agendar_consulta": self._agendar,
            "agradecimento": self._agradecimento,
            "despedida": self._despedida,
        }.get(intent, self._fallback)

        # Enquanto coletamos detalhes, respostas ao slot corrente
        # (ex.: "leve", "3 dias", "nenhum desses", "sou fumante") devem
        # continuar a coleta, e nao cair no fallback ou numa FAQ.
        if (
            session.sintomas
            and session.stage in {"coleta_sintomas", "coleta_detalhes"}
            and intent in {"fora_de_escopo", "duvida_fatores_risco", "informar_dados_pessoais"}
        ):
            handler = self._sintoma

        if intent not in {"fora_de_escopo"}:
            session.fallback_seguidos = 0

        return handler(session)

    # ------------------------------------------------------------------ #
    # Handlers
    # ------------------------------------------------------------------ #

    def _saudacao(self, session: Session) -> dict[str, Any]:
        session.stage = "coleta_sintomas"
        nome = f", {session.nome}" if session.nome else ""
        corpo = (
            f"Ola{nome}! Sou o assistente de triagem inicial em cardiologia da "
            "clinica. Posso te ajudar a organizar seus sintomas antes do "
            "atendimento.\n\nO que voce esta sentindo hoje?"
        )
        return _resposta(
            session,
            corpo,
            options=["Dor no peito", "Falta de ar", "Palpitacao", "Tontura", "So tenho uma duvida"],
        )

    def _sintoma(self, session: Session) -> dict[str, Any]:
        if not session.sintomas:
            session.stage = "coleta_sintomas"
            return _resposta(
                session,
                "Entendi que voce nao esta bem. Consegue descrever o sintoma "
                "principal? Por exemplo: dor no peito, falta de ar, palpitacao, "
                "tontura ou inchaco nas pernas.",
                options=["Dor no peito", "Falta de ar", "Palpitacao", "Tontura"],
            )

        session.stage = "coleta_detalhes"
        faltando = self._proxima_pergunta(session)
        if faltando:
            pergunta, options = faltando
            sintomas_txt = ", ".join(session.sintomas)
            return _resposta(
                session,
                f"Anotei: {sintomas_txt}. {pergunta}",
                options=options,
            )

        # informacao suficiente -> triagem
        session.stage = "triagem"
        flags = _red_flags(session)
        resumo = _montar_resumo(session, flags)
        corpo = (
            "Obrigado pelas informacoes. Preparei um resumo da sua triagem "
            f"inicial abaixo.\n\nClassificacao: {resumo['classificacao']}\n"
            f"Conduta sugerida: {resumo['conduta_sugerida']}"
        )
        return _resposta(session, corpo, summary=resumo,
                         options=["Tenho uma duvida sobre exames", "Encerrar"])

    def _proxima_pergunta(self, session: Session):
        """Devolve (pergunta, options) para o proximo dado faltante.

        Cada pergunta e feita no maximo uma vez (registrada em
        ``session.perguntas_feitas``); depois disso o fluxo segue para a
        triagem mesmo sem a resposta.
        """
        dor_toracica = bool(_SINTOMAS_TORACICOS & set(session.sintomas))
        pendentes: list[tuple[str, str, list[str]]] = []

        if session.intensidade is None:
            pendentes.append((
                "intensidade",
                "Qual a intensidade? Voce diria que e leve, moderada, forte ou "
                "muito forte?",
                ["Leve", "Moderada", "Forte", "Muito forte"],
            ))
        if session.duracao is None:
            pendentes.append((
                "duracao",
                "Ha quanto tempo isso comecou? (por exemplo: 10 minutos, 2 "
                "horas, 3 dias)",
                ["Comecou agora", "Algumas horas", "Alguns dias", "Ha semanas"],
            ))
        if dor_toracica and not session.irradiacao:
            pendentes.append((
                "irradiacao",
                "A dor espalha para algum lugar, como braco, ombro, pescoco, "
                "queixo ou costas?",
                ["Braco esquerdo", "Costas", "Pescoco/queixo", "Nao espalha"],
            ))
        if not session.fatores_risco:
            pendentes.append((
                "fatores_risco",
                "Voce tem algum destes: hipertensao, diabetes, colesterol alto, "
                "e fumante ou ja teve caso de infarto na familia?",
                ["Hipertensao", "Diabetes", "Sou fumante", "Nenhum desses"],
            ))

        for chave, pergunta, options in pendentes:
            if chave not in session.perguntas_feitas:
                session.perguntas_feitas.add(chave)
                return pergunta, options
        return None

    def _dados_pessoais(self, session: Session) -> dict[str, Any]:
        partes = []
        if session.nome:
            partes.append(f"nome: {session.nome}")
        if session.idade:
            partes.append(f"idade: {session.idade} anos")
        conf = ("Anotei " + ", ".join(partes) + ". ") if partes else ""
        if session.sintomas:
            return self._sintoma(session)
        return _resposta(
            session,
            conf + "Pode me contar o que esta sentindo?",
            options=["Dor no peito", "Falta de ar", "Palpitacao", "So tenho uma duvida"],
        )

    def _faq_medicamento(self, session: Session) -> dict[str, Any]:
        return _resposta(session, _RESP_MEDICAMENTO,
                         options=["Tenho um sintoma", "Duvida sobre exames", "Encerrar"])

    def _faq_exame(self, session: Session) -> dict[str, Any]:
        return _resposta(session, _RESP_EXAME,
                         options=["Tenho um sintoma", "Como agendar consulta", "Encerrar"])

    def _faq_fatores_risco(self, session: Session) -> dict[str, Any]:
        extra = ""
        if session.fatores_risco:
            extra = (
                "\n\nNo seu caso, ja registrei: "
                + ", ".join(session.fatores_risco)
                + "."
            )
        return _resposta(session, _RESP_FATORES_RISCO + extra,
                         options=["Tenho um sintoma", "Como agendar consulta", "Encerrar"])

    def _agendar(self, session: Session) -> dict[str, Any]:
        return _resposta(session, _RESP_AGENDAR,
                         options=["Sim, tenho sintoma", "Nao, sem sintomas", "Encerrar"])

    def _agradecimento(self, session: Session) -> dict[str, Any]:
        return _resposta(
            session,
            "Por nada! Posso ajudar em mais alguma coisa?",
            options=["Tenho outra duvida", "Encerrar"],
        )

    def _despedida(self, session: Session) -> dict[str, Any]:
        session.stage = "encerramento"
        resumo = None
        corpo = "Cuide-se! Se surgir dor no peito, falta de ar intensa ou desmaio, procure emergencia (192)."
        if session.sintomas or session.fatores_risco:
            flags = _red_flags(session)
            resumo = _montar_resumo(session, flags)
            corpo = (
                "Encerrando o atendimento. Segue o resumo da sua triagem "
                f"inicial.\n\nClassificacao: {resumo['classificacao']}\n"
                f"Conduta sugerida: {resumo['conduta_sugerida']}\n\n"
                "Cuide-se e leve este resumo ao atendimento."
            )
        return _resposta(session, corpo, summary=resumo, options=[])

    def _fallback(self, session: Session) -> dict[str, Any]:
        session.fallback_seguidos += 1
        if session.fallback_seguidos >= 2:
            session.fallback_seguidos = 0
            return _resposta(
                session,
                "Ainda nao consegui entender. Este assistente cobre apenas "
                "triagem inicial em cardiologia (sintomas, fatores de risco, "
                "exames e medicamentos do coracao). Se for uma emergencia, "
                "ligue 192. Pode reformular sua mensagem?",
                options=["Dor no peito", "Falta de ar", "Duvida sobre exame", "Encerrar"],
            )
        return _resposta(
            session,
            "Desculpe, nao entendi bem. Voce pode descrever um sintoma "
            "(ex.: \"estou com dor no peito ha 1 hora\") ou fazer uma pergunta "
            "sobre exames, medicamentos ou fatores de risco.",
            options=["Dor no peito", "Falta de ar", "Palpitacao", "Tontura"],
        )


# ---------------------------------------------------------------------------
# Helper de montagem de resposta
# ---------------------------------------------------------------------------


def _resposta(
    session: Session,
    corpo: str,
    *,
    summary: dict[str, Any] | None = None,
    options: list[str] | None = None,
) -> dict[str, Any]:
    reply = corpo
    if summary is not None or session.stage in {"emergencia", "encerramento", "triagem"}:
        reply = f"{corpo}\n\n{DISCLAIMER}"
    return {
        "reply": reply,
        "stage": session.stage,
        "summary": summary,
        "options": options or [],
    }
