# MyEditor Report

## 1. Introduction

MyEditor is a small desktop image editor inspired by tools such as GIMP. The
goal was to build a real application, not only separate image-processing
scripts. The user can load an image, preview operations with GUI controls, apply
edits, undo or redo changes, reset the image and save the final result.

The project uses Flet for the graphical interface and OpenCV for the
image-processing algorithms. OpenCV images are stored as NumPy arrays in BGR
format. The GUI converts them only when they need to be displayed.

## 2. Architecture

The code is split into a few small modules.

| File | Role |
| --- | --- |
| `myeditor/app.py` | Flet window, left tool panel, image display, live preview, mouse tools, status messages and undo/redo |
| `myeditor/processing.py` | Main OpenCV functions for filters, transforms, stitching and advanced features |
| `myeditor/scanner.py` | Document detection and crop/straighten helpers |
| `myeditor/segmentation.py` | GrabCut background removal and mask helpers |
| `main.py` | Starts the application |

This separation makes the code easier to explain in the code review. GUI code
collects parameters and displays images. Processing code receives an image array
and returns a new image array.

The most important image states in the GUI are:

- `original_image`: the first image loaded by the user, used by Reset
- `image`: the current edited image
- `preview_image`: a temporary result shown before Apply
- `undo_stack` and `redo_stack`: previous image states for Undo and Redo

## 3. Core Features

### Thresholding

Three thresholding modes are implemented:

- Binary thresholding with a user-controlled intensity value
- Otsu thresholding, where OpenCV chooses the threshold automatically
- Adaptive thresholding, where the threshold is computed locally for each region

The output is converted back to BGR so it can be displayed and saved like the other operations.

### Histogram Equalization

Global equalization is applied to the luminance channel in YCrCb color space. This improves contrast without equalizing each color channel separately, which would create strong color shifts.

CLAHE is applied to the lightness channel in LAB color space. The user can control the clip limit and tile size. CLAHE is useful when the image has uneven lighting.

### Morphology

The application supports dilation, erosion, opening, closing and gradient. The user can choose the kernel size and shape: rectangle, ellipse or cross. The operation is applied to the grayscale image because morphology is usually easier to understand on intensity or binary structures.

### Canny Edge Detection

Canny edge detection exposes the two hysteresis thresholds and the aperture size. The output is a black-and-white edge map converted to BGR for display.

### Geometric Transforms

Affine transform uses three user-selected points. The points are selected directly on the canvas, then OpenCV maps them to a straight rectangle-like output.

Perspective warp uses four user-selected points. The program orders the corners automatically and uses a perspective matrix to straighten the selected area.

### Panorama Stitching

The panorama tool loads several images and uses OpenCV's stitcher. If the stitching status is not successful, the application shows a clear error message instead of crashing.

## 4. Advanced Features

The project focuses on three advanced features for the oral demo. These were
chosen because the visual result is clear and the code can be explained in a
short code review.

| Feature | Technique |
| --- | --- |
| Cartoon Effect | Bilateral filtering for smooth colors, then adaptive thresholding for edges |
| Hough Lines Detection | Canny edges followed by probabilistic Hough transform |
| Remove Background | GrabCut initialized by a rectangle, then refined with brush strokes |

Undo and Redo are kept in the GUI section because they are state management
features, not OpenCV algorithms.

## 5. GUI and User Experience

The application opens into a real desktop window with a top bar, a left tool
panel, a main image display and a right-side parameter panel. Slider-based
operations show a live preview. For large images, the preview is computed on a
downscaled copy so the sliders stay responsive; when the user clicks Apply, the
operation is applied to the full-resolution image.

Mouse interaction is used for geometric transforms. The selected points are drawn on the canvas so the user can see the current selection before the transform is applied.

## 6. Results

The `samples/` folder contains images used during development and demo preparation. The `docs/demo_outputs/` folder contains generated output examples:

| Result | File |
| --- | --- |
| Original sample | `docs/demo_outputs/01_original.png` |
| Otsu thresholding | `docs/demo_outputs/02_otsu_threshold.png` |
| CLAHE contrast enhancement | `docs/demo_outputs/03_clahe.png` |
| Canny edge detection | `docs/demo_outputs/04_canny.png` |
| Cartoon effect | `docs/demo_outputs/05_cartoon.png` |
| Hough line detection | `docs/demo_outputs/06_hough_lines.png` |
| Tilted document sample | `docs/demo_outputs/07_document_perspective_source.png` |
| Panorama stitching result | `docs/demo_outputs/08_panorama_result.png` |

The final oral demo should also show the real GUI, because the graphical
interface is a mandatory part of the project.

## 7. Project Management

This table follows the visible Git history and the merged feature branches.

| Member | Main responsibility | Notes |
| --- | --- | --- |
| Zijie Huang | Base editor work, GUI workflow notes, image state explanation, README/report polish | Focus on Open/Save/Reset, preview state, Undo/Redo and user instructions |
| Uncher | Crop & Straighten and GrabCut background removal work | Feature branches and commits under the Uncher account |
| Rayene Khader | Flet UI modernization, transform tools and before/after comparison | Merged Flet UI and transformer tool branches |
| BrendowDevX | Early package structure and core image-processing work | Early commits for main entry point, app structure, thresholding and histogram work |

Suggested Git workflow:

- One branch per feature
- Small commits for each operation or GUI screen
- Pull request review before merging
- README updated whenever setup or usage changes

## 8. Known Limitations

- Panorama stitching depends on the input images. Photos need enough overlap and texture.
- The affine transform assumes the three points are clicked in the requested order.
- GrabCut works best when the user selects a rectangle that contains the subject
  and some background.
- The GUI is practical for a student project, but not as complete as a full
  professional editor.
- Very large images can still take time for heavy operations such as K-means.

## 9. Possible Improvements

- Add a true Magic Wand / Flood Fill selection tool
- Add a brush mask for inpainting
- Add layers and blend modes
- Export filter recipes
- Package the application as a standalone executable

## 10. Conclusion

MyEditor covers all mandatory operations and adds several advanced features. The code is intentionally simple: each OpenCV operation is isolated in a small function, and the GUI calls those functions with values from menus, sliders or mouse selections. This makes the application usable for a demo and understandable for the individual code review.
