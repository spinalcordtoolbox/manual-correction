#######################################################################
#
# Tests for utils.py functions
#
# RUN BY:
#   python -m pytest -v tests/test_utils.py
#######################################################################

import os
from utils import fetch_subject_and_session, add_suffix, remove_suffix, splitext, curate_dict_yml, check_files_exist


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

    # Test 4: Test for empty strings when input filename path is invalid
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
    input_dict = {'FILES_LABEL': ['/path/to/sub-001_acq-sag_T2w.nii.gz',
                                  '/path/to/sub-002_acq-sag_T2w.nii.gz',
                                  '/path/to/sub-003_acq-sag_T2w.nii.gz']}
    expected_output_dict = {'FILES_LABEL': ['sub-001_acq-sag_T2w.nii.gz',
                                            'sub-002_acq-sag_T2w.nii.gz',
                                            'sub-003_acq-sag_T2w.nii.gz']}
    assert curate_dict_yml(input_dict) == expected_output_dict


def test_check_files_exist_all_files_exist(tmp_path, caplog):
    # create some test files
    path_data = tmp_path / "BIDS"
    os.makedirs(path_data / "sub-001" / "ses-01" / "anat", exist_ok=True)
    os.makedirs(path_data / "sub-002" / "ses-01" / "anat", exist_ok=True)
    open(path_data / "sub-001" / "ses-01" / "anat" / "sub-001_ses-01_T1w.nii.gz", "w").close()
    open(path_data / "sub-001" / "ses-01" / "anat" / "sub-001_ses-01_T1w_seg.nii.gz", "w").close()
    open(path_data / "sub-002" / "ses-01" / "anat" / "sub-002_ses-01_T2star.nii.gz", "w").close()
    open(path_data / "sub-002" / "ses-01" / "anat" / "sub-002_ses-01_T2star_gmseg.nii.gz", "w").close()

    # set up the input data
    dict_files = {
        "FILES_SEG": ["sub-001/ses-01/anat/sub-001_ses-01_T1w.nii.gz"],
        "FILES_GMSEG": ["sub-002/ses-01/anat/sub-002_ses-01_T2star.nii.gz"],
    }
    suffix_dict = {
        'FILES_SEG': '_seg',
        'FILES_GMSEG': '_gmseg',
    }

    # run the function
    check_files_exist(dict_files, path_data, suffix_dict)

    # check that no error warning was raised
    assert len(caplog.records) == 0


def test_check_files_exist_missing_file(tmp_path, caplog):
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
    check_files_exist(dict_files, path_data, suffix_dict)

    # Assert that an error or warning message was logged for the missing files
    assert any('The following files are missing' in rec.message for rec in caplog.records)
    assert any('BIDS/sub-002/ses-01/anat/sub-001_ses-01_T2star.nii.gz' in rec.message for rec in caplog.records)
    assert any('Please check that the files listed in the yaml file and the input path are correct' in rec.message for rec in caplog.records)
    assert any('BIDS/sub-001/ses-01/anat/sub-001_ses-01_T1w_seg.nii.gz' in rec.message for rec in caplog.records)
    assert any('BIDS/sub-002/ses-01/anat/sub-001_ses-01_T2star_gmseg.nii.gz' in rec.message for rec in caplog.records)
    assert any("Please check that the used suffix '_gmseg' is correct" in rec.message for rec in caplog.records)
