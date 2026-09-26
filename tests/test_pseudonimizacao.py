"""Testes de pseudonimizacao: nenhuma chamada de rede real ao Presidio e feita.

`_chamar_analyzer` e mockado para retornar entidades fixas; `_chamar_anonymizer`
e mockado com uma funcao que reproduz o comportamento real do Presidio
Anonymizer (substituicao de substring por offset), para exercitar a logica
real de `anonimizar`/`reverter` sem depender dos servicos externos.
"""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from orchestrator.pseudonimizacao.presidio_client import (
    MapaExpiradoError,
    MapaReversivel,
    anonimizar,
    reverter,
)

TEXTO_ORIGINAL = (
    "Meu nome e Joao da Silva, meu CPF e 123.456.789-00 "
    "e meu email e joao.silva@example.com"
)


def _entidades_mockadas() -> list[dict]:
    return [
        {
            "entity_type": "PERSON",
            "start": TEXTO_ORIGINAL.index("Joao da Silva"),
            "end": TEXTO_ORIGINAL.index("Joao da Silva") + len("Joao da Silva"),
            "score": 0.9,
        },
        {
            "entity_type": "CPF",
            "start": TEXTO_ORIGINAL.index("123.456.789-00"),
            "end": TEXTO_ORIGINAL.index("123.456.789-00") + len("123.456.789-00"),
            "score": 0.9,
        },
        {
            "entity_type": "EMAIL_ADDRESS",
            "start": TEXTO_ORIGINAL.index("joao.silva@example.com"),
            "end": TEXTO_ORIGINAL.index("joao.silva@example.com") + len("joao.silva@example.com"),
            "score": 0.9,
        },
    ]


def _fake_anonymizer(texto: str, entidade: dict, placeholder: str) -> str:
    inicio, fim = entidade["start"], entidade["end"]
    return texto[:inicio] + placeholder + texto[fim:]


@patch("orchestrator.pseudonimizacao.presidio_client._chamar_anonymizer", side_effect=_fake_anonymizer)
@patch("orchestrator.pseudonimizacao.presidio_client._chamar_analyzer", return_value=_entidades_mockadas())
def test_round_trip_anonimizar_e_reverter(mock_analyzer, mock_anonymizer) -> None:
    texto_anonimizado, mapa = anonimizar(TEXTO_ORIGINAL)

    # PII nao deve mais aparecer no texto anonimizado
    assert "Joao da Silva" not in texto_anonimizado
    assert "123.456.789-00" not in texto_anonimizado
    assert "joao.silva@example.com" not in texto_anonimizado
    assert "<PERSON_0>" in texto_anonimizado
    assert "<CPF_0>" in texto_anonimizado
    assert "<EMAIL_ADDRESS_0>" in texto_anonimizado

    # simula uma resposta do modelo grande que referencia os placeholders
    resposta_modelo_grande = (
        f"Confirmado, <PERSON_0>! Seu CPF (<CPF_0>) e o email (<EMAIL_ADDRESS_0>) "
        "foram validados com sucesso."
    )

    texto_revertido = reverter(resposta_modelo_grande, mapa)

    esperado = (
        "Confirmado, Joao da Silva! Seu CPF (123.456.789-00) e o email "
        "(joao.silva@example.com) foram validados com sucesso."
    )
    assert texto_revertido == esperado


def test_reverter_falha_quando_mapa_expirou() -> None:
    mapa = MapaReversivel(valores={"<PERSON_0>": "Joao da Silva"}, ttl_segundos=0.01)
    time.sleep(0.02)

    with pytest.raises(MapaExpiradoError):
        reverter("Ola <PERSON_0>", mapa)


def test_mapa_nao_expirado_ainda_reverte_normalmente() -> None:
    mapa = MapaReversivel(valores={"<PERSON_0>": "Joao da Silva"}, ttl_segundos=60)
    assert reverter("Ola <PERSON_0>", mapa) == "Ola Joao da Silva"
