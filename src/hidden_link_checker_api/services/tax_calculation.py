"""Integration boundary for the shared tax calculation library."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from shared_calculation import CalculationResult, calculate


def calculate_tax(
    data: list[Mapping[str, Any]], metadata: Mapping[str, Any]
) -> CalculationResult:
    """Calculate tax for records using the shared calculation library."""
    return calculate(data, metadata)


def calculate_tax_file(
    input_path: str | Path, output_path: str | Path | None = None
) -> CalculationResult:
    """Calculate a JSON input and optionally write the result as JSON."""
    input_data = _load_input(input_path)
    result = calculate_tax(input_data["data"], input_data["metadata"])
    if output_path is not None:
        _write_output(result, input_data["metadata"], output_path)
    return result


def _write_output(
    result: CalculationResult, metadata: Mapping[str, Any], output_path: str | Path
) -> None:
    item_field = metadata["column_mapping"]["item_name"]
    output = {
        "items": [
            {
                "item_name": item.original_data[item_field],
                "before_tax": str(item.before_tax),
                "vat": str(item.vat),
                "after_tax": str(item.after_tax),
            }
            for item in result.items
        ],
        "total_before_tax": str(result.total_before_tax),
        "total_after_tax": str(result.total_after_tax),
    }
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")


def _load_input(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        input_data = json.load(handle)

    if not isinstance(input_data, dict):
        raise TypeError("tax calculation input must be a JSON object")
    if not isinstance(input_data.get("data"), list):
        raise TypeError("tax calculation input must contain a data list")
    if not isinstance(input_data.get("metadata"), dict):
        raise TypeError("tax calculation input must contain a metadata object")
    return input_data