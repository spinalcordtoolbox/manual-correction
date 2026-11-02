#######################################################################
#
# Tests for utils.download_if_annexed
#
# RUN BY:
#   python -m pytest -v tests/test_download_if_annexed.py
#######################################################################

import gzip
import os
import subprocess
from unittest.mock import patch

from utils import download_if_annexed, is_gzip_file


def test_gzip_file_is_not_downloaded(tmp_path):
    fname = tmp_path / 'sub-001_T2w.nii.gz'
    with gzip.open(fname, 'wb') as f:
        f.write(b'data')

    assert is_gzip_file(str(fname))
    with patch('utils.subprocess.run') as mock_run:
        download_if_annexed(str(fname))
    mock_run.assert_not_called()


def test_pointer_file_is_downloaded_from_its_own_folder(tmp_path):
    fname = tmp_path / 'sub-001_T2w.nii.gz'
    fname.write_text('/annex/objects/SHA256E-s1--abc.nii.gz\n')

    assert not is_gzip_file(str(fname))
    with patch('utils.subprocess.run') as mock_run:
        download_if_annexed(str(fname))
    mock_run.assert_called_once_with(['git', 'annex', 'get', fname.name], check=True, cwd=str(tmp_path))


def test_broken_symlink_is_downloaded(tmp_path):
    fname = tmp_path / 'sub-001_T2w.nii.gz'
    os.symlink(tmp_path / '.git' / 'annex' / 'objects' / 'missing', fname)

    assert not is_gzip_file(str(fname))
    with patch('utils.subprocess.run') as mock_run:
        download_if_annexed(str(fname))
    mock_run.assert_called_once()


def test_missing_file_is_not_downloaded(tmp_path):
    with patch('utils.subprocess.run') as mock_run:
        download_if_annexed(str(tmp_path / 'missing.nii.gz'))
    mock_run.assert_not_called()


def test_failed_download_does_not_raise(tmp_path):
    fname = tmp_path / 'sub-001_T2w.nii.gz'
    fname.write_text('pointer')

    with patch('utils.subprocess.run', side_effect=subprocess.CalledProcessError(1, 'git')):
        download_if_annexed(str(fname))
