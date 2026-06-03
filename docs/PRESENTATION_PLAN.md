# Oral Presentation Plan

## 1. Opening

- Project goal: a small GIMP-like desktop image editor
- Stack: Python, Tkinter, OpenCV, Pillow
- Demo image loaded in the GUI

## 2. Functional Demo

- Open and save image
- Thresholding: binary, Otsu, adaptive
- Histogram equalization: global and CLAHE
- Morphology with kernel controls
- Canny with two thresholds
- Perspective warp by clicking four points
- One or two advanced effects: cartoon, K-means, ORB or Hough lines
- Panorama stitching if sample images work well
- Undo and redo

## 3. Technical Explanation

- `app.py`: interface, dialogs, preview, canvas, mouse points
- `processing.py`: OpenCV functions
- Image format: BGR arrays in processing, RGB conversion only for display
- Live preview on a downscaled copy, full-resolution processing on Apply

## 4. Project Management

- Show the contribution table
- Explain branch / commit organization
- Mention main blockers and how they were solved

## 5. Conclusion

- Mandatory features completed
- More than two advanced features completed
- Limitations: stitching input quality, simple GUI design, heavy filters on very large images
- Next steps: crop tool, inpainting brush, layers

