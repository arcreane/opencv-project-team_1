import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageTk

from myeditor import processing, scanner, segmentation


RESAMPLE = getattr(Image, "Resampling", Image).LANCZOS
IMAGE_TYPES = [
    ("Image files", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"),
    ("All files", "*.*"),
]


class FilterDialog:
    def __init__(self, editor, title, controls, callback):
        self.editor = editor
        self.title = title
        self.controls = controls
        self.callback = callback
        self.base_image = editor.image.copy()
        self.preview_base = self.make_preview_base(self.base_image)
        self.vars = {}
        self.pending_update = None
        self.closed = False

        self.window = tk.Toplevel(editor.root)
        self.window.title(title)
        self.window.resizable(False, False)
        self.window.transient(editor.root)
        self.window.protocol("WM_DELETE_WINDOW", self.cancel)

        body = ttk.Frame(self.window, padding=12)
        body.grid(row=0, column=0, sticky="nsew")

        for row, control in enumerate(controls):
            ttk.Label(body, text=control["label"]).grid(row=row, column=0, sticky="w", pady=4)
            if control["type"] == "choice":
                var = tk.StringVar(value=control["value"])
                widget = ttk.OptionMenu(body, var, control["value"], *control["values"])
                widget.grid(row=row, column=1, sticky="ew", pady=4)
            else:
                var = tk.DoubleVar(value=control["value"])
                widget = tk.Scale(
                    body,
                    from_=control["from"],
                    to=control["to"],
                    resolution=control.get("resolution", 1),
                    orient="horizontal",
                    length=260,
                    variable=var,
                    command=lambda _value: self.schedule_preview(),
                )
                widget.grid(row=row, column=1, sticky="ew", pady=4)
            self.vars[control["name"]] = var
            var.trace_add("write", lambda *_args: self.schedule_preview())

        buttons = ttk.Frame(body)
        buttons.grid(row=len(controls), column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=self.cancel).grid(row=0, column=0, padx=4)
        ttk.Button(buttons, text="Apply", command=self.apply).grid(row=0, column=1, padx=4)

        body.columnconfigure(1, weight=1)
        self.update_preview()
        self.window.grab_set()

    def make_preview_base(self, image):
        height, width = image.shape[:2]
        max_side = max(height, width)
        if max_side <= 1100:
            return image
        scale = 1100 / max_side
        size = (max(1, int(width * scale)), max(1, int(height * scale)))
        return cv2.resize(image, size, interpolation=cv2.INTER_AREA)

    def values(self):
        return {name: var.get() for name, var in self.vars.items()}

    def schedule_preview(self):
        if self.closed:
            return
        if self.pending_update is not None:
            self.window.after_cancel(self.pending_update)
        self.pending_update = self.window.after(80, self.update_preview)

    def update_preview(self):
        if self.closed:
            return
        self.pending_update = None
        try:
            preview = self.callback(self.preview_base, self.values())
            self.editor.show_preview(preview, self.title)
        except Exception as error:
            self.editor.set_status(str(error))

    def apply(self):
        try:
            result = self.callback(self.base_image, self.values())
            self.closed = True
            self.window.destroy()
            self.editor.commit_image(result, self.title)
        except Exception as error:
            messagebox.showerror(self.title, str(error))

    def cancel(self):
        self.closed = True
        self.editor.clear_preview()
        self.window.destroy()


class ScanDialog:
    ENHANCE_MODES = {"B&W": "bw", "Color": "color", "Gray": "gray"}

    def __init__(self, editor):
        self.editor = editor
        self.enhance = tk.StringVar(value="B&W")
        self.tk_preview = None

        self.window = tk.Toplevel(editor.root)
        self.window.title("Crop & Straighten")
        self.window.resizable(False, False)
        self.window.transient(editor.root)
        self.window.protocol("WM_DELETE_WINDOW", self.cancel)

        body = ttk.Frame(self.window, padding=12)
        body.grid(row=0, column=0, sticky="nsew")
        ttk.Label(
            body,
            text="Drag the green corners on the image to fit the document.",
            wraplength=280,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        self.preview_label = ttk.Label(body)
        self.preview_label.grid(row=1, column=0, columnspan=2, pady=4)

        ttk.Label(body, text="Output").grid(row=2, column=0, sticky="w", pady=4)
        ttk.OptionMenu(
            body,
            self.enhance,
            "B&W",
            *self.ENHANCE_MODES,
            command=lambda _value: self.update_preview(),
        ).grid(row=2, column=1, sticky="ew", pady=4)

        buttons = ttk.Frame(body)
        buttons.grid(row=3, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=self.cancel).grid(row=0, column=0, padx=4)
        ttk.Button(buttons, text="Apply", command=self.apply).grid(row=0, column=1, padx=4)

        self.update_preview()

    def enhance_mode(self):
        return self.ENHANCE_MODES[self.enhance.get()]

    def build_result(self):
        warped = scanner.four_point_transform(self.editor.image, self.editor.scan_corners)
        return scanner.enhance_scan(warped, mode=self.enhance_mode())

    def update_preview(self):
        try:
            result = self.build_result()
        except Exception as error:
            self.editor.set_status(str(error))
            return
        rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb)
        pil_image.thumbnail((280, 280), RESAMPLE)
        self.tk_preview = ImageTk.PhotoImage(pil_image)
        self.preview_label.configure(image=self.tk_preview)

    def apply(self):
        try:
            result = self.build_result()
        except Exception as error:
            messagebox.showerror("Crop & Straighten", str(error))
            return
        self.window.destroy()
        self.editor.finish_scan(result)

    def cancel(self):
        self.window.destroy()
        self.editor.cancel_scan()


class GrabCutDialog:
    MODES = {
        "Transparent (PNG)": "transparent",
        "Background colour": "color",
        "Blur background": "blur",
        "Mask": "mask",
    }
    BRUSHES = {"Keep subject": "fg", "Remove area": "bg"}

    def __init__(self, editor):
        self.editor = editor
        self.mode = tk.StringVar(value="Transparent (PNG)")
        self.brush = tk.StringVar(value="Keep subject")
        self.blur_strength = tk.IntVar(value=25)
        self.fill_color = (255, 255, 255)  # BGR, default white
        self.tk_preview = None

        self.window = tk.Toplevel(editor.root)
        self.window.title("Remove Background (GrabCut)")
        self.window.resizable(False, False)
        self.window.transient(editor.root)
        self.window.protocol("WM_DELETE_WINDOW", self.cancel)

        body = ttk.Frame(self.window, padding=12)
        body.grid(row=0, column=0, sticky="nsew")
        ttk.Label(
            body,
            text="Pick how the background should look, then Apply. "
            "Transparent saves a PNG; the others edit the picture. "
            "Drag on the image with the touch-up brush to fix the cut-out.",
            wraplength=280,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        self.preview_label = ttk.Label(body)
        self.preview_label.grid(row=1, column=0, columnspan=2, pady=4)

        ttk.Label(body, text="Output").grid(row=2, column=0, sticky="w", pady=4)
        ttk.OptionMenu(
            body,
            self.mode,
            "Transparent (PNG)",
            *self.MODES,
            command=lambda _value: self.update_preview(),
        ).grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Label(body, text="Fill colour").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Button(body, text="Choose...", command=self.choose_color).grid(
            row=3, column=1, sticky="ew", pady=4
        )

        ttk.Label(body, text="Blur strength").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Scale(
            body,
            from_=5,
            to=61,
            variable=self.blur_strength,
            command=lambda _value: self.update_preview(),
        ).grid(row=4, column=1, sticky="ew", pady=4)

        ttk.Label(body, text="Touch-up brush").grid(row=5, column=0, sticky="w", pady=4)
        ttk.OptionMenu(body, self.brush, "Keep subject", *self.BRUSHES).grid(
            row=5, column=1, sticky="ew", pady=4
        )
        ttk.Button(body, text="Clear touch-ups", command=self.clear_touchups).grid(
            row=6, column=1, sticky="ew", pady=4
        )

        buttons = ttk.Frame(body)
        buttons.grid(row=7, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=self.cancel).grid(row=0, column=0, padx=4)
        ttk.Button(buttons, text="Apply", command=self.apply).grid(row=0, column=1, padx=4)

        self.update_preview()

    def mode_value(self):
        return self.MODES[self.mode.get()]

    def brush_value(self):
        return self.BRUSHES[self.brush.get()]

    def clear_touchups(self):
        self.editor.clear_grabcut_touchups()
        self.update_preview()

    def choose_color(self):
        rgb, _hex = colorchooser.askcolor(title="Background colour", parent=self.window)
        if rgb is not None:
            red, green, blue = (int(channel) for channel in rgb)
            self.fill_color = (blue, green, red)  # colorchooser gives RGB, OpenCV wants BGR
            self.mode.set("Background colour")
            self.update_preview()

    def build_result(self):
        image = self.editor.image
        mask = self.editor.grabcut_mask
        mode = self.mode_value()
        if mode == "transparent":
            return segmentation.cutout_transparent(image, mask)
        if mode == "color":
            return segmentation.fill_background(image, mask, self.fill_color)
        if mode == "blur":
            return segmentation.blur_background(image, mask, self.blur_strength.get())
        return segmentation.mask_preview(mask)

    def update_preview(self):
        result = self.build_result()
        if result.shape[2] == 4:  # BGRA: show the transparency over a checkerboard
            result = segmentation.composite_checkerboard(result)
        rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb)
        pil_image.thumbnail((280, 280), RESAMPLE)
        self.tk_preview = ImageTk.PhotoImage(pil_image)
        self.preview_label.configure(image=self.tk_preview)

    def apply(self):
        result = self.build_result()
        self.window.destroy()
        if self.mode_value() == "transparent":
            self.editor.export_cutout_png(result)
        else:
            self.editor.finish_grabcut(result)

    def cancel(self):
        self.window.destroy()
        self.editor.cancel_grabcut()


class ImageEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("MyEditor")
        self.root.minsize(960, 640)

        self.image = None
        self.original_image = None
        self.preview_image = None
        self.image_path = None
        self.undo_stack = []
        self.redo_stack = []

        self.tk_image = None
        self.view_scale = 1.0
        self.view_offset_x = 0
        self.view_offset_y = 0

        self.point_tool = None
        self.points = []

        self.scan_active = False
        self.scan_corners = []
        self.scan_drag_index = None
        self.scan_dialog = None

        self.grabcut_selecting = False
        self.grabcut_start = None
        self.grabcut_rect = None
        self.grabcut_mask = None
        self.grabcut_base_mask = None
        self.grabcut_fg_points = []
        self.grabcut_bg_points = []
        self.grabcut_dialog = None

        self.status_var = tk.StringVar(value="Open an image to start.")
        self.build_ui()
        self.bind_shortcuts()

    def build_ui(self):
        self.build_menu()

        toolbar = ttk.Frame(self.root, padding=(8, 6))
        toolbar.pack(side="top", fill="x")

        ttk.Button(toolbar, text="Open", command=self.open_image).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Save As", command=self.save_as).pack(side="left", padx=2)
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(toolbar, text="Undo", command=self.undo).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Redo", command=self.redo).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Reset", command=self.reset_image).pack(side="left", padx=2)
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(toolbar, text="Affine 3 pts", command=self.start_affine_tool).pack(
            side="left", padx=2
        )
        ttk.Button(toolbar, text="Perspective 4 pts", command=self.start_perspective_tool).pack(
            side="left", padx=2
        )
        ttk.Button(toolbar, text="Crop & Straighten", command=self.start_scan_tool).pack(
            side="left", padx=2
        )
        ttk.Button(toolbar, text="Remove Background", command=self.start_grabcut_tool).pack(
            side="left", padx=2
        )

        self.canvas = tk.Canvas(self.root, bg="#202124", highlightthickness=0)
        self.canvas.pack(side="top", fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self.render())
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        status = ttk.Label(self.root, textvariable=self.status_var, anchor="w", padding=(8, 4))
        status.pack(side="bottom", fill="x")

    def build_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_image)
        file_menu.add_command(label="Save As...", accelerator="Ctrl+S", command=self.save_as)
        file_menu.add_command(label="Stitch Panorama...", command=self.stitch_panorama)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=False)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=self.undo)
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=self.redo)
        edit_menu.add_command(label="Reset to Original", command=self.reset_image)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        core_menu = tk.Menu(menubar, tearoff=False)
        core_menu.add_command(label="Thresholding...", command=self.threshold_dialog)
        core_menu.add_command(label="Histogram Equalization...", command=self.equalization_dialog)
        core_menu.add_command(label="Morphology...", command=self.morphology_dialog)
        core_menu.add_command(label="Canny Edge Detection...", command=self.canny_dialog)
        core_menu.add_separator()
        core_menu.add_command(label="Affine From 3 Points", command=self.start_affine_tool)
        core_menu.add_command(label="Perspective Warp From 4 Points", command=self.start_perspective_tool)
        core_menu.add_command(label="Crop & Straighten (Scan)...", command=self.start_scan_tool)
        core_menu.add_command(label="Panorama / Stitching...", command=self.stitch_panorama)
        menubar.add_cascade(label="Core", menu=core_menu)

        advanced_menu = tk.Menu(menubar, tearoff=False)
        advanced_menu.add_command(label="Gamma Correction...", command=self.gamma_dialog)
        advanced_menu.add_command(label="Unsharp Mask...", command=self.unsharp_dialog)
        advanced_menu.add_command(label="Bilateral Denoising...", command=self.bilateral_dialog)
        advanced_menu.add_command(label="K-means Color Quantization...", command=self.kmeans_dialog)
        advanced_menu.add_command(label="Vignette...", command=self.vignette_dialog)
        advanced_menu.add_command(label="Remove Background (GrabCut)...", command=self.start_grabcut_tool)
        advanced_menu.add_separator()
        advanced_menu.add_command(label="Cartoon Effect", command=self.apply_cartoon)
        advanced_menu.add_command(label="Pencil Sketch", command=self.apply_pencil)
        advanced_menu.add_command(label="ORB Keypoints", command=self.apply_orb)
        advanced_menu.add_command(label="Hough Lines", command=self.apply_hough)
        advanced_menu.add_command(label="Connected Components", command=self.apply_components)
        menubar.add_cascade(label="Advanced", menu=advanced_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Feature List", command=self.show_features)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def bind_shortcuts(self):
        for key in ("<Control-o>", "<Command-o>"):
            self.root.bind(key, lambda _event: self.open_image())
        for key in ("<Control-s>", "<Command-s>"):
            self.root.bind(key, lambda _event: self.save_as())
        for key in ("<Control-z>", "<Command-z>"):
            self.root.bind(key, lambda _event: self.undo())
        for key in ("<Control-y>", "<Command-y>"):
            self.root.bind(key, lambda _event: self.redo())
        self.root.bind("<Escape>", lambda _event: self.on_escape())

    def set_status(self, text):
        self.status_var.set(text)

    def require_image(self):
        if self.image is None:
            messagebox.showinfo("MyEditor", "Open an image first.")
            return False
        return True

    def open_image(self):
        path = filedialog.askopenfilename(filetypes=IMAGE_TYPES)
        if not path:
            return
        try:
            image = processing.read_image(path)
        except Exception as error:
            messagebox.showerror("Open image", str(error))
            return

        self.image = image
        self.original_image = image.copy()
        self.image_path = path
        self.preview_image = None
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.cancel_point_tool(show_status=False)
        self.update_image_status("Loaded")
        self.render()

    def save_as(self):
        if not self.require_image():
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=IMAGE_TYPES,
        )
        if not path:
            return
        try:
            processing.save_image(path, self.image)
            self.set_status(f"Saved: {path}")
        except Exception as error:
            messagebox.showerror("Save image", str(error))

    def commit_image(self, image, action):
        if self.image is not None:
            self.undo_stack.append(self.image.copy())
            self.undo_stack = self.undo_stack[-25:]
        self.image = processing.as_bgr(image)
        if self.original_image is None:
            self.original_image = self.image.copy()
        self.preview_image = None
        self.redo_stack.clear()
        self.cancel_point_tool(show_status=False)
        self.update_image_status(action)
        self.render()

    def show_preview(self, image, action):
        self.preview_image = processing.as_bgr(image)
        height, width = self.preview_image.shape[:2]
        self.set_status(f"Preview: {action} ({width} x {height})")
        self.render()

    def clear_preview(self):
        self.preview_image = None
        self.update_image_status("Ready")
        self.render()

    def undo(self):
        if self.image is None or not self.undo_stack:
            self.set_status("Nothing to undo.")
            return
        self.redo_stack.append(self.image.copy())
        self.image = self.undo_stack.pop()
        self.preview_image = None
        self.update_image_status("Undo")
        self.render()

    def redo(self):
        if self.image is None or not self.redo_stack:
            self.set_status("Nothing to redo.")
            return
        self.undo_stack.append(self.image.copy())
        self.image = self.redo_stack.pop()
        self.preview_image = None
        self.update_image_status("Redo")
        self.render()

    def reset_image(self):
        if self.original_image is None:
            self.set_status("No original image.")
            return
        self.commit_image(self.original_image.copy(), "Reset to original")

    def update_image_status(self, action):
        if self.image is None:
            self.set_status("Open an image to start.")
            return
        height, width = self.image.shape[:2]
        self.set_status(f"{action}: {width} x {height}")

    def current_display_image(self):
        if self.preview_image is not None:
            return self.preview_image
        return self.image

    def render(self):
        self.canvas.delete("all")
        canvas_width = max(self.canvas.winfo_width(), 1)
        canvas_height = max(self.canvas.winfo_height(), 1)
        image = self.current_display_image()

        if image is None:
            self.canvas.create_text(
                canvas_width // 2,
                canvas_height // 2,
                fill="#dcdcdc",
                text="Open an image to start",
                font=("Helvetica", 18),
            )
            return

        height, width = image.shape[:2]
        scale = min(canvas_width / width, canvas_height / height, 1.0)
        display_width = max(1, int(width * scale))
        display_height = max(1, int(height * scale))
        self.view_scale = scale
        self.view_offset_x = (canvas_width - display_width) // 2
        self.view_offset_y = (canvas_height - display_height) // 2

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb).resize((display_width, display_height), RESAMPLE)
        self.tk_image = ImageTk.PhotoImage(pil_image)
        self.canvas.create_image(
            self.view_offset_x,
            self.view_offset_y,
            image=self.tk_image,
            anchor="nw",
        )
        self.draw_selected_points()
        if self.scan_active:
            self.draw_scan_overlay()
        if self.grabcut_rect is not None:
            self.draw_grabcut_overlay()

    def draw_selected_points(self):
        if not self.point_tool:
            return
        radius = 5
        screen_points = []
        for index, (x_pos, y_pos) in enumerate(self.points, start=1):
            sx = self.view_offset_x + x_pos * self.view_scale
            sy = self.view_offset_y + y_pos * self.view_scale
            screen_points.append((sx, sy))
            self.canvas.create_oval(
                sx - radius,
                sy - radius,
                sx + radius,
                sy + radius,
                outline="#ffffff",
                fill="#ffcc00",
                width=2,
            )
            self.canvas.create_text(
                sx + 10,
                sy - 10,
                text=str(index),
                fill="#ffffff",
                font=("Helvetica", 11, "bold"),
            )
        if len(screen_points) > 1:
            self.canvas.create_line(*screen_points, fill="#ffcc00", width=2)

    def canvas_to_image(self, event):
        image = self.current_display_image()
        if image is None or self.view_scale <= 0:
            return None
        x_pos = (event.x - self.view_offset_x) / self.view_scale
        y_pos = (event.y - self.view_offset_y) / self.view_scale
        height, width = image.shape[:2]
        if 0 <= x_pos < width and 0 <= y_pos < height:
            return (float(x_pos), float(y_pos))
        return None

    def on_canvas_click(self, event):
        if self.grabcut_selecting:
            self.grabcut_start = self._image_point_clamped(event)
            self.grabcut_rect = None
            return
        if self.grabcut_dialog is not None:
            self.grabcut_paint(event)
            return
        if self.scan_active:
            self.scan_drag_index = self.scan_hit_corner(event)
            return
        if not self.point_tool:
            return
        point = self.canvas_to_image(event)
        if point is None:
            return

        self.points.append(point)
        if self.point_tool == "scan_manual":
            if len(self.points) < 4:
                self.render()
                self.set_status(
                    f"Corner {len(self.points)} saved. Click corner {len(self.points) + 1}."
                )
                return
            corners = self.points
            self.point_tool = None
            self.points = []
            self.begin_scan_adjust(corners)
            return

        needed = 3 if self.point_tool == "affine" else 4
        if len(self.points) < needed:
            self.render()
            self.set_status(f"Point {len(self.points)} saved. Select point {len(self.points) + 1}.")
            return

        try:
            if self.point_tool == "affine":
                result = processing.affine_warp(self.image, self.points)
                title = "Affine transform"
            else:
                result = processing.perspective_warp(self.image, self.points)
                title = "Perspective warp"
            self.preview_image = result
            self.render()
            if messagebox.askyesno(title, "Apply this transform?"):
                self.commit_image(result, title)
            else:
                self.preview_image = None
                self.update_image_status("Transform cancelled")
                self.render()
        except Exception as error:
            messagebox.showerror("Transform", str(error))
        finally:
            self.point_tool = None
            self.points = []

    def start_affine_tool(self):
        if not self.require_image():
            return
        self.point_tool = "affine"
        self.points = []
        self.preview_image = None
        self.set_status("Affine: click top-left, top-right, then bottom-left.")
        self.render()

    def start_perspective_tool(self):
        if not self.require_image():
            return
        self.point_tool = "perspective"
        self.points = []
        self.preview_image = None
        self.set_status("Perspective: click the four corners of the area to straighten.")
        self.render()

    def cancel_point_tool(self, show_status=True):
        if self.point_tool and show_status:
            self.set_status("Point selection cancelled.")
        self.point_tool = None
        self.points = []
        self.render()

    def on_escape(self):
        if self.scan_active and self.scan_dialog is not None:
            self.scan_dialog.cancel()
            return
        if self.grabcut_dialog is not None:
            self.grabcut_dialog.cancel()
            return
        if self.grabcut_selecting:
            self.cancel_grabcut()
            return
        self.cancel_point_tool()

    def start_scan_tool(self):
        if not self.require_image():
            return
        self.cancel_point_tool(show_status=False)
        corners = scanner.detect_document(self.image)
        if corners is not None:
            self.set_status("Document detected. Drag the corners to adjust, then Apply.")
            self.begin_scan_adjust(corners.tolist())
        else:
            self.point_tool = "scan_manual"
            self.points = []
            self.preview_image = None
            self.set_status("No document found. Click the four corners of the document.")
            self.render()

    def begin_scan_adjust(self, corners):
        self.point_tool = None
        self.points = []
        self.scan_active = True
        self.scan_corners = [[float(x), float(y)] for x, y in corners]
        self.preview_image = None
        self.render()
        self.scan_dialog = ScanDialog(self)

    def scan_hit_corner(self, event):
        radius = 12
        for index, (x_pos, y_pos) in enumerate(self.scan_corners):
            sx = self.view_offset_x + x_pos * self.view_scale
            sy = self.view_offset_y + y_pos * self.view_scale
            if abs(event.x - sx) <= radius and abs(event.y - sy) <= radius:
                return index
        return None

    def on_canvas_drag(self, event):
        if self.grabcut_selecting and self.grabcut_start is not None:
            end = self._image_point_clamped(event)
            self.grabcut_rect = self._rect_from_points(self.grabcut_start, end)
            self.render()
            return
        if self.grabcut_dialog is not None:
            self.grabcut_paint(event)
            return
        if not self.scan_active or self.scan_drag_index is None:
            return
        if self.image is None or self.view_scale <= 0:
            return
        height, width = self.image.shape[:2]
        x_pos = min(max((event.x - self.view_offset_x) / self.view_scale, 0), width - 1)
        y_pos = min(max((event.y - self.view_offset_y) / self.view_scale, 0), height - 1)
        self.scan_corners[self.scan_drag_index] = [float(x_pos), float(y_pos)]
        self.render()
        if self.scan_dialog is not None:
            self.scan_dialog.update_preview()

    def on_canvas_release(self, _event):
        if self.grabcut_selecting:
            self.finish_grabcut_selection()
            return
        if self.grabcut_dialog is not None:
            self.apply_grabcut_refine()
            return
        self.scan_drag_index = None

    def draw_scan_overlay(self):
        screen = []
        for x_pos, y_pos in self.scan_corners:
            sx = self.view_offset_x + x_pos * self.view_scale
            sy = self.view_offset_y + y_pos * self.view_scale
            screen.append((sx, sy))
        if len(screen) == 4:
            flat = [value for point in screen for value in point]
            self.canvas.create_polygon(*flat, outline="#00e0a0", fill="", width=2)
        for sx, sy in screen:
            radius = 7
            self.canvas.create_oval(
                sx - radius,
                sy - radius,
                sx + radius,
                sy + radius,
                outline="#ffffff",
                fill="#00e0a0",
                width=2,
            )

    def finish_scan(self, result):
        self.scan_active = False
        self.scan_corners = []
        self.scan_dialog = None
        self.commit_image(result, "Crop & Straighten")

    def cancel_scan(self):
        self.scan_active = False
        self.scan_corners = []
        self.scan_dialog = None
        self.update_image_status("Ready")
        self.render()

    def _image_point_clamped(self, event):
        # Canvas pixel -> image pixel, kept inside the image bounds.
        height, width = self.image.shape[:2]
        x_pos = min(max((event.x - self.view_offset_x) / self.view_scale, 0), width - 1)
        y_pos = min(max((event.y - self.view_offset_y) / self.view_scale, 0), height - 1)
        return (float(x_pos), float(y_pos))

    @staticmethod
    def _rect_from_points(start, end):
        # Two opposite corners -> (x, y, w, h), whatever the drag direction.
        x0, y0 = start
        x1, y1 = end
        x, y = int(min(x0, x1)), int(min(y0, y1))
        return (x, y, int(abs(x1 - x0)), int(abs(y1 - y0)))

    def start_grabcut_tool(self):
        if not self.require_image():
            return
        self.cancel_point_tool(show_status=False)
        self.grabcut_selecting = True
        self.grabcut_start = None
        self.grabcut_rect = None
        self.preview_image = None
        self.set_status("Drag a rectangle around the subject you want to keep.")
        self.render()

    def finish_grabcut_selection(self):
        self.grabcut_selecting = False
        rect = self.grabcut_rect
        if rect is None or rect[2] < 10 or rect[3] < 10:
            self.grabcut_rect = None
            self.set_status("Selection too small. Start again from Remove Background.")
            self.render()
            return
        self.set_status("Separating subject from background...")
        self.root.update_idletasks()
        try:
            self.grabcut_mask = segmentation.grabcut_mask(self.image, rect)
        except Exception as error:
            messagebox.showerror("Remove Background", str(error))
            self.grabcut_rect = None
            self.render()
            return
        self.grabcut_base_mask = self.grabcut_mask.copy()
        self.grabcut_fg_points = []
        self.grabcut_bg_points = []
        self.grabcut_dialog = GrabCutDialog(self)

    def finish_grabcut(self, result):
        self._reset_grabcut_state()
        self.commit_image(result, "Remove Background")

    def _reset_grabcut_state(self):
        self.grabcut_rect = None
        self.grabcut_mask = None
        self.grabcut_base_mask = None
        self.grabcut_fg_points = []
        self.grabcut_bg_points = []
        self.grabcut_dialog = None

    def cancel_grabcut(self):
        self.grabcut_selecting = False
        self.grabcut_start = None
        self.grabcut_rect = None
        self.grabcut_mask = None
        self.grabcut_base_mask = None
        self.grabcut_fg_points = []
        self.grabcut_bg_points = []
        self.grabcut_dialog = None
        self.update_image_status("Ready")
        self.render()

    def grabcut_paint(self, event):
        # Add a brush mark: green keeps the subject, red removes the area.
        point = self._image_point_clamped(event)
        if self.grabcut_dialog.brush_value() == "fg":
            self.grabcut_fg_points.append(point)
        else:
            self.grabcut_bg_points.append(point)
        self.render()

    def apply_grabcut_refine(self):
        if not self.grabcut_fg_points and not self.grabcut_bg_points:
            return
        try:
            self.grabcut_mask = segmentation.refine_mask(
                self.image,
                self.grabcut_base_mask,
                self.grabcut_fg_points,
                self.grabcut_bg_points,
            )
        except Exception as error:
            messagebox.showerror("Remove Background", str(error))
            return
        if self.grabcut_dialog is not None:
            self.grabcut_dialog.update_preview()

    def clear_grabcut_touchups(self):
        self.grabcut_fg_points = []
        self.grabcut_bg_points = []
        if self.grabcut_base_mask is not None:
            self.grabcut_mask = self.grabcut_base_mask.copy()
        self.render()

    def export_cutout_png(self, bgra):
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG image", "*.png")],
        )
        if not path:
            self.cancel_grabcut()
            return
        try:
            segmentation.save_cutout(path, bgra)
        except Exception as error:
            messagebox.showerror("Remove Background", str(error))
            self.cancel_grabcut()
            return
        self._reset_grabcut_state()
        self.set_status(f"Saved cut-out: {path}")
        self.render()

    def draw_grabcut_overlay(self):
        x, y, width, height = self.grabcut_rect
        sx = self.view_offset_x + x * self.view_scale
        sy = self.view_offset_y + y * self.view_scale
        self.canvas.create_rectangle(
            sx,
            sy,
            sx + width * self.view_scale,
            sy + height * self.view_scale,
            outline="#00e0a0",
            width=2,
        )
        self._draw_brush_points(self.grabcut_fg_points, "#33dd55")  # keep
        self._draw_brush_points(self.grabcut_bg_points, "#ff5555")  # remove

    def _draw_brush_points(self, points, color):
        radius = 3
        for x_pos, y_pos in points:
            cx = self.view_offset_x + x_pos * self.view_scale
            cy = self.view_offset_y + y_pos * self.view_scale
            self.canvas.create_oval(
                cx - radius, cy - radius, cx + radius, cy + radius, fill=color, outline=""
            )

    def open_filter(self, title, controls, callback):
        if not self.require_image():
            return
        FilterDialog(self, title, controls, callback)

    def threshold_dialog(self):
        controls = [
            {
                "type": "choice",
                "name": "mode",
                "label": "Mode",
                "values": ["Binary", "Otsu", "Adaptive"],
                "value": "Binary",
            },
            {
                "type": "scale",
                "name": "threshold",
                "label": "Binary threshold",
                "from": 0,
                "to": 255,
                "value": 127,
            },
            {
                "type": "scale",
                "name": "block_size",
                "label": "Adaptive block size",
                "from": 3,
                "to": 99,
                "value": 15,
            },
            {
                "type": "scale",
                "name": "c_value",
                "label": "Adaptive C",
                "from": -20,
                "to": 20,
                "value": 4,
            },
        ]

        def apply_filter(image, values):
            if values["mode"] == "Otsu":
                return processing.otsu_threshold(image)
            if values["mode"] == "Adaptive":
                return processing.adaptive_threshold(
                    image,
                    values["block_size"],
                    values["c_value"],
                )
            return processing.binary_threshold(image, values["threshold"])

        self.open_filter("Thresholding", controls, apply_filter)

    def equalization_dialog(self):
        controls = [
            {
                "type": "choice",
                "name": "mode",
                "label": "Mode",
                "values": ["Global", "CLAHE"],
                "value": "Global",
            },
            {
                "type": "scale",
                "name": "clip",
                "label": "CLAHE clip limit",
                "from": 0.5,
                "to": 8.0,
                "resolution": 0.1,
                "value": 2.0,
            },
            {
                "type": "scale",
                "name": "tile",
                "label": "CLAHE tile size",
                "from": 2,
                "to": 16,
                "value": 8,
            },
        ]

        def apply_filter(image, values):
            if values["mode"] == "CLAHE":
                return processing.equalize_clahe(image, values["clip"], values["tile"])
            return processing.equalize_global(image)

        self.open_filter("Histogram equalization", controls, apply_filter)

    def morphology_dialog(self):
        controls = [
            {
                "type": "choice",
                "name": "operation",
                "label": "Operation",
                "values": ["Dilate", "Erode", "Open", "Close", "Gradient"],
                "value": "Open",
            },
            {
                "type": "choice",
                "name": "shape",
                "label": "Kernel shape",
                "values": ["Rectangle", "Ellipse", "Cross"],
                "value": "Rectangle",
            },
            {
                "type": "scale",
                "name": "size",
                "label": "Kernel size",
                "from": 1,
                "to": 35,
                "value": 5,
            },
        ]

        def apply_filter(image, values):
            return processing.morphology(
                image,
                values["operation"],
                values["size"],
                values["shape"],
            )

        self.open_filter("Morphology", controls, apply_filter)

    def canny_dialog(self):
        controls = [
            {
                "type": "scale",
                "name": "low",
                "label": "Low threshold",
                "from": 0,
                "to": 255,
                "value": 80,
            },
            {
                "type": "scale",
                "name": "high",
                "label": "High threshold",
                "from": 0,
                "to": 255,
                "value": 160,
            },
            {
                "type": "choice",
                "name": "aperture",
                "label": "Aperture size",
                "values": ["3", "5", "7"],
                "value": "3",
            },
        ]

        def apply_filter(image, values):
            return processing.canny_edges(
                image,
                values["low"],
                values["high"],
                int(values["aperture"]),
            )

        self.open_filter("Canny edge detection", controls, apply_filter)

    def gamma_dialog(self):
        controls = [
            {
                "type": "scale",
                "name": "gamma",
                "label": "Gamma",
                "from": 0.2,
                "to": 3.0,
                "resolution": 0.1,
                "value": 1.2,
            }
        ]
        self.open_filter(
            "Gamma correction",
            controls,
            lambda image, values: processing.gamma_correction(image, values["gamma"]),
        )

    def unsharp_dialog(self):
        controls = [
            {
                "type": "scale",
                "name": "amount",
                "label": "Amount",
                "from": 0.0,
                "to": 3.0,
                "resolution": 0.1,
                "value": 1.0,
            },
            {
                "type": "scale",
                "name": "radius",
                "label": "Blur radius",
                "from": 1,
                "to": 25,
                "value": 5,
            },
        ]
        self.open_filter(
            "Unsharp mask",
            controls,
            lambda image, values: processing.unsharp_mask(
                image,
                values["amount"],
                values["radius"],
            ),
        )

    def bilateral_dialog(self):
        controls = [
            {
                "type": "scale",
                "name": "diameter",
                "label": "Diameter",
                "from": 3,
                "to": 21,
                "value": 9,
            },
            {
                "type": "scale",
                "name": "sigma",
                "label": "Sigma",
                "from": 10,
                "to": 160,
                "value": 75,
            },
        ]

        def apply_filter(image, values):
            return processing.bilateral_denoise(
                image,
                values["diameter"],
                values["sigma"],
                values["sigma"],
            )

        self.open_filter("Bilateral denoising", controls, apply_filter)

    def kmeans_dialog(self):
        controls = [
            {
                "type": "scale",
                "name": "colors",
                "label": "Number of colors",
                "from": 2,
                "to": 16,
                "value": 8,
            }
        ]
        self.open_filter(
            "K-means color quantization",
            controls,
            lambda image, values: processing.kmeans_quantization(image, values["colors"]),
        )

    def vignette_dialog(self):
        controls = [
            {
                "type": "scale",
                "name": "strength",
                "label": "Strength",
                "from": 0.0,
                "to": 1.0,
                "resolution": 0.05,
                "value": 0.45,
            }
        ]
        self.open_filter(
            "Vignette",
            controls,
            lambda image, values: processing.vignette(image, values["strength"]),
        )

    def run_simple_filter(self, title, function):
        if not self.require_image():
            return
        try:
            self.root.config(cursor="watch")
            self.root.update_idletasks()
            self.commit_image(function(self.image), title)
        except Exception as error:
            messagebox.showerror(title, str(error))
        finally:
            self.root.config(cursor="")

    def apply_cartoon(self):
        self.run_simple_filter("Cartoon effect", processing.cartoon_effect)

    def apply_pencil(self):
        self.run_simple_filter("Pencil sketch", processing.pencil_sketch)

    def apply_orb(self):
        self.run_simple_filter("ORB keypoints", processing.orb_keypoints)

    def apply_hough(self):
        self.run_simple_filter("Hough lines", processing.hough_lines)

    def apply_components(self):
        self.run_simple_filter("Connected components", processing.connected_components)

    def stitch_panorama(self):
        paths = filedialog.askopenfilenames(filetypes=IMAGE_TYPES)
        if not paths:
            return
        if len(paths) < 2:
            messagebox.showinfo("Panorama", "Choose at least two images.")
            return
        try:
            self.root.config(cursor="watch")
            self.root.update_idletasks()
            result = processing.stitch_images(paths)
            self.commit_image(result, "Panorama")
        except Exception as error:
            messagebox.showerror("Panorama", str(error))
        finally:
            self.root.config(cursor="")

    def show_features(self):
        messagebox.showinfo(
            "MyEditor feature list",
            "Core features:\n"
            "- binary, Otsu and adaptive thresholding\n"
            "- global histogram equalization and CLAHE\n"
            "- dilation, erosion, opening, closing and gradient\n"
            "- Canny edge detection\n"
            "- affine and perspective transforms with mouse points\n"
            "- panorama stitching\n\n"
            "Advanced features:\n"
            "- gamma correction, unsharp mask, bilateral denoising\n"
            "- K-means color quantization\n"
            "- cartoon, pencil sketch and vignette effects\n"
            "- ORB keypoints, Hough lines and connected components\n"
            "- undo / redo stack",
        )


def run():
    root = tk.Tk()
    ImageEditor(root)
    root.mainloop()
