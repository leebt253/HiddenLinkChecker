import json
from decimal import Decimal
from pathlib import Path

import pytest

from hidden_link_checker_api.services.tax_calculation import calculate_tax_file


SAMPLE_INPUTS = sorted(
    path
    for path in Path(__file__).parents[3].joinpath("examples", "tax_inputs").glob("*.json")
    if not path.name.endswith(".result.json")
)


@pytest.mark.parametrize("input_path", SAMPLE_INPUTS, ids=lambda path: path.stem)
def test_sample_tax_inputs_are_calculated(input_path: Path):
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    result = calculate_tax_file(input_path)
    output_path = input_path.parents[1].joinpath("tax_outputs", input_path.name)
    if not output_path.exists():
        output_path = input_path.with_name(f"{input_path.stem}.result.json")
    expected = json.loads(output_path.read_text(encoding="utf-8"))
    item_field = payload["metadata"]["column_mapping"]["item_name"]

    assert len(payload["data"]) >= 10
    assert len(result.items) == len(expected["items"])
    for item, expected_item in zip(result.items, expected["items"]):
        assert item.original_data[item_field] == expected_item["item_name"]
        assert str(item.before_tax) == expected_item["before_tax"]
        assert str(item.vat) == expected_item["vat"]
        assert str(item.after_tax) == expected_item["after_tax"]

    assert result.total_before_tax > Decimal("0")
    assert result.total_after_tax >= result.total_before_tax
    assert str(result.total_before_tax) == expected["total_before_tax"]
    assert str(result.total_after_tax) == expected["total_after_tax"]


def test_calculate_tax_file_writes_json_output(tmp_path: Path):
    input_path = SAMPLE_INPUTS[0]
    output_path = tmp_path / "nested" / "calculation.json"

    calculate_tax_file(input_path, output_path)

    expected_path = input_path.parents[1].joinpath("tax_outputs", input_path.name)
    if not expected_path.exists():
        expected_path = input_path.with_name(f"{input_path.stem}.result.json")
    assert json.loads(output_path.read_text(encoding="utf-8")) == json.loads(
        expected_path.read_text(encoding="utf-8")
    )