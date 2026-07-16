#######################################################################
#
# Tests for get_qc_input_files.py
#
# RUN BY:
#   python -m pytest -v tests/test_get_qc_input_files.py
#######################################################################

import os
import sys
import json
import subprocess
from pathlib import Path

from get_qc_input_files import (
    filter_input_files,
    filter_label_files,
    entry_matches,
    load_qc_report,
    extract_label_file,
    QC_STATUS_TO_EMOJI,
)

# Path to the script under test, resolved relative to this test file so it works
# regardless of the current working directory.
SCRIPT_PATH = Path(__file__).resolve().parent.parent / "get_qc_input_files.py"
REPO_ROOT = SCRIPT_PATH.parent


def sample_report():
    """Return a small in-memory QC report exercising the various filters.

    Entries cover: pass/warn/fail QC statuses, unset ("") QC, ranks 0/2/5,
    rank=None, an entry with no inputFile, and cmdlines with and without a
    ``-s`` label argument.
    """
    return {
        "datasets": [
            {  # 0: pass, rank 2
                "qc": "✅",
                "rank": 2,
                "inputFile": "sub-001_T2w.nii.gz",
                "path": "sub-001",
                "cmdline": "sct_qc -p sct_deepseg_sc -i sub-001/anat/sub-001_T2w.nii.gz "
                           "-s sub-001/anat/sub-001_T2w_seg.nii.gz",
            },
            {  # 1: unset qc, rank 2
                "qc": "",
                "rank": 2,
                "inputFile": "sub-002_T2w.nii.gz",
                "path": "sub-002",
                "cmdline": "sct_qc -p sct_deepseg_sc -i sub-002/anat/sub-002_T2w.nii.gz "
                           "-s sub-002/anat/sub-002_T2w_seg.nii.gz",
            },
            {  # 2: unset qc, rank 0
                "qc": "",
                "rank": 0,
                "inputFile": "sub-003_T2w.nii.gz",
                "path": "sub-003",
                "cmdline": "sct_qc -p sct_deepseg_sc -i sub-003/anat/sub-003_T2w.nii.gz "
                           "-s sub-003/anat/sub-003_T2w_seg.nii.gz",
            },
            {  # 3: warn, rank None
                "qc": "⚠️",
                "rank": None,
                "inputFile": "sub-004_T2w.nii.gz",
                "path": "sub-004",
                "cmdline": "sct_qc -p sct_deepseg_sc -i sub-004/anat/sub-004_T2w.nii.gz "
                           "-s sub-004/anat/sub-004_T2w_seg.nii.gz",
            },
            {  # 4: pass, rank 5, NO inputFile, has -s label
                "qc": "✅",
                "rank": 5,
                "path": "sub-005",
                "cmdline": "sct_qc -p sct_get_centerline -i sub-005/anat/sub-005_T2w.nii.gz "
                           "-s sub-005/anat/sub-005_T2w_pmj.nii.gz",
            },
            {  # 5: fail, rank None, cmdline with NO -s label
                "qc": "❌",
                "rank": None,
                "inputFile": "sub-006_T2w.nii.gz",
                "path": "sub-006",
                "cmdline": "sct_qc -p some_process -i sub-006/anat/sub-006_T2w.nii.gz",
            },
        ]
    }


def write_report(tmp_path):
    """Write the sample report to a JSON file and return its Path."""
    report_path = tmp_path / "qc_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(sample_report(), f)
    return report_path


# ---------------------------------------------------------------------------
# --qc filtering (filter_input_files with a QC emoji, rank=None)
# ---------------------------------------------------------------------------

def test_filter_input_files_qc_pass():
    """--qc pass returns only the ✅ entries' inputFiles (skipping ones w/o inputFile)."""
    report = sample_report()
    result = filter_input_files(report, QC_STATUS_TO_EMOJI["pass"], None)
    # Entry 0 is ✅ with an inputFile; entry 4 is ✅ but has no inputFile (skipped).
    assert result == ["sub-001_T2w.nii.gz"]


def test_filter_input_files_qc_warn():
    """--qc warn returns the single ⚠️ entry's inputFile."""
    report = sample_report()
    result = filter_input_files(report, QC_STATUS_TO_EMOJI["warn"], None)
    assert result == ["sub-004_T2w.nii.gz"]


def test_filter_input_files_qc_fail():
    """--qc fail returns the single ❌ entry's inputFile."""
    report = sample_report()
    result = filter_input_files(report, QC_STATUS_TO_EMOJI["fail"], None)
    assert result == ["sub-006_T2w.nii.gz"]


def test_filter_input_files_qc_full_path():
    """full_path=True joins path/inputFile."""
    report = sample_report()
    result = filter_input_files(report, QC_STATUS_TO_EMOJI["pass"], None, full_path=True)
    assert result == ["sub-001/sub-001_T2w.nii.gz"]


# ---------------------------------------------------------------------------
# --rank filtering (filter_input_files with emoji=None)
# ---------------------------------------------------------------------------

def test_filter_input_files_rank_matches_regardless_of_qc():
    """--rank 2 returns all entries with rank 2 regardless of their QC status."""
    report = sample_report()
    result = filter_input_files(report, None, 2)
    # Entry 0 (✅) and entry 1 ("") both have rank 2.
    assert result == ["sub-001_T2w.nii.gz", "sub-002_T2w.nii.gz"]


def test_filter_input_files_rank_zero():
    """--rank 0 returns its single entry (0 must not be treated as 'no filter')."""
    report = sample_report()
    result = filter_input_files(report, None, 0)
    assert result == ["sub-003_T2w.nii.gz"]


def test_filter_input_files_rank_not_present_returns_empty():
    """A rank present on no entry returns an empty list."""
    report = sample_report()
    result = filter_input_files(report, None, 9)
    assert result == []


def test_entry_matches_none_none_always_true():
    """entry_matches(item, None, None) is always True (the 'no filter' path)."""
    assert entry_matches({"qc": "✅", "rank": 2}, None, None) is True
    assert entry_matches({"qc": "", "rank": None}, None, None) is True
    assert entry_matches({}, None, None) is True


# ---------------------------------------------------------------------------
# Combined --qc + --rank (AND semantics)
# ---------------------------------------------------------------------------

def test_filter_input_files_qc_and_rank_match():
    """Combined filter returns only entries matching BOTH qc and rank."""
    report = sample_report()
    result = filter_input_files(report, QC_STATUS_TO_EMOJI["pass"], 2)
    # Entry 0 is ✅ AND rank 2. Entry 1 is rank 2 but not ✅; entry 4 is ✅ but rank 5.
    assert result == ["sub-001_T2w.nii.gz"]


def test_filter_input_files_qc_and_rank_no_match():
    """Combined filter returns [] when no entry matches both."""
    report = sample_report()
    result = filter_input_files(report, QC_STATUS_TO_EMOJI["pass"], 0)
    assert result == []


# ---------------------------------------------------------------------------
# entry_matches truth table
# ---------------------------------------------------------------------------

def test_entry_matches_truth_table():
    """entry_matches AND-combines the provided (non-None) filters."""
    item = {"qc": "✅", "rank": 2}
    # (None, None) -> True
    assert entry_matches(item, None, None) is True
    # matching emoji only
    assert entry_matches(item, "✅", None) is True
    # non-matching emoji
    assert entry_matches(item, "⚠️", None) is False
    # matching rank only
    assert entry_matches(item, None, 2) is True
    # non-matching rank
    assert entry_matches(item, None, 3) is False
    # both match
    assert entry_matches(item, "✅", 2) is True
    # one matches, one doesn't
    assert entry_matches(item, "✅", 3) is False
    assert entry_matches(item, "⚠️", 2) is False


# ---------------------------------------------------------------------------
# filter_label_files
# ---------------------------------------------------------------------------

def test_filter_label_files_basename_default():
    """filter_label_files returns the -s file basename by default."""
    report = sample_report()
    result = filter_label_files(report, QC_STATUS_TO_EMOJI["pass"], None)
    # Both ✅ entries (0 and 4) have a -s label, even though entry 4 has no inputFile.
    assert result == ["sub-001_T2w_seg.nii.gz", "sub-005_T2w_pmj.nii.gz"]


def test_filter_label_files_full_path():
    """filter_label_files returns the full -s path when full_path=True."""
    report = sample_report()
    result = filter_label_files(report, QC_STATUS_TO_EMOJI["pass"], None, full_path=True)
    assert result == [
        "sub-001/anat/sub-001_T2w_seg.nii.gz",
        "sub-005/anat/sub-005_T2w_pmj.nii.gz",
    ]


def test_filter_label_files_skips_entries_without_s_arg():
    """Entries whose cmdline has no -s ... .nii.gz are skipped."""
    report = sample_report()
    # Entry 5 (❌) has a cmdline without -s, so nothing is returned.
    result = filter_label_files(report, QC_STATUS_TO_EMOJI["fail"], None)
    assert result == []


def test_filter_label_files_respects_rank_filter():
    """filter_label_files honours the rank filter."""
    report = sample_report()
    result = filter_label_files(report, None, 2)
    assert result == ["sub-001_T2w_seg.nii.gz", "sub-002_T2w_seg.nii.gz"]


# ---------------------------------------------------------------------------
# extract_label_file
# ---------------------------------------------------------------------------

def test_extract_label_file_normal():
    """extract_label_file pulls the -s path out of a normal cmdline."""
    cmdline = "sct_qc -p sct_deepseg_sc -i img.nii.gz -s sub-001/anat/sub-001_T2w_seg.nii.gz"
    assert extract_label_file(cmdline) == "sub-001/anat/sub-001_T2w_seg.nii.gz"


def test_extract_label_file_no_s_arg():
    """extract_label_file returns None when there is no -s argument."""
    assert extract_label_file("sct_qc -p some_process -i sub-006_T2w.nii.gz") is None


def test_extract_label_file_empty_and_none():
    """extract_label_file returns None for empty string and None input."""
    assert extract_label_file("") is None
    assert extract_label_file(None) is None


# ---------------------------------------------------------------------------
# load_qc_report
# ---------------------------------------------------------------------------

def test_load_qc_report_roundtrip(tmp_path):
    """load_qc_report reads a JSON file back to an equal dict."""
    report = sample_report()
    report_path = tmp_path / "qc_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f)

    loaded = load_qc_report(report_path)
    assert loaded == report


# ---------------------------------------------------------------------------
# CLI-level behavior (subprocess)
# ---------------------------------------------------------------------------

def run_cli(*args):
    """Run the script as a subprocess and return the CompletedProcess."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
        env=env,
    )


def test_cli_qc_pass(tmp_path):
    """--qc pass exits 0, prints the inputFile and the pass summary line."""
    report_path = write_report(tmp_path)
    result = run_cli("--qc", "pass", str(report_path))
    assert result.returncode == 0, result.stderr
    assert "sub-001_T2w.nii.gz" in result.stdout
    assert f"Total files with QC 'pass' ({QC_STATUS_TO_EMOJI['pass']}): 1" in result.stdout


def test_cli_rank(tmp_path):
    """--rank 2 exits 0 and reports the rank summary line."""
    report_path = write_report(tmp_path)
    result = run_cli("--rank", "2", str(report_path))
    assert result.returncode == 0, result.stderr
    assert "sub-001_T2w.nii.gz" in result.stdout
    assert "sub-002_T2w.nii.gz" in result.stdout
    assert "Total files with rank 2: 2" in result.stdout


def test_cli_qc_and_rank(tmp_path):
    """--qc pass --rank 2 exits 0 and reports the combined summary line."""
    report_path = write_report(tmp_path)
    result = run_cli("--qc", "pass", "--rank", "2", str(report_path))
    assert result.returncode == 0, result.stderr
    expected = f"Total files with QC 'pass' ({QC_STATUS_TO_EMOJI['pass']}) and rank 2: 1"
    assert expected in result.stdout


def test_cli_requires_qc_or_rank(tmp_path):
    """Passing neither --qc nor --rank is an argparse error (exit code 2)."""
    report_path = write_report(tmp_path)
    result = run_cli(str(report_path))
    assert result.returncode == 2
    assert "at least one of --qc" in result.stderr


def test_cli_rank_out_of_range(tmp_path):
    """An out-of-range --rank is an invalid choice (exit code 2)."""
    report_path = write_report(tmp_path)
    result = run_cli("--rank", "10", str(report_path))
    assert result.returncode == 2
    assert "invalid choice" in result.stderr
