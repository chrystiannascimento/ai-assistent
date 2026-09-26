"""Valida orchestrator/config.yaml contra o schema Pydantic de litellm_config.py."""
from __future__ import annotations

from pathlib import Path

from orchestrator.litellm_config import carregar_config

CONFIG_PATH = Path(__file__).resolve().parent.parent / "orchestrator" / "config.yaml"


def test_config_yaml_e_valido() -> None:
    config = carregar_config(CONFIG_PATH)
    assert len(config.model_list) >= 2


def test_config_yaml_tem_orquestrador_local() -> None:
    config = carregar_config(CONFIG_PATH)
    nomes = [m.model_name for m in config.model_list]
    assert "orquestrador-local" in nomes


def test_config_yaml_tem_fallback_do_local_para_modelo_maior() -> None:
    config = carregar_config(CONFIG_PATH)
    assert len(config.router_settings.fallbacks) >= 1
    fallback = config.router_settings.fallbacks[0]
    assert "orquestrador-local" in fallback
    assert len(fallback["orquestrador-local"]) >= 1
