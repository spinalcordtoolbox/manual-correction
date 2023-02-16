#!/usr/bin/env python
#
# Script to perform manual correction of spinal cord segmentation, gray matter segmentation, vertebral labeling, and
# pontomedullary junction labeling.
#
# For usage, type: python manual_correction.py -h
#
# For examples, see: https://github.com/spinalcordtoolbox/manual-correction/wiki
#
# Authors: Jan Valosek, Sandrine Bédard, Naga Karthik, Julien Cohen-Adad
#

import argparse
import coloredlogs
import glob
import json
import os
import sys
import shutil
from textwrap import dedent
import time
import utils


def get_parser():
    """
    parser function
    """
    parser = argparse.ArgumentParser(
        description='Manual correction of spinal cord segmentation, gray matter segmentation, multiple sclerosis '
                    'lesion segmentation, vertebral labeling, and pontomedullary junction labeling. '
                    'Manually corrected files are saved under derivatives/ folder (according to BIDS standard).',
        formatter_class=utils.SmartFormatter,
        prog=os.path.basename(__file__).strip('.py')
    )
    parser.add_argument(
        '-config',
        metavar="<file>",
        required=True,
        help=
        "R|Config yaml file listing images that require manual corrections for segmentation and vertebral "
        "labeling. "
        "'FILES_SEG' lists images associated with spinal cord segmentation, "
        "'FILES_GMSEG' lists images associated with gray matter segmentation, "
        "'FILES_LESION' lists images associated with multiple sclerosis lesion segmentation, "
        "'FILES_LABEL' lists images associated with vertebral labeling, "
        "and 'FILES_PMJ' lists images associated with pontomedullary junction labeling. "
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
            FILES_LESION:
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
        '-path-out',
        metavar="<folder>",
        help=
        "R|Path to the output folder where the corrected labels will be saved. Example: ~/<your_dataset>/"
        "Note: The path provided within this flag will be combined with the path provided within the "
        "'-path-derivatives' flag. ",
        default='./'
    )
    parser.add_argument(
        '-path-derivatives',
        metavar="<folder>",
        help=
        "R|Path to the 'derivatives' BIDS-complaint folder where the corrected labels will be saved. "
        "Default: derivatives/labels"
        "Note: if the provided folder (e.g., 'derivatives/labels') does not already exist, it will be created."
        "Note: if segmentation or labels files already exist and you would like to correct them, provide path to them "
        "within this flag.",
        default=os.path.join('derivatives', 'labels')
    )
    parser.add_argument(
        '-suffix-files-in',
        help=
        "R|Suffix of the input files. For example: '_RPI_r'."
        "Note: this flag is useful in cases when the input files have been processed and thus contains a specific "
        "suffix.",
        default=''
    )
    parser.add_argument(
        '-suffix-files-seg',
        help="FILES-SEG suffix. Available options: '_seg' (default), '_label-SC_mask'.",
        choices=['_seg', '_label-SC_mask'],
        default='_seg'
    )
    parser.add_argument(
        '-suffix-files-gmseg',
        help="FILES-GMSEG suffix. Available options: '_gmseg' (default), '_label-GM_mask'.",
        choices=['_gmseg', '_label-GM_mask'],
        default='_gmseg'
    )
    parser.add_argument(
        '-suffix-files-lesion',
        help="FILES-LESION suffix. Available options: '_lesion' (default).",
        choices=['_lesion'],
        default='_lesion'
    )
    parser.add_argument(
        '-suffix-files-label',
        help="FILES-LABEL suffix. Available options: '_labels' (default), '_labels-disc'.",
        choices=['_labels', '_labels-disc'],
        default='_labels'
    )
    parser.add_argument(
        '-suffix-files-pmj',
        help="FILES-PMJ suffix. Available options: '_pmj' (default), '_label-pmj'.",
        choices=['_pmj', '_label-pmj'],
        default='_pmj'
    )
    parser.add_argument(
        '-label-disc-list',
        help="Comma-separated list containing individual values and/or intervals for disc labeling. Example: '1:4,6,8' "
             "or 1:20 (default)",
        default='1:20'
    )
    parser.add_argument(
        '-viewer',
        help="Viewer used for manual correction. Available options: 'itksnap' (default), 'fsleyes', 'slicer'.",
        choices=['fsleyes', 'itksnap', 'slicer'],
        default='itksnap'
    )
    parser.add_argument(
        '-fsl-color',
        help="Color to be used for loading the label file on FSLeyes (default: red). `fsleyes -h` gives all the "
             "available color options. If using a combination of colors, specify them with '-', e.g. 'red-yellow'.",
        type=str,
        default='red'
    )
    parser.add_argument(
        '-denoise',
        help="Denoise the input image using 'sct_maths -denoise p=1,b=2'.",
        action='store_true'
    )
    parser.add_argument(
        '-load-other-contrast',
        help="Load additional image to the viewer. This flag is useful if you want to use an additional contrast than "
             "provided by the .yml file. Only valid for '-viewer fsleyes'. The filenames of the additional contrast "
             "are derived from the filename provided by '-config'. For instance, if you want to open T2w overlaid by "
             "PSIR image, specify T2w filename using '-config' flag and within this flag provides only PSIR. Another "
             "examples: 'PSIR', 'STIR', 'acq-sag_T1w' etc.",
        type=str,
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


# TODO: add also sct_get_centerline
def get_function_for_qc(task):
    """
    Get the function to use for QC based on the task.
    :param task:
    :return:
    """
    if task == 'FILES_SEG':
        return 'sct_deepseg_sc'
    elif task == "FILES_GMSEG":
        return "sct_deepseg_gm"
    elif task == 'FILES_LABEL':
        return 'sct_label_utils'
    elif task == 'FILES_PMJ':
        return 'sct_detect_pmj'
    else:
        raise ValueError("This task is not recognized: {}".format(task))


def correct_segmentation(fname, fname_other_contrast, fname_seg_out, viewer, viewer_color):
    """
    Open viewer (ITK-SNAP, FSLeyes, or 3D Slicer) with fname and fname_seg_out.
    :param fname:
    :param fname_other_contrast: other contrast to load in the viewer (specified by the '-load-other-contrast' flag).
    Only valid for FSLeyes.
    :param fname_seg_out:
    :param viewer:
    :param viewer_color: color to be used for the label. Only valid for on FSLeyes (default: red).
    :return:
    """
    # launch ITK-SNAP
    if viewer == 'itksnap':
        print("In ITK-SNAP, correct the segmentation, then save it with the same name (overwrite).")
        # Note: command line differs for macOs/Linux and Windows
        if shutil.which('itksnap') is not None:  # Check if command 'itksnap' exists
            # macOS and Linux
            os.system('itksnap -g {} -s {}'.format(fname, fname_seg_out))
        elif shutil.which('ITK-SNAP') is not None:  # Check if command 'ITK-SNAP' exists
            # Windows
            os.system('ITK-SNAP -g {} -s {}'.format(fname, fname_seg_out))
        else:
            viewer_not_found(viewer)
    # launch FSLeyes
    elif viewer == 'fsleyes':
        if shutil.which('fsleyes') is not None:  # Check if command 'fsleyes' exists
            print("In FSLeyes, click on 'Edit mode', correct the segmentation, and then save it with the same name "
                  "(overwrite).")
            if fname_other_contrast:
                os.system('fsleyes {} {} {} -cm {}'.format(fname, fname_other_contrast, fname_seg_out, viewer_color))
            else:
                os.system('fsleyes {} {} -cm {}'.format(fname, fname_seg_out, viewer_color))
        else:
            viewer_not_found(viewer)
    # launch 3D Slicer
    elif viewer == 'slicer':
        if shutil.which('slicer') is not None:
            # TODO: Add instructions for 3D Slicer
            pass
        else:
            viewer_not_found(viewer)


def viewer_not_found(viewer):
    """
    Print that viewer is not installed and exit the program.
    :param viewer:
    :return:
    """
    sys.exit("{} not found. Please install it before using this program or check if it was added to PATH variable. "
             "You can also use another viewer by using the flag -viewer.".format(viewer))


def correct_vertebral_labeling(fname, fname_label, label_list, viewer='sct_label_utils'):
    """
    Open sct_label_utils to manually label vertebral levels.
    :param fname:
    :param fname_label:
    :param label_list: Comma-separated list containing individual values and/or intervals. Example: '1:4,6,8' or 1:20
    :return:
    """
    if shutil.which(viewer) is not None:  # Check if command 'sct_label_utils' exists
        message = "Click at the posterior tip of the disc(s). Then click 'Save and Quit'."
        if os.path.exists(fname_label):
            os.system('sct_label_utils -i {} -create-viewer {} -o {} -ilabel {} -msg "{}"'.format(fname, label_list, fname_label, fname_label, message))
        else:
            os.system('sct_label_utils -i {} -create-viewer {} -o {} -msg "{}"'.format(fname, label_list, fname_label, message))
    else:
        viewer_not_found(viewer)


def correct_pmj_label(fname, fname_label, viewer='sct_label_utils'):
    """
    Open sct_label_utils to manually label PMJ.
    :param fname:
    :param fname_label:
    :return:
    """
    if shutil.which(viewer) is not None:  # Check if command 'sct_label_utils' exists
        message = "Click at the posterior tip of the pontomedullary junction (PMJ). Then click 'Save and Quit'."
        os.system('sct_label_utils -i {} -create-viewer 50 -o {} -msg "{}"'.format(fname, fname_label, message))
    else:
        viewer_not_found(viewer)


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
        # Add last newline
        outfile.write("\n")


def ask_if_modify(fname_label, fname_seg):
    """
    Check if the label file under derivatives already exists. If so, asks user if they want to modify it.
    If the label file under derivatives does not exist, copy it from processed data.
    If the file under derivatives and the file under processed data do not exist, create a new empty mask.
    :param fname_label: file under derivatives
    :param fname_seg: file under processed data
    :return:
    """
    # Check if file under derivatives already exists
    if os.path.isfile(fname_label):
        answer = None
        while answer not in ("y", "n"):
            answer = input("WARNING! The file {} already exists. "
                           "Would you like to modify it? [y/n] ".format(fname_label))
            if answer == "y":
                do_labeling = True
            elif answer == "n":
                do_labeling = False
            else:
                print("Please answer with 'y' or 'n'")
            # We don't want to copy because we want to modify the existing file
            copy = False
            create_empty_mask = False
    # If the file under derivatives does not exist, copy it from processed data
    elif not os.path.isfile(fname_label) and os.path.isfile(fname_seg):
        do_labeling = True
        copy = True
        create_empty_mask = False
    # If the file under derivatives and the file under processed data do not exist, create a new empty mask
    else:
        do_labeling = True
        copy = False
        create_empty_mask = True

    return do_labeling, copy, create_empty_mask


def generate_qc(fname, fname_label, task, fname_qc, subject, config_file):
    """
    Generate QC report.
    :param fname:
    :param fname_seg:
    :param fname_label:
    :param fname_pmj:
    :param qc_folder:
    :return:
    """
    os.system('sct_qc -i {} -s {} -p {} -qc {} -qc-subject {}'.format(
        fname, fname_label, get_function_for_qc(task), fname_qc, subject))
    # Archive QC folder
    shutil.copy(utils.get_full_path(config_file), fname_qc)
    shutil.make_archive(fname_qc, 'zip', fname_qc)
    print("Archive created:\n--> {}".format(fname_qc + '.zip'))


def denoise_image(fname):
    """
    Denoise image using non-local means adaptative denoising from P. Coupe et al. as implemented in dipy. For details,
    run sct_maths -h
    :param fname:
    :return:
    """
    print("Denoising {}".format(fname))
    fname_denoised = utils.add_suffix(fname, '_denoised-p1b2')
    os.system('sct_maths -i {} -denoise p=1,b=2 -o {}'.format(fname, fname_denoised))
    return fname_denoised


def remove_denoised_file(fname):
    """
    Remove denoised file
    :param fname:
    :return:
    """
    print("Removing {}".format(fname))
    os.remove(fname)


def main():

    # Parse the command line arguments
    parser = get_parser()
    args = parser.parse_args()

    # Logging level
    # TODO: how is this actually used?
    if args.verbose:
        coloredlogs.install(fmt='%(message)s', level='DEBUG')
    else:
        coloredlogs.install(fmt='%(message)s', level='INFO')

    # Fetch configuration from YAML file
    dict_yml = utils.fetch_yaml_config(args.config)

    # Curate dict_yml to only have filenames instead of absolute path
    dict_yml = utils.curate_dict_yml(dict_yml)

    # Check for missing files before starting the whole process
    if not args.add_seg_only:
        utils.check_files_exist(dict_yml, utils.get_full_path(args.path_in))

    suffix_dict = {
        'FILES_SEG': args.suffix_files_seg,         # e.g., _seg or _label-SC_mask
        'FILES_GMSEG': args.suffix_files_gmseg,     # e.g., _gmseg or _label-GM_mask
        'FILES_LESION': args.suffix_files_lesion,     # e.g., _lesion
        'FILES_LABEL': args.suffix_files_label,     # e.g., _labels or _labels-disc
        'FILES_PMJ': args.suffix_files_pmj          # e.g., _pmj or _label-pmj
    }

    path_out = utils.get_full_path(args.path_out)
    # check that output folder exists and has write permission
    path_out_deriv = utils.check_output_folder(path_out, args.path_derivatives)

    # Get name of expert rater (skip if -qc-only is true)
    if not args.qc_only:
        name_rater = input("Enter your name (Firstname Lastname). It will be used to generate a json sidecar with each "
                           "corrected file: ")

    # Build QC report folder name
    fname_qc = os.path.join(path_out, 'qc_corr_' + time.strftime('%Y%m%d%H%M%S'))

    # Get list of segmentations files for all subjects in -path-in (if -add-seg-only)
    if args.add_seg_only:
        path_list = glob.glob(args.path_in + "/**/*" + args.suffix_files_seg + ".nii.gz", recursive=True)
        # Get only filenames without suffix _seg  to match files in -config .yml list
        file_list = [utils.remove_suffix(os.path.split(path)[-1], args.suffix_files_seg) for path in path_list]

    # TODO: address "none" issue if no file present under a key
    # Perform manual corrections
    for task, files in dict_yml.items():
        # Get the list of segmentation files to add to derivatives, excluding the manually corrected files in -config.
        # TODO: probably extend also for other tasks (such as FILES_GMSEG)
        if args.add_seg_only and task == 'FILES_SEG':
            # Remove the files in the -config list
            for file in files:
                # Remove the file suffix (e.g., '_RPI_r') to match the list of files in -path-in
                file = utils.remove_suffix(file, args.suffix_files_in)
                if file in file_list:
                    file_list.remove(file)
            files = file_list  # Rename to use those files instead of the ones to exclude
        if files is not None:
            for file in files:
                # build file names
                subject, ses, filename, contrast = utils.fetch_subject_and_session(file)
                # Construct absolute path to the input file
                # For example: '/Users/user/dataset/data_processed/sub-001/anat/sub-001_T2w.nii.gz'
                fname = os.path.join(utils.get_full_path(args.path_in), subject, ses, contrast, filename)
                # Construct absolute path to the other contrast file
                if args.load_other_contrast:
                    fname_other_contrast = os.path.join(utils.get_full_path(args.path_in), subject, ses, contrast,
                                                        subject + '_' + ses + '_' + args.load_other_contrast + '.nii.gz')
                # Construct absolute path to the input label (segmentation, labeling etc.) file
                # For example: '/Users/user/dataset/data_processed/sub-001/anat/sub-001_T2w_seg.nii.gz'
                fname_seg = utils.add_suffix(fname, suffix_dict[task])
                # Construct absolute path to the derivative file (i.e., path where manually corrected file will be saved)
                # For example: '/Users/user/dataset/derivatives/labels/sub-001/anat/sub-001_T2w_seg-manual.nii.gz'
                fname_label = os.path.join(path_out_deriv, subject, ses, contrast,
                                           utils.add_suffix(utils.remove_suffix(filename, args.suffix_files_in),
                                                            suffix_dict[task] + '-manual'))
                # Create output folders under derivative if they do not exist
                os.makedirs(os.path.join(path_out_deriv, subject, ses, contrast), exist_ok=True)
                if not args.qc_only:
                    # Check if file under derivatives already exists. If so, asks user if they want to modify it.
                    do_labeling, copy, create_empty_mask = ask_if_modify(fname_label, fname_seg)
                    # Perform labeling (i.e., segmentation correction, labeling correction etc.) for the specific task
                    if do_labeling:
                        if args.denoise:
                            # Denoise the input file
                            fname = denoise_image(fname)
                        # Copy file to derivatives folder
                        if copy:
                            shutil.copyfile(fname_seg, fname_label)
                            print(f'Copying: {fname_seg} to {fname_label}')
                        # Create empty mask in derivatives folder
                        elif create_empty_mask:
                            utils.create_empty_mask(fname, fname_label)
                        if task in ['FILES_SEG', 'FILES_GMSEG']:
                            if not args.add_seg_only:
                                correct_segmentation(fname, fname_other_contrast, fname_label, args.viewer, args.fsl_color)
                        elif task == 'FILES_LESION':
                            correct_segmentation(fname, fname_other_contrast, fname_label, args.viewer, args.fsl_color)
                        elif task == 'FILES_LABEL':
                            correct_vertebral_labeling(fname, fname_label, args.label_disc_list)
                        elif task == 'FILES_PMJ':
                            correct_pmj_label(fname, fname_label)
                        else:
                            sys.exit('Task not recognized from yml file: {}'.format(task))
                        if args.denoise:
                            # Remove the denoised file (we do not need it anymore)
                            remove_denoised_file(fname)

                        if task == 'FILES_LESION':
                            # create json sidecar with the name of the expert rater
                            create_json(fname_label, name_rater)
                            # NOTE: QC for lesion segmentation does not exist or not implemented yet
                        else:
                            # create json sidecar with the name of the expert rater
                            create_json(fname_label, name_rater)
                            # Generate QC report
                            generate_qc(fname, fname_label, task, fname_qc, subject, args.config)

                # Generate QC report only
                if args.qc_only:
                    # Note: QC for lesion segmentation is not implemented yet
                    if task != "FILES_LESION":
                        generate_qc(fname, fname_label, task, fname_qc, subject, args.config)


if __name__ == '__main__':
    main()
