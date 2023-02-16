# Manual correction

This repository contains scripts for the manual correction of spinal cord labels. Currently supported labels are: 
- spinal cord segmentation
- gray matter segmentation
- lesion segmentation (e.g., MS or SCI lesions)
- disc labels
- ponto-medullary junction (PMJ) label

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

### `package_for_correction.py`

The `package_for_correction.py` script is used to create a zip file containing the processed images and labels 
(segmentations, disc labels, etc.). The zip file is then sent to the user for manual correction.

This is useful when you need to correct the labels of a large dataset processed on a remote server. In this case, you do
not need to copy the whole dataset. Instead, only the images and labels that need to be corrected are zipped. The yaml 
list of images to correct can be obtained from the [SCT QC html report](https://spinalcordtoolbox.com/overview/concepts/inspecting-results-qc-fsleyes.html#how-do-i-use-the-qc-report).

### `manual_correction.py`

The `manual_correction.py` script is used to correct the labels (segmentations, disc labels, etc.) of a dataset. 
The script takes as input a processed dataset and outputs the corrected labels to `derivatives/labels` folder.

For the correction of spinal cord and gray matter segmentation, you can choose a viewer ([FSLeyes](https://open.win.ox.ac.uk/pages/fsl/fsleyes/fsleyes/userdoc/#), [ITK-SNAP](http://www.itksnap.org/pmwiki/pmwiki.php), [3D Slicer](https://www.slicer.org)).

For the correction of vertebral labeling and ponto-medullary junction (PMJ), [sct_label_utils](https://github.com/spinalcordtoolbox/spinalcordtoolbox/blob/master/spinalcordtoolbox/scripts/sct_label_utils.py) is used.

### `copy_files_to_derivatives.py`

The `copy_files_to_derivatives.py` script is used to copy manually corrected labels (segmentations, disc labels, etc.) 
from your local `derivatives/labels` folder to the already existing git-annex BIDS dataset's `derivatives/labels` folder.
