#######################################################################
#
# Test for create_json() function
#
# RUN BY:
#   python -m pytest -v tests/test_create_json.py
#######################################################################

import time
import json
from manual_correction import create_json, check_if_modified


def test_create_json_modified(tmp_path):
    """
    Test that the function create_json() creates a JSON file with the expected metadata if modified=True
    """
    # Create a temporary file for testing
    fname_label = "sub-001_ses-01_T1w_seg-manual.nii.gz"
    nifti_file = tmp_path / fname_label
    nifti_file.touch()

    # Call the function with modified=True
    create_json(str(nifti_file), "Test Rater", True)

    # Check that the JSON file was created and contains the expected metadata
    expected_metadata = {'Author': "Test Rater", 'Date': time.strftime('%Y-%m-%d %H:%M:%S')}
    json_file = tmp_path / fname_label.replace(".nii.gz", ".json")
    assert json_file.exists()
    with open(str(json_file), "r") as f:
        metadata = json.load(f)
    assert metadata == expected_metadata
