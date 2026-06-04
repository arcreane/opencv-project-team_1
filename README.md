# MyEditor

MyEditor is a small desktop image editor built for the Multimedia Application final project. The GUI is written with Tkinter and the image-processing work is done with OpenCV.

## Features

Core features:

- Thresholding: binary, Otsu and adaptive thresholding
- Histogram equalization: global equalization and CLAHE
- Morphology: dilation, erosion, opening, closing and gradient, with kernel size and shape controls
- Canny edge detection: low threshold, high threshold and aperture size controls
- Geometric transforms: affine transform from 3 mouse-selected points, perspective warp from 4 points
- Panorama stitching: load several overlapping images and build a panorama

Advanced features:

- Gamma correction
- Unsharp mask
- Bilateral denoising
- K-means color quantization
- Cartoon effect
- Pencil sketch
- Vignette
- ORB keypoint display
- Hough line detection
- Connected components
- Crop & straighten (document scanner): automatic corner detection and perspective correction
- Remove background (GrabCut): transparent PNG, solid colour, blurred background or mask output
- Undo / redo stack

## Install

Use Python 3.10 or newer.

```bash
python3 -m pip install -r requirements.txt
```

or:

```bash
make install
```

## Run

```bash
python3 main.py
```

or:

```bash
make run
```

## How to Use

1. Open an image with `File > Open`.
2. Choose an operation from `Core` or `Advanced`.
3. For slider-based tools, adjust the values and check the live preview.
4. Click `Apply` to keep the result or `Cancel` to return to the current image.
5. Use `Save As` to export the edited image.

For affine transform, click three points in this order: top-left, top-right, bottom-left.

For perspective warp, click the four corners of the area to straighten. The program orders the points automatically.

For panorama stitching, choose at least two overlapping images. If stitching fails, use images with more overlap and more visible texture.

For remove background, click `Remove Background`, then drag a rectangle around the subject you want to keep. Pick an output mode in the dialog: `Transparent` saves a PNG file with an alpha channel, while the other modes edit the current image. Try it on `samples/grabcut_subject.png`.

## Project Structure

```text
myeditor/
  app.py          GUI, dialogs, mouse interaction and undo/redo
  processing.py   OpenCV image-processing functions
  scanner.py      document detection and perspective correction
  segmentation.py GrabCut background removal
main.py           application entry point
samples/          test images for the demo
tests/            small processing smoke tests
```

## Test

```bash
python3 -m pytest tests
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
