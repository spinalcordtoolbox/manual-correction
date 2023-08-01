# Manual correction

This repository contains scripts for the manual correction of spinal cord labels. Currently supported labels are: 
- spinal cord segmentation
- gray matter segmentation
- lesion segmentation (e.g., MS or SCI lesions)
- disc labels
- compression labels
- ponto-medullary junction (PMJ) label
- centerline

We greatly appreciate feedback and suggestions for improvement. Feel free to open an issue and report bugs, suggest new features or ask questions.

## Installation

```console
git clone https://github.com/spinalcordtoolbox/manual-correction.git
cd manual-correction
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

> **Note** All scripts currently assume BIDS-compliant data. For more information about the BIDS standard, please visit http://bids.neuroimaging.io.

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

## Examples

See [wiki](https://github.com/spinalcordtoolbox/manual-correction/wiki)
