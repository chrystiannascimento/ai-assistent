"""Smoke tests contra servicos reais.

Rodam se os servicos estiverem no ar (ex.: via `docker compose up`); caso
contrario sao pulados com uma mensagem explicita, nunca falham silenciosamente.
"""
from __future__ import annotations

import os

import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:4b")


def _ollama_disponivel() -> bool:
    try:
        requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        return True
    except requests.exceptions.RequestException:
        return False


@pytest.mark.skipif(
    not _ollama_disponivel(),
    reason=f"Ollama nao acessivel em {OLLAMA_URL} (suba com `docker compose -f infra/docker-compose.yml up -d`)",
)
def test_ollama_tags_responde() -> None:
    resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
    assert resp.status_code == 200


@pytest.mark.skipif(
    not _ollama_disponivel(),
    reason=f"Ollama nao acessivel em {OLLAMA_URL} (suba com `docker compose -f infra/docker-compose.yml up -d`)",
)
def test_ollama_modelo_qwen_carregado() -> None:
    resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
    modelos = [m.get("name", "") for m in resp.json().get("models", [])]
    assert OLLAMA_MODEL in modelos, (
        f"modelo '{OLLAMA_MODEL}' nao encontrado; rode "
        f"`docker exec -it ollama ollama pull {OLLAMA_MODEL}`"
    )
