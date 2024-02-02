#######################################################################
#
# Tests for update_json() function
#
# RUN BY:
#   python -m pytest -v tests/test_create_json.py
#######################################################################

import time
import json
from manual_correction import update_json


def test_create_json_modified_true(tmp_path):
    """
    Test that the function update_json() creates a JSON file with the expected metadata if modified=True, i.e., the
    label was manually corrected.
    """
    # Create a temporary file for testing
    fname_label = "sub-001_ses-01_T1w_seg-manual.nii.gz"
    nifti_file = tmp_path / fname_label
    nifti_file.touch()

    # Call the function with modified=True
    update_json(str(nifti_file), "Test Rater", modified=True)

    # Check that the JSON file was created and contains the expected metadata
    expected_metadata = {'SpatialReference': 'orig',
                         'GeneratedBy': [{'Name': 'Manual',
                                          'Author': "Test Rater",
                                          'Date': time.strftime('%Y-%m-%d %H:%M:%S')}]}
    json_file = tmp_path / fname_label.replace(".nii.gz", ".json")
    assert json_file.exists()
    with open(str(json_file), "r") as f:
        metadata = json.load(f)
    assert metadata == expected_metadata


def test_create_json_modified_false(tmp_path):
    """
    Test that the function update_json() creates a JSON file with the expected metadata if modified=False, i.e., the
    label was only visually inspected but not modified.
    """
    # Create a temporary file for testing
    fname_label = "sub-001_ses-01_T1w_seg-manual.nii.gz"
    nifti_file = tmp_path / fname_label
    nifti_file.touch()

    # Call the function with modified=True
    update_json(str(nifti_file), "Test Rater", modified=False)

    # Check that the JSON file was created and contains the expected metadata
    expected_metadata = {'SpatialReference': 'orig',
                         'GeneratedBy': [{'Name': 'Visually verified',
                                          'Author': "Test Rater",
                                          'Date': time.strftime('%Y-%m-%d %H:%M:%S')}]}
    json_file = tmp_path / fname_label.replace(".nii.gz", ".json")
    assert json_file.exists()
    with open(str(json_file), "r") as f:
        metadata = json.load(f)
    assert metadata == expected_metadata


def test_update_json_modified_true(tmp_path):
    """
    Test that the function update_json() updates (appends to) the JSON file with the expected metadata if
    modified=True, i.e., the label was manually corrected.
    """
    # Create a temporary file for testing
    fname_label = "sub-001_ses-01_T1w_seg-manual.nii.gz"
    nifti_file = tmp_path / fname_label
    nifti_file.touch()
    # Create JSON file with some metadata
    json_file = tmp_path / fname_label.replace(".nii.gz", ".json")
    with open(str(json_file), "w") as f:
        json.dump({'SpatialReference': 'orig',
                        'GeneratedBy': [{'Name': 'Manual',
                                         'Author': "Test Rater 1",
                                         'Date': "2023-01-01 00:00:00"}]}, f)

    # Call the function with modified=True
    update_json(str(nifti_file), "Test Rater 2", modified=True)

    # Check that the JSON file was created and contains the expected metadata
    expected_metadata = {'SpatialReference': 'orig',
                         'GeneratedBy': [{'Name': 'Manual',
                                          'Author': "Test Rater 1",
                                          'Date': "2023-01-01 00:00:00"},
                                         {'Name': 'Manual',
                                          'Author': "Test Rater 2",
                                          'Date': time.strftime('%Y-%m-%d %H:%M:%S')}]}
    json_file = tmp_path / fname_label.replace(".nii.gz", ".json")
    assert json_file.exists()
    with open(str(json_file), "r") as f:
        metadata = json.load(f)
    assert metadata == expected_metadata


def test_update_json_modified_false(tmp_path):
    """
    Test that the function update_json() updates (appends to) the JSON file with the expected metadata if
    modified=False, i.e., the label was only visually inspected but not modified.
    """
    # Create a temporary file for testing
    fname_label = "sub-001_ses-01_T1w_seg-manual.nii.gz"
    nifti_file = tmp_path / fname_label
    nifti_file.touch()
    # Create JSON file with some metadata
    json_file = tmp_path / fname_label.replace(".nii.gz", ".json")
    with open(str(json_file), "w") as f:
        json.dump({'SpatialReference': 'orig',
                   'GeneratedBy': [{'Name': 'Manual',
                                    'Author': "Test Rater 1",
                                    'Date': "2023-01-01 00:00:00"}]}, f)

    # Call the function with modified=True
    update_json(str(nifti_file), "Test Rater 2", modified=False)

    # Check that the JSON file was created and contains the expected metadata
    expected_metadata = {'SpatialReference': 'orig',
                         'GeneratedBy': [{'Name': 'Manual',
                                          'Author': "Test Rater 1",
                                          'Date': "2023-01-01 00:00:00"},
                                         {'Name': 'Visually verified',
                                          'Author': "Test Rater 2",
                                          'Date': time.strftime('%Y-%m-%d %H:%M:%S')}]}
    json_file = tmp_path / fname_label.replace(".nii.gz", ".json")
    assert json_file.exists()
    with open(str(json_file), "r") as f:
        metadata = json.load(f)
    assert metadata == expected_metadata
