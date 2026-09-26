"""Roteador: consulta o orquestrador local (Ollama) e escalona para o LiteLLM
quando o modelo local invocar a tool `escalar`.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests
from dotenv import load_dotenv

from orchestrator.tools.escalar import ESCALAR_TOOL_SCHEMA, NOME_TOOL_ESCALAR

load_dotenv()

logger = logging.getLogger(__name__)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:4b")
LITELLM_URL = os.environ.get("LITELLM_URL", "http://localhost:4000")
LITELLM_MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY", "")
ESCALATION_MODEL = os.environ.get("ESCALATION_MODEL", "claude-sonnet-5")

HTTP_TIMEOUT_SECONDS = 30.0

SYSTEM_PROMPT_LOCAL = (
    "Voce e o assistente de voz local de uma casa inteligente. Responda "
    "perguntas simples (horario, controle de dispositivos, conversa cotidiana) "
    "diretamente e de forma breve. Se a pergunta exigir conhecimento amplo, "
    "raciocinio complexo, geracao de texto longo, ou estiver fora do seu "
    "escopo, chame a ferramenta 'escalar' em vez de tentar responder."
)

SYSTEM_PROMPT_ESCALONADO = "Voce e um assistente avancado, acionado para perguntas complexas."


class RouterError(RuntimeError):
    """Erro ao consultar o Ollama ou o LiteLLM."""


def _chamar_ollama(pergunta: str) -> dict[str, Any]:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT_LOCAL},
            {"role": "user", "content": pergunta},
        ],
        "tools": [ESCALAR_TOOL_SCHEMA],
        "stream": False,
    }
    resp = requests.post(f"{OLLAMA_URL}/v1/chat/completions", json=payload, timeout=HTTP_TIMEOUT_SECONDS)
    if resp.status_code != 200:
        raise RouterError(f"Ollama respondeu HTTP {resp.status_code}: {resp.text}")
    return resp.json()


def _chamar_litellm(pergunta: str, motivo: str | None = None) -> str:
    mensagens = [{"role": "system", "content": SYSTEM_PROMPT_ESCALONADO}]
    if motivo:
        mensagens.append({"role": "system", "content": f"Motivo do escalonamento: {motivo}"})
    mensagens.append({"role": "user", "content": pergunta})

    payload = {"model": ESCALATION_MODEL, "messages": mensagens, "stream": False}
    headers = {"Authorization": f"Bearer {LITELLM_MASTER_KEY}"} if LITELLM_MASTER_KEY else {}
    resp = requests.post(f"{LITELLM_URL}/chat/completions", json=payload, headers=headers, timeout=HTTP_TIMEOUT_SECONDS)
    if resp.status_code != 200:
        raise RouterError(f"LiteLLM respondeu HTTP {resp.status_code}: {resp.text}")
    return resp.json()["choices"][0]["message"]["content"]


def _extrair_chamada_escalar(mensagem: dict[str, Any]) -> dict[str, Any] | None:
    for chamada in mensagem.get("tool_calls") or []:
        if chamada.get("function", {}).get("name") == NOME_TOOL_ESCALAR:
            return json.loads(chamada["function"].get("arguments") or "{}")
    return None


def responder(pergunta: str) -> str:
    """Responde a pergunta usando o orquestrador local; escalona se necessario."""
    resposta = _chamar_ollama(pergunta)
    mensagem = resposta["choices"][0]["message"]

    argumentos_escalar = _extrair_chamada_escalar(mensagem)
    if argumentos_escalar is not None:
        pergunta_escalada = argumentos_escalar.get("pergunta", pergunta)
        motivo = argumentos_escalar.get("motivo")
        logger.info("Escalonando pergunta para modelo maior (motivo=%s)", motivo)
        return _chamar_litellm(pergunta_escalada, motivo)

    return mensagem.get("content") or ""
