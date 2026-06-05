# Code Review Notes - Zijie Huang

My part focuses on the GUI workflow, image state management and user instructions.

## How the GUI Loads and Displays an Image

- The user chooses `File > Open`.
- The GUI calls `processing.read_image(path)` to load the file as an OpenCV BGR image.
- The loaded image is stored in two places:
  - `original_image`: the first loaded version, used by Reset
  - `image`: the current editable version
- For display, the GUI converts BGR to RGB and shows the image on the Tkinter canvas with Pillow.

## Image State

- `original_image` does not change after opening the file.
- `image` is the current edited image.
- `preview_image` is temporary and is used when a dialog shows a live preview.
- Reset copies `original_image` back into `image`.

## Apply and Cancel

- Parameter tools open a dialog with sliders.
- Moving a slider updates `preview_image`.
- `Apply` runs the processing function on the full image and saves the result as the current image.
- `Cancel` removes the preview and keeps the previous current image.

## Undo and Redo

- Before a new operation is applied, the current image is pushed into `undo_stack`.
- Undo moves the current image to `redo_stack` and restores the previous image.
- Redo restores an image from `redo_stack`.

## How the GUI Calls Processing Functions

- The GUI does not implement OpenCV algorithms directly.
- It collects parameters from menus, sliders or mouse clicks.
- Then it calls functions in `myeditor/processing.py`, for example thresholding, Canny, perspective warp or Hough lines.

## What to Say in Code Review

If the professor asks about my part, I should explain that I worked on making the application usable as a real image editor: opening an image, keeping track of original/current/preview states, applying or cancelling previews, supporting undo/redo, and writing clear usage instructions for the team demo.
