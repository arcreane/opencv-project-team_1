# MyEditor

MyEditor is a small desktop image editor for the Multimedia Application final
project. It is a GIMP-like editor powered by OpenCV: the user can open an image,
choose an operation, adjust parameters, preview the result, apply or cancel the
change, and save the final image.

The current version uses **Python**, **Flet** for the desktop GUI, **OpenCV** for
image processing, **NumPy** for image arrays, and **pytest** for tests.

## Final Scope

Core OpenCV features:

- Thresholding: binary, Otsu and adaptive thresholding
- Histogram equalization: global equalization and CLAHE
- Morphology: dilation, erosion, opening, closing and gradient, with kernel size and shape controls
- Canny edge detection: low threshold, high threshold and aperture size controls
- Geometric transforms: affine transform from 3 mouse-selected points and perspective warp from 4 mouse-selected points
- Panorama stitching: choose several overlapping images and build one panorama

Extra image tools present in the current code:

- Crop & Straighten (Scan): automatic document detection, draggable corners, B&W / Color / Gray output
- Remove Background (GrabCut): rectangle selection, brush touch-ups, transparent PNG cut-out or solid background colour
- Gamma correction, unsharp mask and bilateral denoising
- K-means color quantization
- Cartoon effect, pencil sketch and vignette
- ORB keypoints, Hough lines and connected components
- Undo / Redo image state stack

The current merged code does not implement a separate Magic Wand / Flood Fill
tool, so it is not listed as a final feature.

## Install

Use Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python3 main.py
```

This opens the Flet desktop window.

## How to Use the GUI

1. Click the folder icon to open an image. The `samples/` folder has test images.
2. Pick a tool from the left panel. The main groups are File actions, Core tools,
   Geometry / scan tools, Selection tools and Advanced tools.
3. For parameter tools, move the sliders to see a live preview.
4. Click **Appliquer** to keep the preview, or **Annuler** to return to the current image.
5. Use the save icon to export the edited image.

Basic workflow buttons:

- **Open Image** loads an image into the editor.
- **Save As** writes the current edited image to disk.
- **Reset** restores the original image that was first opened.
- **Undo** returns to the previous edited image.
- **Redo** restores an image that was undone.

Tool notes:

- **Affine**: click three points in this order: top-left, top-right, bottom-left.
- **Perspective**: click four corners of the area to straighten. The program orders
  the corners automatically.
- **Crop & Straighten**: the document is auto-detected; drag the green corners to
  adjust the scan area, choose the output mode, then apply.
- **Remove Background**: drag a rectangle around the subject, refine with the
  brush, then choose transparent PNG or a background colour.
- **Panorama**: choose at least two images with enough overlap and visual features.
  Stitching can fail if the photos do not share enough matching points.

Keyboard shortcuts:

- `Ctrl+O`: open image
- `Ctrl+S`: save image
- `Ctrl+Z`: undo
- `Ctrl+Y`: redo

## Project Structure

```text
myeditor/
  app.py           Flet GUI: panels, live preview, mouse interaction, undo/redo
  processing.py    OpenCV image-processing functions
  scanner.py       document detection and perspective scan
  segmentation.py  GrabCut background removal
main.py            application entry point
assets/            application icon
samples/           test images for the demo
tests/             processing / scanner / segmentation tests
```

## Test

```bash
python3 -m pytest
```

The tests cover the processing, scanner and segmentation functions. The GUI is
also checked manually during the demo, because the project is an interactive
desktop editor.

## Demo Assets

The `samples/` folder contains generated images for testing the editor. To rebuild them:

```bash
python3 tools/make_samples.py
```

To generate the output examples used by the report:

```bash
python3 tools/make_demo_outputs.py
```
