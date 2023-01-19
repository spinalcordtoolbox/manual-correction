#!/usr/bin/env python
#
# Script to package data for manual correction from SpineGeneric adapted for canproco project.
#
# For usage, type: python package_for_correction.py -h
#
# Authors: Jan Valosek, Sandrine Bédard, Julien Cohen-Adad
#


import os
import sys
import shutil
import tempfile
from textwrap import dedent
import argparse
import coloredlogs
import utils


def get_parser():
    """
    parser function
    """
    parser = argparse.ArgumentParser(
        description='Package data for manual correction. In case processing is ran on a remote cluster, it is '
                    'convenient to generate a package of the files that need correction to be able to only copy these '
                    'files locally, instead of copying the ~20GB of total processed files.',
        formatter_class=utils.SmartFormatter,
        prog=os.path.basename(__file__).rstrip('.py')
    )
    parser.add_argument(
        '-config',
        metavar="<file>",
        required=True,
        help=
        "R|Config yaml file listing images that require manual corrections for segmentation and vertebral "
        "labeling. 'FILES_SEG' lists images associated with spinal cord segmentation "
        ",'FILES_GMSEG' lists images associated with gray matter segmentation "
        ",'FILES_LABEL' lists images associated with vertebral labeling "
        "and 'FILES_PMJ' lists images associated with pontomedullary junction labeling"
        "You can validate your .yml file at this website: http://www.yamllint.com/."
        "Below is an example .yml file:\n"
        + dedent(
            """
            FILES_SEG:
            - sub-001_T1w.nii.gz
            - sub-002_T2w.nii.gz
            FILES_GMSEG:
            - sub-001_T1w.nii.gz
            - sub-002_T2w.nii.gz
            FILES_LABEL:
            - sub-001_T1w.nii.gz
            - sub-002_T1w.nii.gz
            FILES_PMJ:
            - sub-001_T1w.nii.gz
            - sub-002_T1w.nii.gz\n
            """)
    )
    parser.add_argument(
        '-path-in',
        metavar="<folder>",
        required=True,
        help='Path to the processed data. Example: ~/<your_dataset>/data_processed',
    )
    parser.add_argument(
        '-o',
        metavar="<folder>",
        help="Zip file that contains the packaged data, without the extension. Default: data_to_correct",
        default='data_to_correct'
    )
    parser.add_argument(
        '-v', '--verbose',
        help="Full verbose (for debugging)",
        action='store_true'
    )

    return parser


def copy_file(fname_in, path_out):
    # create output path
    os.makedirs(path_out, exist_ok=True)
    # copy file
    fname_out = shutil.copy(fname_in, path_out)
    print("-> {}".format(fname_out))


def main():
    # Parse the command line arguments
    parser = get_parser()
    args = parser.parse_args()

    # Logging level
    if args.verbose:
        coloredlogs.install(fmt='%(message)s', level='DEBUG')
    else:
        coloredlogs.install(fmt='%(message)s', level='INFO')

    # Fetch configuration from YAML file
    dict_yml = utils.fetch_yaml_config(args.config)

    # Curate dict_yml to only have filenames instead of absolute path
    dict_yml = utils.curate_dict_yml(dict_yml)

    # Check for missing files before starting the whole process
    utils.check_files_exist(dict_yml, args.path_in)

    # Create temp folder
    path_tmp = tempfile.mkdtemp()

    # Loop across files and copy them in the appropriate directory
    # Note: in case the file is listed twice, we just overwrite it in the destination dir.
    for task, files in dict_yml.items():
        for file in files:
            if task == 'FILES_SEG':
                suffix_label = '_seg'
            elif task == 'FILES_LABEL':
                suffix_label = None
            elif task == 'FILES_PMJ':
                suffix_label = None
            else:
                sys.exit('Task not recognized from yml file: {}'.format(task))
            # Copy image
            copy_file(os.path.join(args.path_in, utils.get_subject(file), utils.get_contrast(file), file),
                      os.path.join(path_tmp, utils.get_subject(file), utils.get_contrast(file)))
            # Copy label if exists
            if suffix_label is not None:
                copy_file(os.path.join(args.path_in, utils.get_subject(file), utils.get_contrast(file),
                                       utils.add_suffix(file, suffix_label)),
                          os.path.join(path_tmp, utils.get_subject(file), utils.get_contrast(file)))

    # Package to zip file
    print("Creating archive...")
    root_dir_tmp = os.path.split(path_tmp)[0]
    base_dir_name = os.path.split(args.o)[1]
    new_path_tmp = os.path.join(root_dir_tmp, base_dir_name)
    if os.path.isdir(new_path_tmp):
        shutil.rmtree(new_path_tmp)
    shutil.move(path_tmp, new_path_tmp)
    fname_archive = shutil.make_archive(args.o, 'zip', root_dir_tmp, base_dir_name)
    print("-> {}".format(fname_archive))


if __name__ == '__main__':
    main()
