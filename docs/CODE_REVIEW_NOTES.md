# Code Review Notes - Zijie Huang

These notes are for my individual code review. My focus is the GUI workflow,
image state management, user instructions and explaining how the editor is used.

## 1. My Personal Contribution

My part is not to rewrite every OpenCV algorithm. My part is to understand and
explain how the application works as a real image editor:

- how the user opens and saves images
- how the original image, current image and preview image are managed
- how Reset, Undo and Redo work
- how parameter tools show a preview before Apply
- how the GUI calls the OpenCV functions in `processing.py`
- how the README and code review notes explain the workflow clearly

## 2. Project Architecture

The project separates GUI logic from image-processing logic.

| File | What it does |
| --- | --- |
| `main.py` | Starts the application by calling `run()` from `myeditor/app.py`. |
| `myeditor/app.py` | Flet GUI, tool panel, image display, preview workflow, mouse interaction, Open/Save/Reset and Undo/Redo. |
| `myeditor/processing.py` | OpenCV functions such as thresholding, CLAHE, morphology, Canny, transforms, stitching and filters. |
| `myeditor/scanner.py` | Document scan / crop and straighten helpers. |
| `myeditor/segmentation.py` | GrabCut background removal and mask helpers. |
| `tests/` | Unit tests for the non-GUI processing functions. |

In the current Flet version, the main editor class is called `MyEditor`. There is
no separate `ImageEditor` or `FilterDialog` class in the current code. The
preview dialog idea is implemented as a right-side tool panel through
`open_tool`, `update_preview`, `apply_filter` and `clear_tool`.

## 3. How `main.py` Starts the App

`main.py` is intentionally small:

```python
from myeditor.app import run

if __name__ == "__main__":
    run()
```

The `run()` function in `myeditor/app.py` starts Flet with `ft.app(...)`. This is
the entry point used by:

```bash
python3 main.py
```

## 4. How `MyEditor` Works

`MyEditor` builds the desktop window:

- top bar for Open, Save, Undo, Redo and Reset
- left panel for choosing tools
- center area for displaying the image
- right panel for tool parameters and Apply / Cancel
- status messages for user feedback
- mouse handling for point selection, crop, scan and GrabCut tools

The important idea is that `app.py` controls the workflow, while OpenCV work is
kept inside helper functions.

## 5. Image State Management

The main state variables are:

- `original_image`: a copy of the image when it is first opened. Reset uses this.
- `image`: the current edited image.
- `preview_image`: temporary image shown while changing sliders or before Apply.
- `undo_stack`: previous image states.
- `redo_stack`: image states that can be restored after Undo.

The display uses:

```python
return self.preview_image if self.preview_image is not None else self.image
```

So if a preview exists, the user sees the preview. If there is no preview, the
user sees the current image.

## 6. Open / Save / Reset Workflow

### Open Image

`open_image` uses the Flet file picker. It reads the selected path with:

```python
processing.read_image(path)
```

Then it stores:

- `self.image = image`
- `self.original_image = image.copy()`
- clears `preview_image`
- clears Undo and Redo stacks
- updates status and renders the image

### Save As

`save_image` first checks that an image is loaded. Then it uses a save file
picker and calls either:

- `processing.save_image(path, self.image)` for normal images
- `segmentation.save_cutout(path, self.image)` for BGRA cut-outs saved as PNG or
  another alpha-capable format

### Reset

`reset_image` checks whether `original_image` exists. If yes, it commits a copy
of the original image as the current image:

```python
self.commit_image(self.original_image.copy(), "Réinitialisé")
```

This means Reset is also undoable.

## 7. Apply / Cancel Workflow

Parameter tools call `open_tool(...)`. This creates sliders or dropdowns in the
right panel.

When a value changes:

1. `schedule_preview()` waits a very short time.
2. `update_preview()` runs the tool on a smaller preview image.
3. The result is stored in `preview_image`.
4. `render()` displays the preview.

When the user clicks **Appliquer**, `apply_filter()` runs the same processing
function on the full-size base image and calls `commit_image(...)`.

When the user clicks **Annuler**, `clear_tool()` removes the tool panel and
clears the preview. The current image is not changed.

## 8. Undo / Redo Workflow

`commit_image(result, action)` is the main method used after applying an edit.
Before replacing the current image, it pushes a copy of the current image into
`undo_stack`. Then it sets the new current image and clears `redo_stack`.

Undo:

1. push the current image to `redo_stack`
2. pop the last image from `undo_stack`
3. display it as the current image

Redo:

1. push the current image to `undo_stack`
2. pop the last image from `redo_stack`
3. display it as the current image

This is simple, but it is easy to explain and works well for this project.

## 9. BGR to RGB / Display Conversion

OpenCV stores normal color images in BGR order. Flet displays encoded image
bytes. The GUI converts the OpenCV image into a displayable PNG in `encode_png`.

For normal BGR images, the app converts from BGR to RGB before PNG encoding. For
BGRA cut-outs from GrabCut, the app keeps the alpha channel and uses a
checkerboard preview so transparency is visible.

## 10. How the GUI Calls `processing.py`

The GUI collects parameters from controls and then calls a processing function.

Examples:

- Thresholding calls `processing.binary_threshold`, `processing.otsu_threshold`
  or `processing.adaptive_threshold`.
- Histogram equalization calls `processing.equalize_global` or
  `processing.equalize_clahe`.
- Morphology calls `processing.morphology`.
- Canny calls `processing.canny_edges`.
- Affine and perspective tools call `processing.affine_warp` and
  `processing.perspective_warp` after mouse point selection.
- Panorama calls `processing.stitch_images`.

This is the architecture I should emphasize: GUI handles interaction,
`processing.py` handles OpenCV.

## 11. If the Professor Asks About Base Code Under My Name

I should answer honestly:

> My main work is around the GUI workflow documentation and understanding the
> editor state flow. I can explain how the app loads an image, stores original
> and current images, creates previews, applies or cancels edits, and manages
> Undo / Redo. I also updated the user-facing instructions so the project can be
> run and demonstrated clearly.

If asked about a specific OpenCV function, I should explain the workflow and the
function call, but I should not claim I wrote every algorithm unless it matches
my real commits.

## 12. What I Should Avoid Saying

- Do not say Magic Wand or Flood Fill is implemented. The current code has
  GrabCut background removal, not a separate Magic Wand tool.
- Do not say the GUI uses Tkinter or Pillow. The current version uses Flet.
- Do not claim teammate features unless they are merged and visible in the final
  code.
- Do not say Undo / Redo is an OpenCV algorithm. It is GUI state management.
- Do not over-explain the project as if it were a huge editor. It is a student
  OpenCV editor with clear mandatory features and some extra tools.
