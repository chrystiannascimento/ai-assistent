"""Wrapper do Presidio (analyzer + anonymizer) com mapa de reversao reversivel.

Fluxo: `anonimizar()` detecta PII via o Presidio Analyzer e usa o Presidio
Anonymizer para substituir cada ocorrencia por um placeholder unico
(`<ENTITY_TYPE_indice>`), guardando o valor original em um mapa em memoria com
TTL curto. `reverter()` troca os placeholders de volta pelos valores reais na
resposta do modelo escalonado. O mapa nunca e persistido em disco.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

PRESIDIO_ANALYZER_URL = os.environ.get("PRESIDIO_ANALYZER_URL", "http://localhost:5001")
PRESIDIO_ANONYMIZER_URL = os.environ.get("PRESIDIO_ANONYMIZER_URL", "http://localhost:5002")
PRESIDIO_LANGUAGE = os.environ.get("PRESIDIO_LANGUAGE", "pt")
TTL_PADRAO_SEGUNDOS = float(os.environ.get("PSEUDONIMIZACAO_TTL_SEGUNDOS", "300"))

HTTP_TIMEOUT_SECONDS = 10.0


class MapaExpiradoError(RuntimeError):
    """O mapa de reversao de pseudonimizacao expirou (TTL excedido)."""


@dataclass
class MapaReversivel:
    """Placeholder -> valor original, valido apenas por `ttl_segundos` a partir da criacao."""

    valores: dict[str, str]
    ttl_segundos: float = TTL_PADRAO_SEGUNDOS
    criado_em: float = field(default_factory=time.monotonic)

    def expirado(self) -> bool:
        return (time.monotonic() - self.criado_em) > self.ttl_segundos


def _chamar_analyzer(texto: str) -> list[dict[str, Any]]:
    resp = requests.post(
        f"{PRESIDIO_ANALYZER_URL}/analyze",
        json={"text": texto, "language": PRESIDIO_LANGUAGE},
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    return resp.json()


def _chamar_anonymizer(texto: str, entidade: dict[str, Any], placeholder: str) -> str:
    resp = requests.post(
        f"{PRESIDIO_ANONYMIZER_URL}/anonymize",
        json={
            "text": texto,
            "analyzer_results": [entidade],
            "anonymizers": {entidade["entity_type"]: {"type": "replace", "new_value": placeholder}},
        },
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    return resp.json()["text"]


def anonimizar(texto: str, ttl_segundos: float | None = None) -> tuple[str, MapaReversivel]:
    """Detecta PII em `texto` e substitui cada ocorrencia por um placeholder unico."""
    entidades = sorted(_chamar_analyzer(texto), key=lambda e: e["start"])

    contadores: dict[str, int] = {}
    valores: dict[str, str] = {}
    itens: list[tuple[dict[str, Any], str]] = []
    for entidade in entidades:
        tipo = entidade["entity_type"]
        indice = contadores.get(tipo, 0)
        contadores[tipo] = indice + 1
        placeholder = f"<{tipo}_{indice}>"
        valores[placeholder] = texto[entidade["start"] : entidade["end"]]
        itens.append((entidade, placeholder))

    texto_atual = texto
    # da direita para a esquerda: os offsets das entidades ainda nao
    # processadas (mais a esquerda) continuam validos apos cada substituicao
    for entidade, placeholder in reversed(itens):
        texto_atual = _chamar_anonymizer(texto_atual, entidade, placeholder)

    mapa = MapaReversivel(valores=valores, ttl_segundos=ttl_segundos if ttl_segundos is not None else TTL_PADRAO_SEGUNDOS)
    return texto_atual, mapa


def reverter(texto_resposta: str, mapa: MapaReversivel) -> str:
    """Troca os placeholders na resposta do modelo escalonado pelos valores originais."""
    if mapa.expirado():
        raise MapaExpiradoError(
            "O mapa de pseudonimizacao expirou; a informacao original nao pode mais ser recuperada."
        )
    texto = texto_resposta
    for placeholder, valor_original in mapa.valores.items():
        texto = texto.replace(placeholder, valor_original)
    return texto
