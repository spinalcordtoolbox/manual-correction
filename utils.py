#!/usr/bin/env python
# -*- coding: utf-8
# Collection of useful functions from spine_generic, used for manual segmentation

import os
import re
import logging
import textwrap
import argparse
import subprocess
import shutil
from pathlib import Path
from enum import Enum

# BIDS utility tool
def get_subject(file):
    """
    Get subject from BIDS file name
    :param file:
    :return: subject
    """
    return file.split('_')[0]


def get_contrast(file):
    """
    Get contrast from BIDS file name
    :param file:
    :return:
    """
    return 'dwi' if (file.split('_')[-1]).split('.')[0] == 'dwi' else 'anat'


class SmartFormatter(argparse.HelpFormatter):
    """
    Custom formatter that inherits from HelpFormatter, which adjusts the default width to the current Terminal size,
    and that gives the possibility to bypass argparse's default formatting by adding "R|" at the beginning of the text.
    Inspired from: https://pythonhosted.org/skaff/_modules/skaff/cli.html
    """
    def __init__(self, *args, **kw):
        self._add_defaults = None
        super(SmartFormatter, self).__init__(*args, **kw)
        # Update _width to match Terminal width
        try:
            self._width = shutil.get_terminal_size()[0]
        except (KeyError, ValueError):
            logging.warning('Not able to fetch Terminal width. Using default: %s'.format(self._width))

    # this is the RawTextHelpFormatter._fill_text
    def _fill_text(self, text, width, indent):
        # print("splot",text)
        if text.startswith('R|'):
            paragraphs = text[2:].splitlines()
            rebroken = [textwrap.wrap(tpar, width) for tpar in paragraphs]
            rebrokenstr = []
            for tlinearr in rebroken:
                if (len(tlinearr) == 0):
                    rebrokenstr.append("")
                else:
                    for tlinepiece in tlinearr:
                        rebrokenstr.append(tlinepiece)
            return '\n'.join(rebrokenstr)  # (argparse._textwrap.wrap(text[2:], width))
        return argparse.RawDescriptionHelpFormatter._fill_text(self, text, width, indent)
    def _split_lines(self, text, width):
        if text.startswith('R|'):
            lines = text[2:].splitlines()
            while lines[0] == '':  # Discard empty start lines
                lines = lines[1:]
            offsets = [re.match("^[ \t]*", l).group(0) for l in lines]
            wrapped = []
            for i in range(len(lines)):
                li = lines[i]
                if len(li) > 0:
                    o = offsets[i]
                    ol = len(o)
                    init_wrap = textwrap.fill(li, width).splitlines()
                    first = init_wrap[0]
                    rest = "\n".join(init_wrap[1:])
                    rest_wrap = textwrap.fill(rest, width - ol).splitlines()
                    offset_lines = [o + wl for wl in rest_wrap]
                    wrapped = wrapped + [first] + offset_lines
                else:
                    wrapped = wrapped + [li]
            return wrapped
        return argparse.HelpFormatter._split_lines(self, text, width)


def splitext(fname):
        """
        Split a fname (folder/file + ext) into a folder/file and extension.

        Note: for .nii.gz the extension is understandably .nii.gz, not .gz
        (``os.path.splitext()`` would want to do the latter, hence the special case).
        """
        dir, filename = os.path.split(fname)
        for special_ext in ['.nii.gz', '.tar.gz']:
            if filename.endswith(special_ext):
                stem, ext = filename[:-len(special_ext)], special_ext
                return os.path.join(dir, stem), ext
        # If no special case, behaves like the regular splitext
        stem, ext = os.path.splitext(filename)
        return os.path.join(dir, stem), ext


def add_suffix(fname, suffix):
    """
    Add suffix between end of file name and extension.

    :param fname: absolute or relative file name. Example: t2.nii
    :param suffix: suffix. Example: _mean
    :return: file name with suffix. Example: t2_mean.nii

    Examples:

    - add_suffix(t2.nii, _mean) -> t2_mean.nii
    - add_suffix(t2.nii.gz, a) -> t2a.nii.gz
    """
    stem, ext = splitext(fname)
    return os.path.join(stem + suffix + ext)


def remove_suffix(fname, suffix):
    """
    Remove suffix between end of file name and extension.

    :param fname: absolute or relative file name with suffix. Example: t2_mean.nii
    :param suffix: suffix. Example: _mean
    :return: file name without suffix. Example: t2.nii

    Examples:

    - remove_suffix(t2_mean.nii, _mean) -> t2.nii
    - remove_suffix(t2a.nii.gz, a) -> t2.nii.gz
    """
    stem, ext = splitext(fname)
    return os.path.join(stem.replace(suffix, '') + ext)


def curate_dict_yml(dict_yml):
    """
    Curate dict_yml to only have filenames instead of absolute path
    :param dict_yml: dict: input yml file as dict
    :return: dict_yml_curate
    """
    dict_yml_curate = {}
    for task, files in dict_yml.items():
        dict_yml_curate[task] = [os.path.basename(file) for file in files]
    return dict_yml_curate


def check_files_exist(dict_files, path_data):
    """
    Check if all files listed in the input dictionary exist
    :param dict_files:
    :param path_data: folder where BIDS dataset is located
    :return:
    """
    missing_files = []
    for task, files in dict_files.items():
        if files is not None:
            for file in files:
                fname = os.path.join(path_data, get_subject(file), get_contrast(file), file)
                if not os.path.exists(fname):
                    missing_files.append(fname)
    if missing_files:
        logging.error("The following files are missing: \n{}. \nPlease check that the files listed "
                        "in the yaml file and the input path are correct.".format(missing_files))


def check_output_folder(path_bids, folder_derivatives):
    """
    Make sure path exists, has writing permissions, and create derivatives folder if it does not exist.
    :param path_bids:
    :return: path_bids_derivatives
    """
    if path_bids is None:
        logging.error("-path-out should be provided.")
    if not os.path.exists(path_bids):
        logging.error("Output path does not exist: {}".format(path_bids))
    path_bids_derivatives = os.path.join(path_bids, folder_derivatives)
    os.makedirs(path_bids_derivatives, exist_ok=True)
    return path_bids_derivatives


def check_software_installed(list_software=['sct']):
    """
    Make sure software are installed
    :param list_software: {'sct'}
    :return:
    """
    install_ok = True
    software_cmd = {
        'sct': 'sct_version'
        }
    logging.info("Checking if required software are installed...")
    for software in list_software:
        try:
            output = subprocess.check_output(software_cmd[software], shell=True)
            logging.info("'{}' (version: {}) is installed.".format(software, output.decode('utf-8').strip('\n')))
        except:
            logging.error("'{}' is not installed. Please install it before using this program.".format(software))
            install_ok = False
    return install_ok
