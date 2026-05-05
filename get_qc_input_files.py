#!/usr/bin/env python3
"""
Extract input filenames from SCT's qc_report.json for a given QC emoji.

Usage:
  python get_qc_input_files.py --qc "✅" qc_report.json
  python get_qc_input_files.py --qc "⚠️" --full-path qc_report.json

Example output:
$ python ~/code/manual-correction/get_qc_input_files.py --qc ✅ qc_report.json
    sub-001_T2w.nii.gz
    sub-004_T2w.nii.gz
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


EMOJI_CHOICES: List[str] = ["✅", "⚠️", "❌"]


def load_qc_report(path: Path) -> Dict[str, Any]:
    """Load QC report JSON file.

    Args:
        path: Path to qc_report.json.

    Returns:
        Parsed JSON as a dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def filter_input_files(
    report: Dict[str, Any], emoji: str, full_path: bool = False
) -> List[str]:
    """Filter inputFile entries by QC emoji.

    Args:
        report: Parsed QC report dictionary.
        emoji: QC emoji to filter by (e.g. "✅", "⚠️", "❌").
        full_path: If True, return path/inputFile, otherwise only inputFile.

    Returns:
        List of inputFile strings (or full paths) matching the given emoji.
    """
    datasets = report.get("datasets", [])
    results: List[str] = []

    for item in datasets:
        if item.get("qc") != emoji:
            continue
        input_file = item.get("inputFile")
        if not input_file:
            continue

        if full_path:
            base_path = item.get("path", "")
            results.append(str(Path(base_path) / input_file))
        else:
            results.append(input_file)

    return results


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Get inputFiles for a given QC emoji from qc_report.json."
    )
    parser.add_argument(
        "qc_report",
        type=Path,
        help="Path to qc_report.json.",
    )
    parser.add_argument(
        "--qc",
        "-q",
        required=True,
        choices=EMOJI_CHOICES,
        help="QC emoji to filter by (✅, ⚠️, or ❌).",
    )
    parser.add_argument(
        "--full-path",
        action="store_true",
        help="Print full paths (path/inputFile) instead of only inputFile.",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point for the script."""
    args = parse_args()
    report = load_qc_report(args.qc_report)
    input_files = filter_input_files(report, args.qc, full_path=args.full_path)

    for f in sorted(input_files):
        print(f)

    # Print total count
    print(f"Total files with QC '{args.qc}': {len(input_files)}")


if __name__ == "__main__":
    main()

