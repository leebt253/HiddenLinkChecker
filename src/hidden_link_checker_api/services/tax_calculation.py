"""Integration boundary for the shared tax calculation library."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from shared_calculation import CalculationResult, calculate


def calculate_tax(
    data: list[Mapping[str, Any]], metadata: Mapping[str, Any]
) -> CalculationResult:
    """Calculate tax for records using the shared calculation library."""
    return calculate(data, metadata)


def calculate_tax_file(path: str | Path) -> CalculationResult:
    """Load a JSON calculation input and calculate its line and order totals."""
    input_data = _load_input(path)
    return calculate_tax(input_data["data"], input_data["metadata"])


def _load_input(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        input_data = json.load(handle)

    if not isinstance(input_data, dict):
        raise ValueError("tax calculation input must be a JSON object")
    if not isinstance(input_data.get("data"), list):
        raise ValueError("tax calculation input must contain a data list")
    if not isinstance(input_data.get("metadata"), dict):
        raise ValueError("tax calculation input must contain a metadata object")
    return input_data