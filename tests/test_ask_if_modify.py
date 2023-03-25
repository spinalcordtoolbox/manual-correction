#######################################################################
#
# Tests for ask_if_modify() function
#
# RUN BY:
#   python -m pytest -v tests/test_ask_if_modify.py
#######################################################################

import os
import pytest
from unittest.mock import patch
from manual_correction import ask_if_modify


@pytest.fixture
def cleanup_files():
    # This fixture will automatically clean up any files created during tests
    yield
    os.system('rm -f *.nii.gz')


def test_ask_if_modify_fname_label_exists_y(tmp_path, cleanup_files):
    """
    Test that the function ask_if_modify() returns the correct values when the label file exists and the user answers "y"
    """
    # create some test files
    path_data = os.path.join(tmp_path, "BIDS")
    path_sub = os.path.join(path_data, "sub-001", "ses-01", "anat")
    os.makedirs(path_sub, exist_ok=True)
    fname_label = os.path.join(path_sub, "sub-001_ses-01_T1w_seg-manual.nii.gz")
    fname_seg = os.path.join(path_sub, "sub-001_ses-01_T1w_seg.nii.gz")
    open(fname_label, "w").close()

    # Patch input() function to simulate user input
    with patch('builtins.input', return_value='y'):
        do_labeling, copy, create_empty_mask = ask_if_modify(fname_label, fname_seg)

    # Check that the function returned the correct values
    assert do_labeling
    assert not copy
    assert not create_empty_mask


def test_ask_if_modify_fname_label_exists_n(tmp_path, cleanup_files):
    """
    Test that the function ask_if_modify() returns the correct values when the label file exists and the user answers "n"
    """
    # create some test files
    path_data = os.path.join(tmp_path, "BIDS")
    path_sub = os.path.join(path_data, "sub-001", "ses-01", "anat")
    os.makedirs(path_sub, exist_ok=True)
    fname_label = os.path.join(path_sub, "sub-001_ses-01_T1w_seg-manual.nii.gz")
    fname_seg = os.path.join(path_sub, "sub-001_ses-01_T1w_seg.nii.gz")
    open(fname_label, "w").close()

    # Patch input() function to simulate user input
    with patch('builtins.input', return_value='n'):
        do_labeling, copy, create_empty_mask = ask_if_modify(fname_label, fname_seg)

    # Check that the function returned the correct values
    assert not do_labeling
    assert not copy
    assert not create_empty_mask


def test_ask_if_modify_fname_label_not_exist(tmp_path, cleanup_files):
    """
    Test that the function ask_if_modify() returns the correct values when the label file does not exist
    """
    # create some test files
    path_data = os.path.join(tmp_path, "BIDS")
    path_sub = os.path.join(path_data, "sub-001", "ses-01", "anat")
    os.makedirs(path_sub, exist_ok=True)
    fname_label = os.path.join(path_sub, "sub-001_ses-01_T1w_seg-manual.nii.gz")
    fname_seg = os.path.join(path_sub, "sub-001_ses-01_T1w_seg.nii.gz")
    open(fname_seg, "w").close()

    # Call function with non-existing fname_label
    do_labeling, copy, create_empty_mask = ask_if_modify(fname_label, fname_seg)

    # Check that the function returned the correct values
    assert do_labeling
    assert copy
    assert not create_empty_mask


def test_create_empty_mask(tmp_path, cleanup_files):
    """
    Test that the function ask_if_modify() returns the correct values when the file under derivatives and the file
    under processed data do not exist --> create a new empty mask
    :param cleanup_files:
    :return:
    """
    # create some test files
    path_data = os.path.join(tmp_path, "BIDS")
    path_sub = os.path.join(path_data, "sub-001", "ses-01", "anat")
    os.makedirs(path_sub, exist_ok=True)
    fname_label = os.path.join(path_sub, "sub-001_ses-01_T1w_seg-manual.nii.gz")
    fname_seg = os.path.join(path_sub, "sub-001_ses-01_T1w_seg.nii.gz")

    # Call function with non-existing fname_label and fname_seg
    do_labeling, copy, create_empty_mask = ask_if_modify(fname_label, fname_seg)

    # Check that the function returned the correct values
    assert do_labeling
    assert not copy
    assert create_empty_mask
