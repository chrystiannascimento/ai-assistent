"""Testes do router: decisao entre responder localmente (Ollama) e escalonar
para o LiteLLM via tool-calling. Nenhuma chamada de rede real e feita."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from orchestrator.router import responder


def _resposta_ollama_direta(texto: str) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [{"message": {"role": "assistant", "content": texto, "tool_calls": None}}]
    }
    return resp


def _resposta_ollama_escalando(pergunta: str, motivo: str) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "function": {
                                "name": "escalar",
                                "arguments": json.dumps({"pergunta": pergunta, "motivo": motivo}),
                            }
                        }
                    ],
                }
            }
        ]
    }
    return resp


def _resposta_litellm(texto: str) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"choices": [{"message": {"content": texto}}]}
    return resp


@patch("orchestrator.router.requests.post")
def test_responde_direto_sem_escalonar(mock_post: MagicMock) -> None:
    mock_post.return_value = _resposta_ollama_direta("Sao 14:32.")

    resultado = responder("Que horas sao?")

    assert resultado == "Sao 14:32."
    assert mock_post.call_count == 1
    url_chamada = mock_post.call_args.args[0]
    assert "11434" in url_chamada


@patch("orchestrator.router.requests.post")
def test_escalona_quando_ollama_chama_tool_escalar(mock_post: MagicMock) -> None:
    pergunta = "Explique em detalhes a teoria da relatividade geral"
    mock_post.side_effect = [
        _resposta_ollama_escalando(pergunta, motivo="pergunta complexa de fisica"),
        _resposta_litellm("A relatividade geral e a teoria de Einstein sobre..."),
    ]

    resultado = responder(pergunta)

    assert resultado == "A relatividade geral e a teoria de Einstein sobre..."
    assert mock_post.call_count == 2
    primeira_url = mock_post.call_args_list[0].args[0]
    segunda_url = mock_post.call_args_list[1].args[0]
    assert "11434" in primeira_url
    assert "4000" in segunda_url
