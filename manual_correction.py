#!/usr/bin/env python
#
# Script to perform manual correction of spinal cord segmentation, gray matter segmentation, MS and SCI lesion
# segmentation, disc labels, compression labels, ponto-medullary junction (PMJ) label, and centerline.
#
# For full help, please run:  python manual_correction.py -h
#
# Example:
#       python manual_correction.py
#       -path-img ~/<your_dataset>/data_processed
#       -config config.yml
#
# For all examples, see: https://github.com/spinalcordtoolbox/manual-correction/wiki
#
# Authors: Jan Valosek, Sandrine Bédard, Naga Karthik, Nathan Molinier, Julien Cohen-Adad
#

import argparse
import tempfile
import coloredlogs
import glob
import json
import os
import logging
import sys
import shutil
from textwrap import dedent
import time
import tqdm
import subprocess

import utils

import numpy as np
import nibabel as nib


def get_parser():
    """
    parser function
    """
    parser = argparse.ArgumentParser(
        description='Manual correction of spinal cord segmentation, gray matter segmentation, MS and SCI lesion '
                    'segmentation, disc labels, compression labels, ponto-medullary junction (PMJ) label, and '
                    'centerline. '
                    'Manually corrected files will be saved under derivatives/labels folder (according to BIDS '
                    'standard) if not specified otherwise.',
        formatter_class=utils.SmartFormatter,
        prog=os.path.basename(__file__).strip('.py')
    )
    parser.add_argument(
        '-config',
        metavar="<file>",
        required=True,
        help=
        "R|Config YAML file listing images that require manual corrections for segmentation and vertebral "
        "labeling. "
        "'FILES_SEG' lists images associated with spinal cord segmentation, "
        "'FILES_GMSEG' lists images associated with gray matter segmentation, "
        "'FILES_LESION' lists images associated with multiple sclerosis lesion segmentation, "
        "'FILES_LABEL' lists images associated with vertebral labeling, "
        "'FILES_COMPRESSION' lists images associated with compression labeling, "
        "'FILES_PMJ' lists images associated with pontomedullary junction labeling, "
        "'FILES_ROOTLETS' lists images associated with rootlets segmentation, "
        "and 'FILES_CENTERLINE' lists images associated with centerline. "
        "You can validate your YAML file at this website: http://www.yamllint.com/."
        "\nNote: if you want to iterate over all subjects, you can use the wildcard '*' (Examples: sub-*_T1w.nii.gz, "
        "sub-*_ses-M0_T2w.nii.gz, sub-*_ses-M0_T2w_RPI_r.nii.gz, etc.).\n"
        "Below is an example YAML file:\n"
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
            FILES_COMPRESSION:
            - sub-001_T1w.nii.gz
            - sub-002_T1w.nii.gz
            FILES_PMJ:
            - sub-001_T1w.nii.gz
            - sub-002_T1w.nii.gz
            FILES_ROOTLETS:
            - sub-001_T1w.nii.gz
            - sub-002_T1w.nii.gz
            FILES_CENTERLINE:
            - sub-001_T1w.nii.gz
            - sub-002_T1w.nii.gz\n
            """)
    )
    parser.add_argument(
        '-path-img',
        metavar="<folder>",
        required=True,
        help=
        "R|Full path to the folder with images (BIDS-compliant). "
        "Examples: '~/<your_dataset>' or 'output/data_processed'."
    )
    parser.add_argument(
        '-path-label',
        metavar="<folder>",
        help=
        "R|Full path to the folder with labels (BIDS-compliant). "
        "\nIf not provided, '-path-img' will be used (assuming that the labels are in the same folder as images). "
        "\nIf your labels are already under 'derivatives/labels', provide the full path to this folder. ",
        default=''
    )
    parser.add_argument(
        '-path-out',
        metavar="<folder>",
        help=
        "R|Full path to the folder where corrected labels will be stored. "
        "Example: '~/<your_dataset>/derivatives/labels'. "
        "\nIf not provided, '-path-img' + 'derivatives/labels' will be used. "
        "\nNote: If the specified path does not exist, it will be created.",
        default=''
    )
    parser.add_argument(
        '-suffix-files-in',
        help=
        "R|Suffix of the input files."
        "This flag is useful in cases when the input files have been processed and thus contain a specific suffix. "
        "For example, if the input image listed under '-config' contains the suffix '_RPI_r' "
        "(e.g., sub-001_T1w_RPI_r.nii.gz), but the label file does not contain this suffix "
        "(e.g., sub-001_T1w_seg.nii.gz), then you would need to provide the suffix '_RPI_r' to this flag.",
        default=''
    )
    parser.add_argument(
        '-suffix-files-seg',
        help="FILES-SEG suffix. Examples: '_seg' (default), '_seg-manual', '_label-SC_mask'.",
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
        help="FILES-LABEL suffix. Examples: '_labels', '_label-disc' (default).",
        default='_label-disc'
    )
    parser.add_argument(
        '-suffix-files-compression',
        help="FILES-COMPRESSION suffix. Examples: '_compression', '_label-compression' (default).",
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
        '-suffix-files-rootlets',
        help="FILES-ROOTLETS suffix. Examples: '_label-rootlets_dseg' (default), '_rootlets'.",
        default='_label-rootlets_dseg'
    )
    parser.add_argument(
        '-label-disc-list',
        help="Comma-separated list containing individual values and/or intervals for disc labeling. Example: '1:4,6,8' "
             "or 1:25 (default)",
        default='1:25'
    )
    parser.add_argument(
        '-viewer',
        help="Viewer used for manual correction. Available options: 'fsleyes' (default), 'itksnap', 'slicer'. "
             "For details about viewers, visit their websites: "
             "FSLeyes (https://open.win.ox.ac.uk/pages/fsl/fsleyes/fsleyes/userdoc/#) "
             "ITK-SNAP (http://www.itksnap.org/pmwiki/pmwiki.php) "
             "3D Slicer (https://www.slicer.org)",
        choices=['fsleyes', 'itksnap', 'slicer'],
        default='fsleyes'
    )
    parser.add_argument(
        '-fsleyes-cm',
        help="Colormap (cm) to be used for loading the label file in FSLeyes (default: red). `fsleyes -h` gives all "
             "the available color options. If using a combination of colors, specify them with '-', e.g. 'red-yellow'.",
        type=str,
        default='red'
    )
    parser.add_argument(
        '-fsleyes-a',
        help="Alpha (a) in percentages to be used for loading the label file in FSLeyes (default: 70). "
             "This flag can be used to adjust the opacity of the label file (e.g., segmentation).",
        type=str,
        default="70"
    )
    parser.add_argument(
        '-fsleyes-dr',
        help="R|Display range (dr) in percentages to be used for loading the input file in FSLeyes (default: 0,70). "
             "This flag can be used to adjust the brightness and contrast of the input image. "
             "\nNote: Use comma to separate values, e.g., 0,70."
             "\nNote: If you need to provide negative values (for example for PSIR/STIR images), use the following "
             "format: -fsleyes-dr=\"-40,70\"",
        type=str,
        default='0,70'
    )
    parser.add_argument(
        '-fsleyes-second-orthoview',
        help="Open a second orthoview in FSLeyes (i.e., open two orthoviews next to each other).",
        action='store_true'
    )
    parser.add_argument(
        '-denoise',
        help="Denoise the input image using 'sct_maths -denoise p=1,b=2'.",
        action='store_true'
    )
    parser.add_argument(
        '-load-other-contrast',
        help="Load additional image to the viewer. This flag is useful if you want to use an additional contrast than "
             "provided by the YAML file. Only valid for '-viewer fsleyes'. The filenames of the additional contrast "
             "are derived from the filename provided by '-config'. For instance, if you want to open T2w overlaid by "
             "PSIR image, specify T2w filename using '-config' flag and within this flag provides only PSIR. Another "
             "examples: 'PSIR', 'STIR', 'acq-sag_T1w', 'T2star' etc.",
        type=str,
        default=None
    )
    parser.add_argument(
        '-qc-only',
        help="Only output QC report based on the manually-corrected files already present in the 'derivatives' folder. "
             "Skip the copy of the source files, and the opening of the manual correction pop-up windows.",
        action='store_true'
    )
    parser.add_argument(
        '-qc-lesion-plane',
        help="Plane of the lesion QC. Available options: sagittal (default), axial.",
        choices=['sagittal', 'axial'],
        default='sagittal'
    )
    parser.add_argument(
        '-add-seg-only',
        help="Only copy the source files (segmentation) that aren't in -config list to the final dataset specified by "
             "'-path-out' flag. Use this flag to add automatically generated and manually QC-ed segmentations to the "
             "final dataset.",
        action='store_true'
    )
    parser.add_argument(
        '-json-metadata', metavar="<file>", required=False,
        help="R|A custom JSON file containing metadata to be added to the output JSON sidecar of all corrected labels. "
             "This flag is useful, for example, when a label was obtained automatically and you want to include this "
             "information into the JSON sidecar. \n"
             "NOTE: the script automatically checks whether the JSON file already exists (for example when "
             "automatically created by SCT 6.4+). If so, the script will reuse its metadata. In such cases, you do not "
             "need to use this flag.\n"
             "Below is an example JSON file:\n"
             + dedent(
             """
             {
                "Name": "sct_deepseg_sc",
                "Version": "SCT v6.2",
                "Date": "yyyy-mm-dd hh:mm:ss"
             }\n
             """),
    )
    parser.add_argument(
        '-change-orient',
        type=str,
        help=
        "R|Orientation to show the image in the viewer. If provided, the image and label will be reoriented before "
        "opening the viewer. After manual correction, the image and label will be reoriented back to the original "
        "orientation.\n"
        "Warning: be aware of this issue when using this flag: "
        "https://github.com/spinalcordtoolbox/manual-correction/issues/101",
        choices=['LAS', 'LAI', 'LPS', 'LPI', 'LSA', 'LSP', 'LIA', 'LIP', 'RAS', 'RAI', 'RPS', 'RPI', 'RSA', 'RSP',
                 'RIA', 'RIP', 'ALS', 'ALI', 'ARS', 'ARI', 'ASL', 'ASR', 'AIL', 'AIR', 'PLS', 'PLI', 'PRS', 'PRI',
                 'PSL', 'PSR', 'PIL', 'PIR', 'SLA', 'SLP', 'SRA', 'SRP', 'SAL', 'SAR', 'SPL', 'SPR', 'ILA', 'ILP',
                 'IRA', 'IRP', 'IAL', 'IAR', 'IPL', 'IPR'],
        default=''
    )
    parser.add_argument(
        '-v', '--verbose',
        help="Full verbose (for debugging)",
        action='store_true'
    )

    return parser


class ParamFSLeyes:
    """
    Default parameters for FSLeyes viewer.
    """
    def __init__(self, cm='red', dr='0,70', min_dr='0', max_dr='1000', a='70', second_orthoview=False):
        """
        :param cm: Colormap (cm) to be used for loading the label file in FSLeyes (default: red).
        :param dr: Display range (dr) in % to be used for loading the input file in FSLeyes (default: 0,70).
        :param min_dr: Minimum pixel intensity value for the display range (dr) to be used for loading the input file in FSLeyes.
        :param max_dr: Maximum pixel intensity value for the display range (dr) to be used for loading the input file in FSLeyes.
        :param a: Alpha (a) in percentages to be used for loading the label file in FSLeyes (default: 70).
        :param second_orthoview: Open a second orthoview in FSLeyes (i.e., open two orthoviews next to each other).
        """
        self.cm = cm
        self.dr = dr
        self.min_dr = min_dr
        self.max_dr = max_dr
        self.a = a
        self.second_orthoview = second_orthoview


def create_fsleyes_script():
    """
    Create a custom Python script to interact with the FSLeyes API.
    Note: the second orthoview cannot be opened from the CLI, instead, FSLeyes API via a custom Python script must
    be used. For details, see: https://www.jiscmail.ac.uk/cgi-bin/wa-jisc.exe?A2=FSL;ab356891.2301
    :param fname: path of the input image.
    :param fname_seg_out: path to the derivative label file
    :param fname_other_contrast: path of the other contrast to be loaded in FSLeyes.
    :param param_fsleyes:
    :return:
    """
    python_script = [
        "ortho_left = frame.addViewPanel(OrthoPanel)",
        "ortho_right = frame.addViewPanel(OrthoPanel)",
        "ortho_left.defaultLayout()",
        "ortho_right.defaultLayout()",
        ""
    ]

    # Create a temporary script
    fname_script = os.path.join(tempfile.mkdtemp(), 'custom_fsleyes_script.py')
    with open(fname_script, 'w') as f:
        f.write('\n'.join(python_script))

    return fname_script


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
    elif task == 'FILES_COMPRESSION':
        # Note: compression labels do not have proper QC -->  we are using workaround with sct_label_utils
        return 'sct_label_utils'
    elif task == 'FILES_PMJ':
        return 'sct_detect_pmj'
    elif task == 'FILES_CENTERLINE':
        # Note: sct_get_centerline does not have proper QC -->  we are using workaround with sct_label_vertebrae
        # Details: https://github.com/spinalcordtoolbox/spinalcordtoolbox/issues/4011#issuecomment-1403828459
        return 'sct_label_vertebrae'
    elif task == 'FILES_LESION':
        return 'sct_deepseg_lesion'
    else:
        raise ValueError("This task is not recognized: {}".format(task))


def correct_segmentation(fname, fname_seg_out, fname_other_contrast, viewer, param_fsleyes):
    """
    Open viewer (ITK-SNAP, FSLeyes, or 3D Slicer) with fname and fname_seg_out.
    :param fname:
    :param fname_seg_out: path to the derivative label file
    :param fname_other_contrast: additional contrast to load in the viewer (specified by the '-load-other-contrast'
    flag). Only valid for FSLeyes (default: None).
    :param viewer:
    :param param_fsleyes: parameters for FSLeyes viewer.
    :return:
    """
    # launch ITK-SNAP
    if viewer == 'itksnap':
        print("In ITK-SNAP, correct the segmentation, then save it with the same name (overwrite).")
        # Note: command line differs for macOs/Linux and Windows
        if shutil.which('itksnap') is not None:  # Check if command 'itksnap' exists
            # macOS and Linux
            subprocess.check_call(['itksnap',
                                   '-g', fname,
                                   '-s', fname_seg_out])
            
        elif shutil.which('ITK-SNAP') is not None:  # Check if command 'ITK-SNAP' exists
            # Windows
            subprocess.check_call(['ITK-SNAP',
                                   '-g', fname,
                                   '-s', fname_seg_out])
        else:
            viewer_not_found(viewer)
    # launch FSLeyes
    elif viewer == 'fsleyes':
        if shutil.which('fsleyes') is not None:  # Check if command 'fsleyes' exists
            # Get min and max intensity
            min_intensity, max_intensity = utils.get_image_intensities(fname)
            # Set min intensity
            param_fsleyes.min_dr = str((max_intensity * int(param_fsleyes.dr.split(',')[0]))/100)
            # Decrease max intensity
            param_fsleyes.max_dr = str((max_intensity * int(param_fsleyes.dr.split(',')[1]))/100)

            print("In FSLeyes, click on 'Edit mode', correct the segmentation, and then save it with the same name "
                  "(overwrite).")
            # FSLeyes arguments explanation:
            # -S, --skipfslcheck    Skip $FSLDIR check/warning
            # -dr, --displayRange   Set display range (min max) for the specified overlay
            # -cm, --cmap           Set colour map for the specified overlay
            # -a, --alpha           Set alpha (opacity) for the specified overlay
            if fname_other_contrast:
                # Open a second orthoview (i.e., open two orthoviews next to each other) using a custom Python script
                # (-r flag)
                if param_fsleyes.second_orthoview:
                    fname_script = create_fsleyes_script()
                    subprocess.check_call(['fsleyes',
                                           '-S',
                                           '-r', fname_script,
                                           fname, '-dr', param_fsleyes.min_dr, param_fsleyes.max_dr,
                                           fname_other_contrast,
                                           fname_seg_out, '-cm', param_fsleyes.cm, '-a', param_fsleyes.a])
                # No second orthoview
                else:
                    subprocess.check_call(['fsleyes',
                                           '-S',
                                           fname, '-dr', param_fsleyes.min_dr, param_fsleyes.max_dr,
                                           fname_other_contrast,
                                           fname_seg_out, '-cm', param_fsleyes.cm, '-a', param_fsleyes.a])
            # Open a second orthoview without second contrast
            elif param_fsleyes.second_orthoview:
                fname_script = create_fsleyes_script()
                subprocess.check_call(['fsleyes',
                                       '-S',
                                       '-r', fname_script,
                                       fname, '-dr', param_fsleyes.min_dr, param_fsleyes.max_dr,
                                       fname_seg_out, '-cm', param_fsleyes.cm, '-a', param_fsleyes.a])
            # No second contrast, no second orthoview
            else:
                subprocess.check_call(['fsleyes',
                                       '-S',
                                       fname,
                                       '-dr', param_fsleyes.min_dr, param_fsleyes.max_dr,
                                       fname_seg_out, '-cm', param_fsleyes.cm, '-a', param_fsleyes.a])
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
            subprocess.check_call(['sct_label_utils', 
                                   '-i', fname, 
                                   '-create-viewer', label_list, 
                                   '-o', fname_label, 
                                   '-ilabel', fname_label, 
                                   '-msg', message])
        else:
            subprocess.check_call(['sct_label_utils',
                                   '-i', fname,
                                   '-create-viewer', label_list,
                                   '-o', fname_label,
                                   '-msg', message])
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
        subprocess.check_call(['sct_label_utils',
                               '-i', fname,
                               '-create-viewer', '50',
                               '-o', fname_label,
                               '-msg', message])
    else:
        viewer_not_found(viewer)


def correct_centerline(fname, fname_label, viewer='sct_get_centerline'):
    """
    Open sct_get_centerline viewer to manually label spinal cord centerline.
    """
    if shutil.which(viewer) is not None:  # Check if command 'sct_get_centerline' exists
        print("Select a few points to extract the centerline. Then click 'Save and Quit'.")
        subprocess.check_call(['sct_get_centerline',
                               '-i', fname,
                               '-method viewer' 
                               '-gap', '30',
                               '-qc qc-manual',
                               '-o', fname_label])
    else:
        viewer_not_found(viewer)


def load_json(fname):
    """
    Load existing JSON file. The content of the JSON file will be added to the JSON file produced by this script.
    :param fname: path to the existing JSON file.
    :return: dictionary with the metadata to be added to the output JSON sidecar.
    """
    if not os.path.isfile(fname):
        sys.exit("ERROR: The file {} does not exist.".format(fname))
    try:
        with open(fname, "r") as f:
            json_metadata = json.load(f)
        return json_metadata
    except json.JSONDecodeError:
        sys.exit("ERROR: The file {} is not a valid JSON file.".format(fname))


def update_json(fname_nifti, name_rater, json_metadata):
    """
    Create/update JSON sidecar with meta information
    :param fname_nifti: str: File name of the nifti image to associate with the JSON sidecar
    :param name_rater: str: Name of the expert rater
    :param json_metadata: dict: Dictionary with the metadata to be added to the JSON sidecar
    :return:
    """
    fname_json = fname_nifti.replace('.gz', '').replace('.nii', '.json')

    # Check if the json file already exists, if so, open it
    if os.path.exists(fname_json):
        # Read already existing json file
        with open(fname_json, "r") as outfile:  # r to read
            json_dict = json.load(outfile)

        # Special checks to fix all of our current json files (Might be deleted later)
        if 'GeneratedBy' not in json_dict.keys():
            json_dict = {'GeneratedBy': [json_dict]}
        if 'SpatialReference' not in json_dict.keys():
            json_dict['SpatialReference'] = 'orig'
    
    # If the json file does not exist, initialize a new one
    else:
        # Init new json dict
        json_dict = {'SpatialReference': 'orig',
                     'GeneratedBy': []}
        # NOTE: we add the custom metadata only when initializing a new JSON file. Because it does not make sense to add
        # these metadata into already existing labels, which we do not know how they were generated.
        if json_metadata:
            # If json_metadata already contains the 'GeneratedBy' key (for example when the label was generated by SCT),
            # use the existing key. Otherwise, create a new one. This will prevent duplication of the 'GeneratedBy' key.
            # Context: https://github.com/spinalcordtoolbox/manual-correction/issues/108
            if 'GeneratedBy' in json_metadata.keys():
                json_dict.update(json_metadata)
            else:
                json_dict['GeneratedBy'].append(json_metadata.copy())

    # If the label was modified or just checked, add "Name": "Manual" to the JSON sidecar
    json_dict['GeneratedBy'].append({'Name': 'Manual',
                                     'Author': name_rater,
                                     'Date': time.strftime('%Y-%m-%d %H:%M:%S')})

    # Write the data to the JSON file
    with open(fname_json, 'w') as outfile:  # w to overwrite the file
        json.dump(json_dict, outfile, indent=4)
        # Add last newline
        outfile.write("\n")
    print("JSON sidecar was updated: {}".format(fname_json))


def ask_if_modify(fname_out, fname_label, do_labeling_always=False):
    """
    Check if the output file already exists. If so, asks user if they want to modify it.
    If the output file does not exist, copy it from label folder.
    If the output file and the label file do not exist, create a new empty mask.
    :param fname_out: manually corrected output file, example: <PATH_DATA>/derivatives/labels/sub-001/anat/sub-001_T2w_seg-manual.nii.gz
    :param fname_label: input label which will be modified, example: <PATH_DATA>/data_processed/sub-001/anat/sub-001_T2w_seg.nii.gz
    :return:
    """
    # Check if the output file already exists
    if os.path.isfile(fname_out):
        answer = None
        if not do_labeling_always:
            print(f'WARNING! The file {fname_out} already exists.')
            while answer not in ("y", "n", "Y"):
                answer = input(f'Would you like to modify it? (type "y" to modify, type "n" to skip, type "Y" to '
                               f'modify all files): ')
                if answer == "y":
                    do_labeling = True
                elif answer == "n":
                    do_labeling = False
                elif answer == "Y":
                    do_labeling_always = True
                    do_labeling = True
                else:
                    print("Invalid input. Please enter [y/n/Y].")
        else:
            do_labeling = True
        # We don't want to copy because we want to modify the existing file
        copy = False
        create_empty_mask = False

    # If the output file does not exist, copy it from label folder
    elif not os.path.isfile(fname_out) and os.path.isfile(fname_label):
        do_labeling = True
        copy = True
        create_empty_mask = False
    # If the output file and the input label file data do not exist, create a new empty mask
    else:
        do_labeling = True
        copy = False
        create_empty_mask = True

    return do_labeling, copy, create_empty_mask, do_labeling_always


def generate_qc(fname, fname_label, task, fname_qc, subject, config_file, qc_lesion_plane, suffix_dict):
    """
    Generate QC report.
    :param fname: background image
    :param fname_label: segmentation mask to be overlaid on the background image
    :param task: task name
    :param fname_qc: QC folder name
    :param subject: subject name
    :param config_file: config file
    :param qc_lesion_plane: plane of the lesion QC
    :param suffix_dict: dictionary of suffixes
    :return:
    """
    # Not all sct_qc -p functions support empty label files. Check if the label file is empty and skip QC if so.
    # Context: https://github.com/spinalcordtoolbox/manual-correction/issues/60#issuecomment-1720280352
    skip_qc_list = ['FILES_LABEL', 'FILES_COMPRESSION', 'FILES_PMJ', 'FILES_CENTERLINE']
    if task in skip_qc_list:
        img_label = nib.load(fname_label)
        data_label = img_label.get_fdata()
        if np.sum(data_label) == 0:
            logging.warning(f"File {fname_label} is empty. Skipping QC.\n")
            return

    # Lesion QC needs also SC segmentation for cropping
    if task == 'FILES_LESION':
        # Construct SC segmentation file name
        fname_seg = fname_label.replace(suffix_dict['FILES_LESION'], suffix_dict['FILES_SEG'])
        # Check if SC segmentation file exists
        if os.path.isfile(fname_seg):
            print("SC segmentation file found: {}. Creating QC.".format(fname_seg))
            # Lesion QC supports only binary segmentation --> binarize the lesion
            fname_label_bin = utils.add_suffix(fname_label, '_bin')
            subprocess.check_call(['sct_maths',
                                   '-i', fname_label,
                                   '-bin', '0',
                                   '-o', fname_label_bin])
            # fname - background image; fname_seg - SC segmentation - used for cropping; fname_label - lesion
            # segmentation
            subprocess.check_call(['sct_qc',
                                   '-i', fname,
                                   '-s', fname_seg,
                                   '-d', fname_label_bin,
                                   '-p', get_function_for_qc(task),
                                   '-plane', qc_lesion_plane,
                                   '-qc', fname_qc,
                                   '-qc-subject', subject])
            # remove binarized lesion segmentation
            os.remove(fname_label_bin)
            # Archive QC folder
            archive_qc(fname_qc, config_file)
        else:
            print("WARNING: SC segmentation file not found: {}. QC report will not be generated.".format(fname_seg))

    # Skip QC for the spinal rootlets segmentation as `sct_qc` does not support it
    # Context: https://github.com/spinalcordtoolbox/spinalcordtoolbox/issues/4166#issuecomment-1654175610
    elif task == 'FILES_ROOTLETS':
        pass

    else:
        subprocess.check_call(['sct_qc',
                               '-i', fname,
                               '-s', fname_label,
                               '-p', get_function_for_qc(task),
                               '-qc', fname_qc,
                               '-qc-subject', subject])
        # Archive QC folder
        archive_qc(fname_qc, config_file)


def archive_qc(fname_qc, config_file):
    """
    Archive QC folder
    """
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
    subprocess.check_call(['sct_maths',
                           '-i', fname,
                           '-denoise', 'p=1,b=2',
                           '-o', fname_denoised])
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

    suffix_dict = {
        'FILES_SEG': args.suffix_files_seg,                 # e.g., _seg or _label-SC_mask
        'FILES_GMSEG': args.suffix_files_gmseg,             # e.g., _gmseg or _label-GM_mask
        'FILES_LESION': args.suffix_files_lesion,           # e.g., _lesion
        'FILES_LABEL': args.suffix_files_label,             # e.g., _labels or _label-disc
        'FILES_COMPRESSION': args.suffix_files_compression,  # e.g., _label-compression
        'FILES_PMJ': args.suffix_files_pmj,                 # e.g., _pmj or _label-pmj
        'FILES_ROOTLETS': args.suffix_files_rootlets,       # e.g., _rootlets or _label-rootlets
        'FILES_CENTERLINE': args.suffix_files_centerline    # e.g., _centerline or _label-centerline
    }
    path_img = utils.get_full_path(args.path_img)

    # If labels are in the same folder as the images, set path_label to path_img
    path_label = path_img if args.path_label == '' else utils.get_full_path(args.path_label)

    # If not specified, output folder for corrected labels is derivatives/labels in the input folder
    path_out = os.path.join(path_img, "derivatives/labels") if args.path_out == '' else utils.get_full_path(
        args.path_out)

    # Print parsed arguments
    logging.info("-" * 100)
    logging.info("Parsing of arguments:")
    logging.info("  Input folder ('-path-img'):     " + path_img)
    logging.info("  Label folder ('-path-label'):   " + path_label)
    logging.info("  Output folder ('-path-out'):    " + path_out)
    logging.info("-" * 100)

    # check that output folder exists or create it
    utils.check_output_folder(path_out)

    # Check for missing files before starting the whole process
    if not args.add_seg_only:
        utils.check_files_exist(dict_yml, path_img, path_label, suffix_dict)

    # Fetch parameters for FSLeyes
    param_fsleyes = ParamFSLeyes(cm=args.fsleyes_cm, dr=args.fsleyes_dr, a=args.fsleyes_a,
                                 second_orthoview=args.fsleyes_second_orthoview)

    # Get list of segmentations files for all subjects in -path-label (if -add-seg-only)
    if args.add_seg_only:
        path_list = glob.glob(args.path_label + "/**/*" + args.suffix_files_seg + ".nii.gz", recursive=True)
        # Get only filenames without suffix _seg  to match files in -config .yml list
        file_list = [utils.remove_suffix(os.path.split(path)[-1], args.suffix_files_seg) for path in path_list]
        # Check if file_list is empty
        if not file_list:
            sys.exit("ERROR: No segmentation file found in {}.".format(args.path_label))

    # If a custom JSON file containing metadata was provided, load it, and verify that it is a valid JSON file
    json_metadata = load_json(args.json_metadata) if args.json_metadata else None

    # Get name of expert rater (skip if -qc-only is true)
    if not args.qc_only:
        name_rater = input("Enter your name (Firstname Lastname). It will be used to generate a json sidecar with each "
                           "corrected file: ")
        print('')

    # Build QC report folder name
    fname_qc = os.path.join(path_img, 'qc_corr')
    
    # Set overwrite variable to False
    do_labeling_always = False

    # TODO: address "none" issue if no file present under a key
    # Perform manual corrections
    for task, files in dict_yml.items():
        if task.startswith('FILES'):
            # Check if task is in suffix_dict.keys(), if not, skip it
            # Note that this check is done after the task.startswith('FILES') check because the manual-correction
            # script should ignore keys that start with CORR (CORR keys are used to track the manual correction
            # progress)
            if task not in suffix_dict.keys():
                logging.warning("WARNING: {} is not a valid task. Skipping it.".format(task))
                continue
            # Get the list of segmentation files to add to derivatives, excluding the manually corrected files in -config.
            # TODO: probably extend also for other tasks (such as FILES_GMSEG)
            if args.add_seg_only and task == 'FILES_SEG':
                # Remove the files in the -config list
                for file in files:
                    # Remove the file suffix (e.g., '_RPI_r') to match the list of files in -path-img
                    file = utils.remove_suffix(file, args.suffix_files_in)
                    if file in file_list:
                        file_list.remove(file)
                files = file_list  # Rename to use those files instead of the ones to exclude
            if len(files) > 0:
                # Handle regex (i.e., iterate over all subjects)
                if '*' in files[0] and len(files) == 1:
                    subject, ses, filename, contrast = utils.fetch_subject_and_session(files[0])
                    # Get list of files recursively
                    glob_files = sorted(glob.glob(os.path.join(path_img, '**', filename),
                                            recursive=True))
                    # Skip filenames containing "notused"
                    glob_files = [file for file in glob_files if 'notused' not in file]
                    # Get list of already corrected files
                    if task.replace('FILES', 'CORR') in dict_yml.keys():
                        corr_files = dict_yml[task.replace('FILES', 'CORR')]
                    else:
                        corr_files = []
                    #  Remove labels under derivatives and already corrected files
                    files = []
                    for file in glob_files:
                        subject, ses, filename, contrast = utils.fetch_subject_and_session(file)
                        if ('derivatives' not in file) and (filename not in corr_files):
                            files.append(file)
                # Loop across files
                for file in tqdm.tqdm(files, desc="{}".format(task), unit="file"):
                    # Print empty line to not overlay with tqdm progress bar
                    time.sleep(0.1)
                    print("")
                    # build file names
                    subject, ses, filename, contrast = utils.fetch_subject_and_session(file)
                    # Construct absolute path to the input file
                    # For example: '/Users/user/dataset/data_processed/sub-001/anat/sub-001_T2w.nii.gz'
                    fname = os.path.join(path_img, subject, ses, contrast, filename)
                    # Construct absolute path to the other contrast file
                    if args.load_other_contrast:
                        # Do not include session in the filename
                        if ses == '':
                            other_contrast_filename = subject + '_' + args.load_other_contrast + '.nii.gz'
                        # Include session in the filename
                        else:
                            other_contrast_filename = subject + '_' + ses + '_' + args.load_other_contrast + '.nii.gz'
                        fname_other_contrast = os.path.join(path_img, subject, ses, contrast, other_contrast_filename)
                    else:
                        fname_other_contrast = None
                    # Construct absolute path to the input label (segmentation, labeling etc.) file
                    # For example: '/Users/user/dataset/data_processed/sub-001/anat/sub-001_T2w_seg.nii.gz'
                    fname_label = utils.add_suffix(os.path.join(path_label, subject, ses, contrast, filename), suffix_dict[task])
                    
                    # Construct absolute path to the output file (i.e., path where manually corrected file will be saved)
                    # For example: '/Users/user/dataset/derivatives/labels/sub-001/anat/sub-001_T2w_seg.nii.gz'
                    # The information regarding the modified data will be stored within the sidecar .json file
                    fname_out = utils.add_suffix(os.path.join(path_out, subject, ses, contrast, filename), suffix_dict[task])

                    # Change orientation of the input image (if different from the original orientation)
                    if args.change_orient:
                        # Get image and label orientation
                        image_orig_orient = utils.get_orientation(fname)
                        label_orig_orient = utils.get_orientation(fname_label)
                        # Change orientation of the input image for better visualization
                        if image_orig_orient != args.change_orient or label_orig_orient != args.change_orient:
                            utils.change_orientation(fname, args.change_orient)
                            utils.change_orientation(fname_label, args.change_orient)
                    
                    # Create subject folder in output if they do not exist
                    os.makedirs(os.path.join(path_out, subject, ses, contrast), exist_ok=True)
                    if not args.qc_only:
                        # Check if the output file already exists. If so, asks user if they want to modify it.
                        do_labeling, copy, create_empty_mask, do_labeling_always = \
                            ask_if_modify(fname_out=fname_out,
                                        fname_label=fname_label,
                                        do_labeling_always=do_labeling_always)
                        # Perform labeling (i.e., segmentation correction, labeling correction etc.) for the specific task
                        if do_labeling:
                            if args.denoise:
                                # Denoise the input file
                                fname = denoise_image(fname)
                            # Copy file to derivatives folder
                            if copy:
                                shutil.copyfile(fname_label, fname_out)
                                print(f'Copying: {fname_label} to {fname_out}')
                                # If the label has a JSON sidecar, read its content
                                # Context: SCT v6.4+ produces JSON sidecars for some outputs that track the provenance
                                # of the function, models, etc.
                                # Details: https://github.com/spinalcordtoolbox/spinalcordtoolbox/pull/4466
                                # We want to include this information in the final JSON sidecar
                                fname_label_json = fname_label.replace('.nii.gz', '.json')
                                if os.path.isfile(fname_label_json):
                                    # Read the JSON file to include the metadata in the final JSON sidecar
                                    json_metadata = load_json(fname_label_json)
                            # Create empty mask in derivatives folder
                            elif create_empty_mask:
                                utils.create_empty_mask(fname, fname_out)

                            if task in ['FILES_SEG', 'FILES_GMSEG', 'FILES_ROOTLETS']:
                                if not args.add_seg_only:
                                    correct_segmentation(fname, fname_out, fname_other_contrast, args.viewer, param_fsleyes)
                            elif task == 'FILES_LESION':
                                correct_segmentation(fname, fname_out, fname_other_contrast, args.viewer, param_fsleyes)
                            elif task == 'FILES_LABEL':
                                correct_vertebral_labeling(fname, fname_out, args.label_disc_list)
                            elif task == 'FILES_COMPRESSION':
                                # Note: be aware of possibility to create compression labels also using
                                # 'sct_label_utils -create-viewer'
                                # Context: https://github.com/spinalcordtoolbox/spinalcordtoolbox/issues/3984
                                correct_segmentation(fname, fname_out, fname_other_contrast, 'fsleyes', param_fsleyes)
                            elif task == 'FILES_PMJ':
                                correct_pmj_label(fname, fname_out)
                            elif task == 'FILES_CENTERLINE':
                                correct_centerline(fname, fname_out)
                            else:
                                sys.exit('Task not recognized from the YAML file: {}'.format(task))
                            if args.denoise:
                                # Remove the denoised file (we do not need it anymore)
                                remove_denoised_file(fname)

                            # Add segmentation only (skip generating QC report)
                            if args.add_seg_only:
                                # We use update_json because we are adding a new segmentation, and we want to create
                                # a JSON file
                                update_json(fname_out, name_rater, json_metadata)
                            # Generate QC report
                            else:
                                update_json(fname_out, name_rater, json_metadata)
                                # Generate QC report
                                generate_qc(fname, fname_out, task, fname_qc, subject, args.config, args.qc_lesion_plane, suffix_dict)

                    # Generate QC report only
                    if args.qc_only:
                        generate_qc(fname, fname_out, task, fname_qc, subject, args.config, args.qc_lesion_plane, suffix_dict)
                    
                    # Keep track of corrected files in YAML.
                    dict_yml = utils.track_corrections(files_dict=dict_yml.copy(), config_path=args.config, file_path=fname, task=task)

                    # Change orientation of the input image back to the original orientation
                    if args.change_orient:
                        image_current_orientation = utils.get_orientation(fname)
                        label_current_orientation = utils.get_orientation(fname_label)
                        if image_current_orientation != image_orig_orient or label_current_orientation != label_orig_orient:
                            utils.change_orientation(fname, image_orig_orient)
                            utils.change_orientation(fname_out, label_orig_orient)

            else:
                sys.exit("ERROR: The list of files to correct is empty. \nMaybe, you have already corrected all the "
                         "files? Please, check the YAML file: {}".format(args.config))


if __name__ == '__main__':
    main()
