"""Definicao da tool `escalar`, exposta ao orquestrador local (Ollama) via function-calling.

Quando o modelo local decide que uma pergunta esta fora do seu escopo, ele
invoca esta tool em vez de responder diretamente; o router.py entao repassa a
pergunta para o LiteLLM, que aciona o modelo maior configurado.
"""
from __future__ import annotations

NOME_TOOL_ESCALAR = "escalar"

ESCALAR_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": NOME_TOOL_ESCALAR,
        "description": (
            "Encaminha a pergunta para um modelo de linguagem maior e mais capaz, "
            "rodando fora da rede local. Use quando a pergunta exigir conhecimento "
            "amplo, raciocinio complexo, geracao de texto longo, ou estiver fora "
            "do escopo de um assistente domestico simples (horario, controle de "
            "dispositivos, conversa cotidiana)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pergunta": {
                    "type": "string",
                    "description": "A pergunta original do usuario, a ser respondida pelo modelo maior.",
                },
                "motivo": {
                    "type": "string",
                    "description": "Motivo curto pelo qual esta pergunta precisa ser escalonada.",
                },
            },
            "required": ["pergunta"],
        },
    },
}
