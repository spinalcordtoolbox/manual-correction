#!/usr/bin/env python
#
# Copy manually corrected labels (segmentations, vertebral labeling, etc.) from the preprocessed dataset to the
# git-annex BIDS dataset's derivatives folder
#
# For full help, please run: python copy_files_to_derivatives.py -h
#
# Example:
#       python copy_files_to_derivatives.py
#       -path-in ~/<your_dataset>/derivatives/labels
#       -path-out ~/<output_dataset>/derivatives/labels
#
# Authors: Jan Valosek
#

import argparse
import glob
import os
import shutil
import utils


def get_parser():
    """
    parser function
    """

    parser = argparse.ArgumentParser(
        description='Copy manually corrected labels (segmentations, disc labels, etc.) to the BIDS derivatives folder.',
        formatter_class=utils.SmartFormatter,
        prog=os.path.basename(__file__).strip('.py')
    )
    parser.add_argument(
        '-path-in',
        metavar="<folder>",
        required=True,
        type=str,
        help='Path to the BIDS-compliant folder with manually corrected labels. Example: '
             '~/<your_dataset>/derivatives/labels'
    )
    parser.add_argument(
        '-path-out',
        metavar="<folder>",
        required=True,
        type=str,
        help='Path to the BIDS-compliant folder where manually corrected files will be copied. Example: '
             '~/<output_dataset>/derivatives/labels'
    )

    return parser


def main():

    # Parse the command line arguments
    parser = get_parser()
    args = parser.parse_args()

    # Check if path_in exists
    if os.path.isdir(args.path_in):
        path_in = os.path.abspath(args.path_in)
    else:
        raise NotADirectoryError(f'{args.path_in} does not exist.')

    # Check if path_out exists
    if os.path.isdir(args.path_out):
        path_out = os.path.abspath(args.path_out)
    else:
        raise NotADirectoryError(f'{args.path_out} does not exist.')

    # Loop across files in input dataset
    for path_file_in in sorted(glob.glob(path_in + '/**/*.nii.gz', recursive=True)):
        sub, ses, filename, contrast = utils.fetch_subject_and_session(path_file_in)
        # Construct path for the output file
        path_file_out = os.path.join(path_out, sub, ses, contrast, filename)
        # Check if subject's folder exists in the output dataset, if not, create it
        path_subject_folder_out = os.path.join(path_out, sub, ses, contrast)
        if not os.path.isdir(path_subject_folder_out):
            os.makedirs(path_subject_folder_out)
            print(f'Creating directory: {path_subject_folder_out}')
        # Copy nii and json files to the output dataset
        # TODO - consider rsync instead of shutil.copy
        shutil.copy(path_file_in, path_file_out)
        print(f'Copying: {path_file_in} to {path_file_out}')
        path_file_json_in = path_file_in.replace('nii.gz', 'json')
        path_file_json_out = path_file_out.replace('nii.gz', 'json')
        if os.path.isfile(path_file_json_in):
            shutil.copy(path_file_json_in, path_file_json_out)
            print(f'Copying: {path_file_json_in} to {path_file_json_out}')
        else:
            print(f'Warning: {path_file_json_in} does not exist.')


if __name__ == '__main__':
    main()
