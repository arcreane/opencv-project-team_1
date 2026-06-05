# MyEditor

MyEditor is a small desktop image editor built for the Multimedia Application final project. The GUI is written with Tkinter and the image-processing work is done with OpenCV.

## Final Scope

Core features:

- Thresholding: binary, Otsu and adaptive thresholding
- Histogram equalization: global equalization and CLAHE
- Morphology: dilation, erosion, opening, closing and gradient, with kernel size and shape controls
- Canny edge detection: low threshold, high threshold and aperture size controls
- Geometric transforms: affine transform from 3 mouse-selected points, perspective warp from 4 points
- Panorama stitching: load several overlapping images and build a panorama

Advanced features used for the final demo:

- Cartoon effect
- Hough line detection
- Magic Wand / flood fill selection

GUI features:

- Open Image
- Save As
- Reset to the original image
- Undo and Redo
- Live preview dialogs for tools with parameters
- Status and error messages

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

## How to Use

1. Open an image with `File > Open`.
2. Choose a tool from the menus: `Core`, `Geometry` or `Advanced`.
3. For tools with sliders, adjust the values and check the live preview.
4. Click `Apply` to keep the preview or `Cancel` to return to the previous image.
5. Use `File > Save As` to export the edited image.

Basic GUI workflow:

- `Open Image` loads a picture and stores it as both the original image and the current image.
- `Save As` saves the current edited image to a new file.
- `Reset` restores the original loaded image.
- `Undo` goes back to the previous edit.
- `Redo` restores an edit after undo.
- If no image is loaded, the GUI shows a message instead of crashing.

For affine transform, click three points in this order: top-left, top-right, bottom-left.

For perspective warp, click the four corners of the area to straighten. The program orders the points automatically.

For Magic Wand, choose a tolerance and overlay color, then click a pixel in the image.

For panorama stitching, choose at least two overlapping images. If stitching fails, use images with more overlap and more visible texture.

## Project Structure

```text
myeditor/
  app.py          GUI, dialogs, mouse interaction and undo/redo
  processing.py   OpenCV image-processing functions
main.py           application entry point
samples/          test images for the demo
tests/            small processing smoke tests
```

## Test

```bash
python -m pytest
```

The tests are small smoke tests for the processing functions. The main validation is still the GUI demo, because the project is an interactive image editor.

## Demo Assets

The `samples/` folder contains generated images for testing the editor. To rebuild them:

```bash
python3 tools/make_samples.py
```

To generate the output examples used by the report:

```bash
python3 tools/make_demo_outputs.py
```
