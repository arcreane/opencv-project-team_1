# MyEditor

MyEditor is a small desktop image editor built for the Multimedia Application
final project. The GUI is written with **Flet** (Flutter under the hood) and the
image-processing work is done with **OpenCV**.

## Final Scope

Core features:

- Thresholding: binary, Otsu and adaptive thresholding
- Histogram equalization: global equalization and CLAHE
- Morphology: dilation, erosion, opening, closing and gradient, with kernel size and shape controls
- Canny edge detection: low threshold, high threshold and aperture size controls
- Geometric transforms: affine transform from 3 mouse-selected points, perspective warp from 4 points
- Crop & Straighten (Scan): auto document detection, draggable corners, B&W / Color / Gray output
- Panorama stitching: load several overlapping images and build a panorama

Selection:

- Remove Background (GrabCut): rectangle selection, brush touch-ups
  (erase background / restore subject) with undo/redo, transparent PNG cut-out
  or solid background colour

Advanced features:

- Gamma correction, unsharp mask, bilateral denoising
- K-means color quantization
- Cartoon effect, pencil sketch, vignette
- ORB keypoints, Hough lines, connected components

GUI features:

- Open / Save As / Reset
- Undo and Redo
- Live preview for tools with parameters
- Status and error messages
- Keyboard shortcuts: Ctrl+O, Ctrl+S, Ctrl+Z, Ctrl+Y

## Install

Use Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

This opens a native desktop window.

## How to Use

1. Open an image with the folder icon in the top bar (`samples/` has test images).
2. Pick a tool in the left panel (Core / Géométrie / Sélection / Advanced).
3. For slider tools, adjust the values and watch the live preview, then
   **Appliquer** to keep the result or **Annuler** to cancel.
4. Use the save icon to export the edited image.

Tool notes:

- **Affine**: click three points in this order: top-left, top-right, bottom-left.
- **Perspective**: click the four corners of the area to straighten. The corners
  are ordered automatically.
- **Crop & Straighten**: the document is auto-detected; drag the green corners to
  adjust, choose the output, then apply.
- **Remove Background**: drag a rectangle around the subject; refine with the
  touch-up brush (erase background / restore subject); choose a transparent PNG
  or a background colour; then apply. Save as PNG to keep transparency.
- **Panorama**: choose at least two overlapping images with enough overlap and
  visible texture.

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
python -m pytest
```

The tests cover the processing, scanner and segmentation functions. The main
validation is still the GUI demo, because the project is an interactive image
editor.

## Demo Assets

The `samples/` folder contains generated images for testing the editor. To rebuild them:

```bash
python3 tools/make_samples.py
```

To generate the output examples used by the report:

```bash
python3 tools/make_demo_outputs.py
```
