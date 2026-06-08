# MyEditor Report

## 1. Introduction

MyEditor is a desktop image editor inspired by simple GIMP workflows. The goal
was to build a real application, not only separate OpenCV scripts. A user can
open an image, choose an operation from the interface, change parameters, preview
the result, apply or cancel the operation, undo or redo edits, and save the final
image.

The current application uses Flet for the desktop GUI and OpenCV for image
processing. Images are stored as NumPy arrays in OpenCV BGR format. This keeps
the processing code close to standard OpenCV examples while still giving the
project a real graphical interface.

## 2. Architecture

The project is split into small files with clear roles.

| File | Role |
| --- | --- |
| `main.py` | Application entry point. It imports and starts the GUI. |
| `myeditor/app.py` | Flet GUI: window layout, left tool panel, image display, live preview, status messages, mouse selection, undo/redo and save/open workflow. |
| `myeditor/processing.py` | Main OpenCV functions for thresholding, equalization, morphology, Canny, transforms, stitching and advanced filters. |
| `myeditor/scanner.py` | Document corner ordering, scan detection and crop/straighten helpers. |
| `myeditor/segmentation.py` | GrabCut background removal, mask refinement and transparent cut-out helpers. |
| `tests/` | Basic tests for processing, scanner and segmentation functions. |

The GUI layer does not reimplement the OpenCV algorithms. It collects user
choices from buttons, sliders or mouse clicks, then calls a function from
`processing.py`, `scanner.py` or `segmentation.py`. This makes the program easier
to test and easier to explain during the individual code review.

The main image states are:

- `original_image`: the image first opened by the user, used by Reset
- `image`: the current edited image
- `preview_image`: temporary result shown before Apply
- `undo_stack` and `redo_stack`: previous image states for Undo and Redo

For display, the OpenCV BGR image is converted to RGB and encoded as a PNG for
the Flet image control.

## 3. Core Features

### Thresholding

The editor supports binary, Otsu and adaptive thresholding. Binary thresholding
uses a user-selected value, Otsu lets OpenCV choose a global threshold, and
adaptive thresholding computes a local threshold for each region.

### Histogram Equalization

Global histogram equalization is applied on the luminance channel in YCrCb color
space. CLAHE is applied on the lightness channel in LAB color space. This avoids
strong color distortion and gives better contrast on dark or low-contrast images.

### Morphology

The morphology tool supports dilation, erosion, opening, closing and gradient.
The user can choose kernel size and kernel shape: rectangle, ellipse or cross.
The operation is applied to grayscale intensity data, then converted back to BGR
for display.

### Canny Edge Detection

Canny exposes the low threshold, high threshold and aperture size. The result is
a black-and-white edge map converted back to BGR so it can be displayed and saved
like the other edited images.

### Geometric Transforms

The affine transform uses three mouse-selected points. The perspective transform
uses four mouse-selected points and orders the corners automatically before
calling OpenCV's perspective warp. These tools show why mouse interaction is
important in a desktop editor.

### Panorama Stitching

The panorama tool asks the user to choose multiple images, then uses OpenCV's
stitcher. If stitching fails, the GUI shows an error message instead of crashing.
This is important because panorama stitching depends heavily on overlap and
visual features in the source photos.

## 4. Additional Tools and Advanced Features

The final code contains more than the minimum required advanced features. The
main ones used for the demo should be the stable and easy-to-explain tools.

| Feature | Technique |
| --- | --- |
| Crop & Straighten | Document contour detection plus perspective transform |
| Remove Background | GrabCut rectangle initialization, mask refinement and transparent cut-out |
| Gamma correction | Lookup table applied to pixel values |
| Unsharp mask | Gaussian blur plus weighted difference |
| Bilateral denoising | Edge-preserving smoothing |
| K-means color quantization | Pixel clustering in BGR color space |
| Cartoon effect | Bilateral smoothing plus adaptive edge mask |
| Pencil sketch | Grayscale inversion, blur and division blend |
| Vignette | Gaussian mask multiplied with the image |
| ORB keypoints | ORB detector and keypoint drawing |
| Hough lines | Canny edge map followed by probabilistic Hough transform |
| Connected components | Otsu thresholding followed by component labeling |

Undo and Redo are also present, but they are better described as GUI/user
experience features rather than OpenCV algorithms.

The current merged code does not implement a separate Magic Wand or Flood Fill
selection tool, so it should not be presented as a final feature.

## 5. GUI and User Experience

The GUI opens as a desktop window with a top action bar, a left tool panel, a
main image display area and a status area. The common workflow is:

1. Open an image.
2. Choose a tool.
3. Adjust parameters or select points on the image.
4. Preview the result.
5. Apply, cancel, undo, redo, reset or save.

Parameter-based tools use live preview so the user can see the effect before
committing it. Geometric tools use mouse clicks on the image. The app also shows
status and error messages, for example when no image is loaded or when panorama
stitching fails.

## 6. Results and Demo

The `samples/` folder contains test images for normal filters, document scanning,
GrabCut and panorama stitching. The `docs/demo_outputs/` folder contains example
outputs generated from the current processing functions:

| Result | File |
| --- | --- |
| Original sample | `docs/demo_outputs/01_original.png` |
| Otsu thresholding | `docs/demo_outputs/02_otsu_threshold.png` |
| CLAHE contrast enhancement | `docs/demo_outputs/03_clahe.png` |
| Canny edge detection | `docs/demo_outputs/04_canny.png` |
| Cartoon effect | `docs/demo_outputs/05_cartoon.png` |
| ORB keypoints | `docs/demo_outputs/06_orb_keypoints.png` |
| Tilted document sample | `docs/demo_outputs/07_document_perspective_source.png` |
| Panorama stitching result | `docs/demo_outputs/08_panorama_result.png` |

For the final PDF submission, the report should also include screenshots of the
actual GUI, because the GUI is a mandatory part of the project.

## 7. Project Management and Contribution

This table should be checked against the GitHub commit history before the final
PDF is exported.

| Member | Main responsibility | Notes |
| --- | --- | --- |
| Zijie Huang | GUI workflow documentation, image state management explanation, Open / Save / Reset / Undo / Redo workflow, user instructions and individual code review notes | Responsible for explaining how the editor is used and how the main state flow works |
| Mahad Moumine Ali | To be confirmed from the final branch / PR history | Fill in only the features that are actually merged and visible in the final code |
| Rayene Khader | To be confirmed from the final branch / PR history | Fill in only the features that are actually merged and visible in the final code |
| Helton do Nascimento Rodrigues Barbosa | To be confirmed from the final branch / PR history | Fill in only the features that are actually merged and visible in the final code |

Suggested workflow:

- Use one branch per member or feature.
- Keep commits small and easy to explain.
- Do not push directly to `main`.
- Before the presentation, confirm that every claimed feature exists in the final
  merged code.

## 8. Known Limitations

- Panorama stitching needs overlapping images with enough texture and matching
  visual features.
- Affine transform depends on the user clicking the three points in the expected
  order.
- GrabCut works best when the rectangle includes the subject and enough
  background around it.
- Very large images can make heavier tools such as K-means slower.
- The GUI is practical for a student project, but it is not as complete as a
  professional editor such as GIMP.

## 9. Possible Improvements

- Add a true Magic Wand / Flood Fill selection tool.
- Add inpainting with a brush mask.
- Add layers and blend modes.
- Add more automated GUI tests.
- Package the application as a standalone executable.

## 10. Conclusion

MyEditor covers the six mandatory OpenCV topics and includes several extra
features for the demo. The most important design choice is the separation between
the GUI workflow and the processing functions. This keeps the application usable,
testable and understandable for the individual code review.
