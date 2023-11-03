# Manual correction

This repository contains scripts for the manual correction of spinal cord labels. 

Currently supported labels are: 
- spinal cord segmentation
- gray matter segmentation
- lesion segmentation (e.g., MS or SCI lesions)
- disc labels
- compression labels
- ponto-medullary junction (PMJ) label
- centerline

> **Note**
> We greatly appreciate feedback and suggestions for improvement. Feel free to open an issue and report bugs, suggest new features or ask questions.

## Table of content
* [1. Dependencies](#1-dependencies)
* [2. Installation](#2-installation)
* [3. Usage](#3-usage)
    * [`manual_correction.py`](#manual_correctionpy)
    * [`package_for_correction.py`](#package_for_correctionpy)
    * [`copy_files_to_derivatives.py`](#copy_files_to_derivativespy)
* [4. Examples](#4-examples)

## 1. Dependencies

- [Spinal Cord Toolbox (SCT)](https://github.com/neuropoly/spinalcordtoolbox)
- [FSLeyes](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FSLeyes) or [ITK-SNAP](http://www.itksnap.org)
- Python 3.8

## 2. Installation

Download the repository:

```console
git clone https://github.com/spinalcordtoolbox/manual-correction.git
cd manual-correction
```

Create a virtual environment and install the required packages:

```console
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Alternatively, you can use existing SCT's conda environment:

```console
source ${SCT_DIR}/python/etc/profile.d/conda.sh
conda activate venv_sct
```

## 3. Usage

> **Important**
> All scripts currently assume BIDS-compliant data. For more information about the BIDS standard, please visit http://bids.neuroimaging.io.


### `manual_correction.py`

This script loops across subjects listed in the YAML file and opens a viewer to correct the labels (segmentations, disc labels, etc.). 

```bash
python manual_correction.py -path-img <INPUT_PATH> -config <CONFIG_FILE>
```

- `INPUT_PATH`: Path to the BIDS-compliant folder with data to be corrected.
- `CONFIG_FILE`: YAML file that lists images to be corrected. This YAML file can be generated by [SCT's QC HTML report](https://spinalcordtoolbox.com/overview/concepts/inspecting-results-qc-fsleyes.html#how-do-i-use-the-qc-report) or created manually. 

For full help, please run: `python manual_correction.py -h`.

### `package_for_correction.py`

If the manual correction is done by someone else than the person doing the processing, this script packages the processed images and existing labels (segmentation, disc labels, etc.) and creates a single ZIP file that can conveniently be sent to collaborators.

```bash
python package_for_correction.py -path-in <INPUT_PATH> -config <CONFIG_FILE>
```

- `INPUT_PATH`: Path to the BIDS-compliant folder with data to be packaged.
- `CONFIG_FILE`: YAML file that lists images to be packaged. This YAML file can be generated by [SCT's QC HTML report](https://spinalcordtoolbox.com/overview/concepts/inspecting-results-qc-fsleyes.html#how-do-i-use-the-qc-report) or created manually. 

For full help, please run: `python package_for_correction.py -h`.

### `copy_files_to_derivatives.py`

This script copies manually corrected labels (segmentations, disc labels, etc.) from your local `derivatives/labels` folder to the already existing dataset's `derivatives/labels` folder.

```bash
python copy_files_to_derivatives.py -path-in <INPUT_PATH> -path-out <OUTPUT_PATH>
```

- `INPUT_PATH`: Path to the BIDS-compliant folder with manually corrected labels.
- `OUTPUT_PATH`: Path to the BIDS-compliant folder where manually corrected files will be copied.

For full help, please run: `python copy_files_to_derivatives.py -h`.

## 4. Examples

See [wiki](https://github.com/spinalcordtoolbox/manual-correction/wiki)
