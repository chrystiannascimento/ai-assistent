"""Validacao tipada do orchestrator/config.yaml (configuracao do LiteLLM)."""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class LiteLLMParams(BaseModel):
    model: str
    api_base: str | None = None
    api_key: str | None = None


class ModelEntry(BaseModel):
    model_name: str
    litellm_params: LiteLLMParams


class RouterSettings(BaseModel):
    fallbacks: list[dict[str, list[str]]] = Field(default_factory=list)


class LiteLLMConfig(BaseModel):
    model_list: list[ModelEntry]
    router_settings: RouterSettings = Field(default_factory=RouterSettings)
    litellm_settings: dict = Field(default_factory=dict)


def carregar_config(caminho: Path | str) -> LiteLLMConfig:
    with open(caminho, encoding="utf-8") as f:
        bruto = yaml.safe_load(f)
    return LiteLLMConfig.model_validate(bruto)
