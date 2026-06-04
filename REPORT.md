# MyEditor Report

## 1. Introduction

MyEditor is a small desktop image editor inspired by tools such as GIMP. The goal was to build a real application, not only separate image-processing scripts. The user can load an image, preview operations with GUI controls, apply edits, undo or redo changes, and save the final result.

The project uses Tkinter for the graphical interface and OpenCV for the image-processing algorithms. Tkinter keeps the interface simple to run on most machines, while OpenCV gives direct access to the required computer vision operations.

## 2. Architecture

The code is split into two main modules.

| File | Role |
| --- | --- |
| `myeditor/app.py` | Window layout, menus, dialogs, canvas display, mouse point selection, undo/redo |
| `myeditor/processing.py` | OpenCV functions for filters, transforms, stitching and advanced features |
| `main.py` | Starts the application |

This separation makes the code easier to explain in the code review. GUI code only gathers parameters and displays images. Processing code receives an image array and returns a new image array.

Images are stored as OpenCV BGR `numpy` arrays inside the application. For display, they are converted to RGB and shown on the Tkinter canvas with Pillow.

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

The project implements more than the required two advanced features:

| Feature | Technique |
| --- | --- |
| Gamma correction | Lookup table applied to all pixel values |
| Unsharp mask | Gaussian blur plus weighted image difference |
| Bilateral denoising | Edge-preserving smoothing |
| K-means color quantization | Pixel clustering in BGR color space |
| Cartoon effect | Bilateral filter plus adaptive edge mask |
| Pencil sketch | Grayscale inversion, blur and division blend |
| Vignette | Gaussian mask multiplied with the image |
| ORB keypoints | OpenCV ORB detector and keypoint drawing |
| Hough lines | Canny edges followed by probabilistic Hough transform |
| Connected components | Otsu thresholding followed by component labeling |
| Undo/redo | Stack of previous image states |

## 5. GUI and User Experience

The application opens into a real desktop window with menus, toolbar buttons, dialogs, sliders and a canvas. Slider-based operations show a live preview. For large images, the preview image is downscaled inside the dialog so sliders stay responsive; when the user clicks Apply, the operation is applied to the full-resolution image.

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
| ORB keypoints | `docs/demo_outputs/06_orb_keypoints.png` |
| Tilted document sample | `docs/demo_outputs/07_document_perspective_source.png` |
| Panorama stitching result | `docs/demo_outputs/08_panorama_result.png` |

For the final PDF report, add screenshots of the actual GUI while showing two or three of these operations.

## 7. Project Management

This table should match the GitHub commit history before submission. Names that are not known yet are kept as placeholders.

| Member | Main responsibility | Notes |
| --- | --- | --- |
| Zijie Huang | GUI workflow, image state management, Open/Save/Reset, Undo/Redo, user instructions | Responsible for the main user flow and documentation for running the app |
| Member 2 | Core OpenCV operations |  |
| Member 3 | Advanced features and samples |  |
| Member 4 | Report, testing, packaging |  |

Suggested Git workflow:

- One branch per feature
- Small commits for each operation or GUI screen
- Pull request review before merging
- README updated whenever setup or usage changes

## 8. Known Limitations

- Panorama stitching depends on the input images. Photos need enough overlap and texture.
- The affine transform assumes the three points are clicked in the requested order.
- The GUI is practical, but not as polished as a full Qt application.
- Very large images can still take time for heavy operations such as K-means.

## 9. Possible Improvements

- Add crop and rotate tools
- Add a brush mask for inpainting
- Add layers and blend modes
- Export filter recipes
- Package the application as a standalone executable

## 10. Conclusion

MyEditor covers all mandatory operations and adds several advanced features. The code is intentionally simple: each OpenCV operation is isolated in a small function, and the GUI calls those functions with values from menus, sliders or mouse selections. This makes the application usable for a demo and understandable for the individual code review.
