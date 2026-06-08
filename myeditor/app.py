"""MyEditor - Flet edition.

Modern desktop UI (Flet / Flutter) for the team's OpenCV image editor.
The image-processing code is unchanged: this module only drives the GUI and
calls into ``myeditor.processing`` and ``myeditor.scanner``.

Features (parity with the repository):
- Core: thresholding, histogram equalization, morphology, Canny,
  affine (3 points), perspective (4 points), Crop & Straighten (Scan),
  panorama stitching.
- Advanced: gamma, unsharp mask, bilateral denoise, K-means quantization,
  vignette, cartoon, pencil sketch, ORB keypoints, Hough lines,
  connected components.
- Undo / redo / reset, live preview, status bar, keyboard shortcuts.
"""

import asyncio
import os

import cv2
import numpy as np
import flet as ft

from myeditor import processing, scanner, segmentation


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")
ICON_PATH = os.path.join(ASSETS_DIR, "logo.ico")

# ---- Color palette (dark, modern) ----------------------------------------
BG = "#13151a"
PANEL = "#1b1e26"
STAGE = "#0e1014"
ACCENT = "#6c8cff"
SCAN_GREEN = (0, 224, 160)      # BGR for overlay
TEXT = "#e6e8ee"
MUTED = "#8b90a0"

PREVIEW_MAX_SIDE = 1100
UNDO_LIMIT = 25
IMG_EXTS = ["png", "jpg", "jpeg", "bmp", "tif", "tiff"]


def encode_png(bgr_image):
    """Encode a BGR OpenCV image to PNG bytes for ft.Image(src=...)."""
    ok, buffer = cv2.imencode(".png", bgr_image)
    if not ok:
        raise ValueError("Could not encode image for display")
    return buffer.tobytes()


BLANK_PNG = encode_png(np.zeros((1, 1, 3), dtype=np.uint8))


class MyEditor:
    def __init__(self, page: ft.Page):
        self.page = page

        # --- image state ---
        self.image = None
        self.original_image = None
        self.preview_image = None
        self.image_path = None
        self.undo_stack = []
        self.redo_stack = []

        # --- view / interaction state ---
        self.view_scale = 1.0
        self.stage_w = 760
        self.stage_h = 600

        # --- active filter tool state ---
        self.active_title = None
        self.active_callback = None
        self.active_controls = []
        self.control_widgets = {}
        self.base_image = None
        self.preview_base = None
        self._preview_future = None

        # --- geometry (point) tool state ---
        self.point_tool = None       # "affine" | "perspective" | None
        self.points = []
        self.pending_result = None

        # --- scanner state ---
        self.scan_active = False
        self.scan_corners = []       # list of [x, y] in image coordinates
        self.scan_drag_index = None
        self.scan_mode_widget = None
        self.scan_preview_img = None

        # --- grabcut (remove background) state ---
        self.grabcut_active = False
        self.grabcut_phase = None        # "select" | "refine"
        self.grabcut_rect = None         # (x, y, w, h) in image coordinates
        self.grabcut_rect_start = None
        self.grabcut_source = None       # full-res BGR snapshot
        self.grabcut_work = None         # downscaled copy GrabCut runs on
        self.grabcut_scale = 1.0
        self.grabcut_mask = None
        self.grabcut_base_mask = None
        self.grabcut_strokes = []        # committed strokes: list of (kind, points)
        self.grabcut_redo = []
        self.grabcut_stroke = []         # current stroke being drawn
        self.grabcut_mode_widget = None
        self.grabcut_brush_widget = None
        self.grabcut_color_widget = None
        self.grabcut_color_row = None
        self.grabcut_preview_img = None
        self.grabcut_undo_btn = None
        self.grabcut_redo_btn = None

        # --- crop state ---
        self.crop_active = False
        self.crop_rect = None
        self.crop_rect_start = None

        # --- before/after compare state ---
        self.compare_active = False
        self.compare_split = 0.5

        self.file_picker = ft.FilePicker()
        self.build()

    # ================================================================== UI
    def build(self):
        page = self.page
        page.title = "MyEditor"
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = BG
        page.padding = 0
        page.services.append(self.file_picker)

        page.window.width = 1280
        page.window.height = 820
        page.window.min_width = 980
        page.window.min_height = 640
        if os.path.exists(ICON_PATH):
            page.window.icon = ICON_PATH

        self.undo_btn = ft.IconButton(ft.Icons.UNDO, tooltip="Annuler (Ctrl+Z)",
                                      on_click=lambda e: self.undo(), disabled=True)
        self.redo_btn = ft.IconButton(ft.Icons.REDO, tooltip="Rétablir (Ctrl+Y)",
                                      on_click=lambda e: self.redo(), disabled=True)
        page.appbar = ft.AppBar(
            title=ft.Text("MyEditor", weight=ft.FontWeight.BOLD, color=TEXT),
            bgcolor=PANEL,
            toolbar_height=54,
            actions=[
                ft.IconButton(ft.Icons.FOLDER_OPEN, tooltip="Ouvrir (Ctrl+O)",
                              on_click=self.open_image),
                ft.IconButton(ft.Icons.SAVE, tooltip="Enregistrer sous (Ctrl+S)",
                              on_click=self.save_image),
                ft.VerticalDivider(width=8),
                self.undo_btn,
                self.redo_btn,
                ft.IconButton(ft.Icons.RESTART_ALT, tooltip="Réinitialiser",
                              on_click=lambda e: self.reset_image()),
                ft.VerticalDivider(width=8),
                ft.IconButton(ft.Icons.COMPARE, tooltip="Avant / Après",
                              on_click=lambda e: self.toggle_compare()),
                ft.Container(width=8),
            ],
        )

        left = ft.Container(
            width=240, bgcolor=PANEL,
            padding=ft.Padding.symmetric(vertical=12, horizontal=10),
            content=ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, controls=[
                self.section("FICHIER"),
                self.nav("Panorama (stitch)", ft.Icons.PANORAMA, self.stitch_panorama),
                self.section("CORE"),
                self.nav("Seuillage", ft.Icons.TONALITY, self.tool_threshold),
                self.nav("Égalisation", ft.Icons.BAR_CHART, self.tool_equalize),
                self.nav("Morphologie", ft.Icons.GRAIN, self.tool_morphology),
                self.nav("Contours (Canny)", ft.Icons.BLUR_ON, self.tool_canny),
                self.section("GÉOMÉTRIE"),
                self.nav("Affine (3 points)", ft.Icons.TRANSFORM,
                         lambda e: self.start_points("affine")),
                self.nav("Perspective (4 points)", ft.Icons.CROP_ROTATE,
                         lambda e: self.start_points("perspective")),
                self.nav("Crop & Straighten (Scan)", ft.Icons.DOCUMENT_SCANNER,
                         lambda e: self.start_scan()),
                self.section("TRANSFORMER"),
                self.nav("Rotation", ft.Icons.ROTATE_RIGHT,
                         lambda e: self.start_rotation()),
                self.nav("Miroir horizontal", ft.Icons.SWAP_HORIZ,
                         lambda e: self.apply_now("Miroir horizontal",
                                                  lambda im: processing.flip(im, True))),
                self.nav("Miroir vertical", ft.Icons.FLIP,
                         lambda e: self.apply_now("Miroir vertical",
                                                  lambda im: processing.flip(im, False))),
                self.nav("Recadrage (Crop)", ft.Icons.CROP,
                         lambda e: self.start_crop()),
                self.section("SÉLECTION"),
                self.nav("Remove Background (GrabCut)", ft.Icons.CONTENT_CUT,
                         lambda e: self.start_grabcut()),
                self.section("ADVANCED"),
                self.nav("Correction Gamma", ft.Icons.BRIGHTNESS_6, self.tool_gamma),
                self.nav("Netteté (Unsharp)", ft.Icons.DETAILS, self.tool_unsharp),
                self.nav("Débruitage bilatéral", ft.Icons.WATER_DROP, self.tool_bilateral),
                self.nav("Quantif. K-means", ft.Icons.PALETTE, self.tool_kmeans),
                self.nav("Vignette", ft.Icons.VIGNETTE, self.tool_vignette),
                self.nav("Cartoon", ft.Icons.BRUSH,
                         lambda e: self.simple_tool("Cartoon", processing.cartoon_effect)),
                self.nav("Croquis crayon", ft.Icons.EDIT,
                         lambda e: self.simple_tool("Croquis crayon", processing.pencil_sketch)),
                self.nav("Points-clés ORB", ft.Icons.SCATTER_PLOT,
                         lambda e: self.simple_tool("ORB keypoints", processing.orb_keypoints)),
                self.nav("Lignes de Hough", ft.Icons.TIMELINE,
                         lambda e: self.simple_tool("Lignes de Hough", processing.hough_lines)),
                self.nav("Composantes connexes", ft.Icons.BUBBLE_CHART,
                         lambda e: self.simple_tool("Composantes connexes",
                                                    processing.connected_components)),
            ]),
        )

        self.canvas_image = ft.Image(src=BLANK_PNG, fit=ft.BoxFit.CONTAIN,
                                     gapless_playback=True)
        self.gesture = ft.GestureDetector(
            content=self.canvas_image,
            on_tap_down=self.on_tap,
            on_pan_start=self.on_pan_start,
            on_pan_update=self.on_pan_update,
            on_pan_end=self.on_pan_end,
            drag_interval=30,
        )
        self.placeholder = ft.Text("Ouvrez une image pour commencer",
                                   color=MUTED, size=18)
        self.image_holder = ft.Container(content=self.placeholder,
                                         alignment=ft.Alignment.CENTER, expand=True)
        self.stage = ft.Container(
            content=self.image_holder, expand=True, bgcolor=STAGE,
            padding=ft.Padding.all(12), alignment=ft.Alignment.CENTER,
            on_size_change=self.on_stage_resize,
        )

        self.panel_column = ft.Column(spacing=14, scroll=ft.ScrollMode.AUTO)
        self.right_panel = ft.Container(
            width=312, bgcolor=PANEL, padding=ft.Padding.all(16),
            visible=False, content=self.panel_column,
        )

        self.status = ft.Text("Ouvrez une image pour commencer.", color=MUTED, size=12)
        status_bar = ft.Container(
            bgcolor=PANEL, padding=ft.Padding.symmetric(vertical=6, horizontal=14),
            content=self.status,
        )

        body = ft.Row([left, self.stage, self.right_panel], spacing=0, expand=True,
                      vertical_alignment=ft.CrossAxisAlignment.STRETCH)
        page.add(ft.Column([body, status_bar], spacing=0, expand=True))

        page.on_keyboard_event = self.on_keyboard

    def section(self, label):
        return ft.Container(
            padding=ft.Padding.only(top=14, bottom=2, left=4),
            content=ft.Text(label, size=11, weight=ft.FontWeight.BOLD, color=MUTED),
        )

    def nav(self, label, icon, handler):
        return ft.TextButton(
            content=ft.Row([ft.Icon(icon, size=18, color=ACCENT),
                            ft.Text(label, color=TEXT, size=13)], spacing=10),
            width=216, on_click=handler,
            style=ft.ButtonStyle(
                padding=ft.Padding.symmetric(vertical=8, horizontal=10),
                alignment=ft.Alignment.CENTER_LEFT,
                shape=ft.RoundedRectangleBorder(radius=8),
                overlay_color=ft.Colors.with_opacity(0.08, ACCENT),
            ),
        )

    # ================================================================ status
    def set_status(self, text):
        self.status.value = text
        self.page.update()

    def update_status(self, action):
        if self.image is None:
            self.set_status("Ouvrez une image pour commencer.")
            return
        h, w = self.image.shape[:2]
        self.set_status(f"{action} — {w} × {h} px")

    def show_error(self, title, message):
        dlg = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(str(message)),
            actions=[ft.TextButton("OK", on_click=lambda e: self.page.pop_dialog())],
        )
        self.page.show_dialog(dlg)

    def require_image(self):
        if self.image is None:
            self.show_error("MyEditor", "Ouvrez d'abord une image.")
            return False
        return True

    # ============================================================== rendering
    def on_stage_resize(self, e):
        self.stage_w = max(int(e.width) - 24, 60)
        self.stage_h = max(int(e.height) - 24, 60)
        self.render()

    def display_source(self):
        return self.preview_image if self.preview_image is not None else self.image

    def render(self):
        img = self.display_source()
        if img is None:
            self.image_holder.content = self.placeholder
            self.page.update()
            return

        if (self.compare_active and self.original_image is not None
                and self.image is not None):
            self.render_compare()
            return

        if img.ndim == 3 and img.shape[2] == 4:
            # BGRA cut-out: show it over a checkerboard so transparency is visible.
            bgr = segmentation.composite_checkerboard(img)
        else:
            bgr = processing.as_bgr(img)
        h, w = bgr.shape[:2]
        scale = min(self.stage_w / w, self.stage_h / h, 1.0)
        dw = max(1, int(w * scale))
        dh = max(1, int(h * scale))
        self.view_scale = scale

        disp = cv2.resize(bgr, (dw, dh), interpolation=cv2.INTER_AREA)
        if self.point_tool and self.points:
            disp = self.draw_points(disp, scale)
        if self.scan_active and self.scan_corners:
            disp = self.draw_scan_corners(disp, scale)
        if self.grabcut_active:
            disp = self.draw_grabcut_overlay(disp, scale)
        if self.crop_active and self.crop_rect:
            disp = self.draw_crop_overlay(disp, scale)

        self.canvas_image.src = encode_png(disp)
        self.canvas_image.width = dw
        self.canvas_image.height = dh
        self.image_holder.content = self.gesture
        self.page.update()

    def _as_display_bgr(self, img):
        if img.ndim == 3 and img.shape[2] == 4:
            return segmentation.composite_checkerboard(img)
        return processing.as_bgr(img)

    def render_compare(self):
        # Split view: left = original, right = current, with a draggable divider.
        current = self._as_display_bgr(self.image)
        h, w = current.shape[:2]
        original = cv2.resize(self._as_display_bgr(self.original_image), (w, h),
                              interpolation=cv2.INTER_AREA)
        scale = min(self.stage_w / w, self.stage_h / h, 1.0)
        dw = max(1, int(w * scale))
        dh = max(1, int(h * scale))
        self.view_scale = scale

        cur_disp = cv2.resize(current, (dw, dh), interpolation=cv2.INTER_AREA)
        org_disp = cv2.resize(original, (dw, dh), interpolation=cv2.INTER_AREA)
        split_x = int(min(max(self.compare_split, 0.0), 1.0) * dw)
        out = cur_disp.copy()
        out[:, :split_x] = org_disp[:, :split_x]
        cv2.line(out, (split_x, 0), (split_x, dh), (255, 255, 255), 2)
        cv2.putText(out, "AVANT", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (255, 255, 255), 2)
        text_size = cv2.getTextSize("APRES", cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
        cv2.putText(out, "APRES", (dw - text_size[0] - 8, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        self.canvas_image.src = encode_png(out)
        self.canvas_image.width = dw
        self.canvas_image.height = dh
        self.image_holder.content = self.gesture
        self.page.update()

    def draw_crop_overlay(self, disp, scale):
        out = disp.copy()
        x, y, w, h = self.crop_rect
        p1 = (int(x * scale), int(y * scale))
        p2 = (int((x + w) * scale), int((y + h) * scale))
        # Dim the area outside the crop rectangle, keep the inside bright.
        shade = out.copy()
        shade[:] = (shade[:] * 0.4).astype(np.uint8)
        shade[p1[1]:p2[1], p1[0]:p2[0]] = out[p1[1]:p2[1], p1[0]:p2[0]]
        cv2.rectangle(shade, p1, p2, (108, 140, 255), 2)
        return shade

    def draw_points(self, disp, scale):
        out = disp.copy()
        screen = [(int(x * scale), int(y * scale)) for (x, y) in self.points]
        for i in range(1, len(screen)):
            cv2.line(out, screen[i - 1], screen[i], (0, 204, 255), 2)
        for idx, (sx, sy) in enumerate(screen, start=1):
            cv2.circle(out, (sx, sy), 6, (0, 204, 255), -1)
            cv2.circle(out, (sx, sy), 6, (255, 255, 255), 2)
            cv2.putText(out, str(idx), (sx + 9, sy - 9),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        return out

    def draw_scan_corners(self, disp, scale):
        out = disp.copy()
        screen = [(int(x * scale), int(y * scale)) for (x, y) in self.scan_corners]
        if len(screen) == 4:
            cv2.polylines(out, [np.array(screen, dtype=np.int32)], True, SCAN_GREEN, 2)
        for sx, sy in screen:
            cv2.circle(out, (sx, sy), 7, SCAN_GREEN, -1)
            cv2.circle(out, (sx, sy), 7, (255, 255, 255), 2)
        return out

    # ============================================================ image state
    def commit_image(self, result, action):
        if self.image is not None:
            self.undo_stack.append(self.image.copy())
            self.undo_stack = self.undo_stack[-UNDO_LIMIT:]
        # Keep a BGRA cut-out as-is (transparency); otherwise normalise to BGR.
        if result.ndim == 3 and result.shape[2] == 4:
            self.image = result
        else:
            self.image = processing.as_bgr(result)
        if self.original_image is None:
            self.original_image = self.image.copy()
        self.preview_image = None
        self.redo_stack.clear()
        self.clear_tool(rerender=False)
        self.update_history_buttons()
        self.update_status(action)
        self.render()

    def undo(self):
        if not self.undo_stack:
            self.set_status("Rien à annuler.")
            return
        self.redo_stack.append(self.image.copy())
        self.image = self.undo_stack.pop()
        self.preview_image = None
        self.clear_tool(rerender=False)
        self.update_history_buttons()
        self.update_status("Annulé")
        self.render()

    def redo(self):
        if not self.redo_stack:
            self.set_status("Rien à rétablir.")
            return
        self.undo_stack.append(self.image.copy())
        self.image = self.redo_stack.pop()
        self.preview_image = None
        self.clear_tool(rerender=False)
        self.update_history_buttons()
        self.update_status("Rétabli")
        self.render()

    def reset_image(self):
        if self.original_image is None:
            self.set_status("Aucune image originale.")
            return
        self.commit_image(self.original_image.copy(), "Réinitialisé")

    def update_history_buttons(self):
        self.undo_btn.disabled = not self.undo_stack
        self.redo_btn.disabled = not self.redo_stack
        self.page.update()

    # =============================================================== file I/O
    async def open_image(self, e):
        files = await self.file_picker.pick_files(
            dialog_title="Ouvrir une image", allow_multiple=False,
            file_type=ft.FilePickerFileType.IMAGE)
        if not files:
            return
        path = files[0].path
        try:
            image = processing.read_image(path)
        except Exception as error:
            self.show_error("Ouvrir", error)
            return
        self.image = image
        self.original_image = image.copy()
        self.image_path = path
        self.preview_image = None
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.clear_tool(rerender=False)
        self.update_history_buttons()
        self.update_status("Image chargée")
        self.render()

    async def save_image(self, e):
        if not self.require_image():
            return
        path = await self.file_picker.save_file(
            dialog_title="Enregistrer l'image", file_name="export.png",
            allowed_extensions=IMG_EXTS)
        if not path:
            return
        try:
            alpha_formats = (".png", ".webp", ".tif", ".tiff")
            if (self.image.ndim == 3 and self.image.shape[2] == 4
                    and path.lower().endswith(alpha_formats)):
                segmentation.save_cutout(path, self.image)
            else:
                processing.save_image(path, self.image)
            self.set_status(f"Enregistré : {path}")
        except Exception as error:
            self.show_error("Enregistrer", error)

    async def stitch_panorama(self, e):
        files = await self.file_picker.pick_files(
            dialog_title="Choisir les images du panorama (>= 2)",
            allow_multiple=True, file_type=ft.FilePickerFileType.IMAGE)
        if not files:
            return
        if len(files) < 2:
            self.show_error("Panorama", "Choisissez au moins deux images.")
            return
        paths = [f.path for f in files]
        self.set_status("Assemblage du panorama… (cela peut prendre un instant)")
        try:
            result = processing.stitch_images(paths)
        except Exception as error:
            self.show_error("Panorama", error)
            return
        self.commit_image(result, "Panorama")

    # ========================================================== filter panel
    def clear_tool(self, rerender=True):
        self.active_title = None
        self.active_callback = None
        self.active_controls = []
        self.control_widgets = {}
        self.point_tool = None
        self.points = []
        self.pending_result = None
        self.scan_active = False
        self.scan_corners = []
        self.scan_drag_index = None
        self.scan_mode_widget = None
        self.scan_preview_img = None
        self.grabcut_active = False
        self.grabcut_phase = None
        self.grabcut_rect = None
        self.grabcut_rect_start = None
        self.grabcut_source = None
        self.grabcut_work = None
        self.grabcut_scale = 1.0
        self.grabcut_mask = None
        self.grabcut_base_mask = None
        self.grabcut_strokes = []
        self.grabcut_redo = []
        self.grabcut_stroke = []
        self.grabcut_mode_widget = None
        self.grabcut_brush_widget = None
        self.grabcut_color_widget = None
        self.grabcut_color_row = None
        self.grabcut_preview_img = None
        self.grabcut_undo_btn = None
        self.grabcut_redo_btn = None
        self.crop_active = False
        self.crop_rect = None
        self.crop_rect_start = None
        self.preview_image = None
        self.right_panel.visible = False
        if rerender:
            self.render()
        else:
            self.page.update()

    def open_tool(self, title, controls, callback, description=None):
        if not self.require_image():
            return
        self.clear_tool(rerender=False)
        self.active_title = title
        self.active_callback = callback
        self.active_controls = controls
        self.control_widgets = {}
        self.base_image = self.image.copy()
        self.preview_base = self.make_preview_base(self.base_image)

        body = [ft.Text(title, size=17, weight=ft.FontWeight.BOLD, color=TEXT)]
        if description:
            body.append(ft.Text(description, size=12, color=MUTED))

        for control in controls:
            if control["type"] == "choice":
                widget = ft.Dropdown(
                    label=control["label"], value=control["value"],
                    options=[ft.DropdownOption(text=v) for v in control["values"]],
                    on_select=lambda e: self.schedule_preview(),
                )
                self.control_widgets[control["name"]] = widget
                body.append(widget)
            else:
                res = control.get("resolution", 1)
                divisions = max(1, int(round((control["to"] - control["from"]) / res)))
                round_digits = 0 if res >= 1 else len(str(res).split(".")[-1])
                widget = ft.Slider(
                    min=control["from"], max=control["to"], value=control["value"],
                    divisions=divisions, round=round_digits, label="{value}",
                    active_color=ACCENT, on_change=lambda e: self.schedule_preview(),
                )
                self.control_widgets[control["name"]] = widget
                body.append(ft.Column(
                    [ft.Text(control["label"], size=12, color=MUTED), widget], spacing=0))

        body.append(ft.Container(height=6))
        body.append(self.action_buttons(self.apply_filter))
        self.panel_column.controls = body
        self.right_panel.visible = True
        self.update_preview()

    def action_buttons(self, apply_handler):
        return ft.Row([
            ft.TextButton("Annuler", on_click=lambda e: self.clear_tool()),
            ft.FilledButton("Appliquer", icon=ft.Icons.CHECK,
                            on_click=apply_handler,
                            style=ft.ButtonStyle(bgcolor=ACCENT)),
        ], alignment=ft.MainAxisAlignment.END, spacing=8)

    def make_preview_base(self, image):
        h, w = image.shape[:2]
        longest = max(h, w)
        if longest <= PREVIEW_MAX_SIDE:
            return image
        scale = PREVIEW_MAX_SIDE / longest
        size = (max(1, int(w * scale)), max(1, int(h * scale)))
        return cv2.resize(image, size, interpolation=cv2.INTER_AREA)

    def values(self):
        out = {}
        for control in self.active_controls:
            widget = self.control_widgets[control["name"]]
            value = widget.value
            if control["type"] != "choice":
                value = float(value)
            out[control["name"]] = value
        return out

    def schedule_preview(self):
        if self._preview_future is not None and not self._preview_future.done():
            self._preview_future.cancel()
        self._preview_future = self.page.run_task(self._preview_after_delay)

    async def _preview_after_delay(self):
        try:
            await asyncio.sleep(0.06)
        except asyncio.CancelledError:
            return
        self.update_preview()

    def update_preview(self):
        if self.active_callback is None or self.preview_base is None:
            return
        try:
            preview = self.active_callback(self.preview_base, self.values())
            self.preview_image = processing.as_bgr(preview)
            self.set_status(f"Aperçu : {self.active_title}")
            self.render()
        except Exception as error:
            self.set_status(str(error))

    def apply_filter(self, e):
        try:
            result = self.active_callback(self.base_image, self.values())
        except Exception as error:
            self.show_error(self.active_title or "Filtre", error)
            return
        self.commit_image(result, self.active_title)

    def simple_tool(self, title, function):
        self.open_tool(title, [], lambda image, values: function(image),
                       description="Effet sans réglage. Vérifiez l'aperçu puis appliquez.")

    # =============================================================== tools
    def tool_threshold(self, e):
        controls = [
            {"type": "choice", "name": "mode", "label": "Mode",
             "values": ["Binary", "Otsu", "Adaptive"], "value": "Binary"},
            {"type": "slider", "name": "threshold", "label": "Seuil binaire",
             "from": 0, "to": 255, "value": 127},
            {"type": "slider", "name": "block_size", "label": "Taille bloc (adaptatif)",
             "from": 3, "to": 99, "value": 15},
            {"type": "slider", "name": "c_value", "label": "Constante C (adaptatif)",
             "from": -20, "to": 20, "value": 4},
        ]

        def run(image, v):
            if v["mode"] == "Otsu":
                return processing.otsu_threshold(image)
            if v["mode"] == "Adaptive":
                return processing.adaptive_threshold(image, v["block_size"], v["c_value"])
            return processing.binary_threshold(image, v["threshold"])

        self.open_tool("Seuillage", controls, run)

    def tool_equalize(self, e):
        controls = [
            {"type": "choice", "name": "mode", "label": "Mode",
             "values": ["Global", "CLAHE"], "value": "Global"},
            {"type": "slider", "name": "clip", "label": "CLAHE clip limit",
             "from": 0.5, "to": 8.0, "resolution": 0.1, "value": 2.0},
            {"type": "slider", "name": "tile", "label": "CLAHE tile size",
             "from": 2, "to": 16, "value": 8},
        ]

        def run(image, v):
            if v["mode"] == "CLAHE":
                return processing.equalize_clahe(image, v["clip"], v["tile"])
            return processing.equalize_global(image)

        self.open_tool("Égalisation d'histogramme", controls, run)

    def tool_morphology(self, e):
        controls = [
            {"type": "choice", "name": "operation", "label": "Opération",
             "values": ["Dilate", "Erode", "Open", "Close", "Gradient"], "value": "Open"},
            {"type": "choice", "name": "shape", "label": "Forme du noyau",
             "values": ["Rectangle", "Ellipse", "Cross"], "value": "Rectangle"},
            {"type": "slider", "name": "size", "label": "Taille du noyau",
             "from": 1, "to": 35, "value": 5},
        ]
        self.open_tool("Morphologie", controls,
                       lambda image, v: processing.morphology(
                           image, v["operation"], v["size"], v["shape"]))

    def tool_canny(self, e):
        controls = [
            {"type": "slider", "name": "low", "label": "Seuil bas",
             "from": 0, "to": 255, "value": 80},
            {"type": "slider", "name": "high", "label": "Seuil haut",
             "from": 0, "to": 255, "value": 160},
            {"type": "choice", "name": "aperture", "label": "Aperture",
             "values": ["3", "5", "7"], "value": "3"},
        ]
        self.open_tool("Contours de Canny", controls,
                       lambda image, v: processing.canny_edges(
                           image, v["low"], v["high"], int(v["aperture"])))

    def tool_gamma(self, e):
        controls = [{"type": "slider", "name": "gamma", "label": "Gamma",
                     "from": 0.2, "to": 3.0, "resolution": 0.1, "value": 1.2}]
        self.open_tool("Correction Gamma", controls,
                       lambda image, v: processing.gamma_correction(image, v["gamma"]))

    def tool_unsharp(self, e):
        controls = [
            {"type": "slider", "name": "amount", "label": "Intensité",
             "from": 0.0, "to": 3.0, "resolution": 0.1, "value": 1.0},
            {"type": "slider", "name": "radius", "label": "Rayon de flou",
             "from": 1, "to": 25, "value": 5},
        ]
        self.open_tool("Masque de netteté", controls,
                       lambda image, v: processing.unsharp_mask(
                           image, v["amount"], v["radius"]))

    def tool_bilateral(self, e):
        controls = [
            {"type": "slider", "name": "diameter", "label": "Diamètre",
             "from": 3, "to": 21, "value": 9},
            {"type": "slider", "name": "sigma", "label": "Sigma",
             "from": 10, "to": 160, "value": 75},
        ]
        self.open_tool("Débruitage bilatéral", controls,
                       lambda image, v: processing.bilateral_denoise(
                           image, v["diameter"], v["sigma"], v["sigma"]))

    def tool_kmeans(self, e):
        controls = [{"type": "slider", "name": "colors", "label": "Nombre de couleurs",
                     "from": 2, "to": 16, "value": 8}]
        self.open_tool("Quantification K-means", controls,
                       lambda image, v: processing.kmeans_quantization(image, v["colors"]))

    def tool_vignette(self, e):
        controls = [{"type": "slider", "name": "strength", "label": "Intensité",
                     "from": 0.0, "to": 1.0, "resolution": 0.05, "value": 0.45}]
        self.open_tool("Vignette", controls,
                       lambda image, v: processing.vignette(image, v["strength"]))

    # ========================================================= geometry tools
    def start_points(self, mode):
        if not self.require_image():
            return
        self.clear_tool(rerender=False)
        self.point_tool = mode
        self.points = []
        self.active_title = ("Transformation affine" if mode == "affine"
                             else "Transformation perspective")
        if mode == "affine":
            instructions = ("Cliquez 3 points sur l'image :\n"
                            "1) haut-gauche\n2) haut-droit\n3) bas-gauche")
        else:
            instructions = ("Cliquez les 4 coins de la zone à redresser.\n"
                            "L'ordre est corrigé automatiquement.")
        self.build_points_panel(instructions, show_apply=False)
        self.render()

    def build_points_panel(self, instructions, show_apply):
        body = [
            ft.Text(self.active_title, size=17, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Text(instructions, size=12, color=MUTED),
            ft.Container(height=6),
        ]
        if show_apply:
            body.append(self.action_buttons(self.apply_geometry))
        else:
            body.append(ft.Row(
                [ft.TextButton("Annuler", on_click=lambda e: self.clear_tool())],
                alignment=ft.MainAxisAlignment.END))
        self.panel_column.controls = body
        self.right_panel.visible = True
        self.page.update()

    def on_tap(self, e):
        if not self.point_tool:
            return
        point = self.event_to_image(e)
        if point is None:
            return
        self.points.append(point)
        needed = 3 if self.point_tool == "affine" else 4

        if len(self.points) < needed:
            self.set_status(f"Point {len(self.points)} enregistré. "
                            f"Sélectionnez le point {len(self.points) + 1}.")
            self.render()
            return

        try:
            if self.point_tool == "affine":
                self.pending_result = processing.affine_warp(self.image, self.points)
            else:
                self.pending_result = processing.perspective_warp(self.image, self.points)
        except Exception as error:
            self.show_error(self.active_title, error)
            self.clear_tool()
            return

        self.preview_image = self.pending_result
        self.build_points_panel("Aperçu prêt. Appliquez ou annulez la transformation.",
                                show_apply=True)
        self.render()

    def apply_geometry(self, e):
        if self.pending_result is None:
            return
        self.commit_image(self.pending_result, self.active_title)

    def event_to_image(self, e):
        """Convert a gesture local position to clamped image coordinates."""
        lp = getattr(e, "local_position", None)
        if lp is None or self.view_scale <= 0 or self.image is None:
            return None
        x = lp.x / self.view_scale
        y = lp.y / self.view_scale
        h, w = self.image.shape[:2]
        if not (0 <= x < w and 0 <= y < h):
            return None
        return (float(x), float(y))

    # =============================================================== scanner
    def start_scan(self):
        if not self.require_image():
            return
        self.clear_tool(rerender=False)
        self.scan_active = True
        self.active_title = "Crop & Straighten"
        try:
            corners = scanner.detect_document(self.image)
        except Exception:
            corners = None
        if corners is not None:
            self.scan_corners = [[float(x), float(y)] for x, y in corners.tolist()]
            self.set_status("Document détecté. Glissez les coins, puis Appliquer.")
        else:
            h, w = self.image.shape[:2]
            mx, my = w * 0.08, h * 0.08
            self.scan_corners = [[mx, my], [w - mx, my], [w - mx, h - my], [mx, h - my]]
            self.set_status("Aucun document trouvé. Placez les 4 coins manuellement.")
        self.build_scan_panel()
        self.render()
        self.update_scan_preview()

    def build_scan_panel(self):
        self.scan_mode_widget = ft.Dropdown(
            label="Sortie", value="B&W",
            options=[ft.DropdownOption(text=t) for t in ("B&W", "Color", "Gray")],
            on_select=lambda e: self.update_scan_preview(),
        )
        self.scan_preview_img = ft.Image(src=BLANK_PNG, width=260,
                                         fit=ft.BoxFit.CONTAIN, gapless_playback=True)
        self.panel_column.controls = [
            ft.Text("Crop & Straighten", size=17, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Text("Glissez les coins verts sur l'image pour ajuster le document.",
                    size=12, color=MUTED),
            self.scan_mode_widget,
            ft.Container(content=self.scan_preview_img, alignment=ft.Alignment.CENTER),
            ft.Container(height=6),
            self.action_buttons(self.apply_scan),
        ]
        self.right_panel.visible = True
        self.page.update()

    def scan_enhance_mode(self):
        mapping = {"B&W": "bw", "Color": "color", "Gray": "gray"}
        widget = self.scan_mode_widget
        return mapping.get(widget.value if widget else "B&W", "bw")

    def build_scan_result(self):
        warped = scanner.four_point_transform(self.image, self.scan_corners)
        return scanner.enhance_scan(warped, mode=self.scan_enhance_mode())

    def update_scan_preview(self):
        if not self.scan_active or self.scan_preview_img is None:
            return
        try:
            result = self.build_scan_result()
        except Exception as error:
            self.set_status(str(error))
            return
        h, w = result.shape[:2]
        scale = min(260 / w, 260 / h, 1.0)
        thumb = cv2.resize(result, (max(1, int(w * scale)), max(1, int(h * scale))),
                           interpolation=cv2.INTER_AREA)
        self.scan_preview_img.src = encode_png(thumb)
        self.page.update()

    def apply_scan(self, e):
        try:
            result = self.build_scan_result()
        except Exception as error:
            self.show_error("Crop & Straighten", error)
            return
        self.commit_image(result, "Crop & Straighten")

    # ---- pan dispatch (compare slider / crop / scanner / grabcut) ----
    def on_pan_start(self, e):
        if self.compare_active:
            self.compare_pan(e)
        elif self.crop_active:
            self.crop_pan_start(e)
        elif self.scan_active:
            self.scan_pan_start(e)
        elif self.grabcut_active:
            self.grabcut_pan_start(e)

    def on_pan_update(self, e):
        if self.compare_active:
            self.compare_pan(e)
        elif self.crop_active:
            self.crop_pan_update(e)
        elif self.scan_active:
            self.scan_pan_update(e)
        elif self.grabcut_active:
            self.grabcut_pan_update(e)

    def on_pan_end(self, e):
        if self.crop_active:
            return
        if self.scan_active:
            self.scan_drag_index = None
        elif self.grabcut_active:
            self.grabcut_pan_end(e)

    def scan_pan_start(self, e):
        lp = getattr(e, "local_position", None)
        if lp is None or self.view_scale <= 0:
            return
        x = lp.x / self.view_scale
        y = lp.y / self.view_scale
        threshold = 18 / self.view_scale
        best, best_dist = None, threshold
        for index, (cx, cy) in enumerate(self.scan_corners):
            dist = ((cx - x) ** 2 + (cy - y) ** 2) ** 0.5
            if dist <= best_dist:
                best, best_dist = index, dist
        self.scan_drag_index = best

    def scan_pan_update(self, e):
        if self.scan_drag_index is None:
            return
        point = self.image_point_clamped(e)
        if point is None:
            return
        self.scan_corners[self.scan_drag_index] = [point[0], point[1]]
        self.render()
        self.update_scan_preview()

    def image_point_clamped(self, e):
        lp = getattr(e, "local_position", None)
        if lp is None or self.view_scale <= 0 or self.image is None:
            return None
        h, w = self.image.shape[:2]
        x = min(max(lp.x / self.view_scale, 0), w - 1)
        y = min(max(lp.y / self.view_scale, 0), h - 1)
        return (float(x), float(y))

    # =============================================================== grabcut
    @staticmethod
    def _rect_from_points(start, end):
        x0, y0 = start
        x1, y1 = end
        x, y = int(min(x0, x1)), int(min(y0, y1))
        return (x, y, int(abs(x1 - x0)), int(abs(y1 - y0)))

    @staticmethod
    def _grabcut_downscale(image, max_width=800):
        width = image.shape[1]
        if width <= max_width:
            return image, 1.0
        scale = max_width / width
        size = (int(width * scale), int(image.shape[0] * scale))
        return cv2.resize(image, size, interpolation=cv2.INTER_AREA), scale

    @staticmethod
    def _scale_rect(rect, scale):
        x, y, width, height = rect
        return (int(x * scale), int(y * scale),
                max(1, int(width * scale)), max(1, int(height * scale)))

    def start_grabcut(self):
        if not self.require_image():
            return
        self.clear_tool(rerender=False)
        self.grabcut_active = True
        self.grabcut_phase = "select"
        self.active_title = "Remove Background"
        self.grabcut_rect = None
        self.grabcut_rect_start = None
        self.set_status("Étape 1 : tracez (glisser) un rectangle autour du sujet.")
        self.panel_column.controls = [
            ft.Text("Remove Background", size=17, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Text("Étape 1 : tracez un rectangle autour du sujet à conserver "
                    "(maintenez et glissez sur l'image).", size=12, color=MUTED),
            ft.Container(height=6),
            ft.Row([ft.TextButton("Annuler", on_click=lambda e: self.clear_tool())],
                   alignment=ft.MainAxisAlignment.END),
        ]
        self.right_panel.visible = True
        self.render()

    def grabcut_pan_start(self, e):
        point = self.image_point_clamped(e)
        if point is None:
            return
        if self.grabcut_phase == "select":
            self.grabcut_rect_start = point
            self.grabcut_rect = None
        elif self.grabcut_phase == "refine":
            self.grabcut_stroke = [point]
            self.render()

    def grabcut_pan_update(self, e):
        point = self.image_point_clamped(e)
        if point is None:
            return
        if self.grabcut_phase == "select" and self.grabcut_rect_start is not None:
            self.grabcut_rect = self._rect_from_points(self.grabcut_rect_start, point)
            self.render()
        elif self.grabcut_phase == "refine":
            self.grabcut_stroke.append(point)
            self.render()

    def grabcut_pan_end(self, e):
        if self.grabcut_phase == "select":
            self.finish_grabcut_selection()
        elif self.grabcut_phase == "refine":
            self.commit_grabcut_stroke()

    def finish_grabcut_selection(self):
        rect = self.grabcut_rect
        if rect is None or rect[2] < 10 or rect[3] < 10:
            self.grabcut_rect = None
            self.set_status("Sélection trop petite. Recommencez le rectangle.")
            self.render()
            return
        self.set_status("Séparation du sujet et du fond…")
        self.page.update()
        source = processing.as_bgr(self.image)
        work, scale = self._grabcut_downscale(source)
        try:
            mask = segmentation.grabcut_mask(work, self._scale_rect(rect, scale))
        except Exception as error:
            self.show_error("Remove Background", error)
            self.clear_tool()
            return
        self.grabcut_source = source
        self.grabcut_work = work
        self.grabcut_scale = scale
        self.grabcut_mask = mask
        self.grabcut_base_mask = mask.copy()
        self.grabcut_strokes = []
        self.grabcut_redo = []
        self.grabcut_stroke = []
        self.grabcut_phase = "refine"
        self.build_grabcut_panel()
        self.update_grabcut_preview()

    def build_grabcut_panel(self):
        self.grabcut_mode_widget = ft.Dropdown(
            label="Sortie", value="Transparent (PNG)",
            options=[ft.DropdownOption(text=t)
                     for t in ("Transparent (PNG)", "Couleur de fond")],
            on_select=lambda e: self.on_grabcut_mode_change(),
        )
        self.grabcut_color_widget = ft.Dropdown(
            label="Couleur de fond", value="Blanc",
            options=[ft.DropdownOption(text=t)
                     for t in ("Blanc", "Noir", "Gris", "Vert", "Bleu", "Rouge")],
            on_select=lambda e: self.update_grabcut_preview(),
        )
        self.grabcut_color_row = ft.Container(content=self.grabcut_color_widget,
                                              visible=False)
        self.grabcut_brush_widget = ft.Dropdown(
            label="Pinceau de retouche", value="Effacer le fond",
            options=[ft.DropdownOption(text=t)
                     for t in ("Effacer le fond", "Restaurer le sujet")],
        )
        self.grabcut_undo_btn = ft.TextButton(
            "Annuler retouche", icon=ft.Icons.UNDO, disabled=True,
            on_click=lambda e: self.grabcut_undo_touchup())
        self.grabcut_redo_btn = ft.TextButton(
            "Rétablir", icon=ft.Icons.REDO, disabled=True,
            on_click=lambda e: self.grabcut_redo_touchup())
        self.grabcut_preview_img = ft.Image(src=BLANK_PNG, width=260,
                                            fit=ft.BoxFit.CONTAIN, gapless_playback=True)
        self.panel_column.controls = [
            ft.Text("Remove Background", size=17, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Text("Étape 2 : choisissez la sortie. Pour corriger, choisissez un "
                    "pinceau et glissez sur l'image.", size=12, color=MUTED),
            self.grabcut_mode_widget,
            self.grabcut_color_row,
            ft.Container(content=self.grabcut_preview_img, alignment=ft.Alignment.CENTER),
            self.grabcut_brush_widget,
            ft.Row([self.grabcut_undo_btn, self.grabcut_redo_btn], spacing=6),
            ft.Container(height=6),
            self.action_buttons(self.apply_grabcut),
        ]
        self.right_panel.visible = True
        self.page.update()

    def on_grabcut_mode_change(self):
        self.grabcut_color_row.visible = (self.grabcut_mode_value() == "color")
        self.update_grabcut_preview()
        self.page.update()

    def grabcut_mode_value(self):
        widget = self.grabcut_mode_widget
        return "color" if (widget and widget.value == "Couleur de fond") else "transparent"

    def grabcut_brush_value(self):
        widget = self.grabcut_brush_widget
        return "fg" if (widget and widget.value == "Restaurer le sujet") else "bg"

    def grabcut_fill_color(self):
        mapping = {"Blanc": (255, 255, 255), "Noir": (0, 0, 0), "Gris": (128, 128, 128),
                   "Vert": (0, 255, 0), "Bleu": (255, 0, 0), "Rouge": (0, 0, 255)}
        widget = self.grabcut_color_widget
        return mapping.get(widget.value if widget else "Blanc", (255, 255, 255))

    def grabcut_brush_radius(self):
        screen_px = 10
        return max(2, int(screen_px / max(self.view_scale, 1e-6) * self.grabcut_scale))

    def full_mask(self):
        if self.grabcut_mask is None:
            return None
        if self.grabcut_scale == 1.0:
            mask = self.grabcut_mask
        else:
            h, w = self.image.shape[:2]
            mask = cv2.resize(self.grabcut_mask, (w, h), interpolation=cv2.INTER_LINEAR)
        return segmentation.refine_edge(mask)

    def build_grabcut_result(self):
        image = self.grabcut_source
        mask = self.full_mask()
        if self.grabcut_mode_value() == "color":
            return segmentation.fill_background(image, mask, self.grabcut_fill_color())
        return segmentation.cutout_transparent(image, mask)

    def build_grabcut_display(self):
        work = self.grabcut_work
        mask = segmentation.refine_edge(self.grabcut_mask)
        if self.grabcut_mode_value() == "color":
            return segmentation.fill_background(work, mask, self.grabcut_fill_color())
        return segmentation.composite_checkerboard(
            segmentation.cutout_transparent(work, mask))

    def update_grabcut_preview(self):
        if not self.grabcut_active or self.grabcut_phase != "refine":
            return
        try:
            display = self.build_grabcut_display()
        except Exception as error:
            self.set_status(str(error))
            return
        h, w = self.image.shape[:2]
        self.preview_image = cv2.resize(display, (w, h), interpolation=cv2.INTER_NEAREST)
        dh, dw = display.shape[:2]
        scale = min(260 / dw, 260 / dh, 1.0)
        thumb = cv2.resize(display, (max(1, int(dw * scale)), max(1, int(dh * scale))),
                           interpolation=cv2.INTER_AREA)
        if self.grabcut_preview_img is not None:
            self.grabcut_preview_img.src = encode_png(thumb)
        self.render()

    def commit_grabcut_stroke(self):
        if not self.grabcut_stroke:
            return
        self.grabcut_strokes.append((self.grabcut_brush_value(), self.grabcut_stroke))
        self.grabcut_redo = []
        self.grabcut_stroke = []
        self.recompute_grabcut_mask()

    def recompute_grabcut_mask(self):
        scale = self.grabcut_scale
        fg = [(x * scale, y * scale) for kind, pts in self.grabcut_strokes
              if kind == "fg" for x, y in pts]
        bg = [(x * scale, y * scale) for kind, pts in self.grabcut_strokes
              if kind == "bg" for x, y in pts]
        if not fg and not bg:
            self.grabcut_mask = self.grabcut_base_mask.copy()
        else:
            try:
                self.grabcut_mask = segmentation.refine_mask(
                    self.grabcut_work, self.grabcut_base_mask, fg, bg,
                    radius=self.grabcut_brush_radius(),
                    keep_rect=self._scale_rect(self.grabcut_rect, scale))
            except Exception as error:
                self.show_error("Remove Background", error)
                return
        self.update_grabcut_history_buttons()
        self.update_grabcut_preview()

    def grabcut_undo_touchup(self):
        if not self.grabcut_strokes:
            return
        self.grabcut_redo.append(self.grabcut_strokes.pop())
        self.recompute_grabcut_mask()

    def grabcut_redo_touchup(self):
        if not self.grabcut_redo:
            return
        self.grabcut_strokes.append(self.grabcut_redo.pop())
        self.recompute_grabcut_mask()

    def update_grabcut_history_buttons(self):
        if self.grabcut_undo_btn is not None:
            self.grabcut_undo_btn.disabled = not self.grabcut_strokes
            self.grabcut_redo_btn.disabled = not self.grabcut_redo
            self.page.update()

    def apply_grabcut(self, e):
        try:
            result = self.build_grabcut_result()
        except Exception as error:
            self.show_error("Remove Background", error)
            return
        self.commit_image(result, "Remove Background")

    def draw_grabcut_overlay(self, disp, scale):
        out = disp.copy()
        if self.grabcut_phase == "select" and self.grabcut_rect:
            x, y, w, h = self.grabcut_rect
            cv2.rectangle(out, (int(x * scale), int(y * scale)),
                          (int((x + w) * scale), int((y + h) * scale)), SCAN_GREEN, 2)
        if self.grabcut_stroke:
            color = (85, 221, 51) if self.grabcut_brush_value() == "fg" else (85, 85, 255)
            for (px, py) in self.grabcut_stroke:
                cv2.circle(out, (int(px * scale), int(py * scale)), 3, color, -1)
        return out

    # =========================================================== transform
    def apply_now(self, title, function):
        # Apply an instant transform (no dialog), e.g. mirror.
        if not self.require_image():
            return
        try:
            result = function(self.image)
        except Exception as error:
            self.show_error(title, error)
            return
        self.commit_image(result, title)

    def start_rotation(self):
        if not self.require_image():
            return
        self.clear_tool(rerender=False)
        self.active_title = "Rotation"
        self.active_callback = lambda image, v: processing.rotate(image, v["angle"])
        self.active_controls = [{"type": "slider", "name": "angle",
                                 "label": "Angle libre (°)", "from": -180, "to": 180,
                                 "value": 0}]
        self.control_widgets = {}
        self.base_image = self.image.copy()
        self.preview_base = self.make_preview_base(self.base_image)
        slider = ft.Slider(min=-180, max=180, value=0, divisions=360, round=0,
                           label="{value}", active_color=ACCENT,
                           on_change=lambda e: self.schedule_preview())
        self.control_widgets["angle"] = slider
        self.panel_column.controls = [
            ft.Text("Rotation", size=17, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Text("Boutons rapides (90° / 180°) ou angle libre, puis Appliquer.",
                    size=12, color=MUTED),
            ft.Row([
                ft.OutlinedButton("⟲ 90°", on_click=lambda e: self.apply_quarter(1)),
                ft.OutlinedButton("⟳ 90°", on_click=lambda e: self.apply_quarter(3)),
                ft.OutlinedButton("180°", on_click=lambda e: self.apply_quarter(2)),
            ], spacing=6),
            ft.Column([ft.Text("Angle libre (°)", size=12, color=MUTED), slider],
                      spacing=0),
            ft.Container(height=6),
            self.action_buttons(self.apply_filter),
        ]
        self.right_panel.visible = True
        self.update_preview()

    def apply_quarter(self, steps):
        try:
            result = processing.rotate_quarter(self.base_image, steps)
        except Exception as error:
            self.show_error("Rotation", error)
            return
        self.commit_image(result, "Rotation")

    # ---- crop ----
    def start_crop(self):
        if not self.require_image():
            return
        self.clear_tool(rerender=False)
        self.crop_active = True
        self.crop_rect = None
        self.crop_rect_start = None
        self.active_title = "Recadrage"
        self.set_status("Tracez (glisser) le rectangle à conserver, puis Appliquer.")
        self.panel_column.controls = [
            ft.Text("Recadrage (Crop)", size=17, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Text("Tracez un rectangle sur l'image (maintenez et glissez), "
                    "puis Appliquer.", size=12, color=MUTED),
            ft.Container(height=6),
            self.action_buttons(self.apply_crop),
        ]
        self.right_panel.visible = True
        self.render()

    def crop_pan_start(self, e):
        point = self.image_point_clamped(e)
        if point is None:
            return
        self.crop_rect_start = point
        self.crop_rect = None

    def crop_pan_update(self, e):
        point = self.image_point_clamped(e)
        if point is None or self.crop_rect_start is None:
            return
        self.crop_rect = self._rect_from_points(self.crop_rect_start, point)
        self.render()

    def apply_crop(self, e):
        if self.crop_rect is None or self.crop_rect[2] < 5 or self.crop_rect[3] < 5:
            self.show_error("Recadrage", "Sélection trop petite. Tracez un rectangle.")
            return
        try:
            result = processing.crop(self.image, self.crop_rect)
        except Exception as error:
            self.show_error("Recadrage", error)
            return
        self.commit_image(result, "Recadrage")

    # ---- before / after compare ----
    def toggle_compare(self):
        if self.image is None or self.original_image is None:
            self.set_status("Ouvrez une image (et faites une modification) d'abord.")
            return
        if self.compare_active:
            self.compare_active = False
            self.set_status("Comparaison désactivée.")
            self.render()
            return
        self.clear_tool(rerender=False)
        self.compare_active = True
        self.compare_split = 0.5
        self.set_status("Avant / Après : glissez sur l'image pour déplacer la séparation.")
        self.render()

    def compare_pan(self, e):
        lp = getattr(e, "local_position", None)
        if lp is None or self.image is None or self.view_scale <= 0:
            return
        dw = max(1.0, self.image.shape[1] * self.view_scale)
        self.compare_split = min(max(lp.x / dw, 0.0), 1.0)
        self.render()

    # =============================================================== keyboard
    def on_keyboard(self, e):
        if not e.ctrl:
            return
        key = (e.key or "").lower()
        if key == "z":
            self.undo()
        elif key == "y":
            self.redo()
        elif key == "o":
            self.page.run_task(self.open_image, None)
        elif key == "s":
            self.page.run_task(self.save_image, None)


def main(page: ft.Page):
    MyEditor(page)


def run():
    ft.app(main, assets_dir=ASSETS_DIR)


if __name__ == "__main__":
    run()
