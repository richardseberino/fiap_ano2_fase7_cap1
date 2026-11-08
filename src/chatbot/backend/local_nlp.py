# -*- coding: utf-8 -*-
"""Motor de NLP local (fallback offline).

Reproduz, de forma simplificada, o comportamento de classificacao de
*intents* e extracao de *entities* do IBM Watson Assistant. Serve para que o
prototipo funcione (e possa ser demonstrado em video) mesmo sem credenciais
da IBM Cloud. A mesma taxonomia de intents/entities esta no arquivo de
exportacao ``watson/skill-assistente-cardiologico.json``.

A saida de :func:`analyze` imita o formato do campo ``output`` do Watson:

    {
        "intent": {"intent": "informar_sintoma", "confidence": 0.85},
        "entities": [
            {"entity": "sintoma_cardiaco", "value": "dor no peito", "confidence": 1.0}
        ],
        "input": "estou com dor no peito"
    }
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

# ---------------------------------------------------------------------------
# Normalizacao
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    """Minusculas, sem acentos, sem pontuacao redundante, espacos colapsados."""
    text = (text or "").lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Base de conhecimento: intents
# ---------------------------------------------------------------------------
# (intent, peso, [expressoes]) -- a pontuacao final e a soma dos pesos das
# expressoes encontradas. O intent de maior pontuacao vence.

INTENT_RULES: list[tuple[str, float, list[str]]] = [
    (
        "emergencia",
        6.0,
        [
            "nao consigo respirar", "mal consigo respirar", "sem ar",
            "vou desmaiar", "quase desmaiei", "desmaiei", "perdi os sentidos",
            "socorro", "estou passando muito mal", "passando muito mal",
            "dor no peito muito forte", "dor muito forte no peito",
            "aperto muito forte no peito", "dor insuportavel no peito",
            "peito parece que vai explodir", "dor no peito e no braco",
            "suando frio com dor no peito", "chamar ambulancia", "emergencia",
            "acho que estou infartando", "acho que to infartando",
            "acho que estou tendo um infarto", "estou tendo um infarto",
        ],
    ),
    (
        "saudacao",
        3.0,
        ["oi", "ola", "bom dia", "boa tarde", "boa noite", "e ai", "opa",
         "tudo bem", "como vai", "ei"],
    ),
    (
        "despedida",
        3.0,
        ["tchau", "ate logo", "ate mais", "ate breve", "encerrar",
         "finalizar atendimento", "pode encerrar", "por enquanto e so",
         "era so isso", "obrigado tchau"],
    ),
    (
        "agradecimento",
        2.5,
        ["obrigado", "obrigada", "valeu", "agradeco", "muito grato",
         "muito grata", "agradecido"],
    ),
    (
        "informar_sintoma",
        2.0,
        ["estou com", "estou sentindo", "to com", "to sentindo", "sinto",
         "tenho sentido", "ando com", "comecei a sentir", "sente", "dor",
         "doi", "doendo", "aperto", "pontada", "queimacao", "falta de ar",
         "palpitacao", "coracao acelerado", "coracao disparado", "tontura",
         "tonto", "tonteira", "inchaco", "incha", "inchada", "cansaco",
         "canso", "sudorese", "suor frio", "enjoo", "nausea"],
    ),
    (
        "duvida_medicamento",
        3.0,
        ["remedio", "medicamento", "medicacao", "comprimido", "dose",
         "posso tomar", "devo tomar", "parar de tomar", "suspender o remedio",
         "bula", "losartana", "atenolol", "propranolol", "captopril",
         "enalapril", "aas", "acido acetilsalicilico", "sinvastatina",
         "atorvastatina", "anticoagulante", "varfarina", "efeito colateral"],
    ),
    (
        "duvida_fatores_risco",
        3.0,
        ["fumo", "fumante", "cigarro", "colesterol", "colesterol alto",
         "diabetes", "diabetico", "hipertensao", "pressao alta",
         "historico familiar", "meu pai teve infarto", "minha mae teve infarto",
         "sou sedentario", "sedentarismo", "estou acima do peso", "obesidade",
         "sobrepeso", "fator de risco", "fatores de risco", "risco de infarto",
         "risco para infarto", "risco cardiaco", "risco cardiovascular",
         "chance de ter um infarto", "chance de infarto"],
    ),
    (
        "duvida_exame",
        3.0,
        ["exame", "eletrocardiograma", "ecg", "ecocardiograma", "holter",
         "mapa 24 horas", "teste ergometrico", "teste de esteira",
         "cateterismo", "angiotomografia", "resultado do exame",
         "preciso fazer exame", "que exame"],
    ),
    (
        "agendar_consulta",
        3.0,
        ["agendar", "marcar consulta", "marcar uma consulta", "quero uma consulta",
         "consulta com cardiologista", "preciso de um cardiologista",
         "quando posso ir ao medico", "como marco", "agendamento"],
    ),
    (
        "informar_dados_pessoais",
        2.0,
        ["meu nome e", "me chamo", "pode me chamar de", "sou o", "sou a",
         "tenho", "anos de idade", "minha idade"],
    ),
]

# ---------------------------------------------------------------------------
# Base de conhecimento: entities
# ---------------------------------------------------------------------------

ENTITY_RULES: dict[str, dict[str, list[str]]] = {
    "sintoma_cardiaco": {
        "dor no peito": [
            "dor no peito", "dor toracica", "dor no torax", "aperto no peito",
            "peito apertado", "pressao no peito", "peso no peito",
            "queimacao no peito", "pontada no peito", "dor no coracao",
        ],
        "dor no braco": [
            "dor no braco", "dor no braco esquerdo", "formigamento no braco",
            "braco esquerdo dormente", "dormencia no braco",
        ],
        "falta de ar": [
            "falta de ar", "dificuldade para respirar", "dificuldade de respirar",
            "sem folego", "sem ar", "canseira", "dispneia", "ofegante",
            "cansa para respirar",
        ],
        "palpitacao": [
            "palpitacao", "coracao acelerado", "coracao disparado",
            "coracao falhando", "coracao descompassado", "taquicardia",
            "batedeira", "coracao aos pulos",
        ],
        "tontura": [
            "tontura", "tonto", "tonteira", "cabeca leve", "vertigem",
            "sensacao de desmaio", "vista escura",
        ],
        "desmaio": [
            "desmaio", "desmaiei", "sincope", "apaguei", "perdi os sentidos",
            "cheguei a desmaiar",
        ],
        "inchaco nas pernas": [
            "inchaco nas pernas", "pernas inchadas", "pe inchado",
            "pes inchados", "tornozelo inchado", "edema nas pernas",
        ],
        "sudorese fria": [
            "sudorese", "suor frio", "suando frio", "suei frio",
            "suando muito", "transpiracao fria",
        ],
        "fadiga": [
            "cansaco", "fadiga", "muito cansado", "muito cansada",
            "sem energia", "canso facil", "fraqueza",
        ],
        "nausea": ["nausea", "enjoo", "vontade de vomitar", "enjoado"],
    },
    "intensidade": {
        "leve": ["leve", "fraca", "fraco", "levinha", "pouca", "suave"],
        "moderada": ["moderada", "moderado", "media", "medio", "mais ou menos", "razoavel"],
        "forte": ["forte", "intensa", "intenso", "bastante forte", "muita dor"],
        "muito forte": [
            "muito forte", "muito intensa", "insuportavel", "excruciante",
            "pior dor da minha vida", "dor 10", "nota 10", "10 de 10",
        ],
    },
    "irradiacao": {
        "braco esquerdo": [
            "braco esquerdo", "para o braco", "desce para o braco",
            "irradia para o braco", "espalha para o braco",
        ],
        "mandibula": ["mandibula", "queixo", "maxilar", "para o queixo"],
        "costas": ["nas costas", "para as costas", "entre as costas", "nas costa"],
        "pescoco": ["pescoco", "no pescoco", "para o pescoco"],
        "ombro": ["ombro", "no ombro", "para o ombro"],
    },
}

# duracao / tempo de evolucao
_DURACAO_REGEX = re.compile(
    r"(\d+)\s*(minuto|minutos|min|hora|horas|dia|dias|semana|semanas|mes|meses)"
)
_DURACAO_PALAVRAS = {
    "agora": "agora",
    "neste momento": "agora",
    "de repente": "inicio subito",
    "do nada": "inicio subito",
    "comecou agora": "agora",
    "ha pouco": "ha poucos minutos",
    "hoje": "hoje",
    "ontem": "ontem",
    "essa semana": "esta semana",
    "faz tempo": "cronico",
    "ha meses": "cronico",
    "ha anos": "cronico",
}

_IDADE_REGEX = re.compile(r"\b(\d{1,3})\s*anos\b")
_NOME_REGEX = re.compile(r"(?:meu nome e|me chamo|pode me chamar de|sou o|sou a)\s+([a-z]+)")


# ---------------------------------------------------------------------------
# Extracao de entities
# ---------------------------------------------------------------------------


def _extract_entities(norm: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for entity, values in ENTITY_RULES.items():
        for value, synonyms in values.items():
            for syn in synonyms:
                if syn in norm:
                    key = (entity, value)
                    if key not in seen:
                        seen.add(key)
                        found.append(
                            {"entity": entity, "value": value, "confidence": 1.0}
                        )
                    break

    # duracao numerica
    m = _DURACAO_REGEX.search(norm)
    if m:
        found.append(
            {
                "entity": "duracao",
                "value": f"{m.group(1)} {m.group(2)}",
                "confidence": 1.0,
            }
        )
    else:
        for palavra, valor in _DURACAO_PALAVRAS.items():
            if palavra in norm:
                found.append({"entity": "duracao", "value": valor, "confidence": 0.9})
                break

    # idade
    mi = _IDADE_REGEX.search(norm)
    if mi:
        found.append({"entity": "idade", "value": mi.group(1), "confidence": 1.0})

    # nome
    mn = _NOME_REGEX.search(norm)
    if mn:
        found.append(
            {"entity": "nome", "value": mn.group(1).capitalize(), "confidence": 0.8}
        )

    return found


# ---------------------------------------------------------------------------
# Classificacao de intent
# ---------------------------------------------------------------------------


def _classify_intent(norm: str, entities: list[dict[str, Any]]) -> tuple[str, float]:
    scores: dict[str, float] = {}
    for intent, weight, expressions in INTENT_RULES:
        hits = sum(1 for expr in expressions if expr in norm)
        if hits:
            scores[intent] = scores.get(intent, 0.0) + weight + (hits - 1) * 0.5

    entity_names = {e["entity"] for e in entities}
    sintoma_values = {e["value"] for e in entities if e["entity"] == "sintoma_cardiaco"}

    # Reforcos contextuais
    if "sintoma_cardiaco" in entity_names:
        scores["informar_sintoma"] = scores.get("informar_sintoma", 0.0) + 2.0
    if "desmaio" in sintoma_values:
        scores["emergencia"] = scores.get("emergencia", 0.0) + 4.0
    if {"dor no peito"} & sintoma_values and any(
        e["entity"] == "intensidade" and e["value"] == "muito forte" for e in entities
    ):
        scores["emergencia"] = scores.get("emergencia", 0.0) + 4.0

    if not scores:
        return "fora_de_escopo", 0.2

    best = max(scores, key=scores.get)
    # normaliza para uma "confianca" entre ~0.3 e 0.99
    confidence = min(0.99, 0.45 + 0.14 * scores[best])
    return best, confidence


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------


def analyze(text: str) -> dict[str, Any]:
    """Classifica um enunciado do usuario (formato compativel com o Watson)."""
    norm = _normalize(text)
    entities = _extract_entities(norm)
    intent, confidence = _classify_intent(norm, entities)
    return {
        "intent": {"intent": intent, "confidence": round(confidence, 2)},
        "entities": entities,
        "input": text,
        "normalized": norm,
    }
