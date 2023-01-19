#!/usr/bin/env python
#
# Script to perform manual correction of segmentations and vertebral labeling.
#
# For usage, type: python manual_correction.py -h
#
# Authors: Jan Valosek, Julien Cohen-Adad
# Adapted by Sandrine Bédard for cord CSA project UK Biobank

import argparse
import coloredlogs
import glob
import json
import os
import sys
import shutil
from textwrap import dedent
import time
import yaml
import pipeline_ukbiobank.utils as utils

# Folder where to output manual labels, at the root of a BIDS dataset.
# TODO: make it an input argument (with default value)
FOLDER_DERIVATIVES = os.path.join('derivatives', 'labels')


def get_parser():
    """
    parser function
    """
    parser = argparse.ArgumentParser(
        description='Manual correction of spinal cord segmentation, vertebral and pontomedullary junction labeling. '
                    'Manually corrected files are saved under derivatives/ folder (BIDS standard).',
        formatter_class=utils.SmartFormatter,
        prog=os.path.basename(__file__).strip('.py')
    )
    parser.add_argument(
        '-config',
        metavar="<file>",
        required=True,
        help=
        "R|Config yaml file listing images that require manual corrections for segmentation and vertebral "
        "labeling. 'FILES_SEG' lists images associated with spinal cord segmentation "
        ",'FILES_LABEL' lists images associated with vertebral labeling "
        "and 'FILES_PMJ' lists images associated with pontomedullary junction labeling"
        "You can validate your .yml file at this website: http://www.yamllint.com/."
        " If you want to correct segmentation only, ommit 'FILES_LABEL' in the list. Below is an example .yml file:\n"
        + dedent(
            """
            FILES_SEG:
            - sub-1000032_T1w.nii.gz
            - sub-1000083_T2w.nii.gz
            FILES_LABEL:
            - sub-1000032_T1w.nii.gz
            - sub-1000710_T1w.nii.gz
            FILES_PMJ:
            - sub-1000032_T1w.nii.gz
            - sub-1000710_T1w.nii.gz\n
            """)
    )
    parser.add_argument(
        '-path-in',
        metavar="<folder>",
        help='Path to the processed data. Example: ~/ukbiobank_results/data_processed',
        default='./'
    )
    parser.add_argument(
        '-path-out',
        metavar="<folder>",
        help="Path to the BIDS dataset where the corrected labels will be generated. Note: if the derivatives/ folder "
             "does not already exist, it will be created."
             "Example: ~/data-ukbiobank",
        default='./'
    )
    parser.add_argument(
        '-qc-only',
        help="Only output QC report based on the manually-corrected files already present in the derivatives folder. "
             "Skip the copy of the source files, and the opening of the manual correction pop-up windows.",
        action='store_true'
    )
    parser.add_argument(
        '-add-seg-only',
        help="Only copy the source files (segmentation) that aren't in -config list to the derivatives/ folder. "
             "Use this flag to add manually QC-ed automatic segmentations to the derivatives folder.",
        action='store_true'
    )
    parser.add_argument(
        '-v', '--verbose',
        help="Full verbose (for debugging)",
        action='store_true'
    )

    return parser


def get_function(task):
    if task == 'FILES_SEG':
        return 'sct_deepseg_sc'
    elif task == 'FILES_LABEL':
        return 'sct_label_utils'
    elif task == 'FILES_PMJ':
        return 'sct_detect_pmj'
    else:
        raise ValueError("This task is not recognized: {}".format(task))


def get_suffix(task, suffix=''):
    if task == 'FILES_SEG':
        return '_seg'+suffix
    elif task == 'FILES_LABEL':
        return '_labels'+suffix
    elif task == 'FILES_PMJ':
        return '_pmj'+suffix

    else:
        raise ValueError("This task is not recognized: {}".format(task))


def correct_segmentation(fname, fname_seg_out):
    """
    Copy fname_seg in fname_seg_out, then open ITK-SNAP with fname and fname_seg_out.
    :param fname:
    :param fname_seg:
    :param fname_seg_out:
    :param name_rater:
    :return:
    """
    # launch ITK-SNAP
    # Note: command line differs for macOs/Linux and Windows
    print("In ITK-SNAP, correct the segmentation, then save it with the same name (overwrite).")
    if shutil.which('itksnap') is not None:  # Check if command 'itksnap' exists
        os.system('itksnap -g ' + fname + ' -s ' + fname_seg_out)  # for macOS and Linux
    elif shutil.which('ITK-SNAP') is not None:  # Check if command 'ITK-SNAP' exists
        os.system('ITK-SNAP -g ' + fname + ' -s ' + fname_seg_out)  # For windows
    else:
        sys.exit("ITK-SNAP not found. Please install it before using this program or check if it was added to PATH variable. Exit program.")


def correct_vertebral_labeling(fname, fname_label):
    """
    Open sct_label_utils to manually label vertebral levels.
    :param fname:
    :param fname_label:
    :param name_rater:
    :return:
    """
    message = "Click at the posterior tip of the disc between C1-C2, C2-C3 and C3-C4 vertebral levels, then click 'Save and Quit'."
    os.system('sct_label_utils -i {} -create-viewer 2,3,4 -o {} -msg "{}"'.format(fname, fname_label, message))


def correct_pmj_label(fname, fname_label):
    """
    Open sct_label_utils to manually label PMJ.
    :param fname:
    :param fname_label:
    :param name_rater:
    :return:
    """
    message = "Click at the posterior tip of the pontomedullary junction (PMJ) then click 'Save and Quit'."
    os.system('sct_label_utils -i {} -create-viewer 50 -o {} -msg "{}"'.format(fname, fname_label, message))


def create_json(fname_nifti, name_rater):
    """
    Create json sidecar with meta information
    :param fname_nifti: str: File name of the nifti image to associate with the json sidecar
    :param name_rater: str: Name of the expert rater
    :return:
    """
    metadata = {'Author': name_rater, 'Date': time.strftime('%Y-%m-%d %H:%M:%S')}
    fname_json = fname_nifti.rstrip('.nii').rstrip('.nii.gz') + '.json'
    with open(fname_json, 'w') as outfile:
        json.dump(metadata, outfile, indent=4)


def main():

    # Parse the command line arguments
    parser = get_parser()
    args = parser.parse_args()

    # Logging level
    if args.verbose:
        coloredlogs.install(fmt='%(message)s', level='DEBUG')
    else:
        coloredlogs.install(fmt='%(message)s', level='INFO')

    # check if input yml file exists
    if os.path.isfile(args.config):
        fname_yml = args.config
    else:
        sys.exit("ERROR: Input yml file {} does not exist or path is wrong.".format(args.config))

    # fetch input yml file as dict
    with open(fname_yml, 'r') as stream:
        try:
            dict_yml = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    # Curate dict_yml to only have filenames instead of absolute path
    dict_yml = utils.curate_dict_yml(dict_yml)

    # check for missing files before starting the whole process
    utils.check_files_exist(dict_yml, args.path_in)

    # check that output folder exists and has write permission
    path_out_deriv = utils.check_output_folder(args.path_out, FOLDER_DERIVATIVES)

    # Get name of expert rater (skip if -qc-only is true)
    if not args.qc_only:
        name_rater = input("Enter your name (Firstname Lastname). It will be used to generate a json sidecar with each "
                           "corrected file: ")

    # Build QC report folder name
    fname_qc = 'qc_corr_' + time.strftime('%Y%m%d%H%M%S')

    # Get list of segmentations files for all subjects in -path-in (if -add-seg-only)
    if args.add_seg_only:
        path_list = glob.glob(args.path_in + "/**/*_seg.nii.gz", recursive=True)  # TODO: add other extension
        # Get only filenames without suffix _seg  to match files in -config .yml list
        file_list = [utils.remove_suffix(os.path.split(path)[-1], '_seg') for path in path_list]

    # TODO: address "none" issue if no file present under a key
    # Perform manual corrections
    for task, files in dict_yml.items():
        # Get the list of segmentation files to add to derivatives, excluding the manually corrrected files in -config.
        if args.add_seg_only and task == 'FILES_SEG':
            # Remove the files in the -config list
            for file in files:
                if file in file_list:
                    file_list.remove(file)
            files = file_list  # Rename to use those files instead of the ones to exclude
        if files is not None:
            for file in files:
                # build file names
                subject = file.split('_')[0]
                contrast = utils.get_contrast(file)
                fname = os.path.join(args.path_in, subject, contrast, file)
                fname_label = os.path.join(
                    path_out_deriv, subject, contrast, utils.add_suffix(file, get_suffix(task, '-manual')))
                os.makedirs(os.path.join(path_out_deriv, subject, contrast), exist_ok=True)
                if not args.qc_only:
                    if os.path.isfile(fname_label):
                        # if corrected file already exists, asks user if they want to overwrite it
                        answer = None
                        while answer not in ("y", "n"):
                            answer = input("WARNING! The file {} already exists. "
                                           "Would you like to modify it? [y/n] ".format(fname_label))
                            if answer == "y":
                                do_labeling = True
                                overwrite = False
                            elif answer == "n":
                                do_labeling = False
                            else:
                                print("Please answer with 'y' or 'n'")
                    else:
                        do_labeling = True
                        overwrite = True
                    # Perform labeling for the specific task
                    if do_labeling:
                        if task in ['FILES_SEG']:
                            fname_seg = utils.add_suffix(fname, get_suffix(task))
                            if overwrite:
                                shutil.copyfile(fname_seg, fname_label)
                            if not args.add_seg_only:
                                correct_segmentation(fname, fname_label)
                        elif task == 'FILES_LABEL':
                            if not utils.check_software_installed():
                                sys.exit("Some required software are not installed. Exit program.")
                            correct_vertebral_labeling(fname, fname_label)
                        elif task == 'FILES_PMJ':
                            if not utils.check_software_installed():
                                sys.exit("Some required software are not installed. Exit program.")
                            correct_pmj_label(fname, fname_label)
                        else:
                            sys.exit('Task not recognized from yml file: {}'.format(task))
                        # create json sidecar with the name of the expert rater
                        create_json(fname_label, name_rater)

                # generate QC report (only for vertebral labeling or for qc only)
                if args.qc_only or task != 'FILES_SEG':
                    os.system('sct_qc -i {} -s {} -p {} -qc {} -qc-subject {}'.format(
                        fname, fname_label, get_function(task), fname_qc, subject))
                    # Archive QC folder
                    shutil.copy(fname_yml, fname_qc)
                    shutil.make_archive(fname_qc, 'zip', fname_qc)
                    print("Archive created:\n--> {}".format(fname_qc+'.zip'))


if __name__ == '__main__':
    main()
