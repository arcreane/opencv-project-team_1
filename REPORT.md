# MyEditor Final Report

Multimedia Application Final Project 2026  
ISEP - École d'ingénieurs du numérique

Team members:

- Zijie Huang
- Mahad MOUMINE ALI
- Rayene Khader
- Helton DO NASCIMENTO RODRIGUES BARBOSA

## 1. Introduction

MyEditor is our multimedia final project. It is a desktop image editor inspired
by simple GIMP-like workflows. The objective was to build a complete
OpenCV-based application rather than a set of isolated command-line exercises.
The project prioritised a stable and demonstrable application workflow,
including image loading, parameter adjustment, live preview, application of
effects, undo/redo and export.

The final version uses Python, Flet, OpenCV, NumPy and pytest. Flet provides the
desktop graphical interface. OpenCV and NumPy are used for image operations.
Pytest is used for functional tests on processing and helper functions.

## 2. Architecture

The project is divided into a GUI layer and processing/helper modules. This was
important because the GUI should only manage the user workflow, while the image
operations stay in separate functions.

| File or folder | Role |
| --- | --- |
| `main.py` | Entry point. It launches the Flet application. |
| `myeditor/app.py` | GUI layer. It creates the Flet window, top app bar, left tool panel, central image display, right parameter panel, status messages, file picker, preview workflow, Undo/Redo, Reset, Before/After comparison and mouse interactions. |
| `myeditor/processing.py` | Main OpenCV functions: thresholding, histogram equalization, morphology, Canny, geometric transforms, panorama stitching and extra effects. |
| `myeditor/scanner.py` | Document scan / Crop & Straighten helper functions. |
| `myeditor/segmentation.py` | GrabCut background removal and mask helper functions. |
| `tests/` | Pytest tests for processing functions and helper modules. |
| `samples/` | Sample images used for testing and live demonstration. |

The main GUI class is `MyEditor` in `myeditor/app.py`. It does not directly
implement every OpenCV algorithm. It collects input from buttons, sliders,
dropdowns or mouse clicks, then calls functions from `processing.py`,
`scanner.py` or `segmentation.py`.

OpenCV stores colour images as NumPy arrays, usually in BGR channel order. The
GUI keeps this representation for processing and encodes images as PNG bytes
when displaying them in Flet.

## 3. GUI Workflow and Image State

The editor follows a simple workflow:

1. The user opens an image with the file picker.
2. The image appears in the central display area.
3. The user chooses a tool from the left panel.
4. The right panel shows parameters such as sliders, dropdowns or Apply/Cancel buttons.
5. For parameter-based tools, a live preview is shown before changing the current image.
6. If the user clicks Apply, the full-size result becomes the current image.
7. If the user clicks Cancel, the temporary preview is discarded.
8. The user can save, reset, undo, redo or compare before/after.

The important state variables are:

| Variable | Purpose |
| --- | --- |
| `original_image` | First image loaded from disk. It is kept for Reset. |
| `image` | Current edited image shown in the editor. |
| `preview_image` | Temporary image shown before Apply. |
| `undo_stack` | Previous image states used by Undo. |
| `redo_stack` | Image states restored by Redo. |
| `base_image` | Full-size image used when a tool is finally applied. |
| `preview_base` | Smaller image used for faster live preview. |

The `commit_image()` method is the central part of the editing workflow. When
the user applies a result, it stores the previous image in `undo_stack`, updates
the current `image`, clears `preview_image`, clears `redo_stack` after a new
edit, closes the active tool panel, updates the buttons/status and re-renders
the image. This makes Apply, Reset, Undo and Redo behave consistently.

Reset copies `original_image` back into the current image through this same
commit workflow. Before/After comparison uses the original image and current
image together so the user can visually compare the edit result.

## 4. Mandatory OpenCV Features

### 4.1 Thresholding

Thresholding converts a grayscale image into a binary black-and-white result.
The editor supports three modes.

- Binary thresholding uses `cv2.threshold` with a user-selected threshold value.
- Otsu thresholding uses `cv2.threshold` with Otsu's method, so OpenCV chooses the threshold automatically.
- Adaptive thresholding uses `cv2.adaptiveThreshold`, where the threshold is calculated locally for different areas of the image.

The GUI exposes the binary threshold value, adaptive block size and adaptive
constant. This is useful for separating bright and dark regions, especially when
preparing an image for shape detection or morphology.

### 4.2 Histogram Equalization

Histogram equalization improves image contrast. The project includes global
equalization and CLAHE.

Global equalization uses `cv2.equalizeHist` on the luminance channel instead of
equalizing BGR channels separately. This improves contrast while reducing strong
color shifts. CLAHE uses `cv2.createCLAHE` on the lightness channel in LAB color
space. CLAHE is better for images where lighting changes across the picture.

The GUI exposes the CLAHE clip limit and tile size. These parameters control
how strong the local contrast enhancement is.

### 4.3 Morphology

Morphology changes bright and dark structures in a grayscale image. The editor
builds a kernel with `cv2.getStructuringElement` and supports dilation, erosion,
opening, closing and gradient through `cv2.morphologyEx`.

- Dilate expands bright regions.
- Erode shrinks bright regions.
- Open removes small bright noise.
- Close fills small gaps.
- Gradient highlights borders.

The GUI exposes operation type, kernel size and kernel shape. Kernel shape can
be rectangle, ellipse or cross. This makes the tool useful for cleaning binary
or thresholded images before further analysis.

### 4.4 Canny Edge Detection

Canny edge detection finds edges in an image with `cv2.Canny`. The GUI exposes
the low threshold, high threshold and aperture size. The low and high thresholds
control weak and strong edges in the hysteresis step. The aperture size changes
the Sobel kernel used internally for gradients.

This tool is useful for showing contours and for preparing images for line
detection.

### 4.5 Geometric Transforms

The project includes two point-based geometric transforms.

Affine transform uses three points selected by the user. The code uses
`cv2.getAffineTransform` and `cv2.warpAffine`. Affine transform can move, scale,
rotate or shear an image region while preserving parallel lines.

Perspective transform uses four points selected by the user. The code orders
the selected corners, then uses `cv2.getPerspectiveTransform` and
`cv2.warpPerspective`. Perspective transform can correct viewpoint distortion,
for example when straightening a tilted document or rectangular object.

### 4.6 Panorama Stitching

The panorama tool lets the user choose multiple images. It uses
`cv2.Stitcher_create` to find matching visual features and combine overlapping
images. This works best when the images have enough overlap and clear texture.

If stitching fails, the application catches the error and shows a clear message
instead of crashing. This is important because panorama stitching can fail when
there are not enough reliable matches.

## 5. Advanced Features

For the oral demo and written report, the project focuses on three advanced
features. These tools are visual, easy to demonstrate and different from the
six mandatory feature groups.

| Feature | Implementation idea and use |
| --- | --- |
| Cartoon effect | Combines bilateral filtering with an adaptive edge mask. |
| Hough lines | Uses Canny edges and `cv2.HoughLinesP` to draw straight line segments. |
| Remove Background / GrabCut | Uses GrabCut with an initial rectangle and optional brush refinement. |

This is not a separate Magic Wand or Flood Fill tool; the implemented selection
feature is based on GrabCut.

Some smaller tools are also available in the interface, such as gamma
correction, unsharp mask, bilateral denoising, K-means color quantization,
vignette, pencil sketch, ORB keypoints, connected components, rotation, mirror
and crop. They support the editor workflow, but they are not treated as the main
advanced features of the project.

## 6. Screenshots and Demo Outputs

The repository already contains generated output images in `docs/demo_outputs/`.
They are connected to the main operations and can be used in the final PDF or
slides.

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
| Flet GUI with Canny preview | `docs/demo_outputs/09_gui_canny_preview.png` |

The GUI screenshot shows the real Flet interface with a sample image loaded,
the Canny tool selected, live preview visible in the central area and parameter
controls on the right panel.

## 7. Testing

We used pytest for smoke tests and helper-function tests. The tests check that
processing functions return valid images, keep reasonable output sizes and do
not crash on normal inputs. They also check important scanner and segmentation
helpers.

The GUI is mainly validated through manual demo because interactive desktop
behavior is harder to automate in this project. We do not claim perfect visual
quality testing. The tests are functional checks that help catch broken
functions and obvious regressions.

Test command: `python3 -m pytest`

At the latest local check, 23 tests passed.

## 8. Project Management and Contributions

We used Git branches and pull requests to separate work. The contribution table
below follows the visible repository history and the team-provided contribution
descriptions.

| Member | Main contribution |
| --- | --- |
| Zijie Huang | GUI workflow notes, image state explanation, Open/Save/Reset and Undo/Redo documentation, README and report polishing. |
| Mahad MOUMINE ALI | Crop & Straighten branch work, GrabCut background removal and segmentation workflow. |
| Rayene Khader | Flet interface modernization, transform tools and before/after comparison. |
| Helton DO NASCIMENTO RODRIGUES BARBOSA | Early project structure and support for core processing work. |

The main project management choice was to keep image-processing functions
separate from GUI code. This made it easier for team members to work on
different parts and also made code review easier.

## 9. Known Limitations

- Panorama stitching depends on overlap and visible features in the input images.
- Affine and perspective results depend on the user selecting correct points.
- GrabCut works best when the initial rectangle includes the full subject and enough background.
- K-means and other heavier tools can be slower on very large images.
- The project is a student image editor and is not as complete as professional tools such as GIMP or Photoshop.
- GUI testing is mostly manual.
- GUI interaction is mainly tested manually because automated testing of mouse-based Flet interactions is more complex.

## 10. Future Improvements

- Add more robust automated GUI tests.
- Add batch processing for applying a tool to several images.
- Add more precise selection tools.
- Add more export options.
- Improve performance for very large images.
- Add a more advanced layer and history system.

## 11. Conclusion

MyEditor meets the main project requirements. It provides a desktop GUI
workflow, implements all six mandatory OpenCV feature groups, and includes
advanced tools such as Cartoon Effect, Hough Lines Detection and GrabCut
background removal. The current report focuses on what is actually implemented
in the Flet version of the application. Separating GUI code from processing
modules makes the project easier to test, maintain and explain during code
review.
