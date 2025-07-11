#######################################################################
#
# Tests for utils.py functions
#
# RUN BY:
#   python -m pytest -v tests/test_utils.py
#######################################################################

import os

import numpy as np
import nibabel as nib

from utils import fetch_subject_and_session, add_suffix, remove_suffix, splitext, curate_dict_yml, get_full_path, \
    check_files_exist, fetch_yaml_config, track_corrections, get_orientation, change_orientation


def test_fetch_subject_and_session():
    # Test 1: Test for correct subject ID, session ID, filename, and contrast
    filename_path = "/home/user/MRI/bids/sub-001/ses-01/anat/sub-001_ses-01_T1w.nii.gz"
    subjectID, sessionID, filename, contrast = fetch_subject_and_session(filename_path)
    assert subjectID == "sub-001"
    assert sessionID == "ses-01"
    assert filename == "sub-001_ses-01_T1w.nii.gz"
    assert contrast == "anat"

    # Test 2: Test for correct subject ID, session ID, filename, and contrast for a different file
    filename_path = "/home/user/MRI/bids/sub-002/ses-02/dwi/sub-002_ses-02_dwi.nii.gz"
    subjectID, sessionID, filename, contrast = fetch_subject_and_session(filename_path)
    assert subjectID == "sub-002"
    assert sessionID == "ses-02"
    assert filename == "sub-002_ses-02_dwi.nii.gz"
    assert contrast == "dwi"

    # Test 3: Test for correct subject ID, session ID, and filename for a file with missing session ID
    filename_path = "/home/user/MRI/bids/sub-003/anat/sub-003_T1w.nii.gz"
    subjectID, sessionID, filename, contrast = fetch_subject_and_session(filename_path)
    assert subjectID == "sub-003"
    assert sessionID == ""
    assert filename == "sub-003_T1w.nii.gz"
    assert contrast == "anat"

    # Test 4: Test if only filename (without session) is provided
    filename_path = "sub-003_T1w.nii.gz"
    subjectID, sessionID, filename, contrast = fetch_subject_and_session(filename_path)
    assert subjectID == "sub-003"
    assert sessionID == ""
    assert filename == "sub-003_T1w.nii.gz"
    assert contrast == "anat"

    # Test 5: Test if only filename (with session) is provided
    filename_path = "sub-003_ses-01_T1w.nii.gz"
    subjectID, sessionID, filename, contrast = fetch_subject_and_session(filename_path)
    assert subjectID == "sub-003"
    assert sessionID == "ses-01"
    assert filename == "sub-003_ses-01_T1w.nii.gz"
    assert contrast == "anat"

    # Test 6: Test if only filename (with session with >2 characters) is provided
    filename_path = "sub-003_ses-001_T1w.nii.gz"
    subjectID, sessionID, filename, contrast = fetch_subject_and_session(filename_path)
    assert subjectID == "sub-003"
    assert sessionID == "ses-001"
    assert filename == "sub-003_ses-001_T1w.nii.gz"
    assert contrast == "anat"

    # Test 7: Test for empty strings when input filename path is invalid
    filename_path = "invalid_filename_path.nii.gz"
    subjectID, sessionID, filename, contrast = fetch_subject_and_session(filename_path)
    assert subjectID == ""
    assert sessionID == ""
    assert filename == "invalid_filename_path.nii.gz"
    assert contrast == "anat"


def test_splitext():
    assert splitext('sub-001_ses-01_T1w.nii') == ('sub-001_ses-01_T1w', '.nii')
    assert splitext('anat/sub-001_ses-01_T1w.nii.gz') == ('anat/sub-001_ses-01_T1w', '.nii.gz')


def test_add_suffix():
    assert add_suffix('sub-001_ses-01_T1w.nii', '_seg') == 'sub-001_ses-01_T1w_seg.nii'
    assert add_suffix('anat/sub-001_ses-01_T1w.nii.gz', '_seg') == 'anat/sub-001_ses-01_T1w_seg.nii.gz'


def test_remove_suffix():
    assert remove_suffix('sub-001_ses-01_T1w_seg.nii', '_seg') == 'sub-001_ses-01_T1w.nii'
    assert remove_suffix('anat/sub-001_ses-01_T1w_seg.nii.gz', '_seg') == 'anat/sub-001_ses-01_T1w.nii.gz'


def test_curate_dict_yml():
    """
    Test that the curate_dict_yml function returns the expected output dictionary
    """
    input_dict = {'FILES_LABEL': ['/path/to/sub-001_acq-sag_T2w.nii.gz',
                                  '/path/to/sub-002_acq-sag_T2w.nii.gz',
                                  '/path/to/sub-003_acq-sag_T2w.nii.gz']}
    expected_output_dict = {'FILES_LABEL': ['sub-001_acq-sag_T2w.nii.gz',
                                            'sub-002_acq-sag_T2w.nii.gz',
                                            'sub-003_acq-sag_T2w.nii.gz']}
    assert curate_dict_yml(input_dict) == expected_output_dict


def test_get_full_path(tmp_path):
    """
    Test that the full path is returned. If ~ is passed, expand it to home directory.
    """
    assert get_full_path('~/MRI/BIDS') == os.path.expanduser('~/MRI/BIDS')
    assert get_full_path('MRI/BIDS') == os.path.abspath('MRI/BIDS')


def test_check_files_exist_all_files_exist(tmp_path, caplog):
    """
    Test that the check_files_exist function does not raise any warning when all files exist
    """
    # create some test files
    path_data = tmp_path / "BIDS"
    os.makedirs(path_data / "sub-001" / "ses-01" / "anat", exist_ok=True)
    os.makedirs(path_data / "sub-002" / "ses-01" / "anat", exist_ok=True)
    open(path_data / "sub-001" / "ses-01" / "anat" / "sub-001_ses-01_T1w.nii.gz", "w").close()
    open(path_data / "sub-001" / "ses-01" / "anat" / "sub-001_ses-01_T1w_seg.nii.gz", "w").close()
    open(path_data / "sub-001" / "ses-01" / "anat" / "sub-001_ses-01_T1w_labels-disc.nii.gz", "w").close()
    open(path_data / "sub-002" / "ses-01" / "anat" / "sub-002_ses-01_T2star.nii.gz", "w").close()
    open(path_data / "sub-002" / "ses-01" / "anat" / "sub-002_ses-01_T2star_gmseg.nii.gz", "w").close()
    open(path_data / "sub-002" / "ses-01" / "anat" / "sub-002_ses-01_T1w_labels-disc.nii.gz", "w").close()

    # create a YML config file
    dict_files = {
        "FILES_SEG": ["sub-001/ses-01/anat/sub-001_ses-01_T1w.nii.gz"],
        "FILES_GMSEG": ["sub-002/ses-01/anat/sub-002_ses-01_T2star.nii.gz"],
        "FILES_LABEL": ["sub-*_T1w.nii.gz"],
    }
    suffix_dict = {
        'FILES_SEG': '_seg',
        'FILES_GMSEG': '_gmseg',
        'FILES_LABEL': '_labels-disc',
    }

    # run the function
    check_files_exist(dict_files, path_img=path_data, path_label=path_data, suffix_dict=suffix_dict)

    # check that no error or warning was raised
    assert len(caplog.records) == 0


def test_check_files_exist_missing_file(tmp_path, caplog):
    """
    Test that the check_files_exist function raises warnings when a file or label is missing
    """
    # create some test files
    path_data = tmp_path / "BIDS"
    os.makedirs(path_data / "sub-001" / "ses-01" / "anat", exist_ok=True)
    open(path_data / "sub-001" / "ses-01" / "anat" / "sub-001_ses-01_T1w.nii.gz", "w").close()

    # set up the input data
    dict_files = {
        "FILES_SEG": ["sub-001/ses-01/anat/sub-001_ses-01_T1w.nii.gz"],
        "FILES_GMSEG": ["sub-002/ses-01/anat/sub-001_ses-01_T2star.nii.gz"],
    }
    suffix_dict = {
        'FILES_SEG': '_seg',
        'FILES_GMSEG': '_gmseg',
    }

    # run the function
    check_files_exist(dict_files, path_img=path_data, path_label=path_data, suffix_dict=suffix_dict)

    # Assert that an error or warning message was logged for the missing files
    assert any('The following files are missing' in rec.message for rec in caplog.records)
    assert any('BIDS/sub-002/ses-01/anat/sub-001_ses-01_T2star.nii.gz' in rec.message for rec in caplog.records)
    assert any('Please check that the files listed in the yaml file and the input path are correct' in rec.message for rec in caplog.records)
    assert any('BIDS/sub-001/ses-01/anat/sub-001_ses-01_T1w_seg.nii.gz' in rec.message for rec in caplog.records)
    assert any('BIDS/sub-002/ses-01/anat/sub-001_ses-01_T2star_gmseg.nii.gz' in rec.message for rec in caplog.records)
    assert any("Please check that the used suffix ['_gmseg', '_seg'] is correct" in rec.message for rec in caplog.records)


def test_track_corrections(tmp_path):
    """
    Test that the track_corrections function correctly updates the config file
    """
    # Dictionary with the original config file
    dict_files = {
        "FILES_LABEL": ["sub-amuALT_T1w.nii.gz", "sub-amuAL_T1w.nii.gz"],
    }
    # Path where modified config file will be saved
    path_data = tmp_path / "BIDS"
    os.makedirs(path_data, exist_ok=True)
    config_path = tmp_path / "BIDS" / "config.yml"
    # Path to the last corrected image
    file_path = "sub-amuAL/anat/sub-amuAL_T1w.nii.gz"
    # Specify the task
    task = "FILES_LABEL"

    # Call the function --> the function will modify the config file
    track_corrections(dict_files, config_path, file_path, task)

    # Read the updated YAML file
    dict_files_updated = fetch_yaml_config(config_path)

    # Create a test dictionary
    dict_files_test = {'FILES_LABEL': ['sub-amuALT_T1w.nii.gz'], 'CORR_LABEL': ['sub-amuAL_T1w.nii.gz']}

    # Assert that the config file was updated correctly
    assert dict_files_updated == dict_files_test


def test_fetch_yaml_config(tmp_path, monkeypatch):
    """
    Test that the fetch_yaml_config function correctly loads YAML files and handles errors.
    """
    # Create a temp directory for test files
    yaml_dir = tmp_path / "yaml_tests"
    yaml_dir.mkdir()

    # Test case 1: Valid YAML file
    valid_yaml = yaml_dir / "valid_config.yml"
    with open(valid_yaml, 'w') as f:
        f.write("FILES_LESION:\n  - \"*T2w.nii.gz\"\nFILES_SEG:\n  - sub-001_T1w.nii.gz")

    # Test loading a valid YAML file
    config = fetch_yaml_config(valid_yaml)
    assert config == {"FILES_LESION": ["*T2w.nii.gz"], "FILES_SEG": ["sub-001_T1w.nii.gz"]}

    # Test case 2: Invalid YAML file with unquoted asterisk
    invalid_yaml = yaml_dir / "invalid_config.yml"
    with open(invalid_yaml, 'w') as f:
        f.write("FILES_LESION:\n  - *T2w.nii.gz")

    # Mock sys.exit to prevent test from actually exiting
    def mock_exit(msg):
        raise SystemExit(msg)

    monkeypatch.setattr('sys.exit', mock_exit)

    # Test that the function correctly identifies the asterisk error
    try:
        fetch_yaml_config(invalid_yaml)
        assert False, "Should have raised SystemExit"
    except SystemExit as e:
        error_msg = str(e)
        assert "YAML parsing error" in error_msg
        assert "The '*' character is a special character in YAML" in error_msg
        assert "To use '*' as a wildcard character" in error_msg

    # Test case 3: Non-existent YAML file
    nonexistent_yaml = yaml_dir / "nonexistent.yml"

    # Test that the function correctly handles non-existent files
    try:
        fetch_yaml_config(nonexistent_yaml)
        assert False, "Should have raised SystemExit"
    except SystemExit as e:
        assert "does not exist" in str(e)


def create_dummy_nii_file(tmp_path, filename):
    """
    Create a dummy nifti file for testing purposes
    :param tmp_path: Path to the temporary directory
    :param filename: Name of the nifti file
    :return: Path to the created nifti file
    """
    path_data = tmp_path / "BIDS" / "sub-001" / "ses-01" / "anat"
    os.makedirs(path_data, exist_ok=True)

    # Note: we have to create a 3D array to save it as a nifti file to simulate a real nifti file
    data = np.random.rand(10, 10, 10)
    affine = np.eye(4)
    img = nib.Nifti1Image(data, affine)
    fname_path = path_data / filename
    nib.save(img, fname_path)

    return fname_path


def test_get_orientation(tmp_path):
    """
    Test that the get_orientation function returns the expected orientation
    In this case, we create and check a nifti file with LPI orientation
    """
    # Create a test dummy nifti file using nibabel
    fname_path = create_dummy_nii_file(tmp_path, "sub-001_ses-01_T1w.nii.gz")

    # Get the orientation
    orientation = get_orientation(fname_path)

    # Assert that the orientation is correct
    assert orientation == "LPI"


def test_change_orientation(tmp_path):
    """
    Test that the change_orientation function changes the orientation of the nifti file
    In this case, we reorient the file from LPI to AIL
    """
    # Create a test dummy nifti file using nibabel
    fname_path = create_dummy_nii_file(tmp_path, "sub-001_ses-01_T1w.nii.gz")

    # Change orientation to AIL
    change_orientation(fname_path, "AIL")

    # Get the orientation
    orientation = get_orientation(fname_path)

    # Assert that the orientation is correct
    assert orientation == "AIL"
