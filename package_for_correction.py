#!/usr/bin/env python
#
# Script to package data for manual correction.
#
# For full help, please run: python package_for_correction.py -h`
#
# Example:
#       python package_for_correction.py
#       -path-in ~/<your_dataset>/data_processed
#       -config config.yml
#
# Authors: Jan Valosek, Sandrine Bédard, Julien Cohen-Adad
#

import os
import glob
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
        "R|Config YAML file listing images that require manual corrections for segmentation and vertebral "
        "labeling. "
        "'FILES_SEG' lists images associated with spinal cord segmentation "
        "'FILES_GMSEG' lists images associated with gray matter segmentation, "
        "'FILES_LESION' lists images associated with multiple sclerosis lesion segmentation, "
        "'FILES_LABEL' lists images associated with vertebral labeling, "
        "'FILES_COMPRESSION' lists images associated with compression labeling, "
        "'FILES_PMJ' lists images associated with pontomedullary junction labeling, "
        "and 'FILES_CENTERLINE' lists images associated with centerline. "
        "You can validate your YAML file at this website: http://www.yamllint.com/."
        "Note: if you want to iterate over all subjects, you can use the wildcard '*' (e.g. sub-*_T1w.nii.gz)"
        "Below is an example YAML file:\n"
        + dedent(
            """
            FILES_SEG:
            - sub-001_ses-01_T1w.nii.gz         # example how to specify a specific session
            - sub-002_T2w.nii.gz
            FILES_GMSEG:
            - sub-001_T1w.nii.gz
            - sub-002_T2w.nii.gz
            FILES_LESION:
            - sub-001_T1w.nii.gz
            - sub-002_T2w.nii.gz
            FILES_LABEL:
            - sub-001_T1w.nii.gz
            - sub-002_T1w.nii.gz
            FILES_COMPRESSION:
            - sub-001_T1w.nii.gz
            - sub-002_T1w.nii.gz
            FILES_PMJ:
            - sub-001_T1w.nii.gz
            - sub-002_T1w.nii.gz
            FILES_CENTERLINE:
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
        metavar="<file>",
        help="Zip file that contains the packaged data, without the extension. Default: data_to_correct",
        default='data_to_correct'
    )
    parser.add_argument(
        '-suffix-files-seg',
        help="FILES-SEG suffix. Examples: '_seg' (default), '_label-SC_mask'.",
        default='_seg'
    )
    parser.add_argument(
        '-suffix-files-gmseg',
        help="FILES-GMSEG suffix. Examples: '_gmseg' (default), '_label-GM_mask'.",
        default='_gmseg'
    )
    parser.add_argument(
        '-suffix-files-lesion',
        help="FILES-LESION suffix. Examples: '_lesion' (default).",
        default='_lesion'
    )
    parser.add_argument(
        '-suffix-files-label',
        help="FILES-LABEL suffix. Examples: '_labels' (default), '_label-disc'.",
        default='_label-disc'
    )
    parser.add_argument(
        '-suffix-files-compression',
        help="FILES-COMPRESSION suffix. Examples: '_compression' (default), '_label-compression'.",
        default='_label-compression'
    )
    parser.add_argument(
        '-suffix-files-pmj',
        help="FILES-PMJ suffix. Examples: '_pmj' (default), '_label-pmj'.",
        default='_pmj'
    )
    parser.add_argument(
        '-suffix-files-centerline',
        help="FILES-CENTERLINE suffix. Examples: '_centerline' (default), '_label-centerline'.",
        default='_centerline'
    )
    parser.add_argument(
        '-other-contrast',
        help="Include additional images (contrasts). This flag is useful if you want to use an additional contrast "
             "than provided by the YAML file for manual corrections. Only valid for '-viewer fsleyes'. Example: 'PSIR',"
             " 'STIR', 'acq-sag_T1w' etc.",
        type=str,
        default=None
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
    print(f'Copying: {fname_in} to {fname_out}')


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

    suffix_dict = {
        'FILES_SEG': args.suffix_files_seg,                 # e.g., _seg or _label-SC_mask
        'FILES_GMSEG': args.suffix_files_gmseg,             # e.g., _gmseg or _label-GM_mask
        'FILES_LESION': args.suffix_files_lesion,           # e.g., _lesion
        'FILES_LABEL': args.suffix_files_label,             # e.g., _labels or _labels-disc
        'FILES_COMPRESSION': args.suffix_files_compression,  # e.g., _label-compression
        'FILES_PMJ': args.suffix_files_pmj,                 # e.g., _pmj or _label-pmj
        'FILES_CENTERLINE': args.suffix_files_centerline    # e.g., _centerline or _label-centerline
    }

    # Check for missing files before starting the whole process
    # Note: we pass args.path_in for both path_img and path_label because both both images and their labels (e.g.,
    # SC seg) are located in the same folder, e.g., ~/<your_dataset>/data_processed
    utils.check_files_exist(dict_yml=dict_yml, path_img=utils.get_full_path(args.path_in),
                            path_label=utils.get_full_path(args.path_in), suffix_dict=suffix_dict)

    # Create temp folder
    path_tmp = tempfile.mkdtemp()

    # Loop across files and copy them in the appropriate directory
    # Note: in case the file is listed twice, we just overwrite it in the destination dir.
    for task, files in dict_yml.items():
        # Handle regex (i.e., iterate over all subjects)
        if '*' in files[0] and len(files) == 1:
            subject, ses, filename, contrast = utils.fetch_subject_and_session(files[0])
            # Get list of files recursively
            files = sorted(glob.glob(os.path.join(utils.get_full_path(args.path_in), '**', filename), recursive=True))
            # Skip filenames containing "notused"
            files = [file for file in files if 'notused' not in file]
        for file in files:
            if task in suffix_dict.keys():
                suffix_label = suffix_dict[task]
            else:
                sys.exit('Task not recognized from the YAML file: {}'.format(task))
            subject, ses, filename, contrast = utils.fetch_subject_and_session(file)
            # Construct absolute path to the input file
            # For example: '/Users/user/dataset/data_processed/sub-001/anat/sub-001_T2w.nii.gz'
            fname = os.path.join(utils.get_full_path(args.path_in), subject, ses, contrast, filename)
            # Construct absolute path to the other contrast file/contrast
            if args.other_contrast:
                fname_other_contrast = os.path.join(utils.get_full_path(args.path_in), subject, ses, contrast,
                                                    subject + '_' + ses + '_' + args.other_contrast + '.nii.gz')
            else:
                fname_other_contrast = None
            # Construct absolute path to the temp folder
            path_out = os.path.join(path_tmp, subject, ses, contrast)
            # Copy image
            if os.path.exists(fname):
                copy_file(fname, path_out)
            if args.other_contrast:
                if os.path.exists(fname_other_contrast):
                    copy_file(fname_other_contrast, path_out)
            # Copy label if exists
            if suffix_label is not None:
                # Construct absolute path to the input label (segmentation, labeling etc.) file
                # For example: '/Users/user/dataset/data_processed/sub-001/anat/sub-001_T2w_seg.nii.gz'
                fname_seg = utils.add_suffix(fname, suffix_dict[task])
                if os.path.exists(fname_seg):
                    copy_file(fname_seg, path_out)

    # Package to zip file
    print("Creating archive...")
    root_dir_tmp = os.path.split(path_tmp)[0]
    base_dir_name = os.path.split(args.o)[1]
    new_path_tmp = os.path.join(root_dir_tmp, base_dir_name)
    if os.path.isdir(new_path_tmp):
        shutil.rmtree(new_path_tmp)
    shutil.move(path_tmp, new_path_tmp)
    fname_archive = shutil.make_archive(utils.get_full_path(args.o), 'zip', root_dir_tmp, base_dir_name)
    print("-> {}".format(fname_archive))


if __name__ == '__main__':
    main()
