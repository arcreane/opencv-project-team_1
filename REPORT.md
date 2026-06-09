# MyEditor Report

## 1. Project Goal

MyEditor is a desktop image editor built with Python, Flet and OpenCV. The goal
was to make a small GIMP-like application, not a set of command-line scripts.
The user can open an image, choose an operation, change parameters, preview the
result, apply or cancel the change, and save the final image.

We focused on a stable demo first. The final version covers the six mandatory
OpenCV features from the project brief and three advanced features that are easy
to show during the presentation: Cartoon Effect, Hough Lines Detection and
Remove Background with GrabCut.

## 2. Technologies Used

| Tool | Use in the project |
| --- | --- |
| Python | Main programming language |
| Flet | Desktop graphical interface |
| OpenCV | Image processing algorithms |
| NumPy | Image arrays and numerical operations |
| Pytest | Basic tests for processing functions |

OpenCV stores images as NumPy arrays in BGR format. The GUI keeps this format
for processing and only converts the image when it needs to display it.

## 3. Application Structure

The code is separated into small files so each part can be tested and explained.

| File | Responsibility |
| --- | --- |
| `main.py` | Starts the application |
| `myeditor/app.py` | Flet interface, image display, buttons, tool panels, mouse interaction, status messages, undo and redo |
| `myeditor/processing.py` | Main OpenCV functions: thresholding, histogram equalization, morphology, Canny, transforms, stitching and effects |
| `myeditor/scanner.py` | Document detection and crop/straighten helper functions |
| `myeditor/segmentation.py` | GrabCut background removal and mask refinement |
| `tests/` | Tests for processing, scanner and segmentation code |

The GUI does not contain the image-processing algorithms directly. It collects
the user input, calls a function from the processing modules, and then displays
the returned image. This made the project easier to divide between members.

## 4. GUI Workflow

The interface has a top toolbar, a left tool menu, a central image area and a
right parameter panel. The basic workflow is:

1. Open an image.
2. Choose a tool.
3. Adjust parameters with sliders or dropdowns.
4. Check the preview.
5. Apply the result or cancel it.
6. Save the edited image.

The application keeps several image states:

- `original_image`: the image loaded from disk, used for Reset
- `image`: the current edited image
- `preview_image`: a temporary preview before Apply
- `undo_stack` and `redo_stack`: previous image states

For parameter-based tools, the preview is calculated on a smaller copy of the
image so the sliders stay responsive. When the user clicks Apply, the same
operation is applied to the full image.

## 5. Mandatory Features

### 5.1 Thresholding

The editor supports three thresholding methods:

- Binary thresholding with a manual threshold value
- Otsu thresholding, where OpenCV chooses the threshold automatically
- Adaptive thresholding, where the threshold is calculated locally

The image is converted to grayscale for the operation, then converted back to a
displayable image.

### 5.2 Histogram Equalization

Two contrast tools are included:

- Global histogram equalization
- CLAHE

Global equalization is applied to the luminance channel instead of directly to
each BGR channel. This gives better contrast while avoiding strong color shifts.
CLAHE is useful for images where lighting is not uniform, because it improves
contrast locally.

### 5.3 Morphology

The morphology tool supports dilation, erosion, opening, closing and gradient.
The user can choose the kernel size and the kernel shape: rectangle, ellipse or
cross. These operations are useful for removing small noise, connecting shapes,
filling gaps or highlighting borders.

### 5.4 Canny Edge Detection

Canny edge detection exposes the two threshold values and the aperture size. The
output is a black-and-white edge image, converted back into a displayable format
for the GUI.

### 5.5 Geometric Transforms

The editor includes two point-based transforms:

- Affine transform from three selected points
- Perspective transform from four selected points

The points are selected directly on the image. For perspective transform, the
program orders the four corners before calling OpenCV, so the selected area can
be straightened more reliably.

### 5.6 Panorama Stitching

The panorama tool lets the user choose several overlapping images and uses
OpenCV's stitcher to build a panorama. If stitching fails, the program shows an
error message instead of closing or crashing. This is important because panorama
stitching depends a lot on the input images.

## 6. Advanced Features

### 6.1 Cartoon Effect

The cartoon effect combines smoothing and edge extraction. A bilateral filter
keeps strong edges while smoothing colors. Then an adaptive threshold creates an
edge mask. The final image keeps the simplified colors and visible outlines.

### 6.2 Hough Lines Detection

This feature first detects edges with Canny, then uses the probabilistic Hough
transform to find straight line segments. The detected lines are drawn on top of
the original image. It is useful for showing structure in buildings, documents
or other images with strong straight edges.

### 6.3 Remove Background with GrabCut

The Remove Background tool uses GrabCut. The user first draws a rectangle around
the subject. OpenCV separates probable foreground and background. The user can
then refine the mask with brush strokes to erase background or restore parts of
the subject. The result can be saved with transparency when using PNG.

## 7. Results and Demo Images

The `samples/` folder contains input images used for testing and demonstration.
The `docs/demo_outputs/` folder contains generated examples for the report.

| Example | File |
| --- | --- |
| Original image | `docs/demo_outputs/01_original.png` |
| Otsu thresholding | `docs/demo_outputs/02_otsu_threshold.png` |
| CLAHE | `docs/demo_outputs/03_clahe.png` |
| Canny edge detection | `docs/demo_outputs/04_canny.png` |
| Cartoon effect | `docs/demo_outputs/05_cartoon.png` |
| Hough lines | `docs/demo_outputs/06_hough_lines.png` |
| Document source image | `docs/demo_outputs/07_document_perspective_source.png` |
| Panorama result | `docs/demo_outputs/08_panorama_result.png` |

The most important part of the demo is still the live GUI, because the project
brief requires a real desktop application.

## 8. Testing

We used Pytest for the main processing modules. The tests check that functions
return valid images, keep reasonable output sizes and do not crash on normal
input. The current test suite covers:

- Core processing functions
- Scanner / document detection helpers
- GrabCut segmentation helpers

Final check command:

```bash
python3 -m pytest
```

At the last check, all tests passed.

## 9. Project Management and Contributions

We used Git branches and pull requests to separate work. The table below follows
the visible GitHub history.

| Member | Main work |
| --- | --- |
| Zijie Huang | GUI workflow notes, image state explanation, Open/Save/Reset, Undo/Redo documentation, README and report polishing |
| Uncher | GrabCut background removal and related selection workflow |
| Rayene Khader | Flet interface modernization, transform tools and before/after comparison |
| BrendowDevX | Early project structure and core image-processing work |

During development, the project changed from a simpler interface to a Flet-based
desktop GUI. We kept the OpenCV functions separate from the GUI so that the
application stayed easier to test and explain.

## 10. Limitations

- Panorama stitching needs images with enough overlap and visible texture.
- The affine tool depends on the user clicking the three points in the requested
  order.
- GrabCut works best when the rectangle contains the full subject and some
  background.
- Very large images can slow down heavy tools.
- The editor is designed for a course project, so it does not include full
  professional features such as layers.

## 11. Possible Improvements

- Add a true Magic Wand or Flood Fill selection tool.
- Add inpainting with a brush mask.
- Add layers and blend modes.
- Add better export options.
- Package the application as a standalone executable.

## 12. Conclusion

MyEditor meets the main project requirements: it is a desktop GUI image editor,
it implements the six mandatory OpenCV features, and it adds three advanced
features for the final demo. The code is kept simple on purpose. GUI code
handles user interaction, and processing functions handle image operations. This
keeps the project understandable for the presentation and for the individual
code review.
