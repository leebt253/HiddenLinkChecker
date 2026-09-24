"""Run tax calculation from a JSON input file and write a JSON result."""

from __future__ import annotations

import argparse
from pathlib import Path

from hidden_link_checker_api.services.tax_calculation import calculate_tax_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Path to the calculation input JSON")
    parser.add_argument("output", type=Path, help="Path for the calculation output JSON")
    args = parser.parse_args()

    calculate_tax_file(args.input, args.output)
    print(f"Wrote tax calculation output to {args.output}")


if __name__ == "__main__":
    main()