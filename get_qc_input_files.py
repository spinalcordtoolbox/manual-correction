#!/usr/bin/env python3
"""
Extract file names from SCT's qc_report.json for a given QC status and/or rank.

Entries can be filtered by QC status (``--qc``) and/or by rank (``--rank``); at
least one of the two is required, and when both are given an entry must match
both.

The QC status is passed as a keyword (``pass``, ``warn``, or ``fail``) rather
than the raw emoji, which interacts awkwardly with some shells (e.g. zsh on
macOS). The keyword is mapped internally to the emoji stored in the report.

The rank is the integer 0-9 set with the number keys in the QC report viewer,
stored in each entry's ``rank`` field (independent of the QC status).

By default prints each matching entry's ``inputFile`` (the source image, e.g.
the T2w). Pass ``--label`` to instead print the label file being QC'd, parsed
from the ``-s`` argument of the entry's ``cmdline``. This distinguishes sessions
that have several QC entries (one per label: seg, canal, disc, pmj, ...).

Usage:
  python get_qc_input_files.py --qc pass qc_report.json
  python get_qc_input_files.py --rank 2 qc_report.json
  python get_qc_input_files.py --qc pass --rank 2 qc_report.json
  python get_qc_input_files.py --qc warn --label --full-path qc_report.json

Example output:
$ python ~/code/manual-correction/get_qc_input_files.py --qc pass qc_report.json
    sub-001_T2w.nii.gz
    sub-004_T2w.nii.gz
$ python ~/code/manual-correction/get_qc_input_files.py --qc pass --label qc_report.json
    sub-001_T2w_seg.nii.gz
    sub-001_T2w_pmj.nii.gz
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


# Maps the string keyword accepted on the command line to the emoji stored in
# the QC report. Emojis are avoided as CLI arguments because they interact
# awkwardly with some shells (e.g. zsh on macOS).
QC_STATUS_TO_EMOJI: Dict[str, str] = {
    "pass": "✅",
    "warn": "⚠️",
    "fail": "❌",
}

# Matches the label/segmentation passed to `-s` in an entry's cmdline.
SEG_ARG_RE = re.compile(r"-s\s+(\S+\.nii\.gz)")


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


def extract_label_file(cmdline: str) -> Optional[str]:
    """Extract the label file (the ``-s`` argument) from an entry's cmdline.

    Args:
        cmdline: The ``cmdline`` string of a QC report entry.

    Returns:
        The path passed to ``-s``, or ``None`` if none is found.
    """
    match = SEG_ARG_RE.search(cmdline or "")
    return match.group(1) if match else None


def entry_matches(
    item: Dict[str, Any], emoji: Optional[str], rank: Optional[int]
) -> bool:
    """Check whether a QC report entry matches the requested filters.

    Args:
        item: A single QC report entry.
        emoji: QC emoji to match (e.g. "✅"), or None to not filter by QC.
        rank: Rank integer to match, or None to not filter by rank.

    Returns:
        True if the entry matches all of the provided (non-None) filters.
    """
    if emoji is not None and item.get("qc") != emoji:
        return False
    if rank is not None and item.get("rank") != rank:
        return False
    return True


def filter_input_files(
    report: Dict[str, Any],
    emoji: Optional[str],
    rank: Optional[int],
    full_path: bool = False,
) -> List[str]:
    """Filter inputFile entries by QC emoji and/or rank.

    Args:
        report: Parsed QC report dictionary.
        emoji: QC emoji to filter by (e.g. "✅", "⚠️", "❌"), or None.
        rank: Rank integer (0-9) to filter by, or None.
        full_path: If True, return path/inputFile, otherwise only inputFile.

    Returns:
        List of inputFile strings (or full paths) matching the filters.
    """
    datasets = report.get("datasets", [])
    results: List[str] = []

    for item in datasets:
        if not entry_matches(item, emoji, rank):
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


def filter_label_files(
    report: Dict[str, Any],
    emoji: Optional[str],
    rank: Optional[int],
    full_path: bool = False,
) -> List[str]:
    """Filter label files (cmdline ``-s`` argument) by QC emoji and/or rank.

    Unlike :func:`filter_input_files`, this returns the specific label being
    QC'd, so a session with several entries (seg, canal, disc, pmj, ...) is
    distinguished per label.

    Args:
        report: Parsed QC report dictionary.
        emoji: QC emoji to filter by (e.g. "✅", "⚠️", "❌"), or None.
        rank: Rank integer (0-9) to filter by, or None.
        full_path: If True, return the absolute ``-s`` path, otherwise only the
            file name.

    Returns:
        List of label file strings (or full paths) matching the filters.
    """
    datasets = report.get("datasets", [])
    results: List[str] = []

    for item in datasets:
        if not entry_matches(item, emoji, rank):
            continue
        label_file = extract_label_file(item.get("cmdline", ""))
        if not label_file:
            continue

        results.append(label_file if full_path else Path(label_file).name)

    return results


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Get files for a given QC status and/or rank from "
        "qc_report.json."
    )
    parser.add_argument(
        "qc_report",
        type=Path,
        help="Path to qc_report.json.",
    )
    parser.add_argument(
        "--qc",
        "-q",
        choices=list(QC_STATUS_TO_EMOJI),
        help="QC status to filter by: 'pass' (✅), 'warn' (⚠️), or 'fail' (❌).",
    )
    parser.add_argument(
        "--rank",
        "-r",
        type=int,
        choices=range(10),
        metavar="{0-9}",
        help="Rank (0-9) to filter by, as set with the number keys in the QC "
        "report viewer.",
    )
    parser.add_argument(
        "--label",
        "-l",
        action="store_true",
        help="Print the label file being QC'd (parsed from the cmdline `-s` "
        "argument) instead of the source inputFile. Gives per-label detail "
        "when a session has several QC entries.",
    )
    parser.add_argument(
        "--full-path",
        action="store_true",
        help="Print full paths instead of only the file name.",
    )
    args = parser.parse_args()

    if args.qc is None and args.rank is None:
        parser.error("at least one of --qc/-q or --rank/-r is required.")

    return args


def main() -> None:
    """Entry point for the script."""
    args = parse_args()
    report = load_qc_report(args.qc_report)

    emoji = QC_STATUS_TO_EMOJI[args.qc] if args.qc is not None else None

    if args.label:
        files = filter_label_files(
            report, emoji, args.rank, full_path=args.full_path
        )
    else:
        files = filter_input_files(
            report, emoji, args.rank, full_path=args.full_path
        )

    for f in sorted(files):
        print(f)

    # Print total count, describing the active filters.
    filters = []
    if args.qc is not None:
        filters.append(f"QC '{args.qc}' ({emoji})")
    if args.rank is not None:
        filters.append(f"rank {args.rank}")
    print(f"Total files with {' and '.join(filters)}: {len(files)}")


if __name__ == "__main__":
    main()
