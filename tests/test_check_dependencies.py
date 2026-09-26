"""Testes unitarios da logica pura de scripts/check_dependencies.py (sem rede real)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.check_dependencies import CheckResult, has_critical_failure


def _resultado(ok: bool, critical: bool) -> CheckResult:
    return CheckResult(name="servico-fake", ok=ok, critical=critical, latency_ms=None, message="")


def test_has_critical_failure_true_quando_critico_falha() -> None:
    resultados = [_resultado(ok=True, critical=True), _resultado(ok=False, critical=True)]
    assert has_critical_failure(resultados) is True


def test_has_critical_failure_false_quando_apenas_nao_critico_falha() -> None:
    resultados = [_resultado(ok=True, critical=True), _resultado(ok=False, critical=False)]
    assert has_critical_failure(resultados) is False


def test_has_critical_failure_false_quando_tudo_ok() -> None:
    resultados = [_resultado(ok=True, critical=True), _resultado(ok=True, critical=False)]
    assert has_critical_failure(resultados) is False
