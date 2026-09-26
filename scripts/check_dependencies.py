#!/usr/bin/env python3
"""Verifica a saude de todos os servicos do assistente de voz.

Uso:
    python scripts/check_dependencies.py
    python scripts/check_dependencies.py --json
    python scripts/check_dependencies.py --watch --interval 10
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import requests
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

HTTP_TIMEOUT_SECONDS = 5.0
TCP_TIMEOUT_SECONDS = 3.0


class Color:
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def _use_color() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _colorize(text: str, color: str) -> str:
    if not _use_color():
        return text
    return f"{color}{text}{Color.RESET}"


@dataclass
class CheckResult:
    name: str
    ok: bool
    critical: bool
    latency_ms: float | None
    message: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "ok": self.ok,
            "critical": self.critical,
            "latency_ms": self.latency_ms,
            "message": self.message,
        }


@dataclass
class Check:
    name: str
    critical: bool
    run: Callable[[], tuple[bool, str]] = field(repr=False)

    def execute(self) -> CheckResult:
        start = time.perf_counter()
        try:
            ok, message = self.run()
        except Exception as exc:  # defesa contra qualquer falha inesperada de rede/parsing
            ok, message = False, f"erro inesperado: {exc}"
        latency_ms = (time.perf_counter() - start) * 1000
        return CheckResult(
            name=self.name,
            ok=ok,
            critical=self.critical,
            latency_ms=latency_ms if ok else None,
            message=message,
        )


def check_http(url: str, headers: dict | None = None) -> tuple[bool, str]:
    try:
        resp = requests.get(url, headers=headers or {}, timeout=HTTP_TIMEOUT_SECONDS)
    except requests.exceptions.RequestException as exc:
        return False, f"sem conexao com {url} ({exc.__class__.__name__})"
    if resp.status_code == 200:
        return True, "OK"
    return False, f"HTTP {resp.status_code}"


def check_tcp(host: str, port: int) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=TCP_TIMEOUT_SECONDS):
            return True, "OK"
    except OSError as exc:
        return False, f"sem conexao com {host}:{port} ({exc.__class__.__name__})"


def check_home_assistant() -> tuple[bool, str]:
    url = os.environ.get("HA_URL", "http://localhost:8123")
    token = os.environ.get("HA_LONG_LIVED_TOKEN", "")
    return check_http(f"{url}/api/", headers={"Authorization": f"Bearer {token}"})


def check_ollama() -> tuple[bool, str]:
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    expected_model = os.environ.get("OLLAMA_MODEL", "qwen3:4b")
    try:
        resp = requests.get(f"{url}/api/tags", timeout=HTTP_TIMEOUT_SECONDS)
    except requests.exceptions.RequestException as exc:
        return False, f"sem conexao com {url} ({exc.__class__.__name__})"
    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}"
    models = [m.get("name", "") for m in resp.json().get("models", [])]
    if expected_model not in models:
        return False, f"modelo '{expected_model}' nao encontrado (disponiveis: {models or 'nenhum'})"
    return True, f"OK (modelo '{expected_model}' carregado)"


def check_litellm() -> tuple[bool, str]:
    url = os.environ.get("LITELLM_URL", "http://localhost:4000")
    return check_http(f"{url}/health")


def check_presidio_analyzer() -> tuple[bool, str]:
    url = os.environ.get("PRESIDIO_ANALYZER_URL", "http://localhost:5001")
    return check_http(f"{url}/health")


def check_presidio_anonymizer() -> tuple[bool, str]:
    url = os.environ.get("PRESIDIO_ANONYMIZER_URL", "http://localhost:5002")
    return check_http(f"{url}/health")


def check_wyoming_wakeword() -> tuple[bool, str]:
    host = os.environ.get("WYOMING_WAKEWORD_HOST", "localhost")
    port = int(os.environ.get("WYOMING_WAKEWORD_PORT", "10400"))
    return check_tcp(host, port)


def check_wyoming_whisper() -> tuple[bool, str]:
    host = os.environ.get("WYOMING_WHISPER_HOST", "localhost")
    port = int(os.environ.get("WYOMING_WHISPER_PORT", "10300"))
    return check_tcp(host, port)


def check_wyoming_piper() -> tuple[bool, str]:
    host = os.environ.get("WYOMING_PIPER_HOST", "localhost")
    port = int(os.environ.get("WYOMING_PIPER_PORT", "10200"))
    return check_tcp(host, port)


def build_checks() -> list[Check]:
    """Registro dos servicos monitorados.

    Cresce a cada fase do projeto conforme os respectivos docker-compose sao
    criados (ver README, secao de fases): Fase 0 comeca com HA + Ollama.
    """
    return [
        Check("Home Assistant", critical=True, run=check_home_assistant),
        Check("Ollama", critical=True, run=check_ollama),
        Check("Wyoming - openWakeWord", critical=False, run=check_wyoming_wakeword),
        Check("Wyoming - Whisper", critical=False, run=check_wyoming_whisper),
        Check("Wyoming - Piper", critical=False, run=check_wyoming_piper),
        Check("LiteLLM", critical=False, run=check_litellm),
        Check("Presidio Analyzer", critical=False, run=check_presidio_analyzer),
        Check("Presidio Anonymizer", critical=False, run=check_presidio_anonymizer),
    ]


def run_checks() -> list[CheckResult]:
    return [check.execute() for check in build_checks()]


def print_human(results: list[CheckResult]) -> None:
    name_width = max(len(r.name) for r in results) + 2
    for r in results:
        if r.ok:
            status = _colorize("OK", Color.GREEN)
            detail = f"{r.latency_ms:.0f}ms" if r.latency_ms is not None else ""
        else:
            crit_tag = " [CRITICO]" if r.critical else ""
            status = _colorize(f"FALHA{crit_tag}", Color.RED if r.critical else Color.YELLOW)
            detail = r.message
        print(f"{r.name.ljust(name_width)} {status.ljust(20 if _use_color() else 10)} {detail}")


def print_json(results: list[CheckResult]) -> None:
    print(json.dumps({"timestamp": time.time(), "checks": [r.to_dict() for r in results]}, indent=2))


def has_critical_failure(results: list[CheckResult]) -> bool:
    return any(not r.ok and r.critical for r in results)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="saida estruturada em JSON")
    parser.add_argument("--watch", action="store_true", help="checagem continua")
    parser.add_argument("--interval", type=float, default=10.0, help="intervalo em segundos para --watch (default: 10)")
    args = parser.parse_args()

    def run_once() -> list[CheckResult]:
        results = run_checks()
        if args.json:
            print_json(results)
        else:
            print_human(results)
        return results

    if args.watch:
        try:
            while True:
                results = run_once()
                if not args.json:
                    print(_colorize("-" * 40, Color.BOLD))
                time.sleep(args.interval)
        except KeyboardInterrupt:
            return 0
        return 0 if not has_critical_failure(results) else 1

    results = run_once()
    return 1 if has_critical_failure(results) else 0


if __name__ == "__main__":
    sys.exit(main())
