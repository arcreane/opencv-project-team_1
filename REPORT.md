# MyEditor Final Report

## 1. Introduction

MyEditor is our multimedia final project. It is a desktop image editor inspired
by simple GIMP-like workflows. The goal was not to write isolated OpenCV
exercises, but to build an application where a user can open an image, choose a
tool, change parameters, preview the result, apply or cancel the operation, and
save the edited image.

The final version uses Python, Flet, OpenCV, NumPy and pytest. Flet is used for
the desktop graphical interface. OpenCV and NumPy are used for image operations.
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
| `samples/` | Sample images used for testing and demonstration. |

The main GUI class is `MyEditor` in `myeditor/app.py`. It does not directly
implement every OpenCV algorithm. It collects input from buttons, sliders,
dropdowns or mouse clicks, then calls functions from `processing.py`,
`scanner.py` or `segmentation.py`.

OpenCV images are stored as NumPy arrays in BGR format. The GUI converts images
only when they need to be displayed in the Flet image component.

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

The `commit_image()` method is the central part of the editing workflow. Before
replacing the current image, it saves the previous image in `undo_stack`. It
then updates `image`, clears `preview_image`, clears the redo history after a
new edit, closes the active tool panel, updates the Undo/Redo buttons, updates
the status message and renders the image again.

Reset copies `original_image` back into the current image through the same
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
supports dilation, erosion, opening, closing and gradient through
`cv2.morphologyEx`.

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

The panorama tool lets the user choose multiple images. It uses OpenCV's
Stitcher to find matching visual features and combine overlapping images. This
works best when the images have enough overlap and clear texture.

If stitching fails, the application catches the error and shows a clear message
instead of crashing. This is important because panorama stitching can fail when
there are not enough reliable matches.

## 5. Advanced and Extra Features

The application includes more tools than the minimum requirements. For the oral
demo, the strongest advanced features are Cartoon Effect, Hough Lines and
Remove Background with GrabCut. Other tools are still available in the
interface, but we do not present them as separate major research features.

| Feature | Implementation idea and use |
| --- | --- |
| Gamma correction | Uses a lookup table with `cv2.LUT` to brighten or darken midtones. |
| Unsharp mask | Uses Gaussian blur and weighted addition to make details sharper. |
| Bilateral denoising | Uses `cv2.bilateralFilter` to smooth noise while keeping edges more visible. |
| K-means color quantization | Uses `cv2.kmeans` to reduce the number of colors in an image. |
| Vignette | Builds a Gaussian mask and darkens the border area. |
| Cartoon effect | Combines bilateral filtering with an adaptive edge mask. |
| Pencil sketch | Uses grayscale inversion, blur and division blending to create a sketch-like result. |
| ORB keypoints | Uses `cv2.ORB_create` and draws detected keypoints on the image. |
| Hough lines | Uses Canny edges and `cv2.HoughLinesP` to draw straight line segments. |
| Connected components | Uses Otsu thresholding and `cv2.connectedComponents` to color separate regions. |
| Crop & Straighten / document scan | Detects a document-like quadrilateral, applies perspective correction and offers B&W, color or gray output. |
| Remove Background / GrabCut | Uses GrabCut with an initial rectangle and optional brush refinement. |
| Rotation | Supports quick 90/180 degree rotation and free-angle rotation. |
| Horizontal mirror | Uses `cv2.flip` to mirror the image left/right. |
| Vertical mirror | Uses `cv2.flip` to mirror the image top/bottom. |
| Crop | Lets the user draw a rectangle and keep only that region. |

The project does not implement a separate Magic Wand or Flood Fill selection
tool. Background removal is handled by the GrabCut workflow.

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

Screenshots still to add before exporting the final submitted PDF:

- [TODO: Insert screenshot of the main interface after opening an image]
- [TODO: Insert screenshot of Canny preview with the right-side parameters]
- [TODO: Insert screenshot of Thresholding or CLAHE result]
- [TODO: Insert screenshot of Morphology result]
- [TODO: Insert screenshot of Perspective or Crop & Straighten result]
- [TODO: Insert screenshot of an advanced effect such as Cartoon, Hough Lines or ORB]
- [TODO: Insert screenshot of the Before/After comparison mode]

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

At the last check, all tests passed.

## 8. Project Management and Contributions

We used Git branches and pull requests to separate work. The contribution table
below follows the visible repository history and should be confirmed by the team
before final submission.

| Member | Main contribution |
| --- | --- |
| Zijie Huang | Focused on GUI workflow documentation, image state management explanation, Open/Save/Reset and Undo/Redo workflow, user instructions, README/report polishing, and code review preparation. |
| Uncher | Mainly contributed to GrabCut background removal and related selection workflow. |
| Rayene Khader | Mainly contributed to the Flet interface modernization, transform tools and before/after comparison work. |
| BrendowDevX | Mainly contributed to early project structure and core image-processing work. |

The main project management choice was to keep image-processing functions
separate from GUI code. This made it easier for team members to work on
different parts and also made code review easier.

TODO for the team: confirm the final wording of teammate names and
contributions before submitting the PDF.

## 9. Known Limitations

- Panorama stitching depends on overlap and visible features in the input images.
- Affine and perspective results depend on the user selecting correct points.
- GrabCut works best when the initial rectangle includes the full subject and enough background.
- K-means and other heavier tools can be slower on very large images.
- The project is a student image editor and is not as complete as professional tools such as GIMP or Photoshop.
- GUI testing is mostly manual.

## 10. Future Improvements

- Add more robust automated GUI tests.
- Add batch processing for applying a tool to several images.
- Add more precise selection tools.
- Add more export options.
- Improve performance for very large images.
- Add a more advanced layer and history system.

## 11. Conclusion

MyEditor meets the main requirements of the project. It is a real desktop image
editor with a GUI workflow, it implements all six mandatory OpenCV features, and
it includes several extra tools. The current report focuses on what is actually
implemented in the Flet version of the application. The code remains organized
around a simple idea: `app.py` handles user interaction, and the processing
modules handle image operations.
