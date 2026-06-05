import os

import cv2
import numpy as np


def grabcut_mask(image, rect, iterations=5):
    # Separate subject from background using GrabCut, seeded by a rectangle.
    # The pixels inside rect start as probable foreground, outside as sure background;
    # GrabCut then refines two Gaussian mixture color models over a few iterations.
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    bg_model = np.zeros((1, 65), dtype=np.float64)
    fg_model = np.zeros((1, 65), dtype=np.float64)

    cv2.grabCut(image, mask, tuple(rect), bg_model, fg_model, iterations, cv2.GC_INIT_WITH_RECT)

    # GC_FGD / GC_PR_FGD -> subject, the rest -> background.
    binary = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0)
    return binary.astype(np.uint8)


def refine_mask(image, mask, fg_points, bg_points, radius=6, iterations=3, keep_rect=None):
    # Re-run GrabCut starting from the current mask, plus the user's scribbles:
    # foreground marks become sure-subject, background marks sure-background.
    gc_mask = np.where(mask == 255, cv2.GC_PR_FGD, cv2.GC_PR_BGD).astype(np.uint8)
    for x, y in fg_points:
        cv2.circle(gc_mask, (int(x), int(y)), radius, int(cv2.GC_FGD), -1)
    for x, y in bg_points:
        cv2.circle(gc_mask, (int(x), int(y)), radius, int(cv2.GC_BGD), -1)

    if keep_rect is not None:
        # Everything outside the original selection stays sure-background, so the
        # brush can never bring back an object the user never selected.
        rx, ry, rw, rh = keep_rect
        outside = np.ones(gc_mask.shape, dtype=bool)
        outside[ry:ry + rh, rx:rx + rw] = False
        gc_mask[outside] = cv2.GC_BGD

    # GrabCut needs both a foreground and a background sample; if the scribbles
    # wiped out one side, just honour the scribbles instead of crashing.
    has_fg = np.any((gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD))
    has_bg = np.any((gc_mask == cv2.GC_BGD) | (gc_mask == cv2.GC_PR_BGD))
    if has_fg and has_bg:
        bg_model = np.zeros((1, 65), dtype=np.float64)
        fg_model = np.zeros((1, 65), dtype=np.float64)
        cv2.grabCut(image, gc_mask, None, bg_model, fg_model, iterations, cv2.GC_INIT_WITH_MASK)

    binary = np.where((gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD), 255, 0)
    return binary.astype(np.uint8)


def refine_edge(mask, erode_px=1, blur=1):
    # GrabCut tends to keep a thin ring of background pixels around the subject
    # (the "white halo"). Erode the mask to drop that ring, then blur to soften
    # the edge into a clean anti-aliased alpha.
    if erode_px > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * erode_px + 1, 2 * erode_px + 1))
        mask = cv2.erode(mask, kernel)
    if blur > 0:
        mask = cv2.GaussianBlur(mask, (2 * blur + 1, 2 * blur + 1), 0)
    return mask


def cutout_transparent(image, mask):
    # Keep the colours, use the mask as an alpha channel: the background becomes
    # transparent once the result is saved as PNG.
    bgra = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    bgra[:, :, 3] = mask
    return bgra


def fill_background(image, mask, color):
    # Replace background pixels with a solid colour, keep the subject. Threshold at
    # the mid-point so a soft (anti-aliased) mask still splits cleanly into the two.
    result = image.copy()
    result[mask < 128] = color
    return result


def composite_checkerboard(bgra, square=10, light=255, dark=200):
    # Display helper: lay a BGRA cut-out over a gray checkerboard so the
    # transparent areas are visible on screen. Returns a plain BGR image.
    height, width = bgra.shape[:2]
    rows = (np.arange(height) // square)[:, None]
    cols = (np.arange(width) // square)[None, :]
    board = np.where((rows + cols) % 2 == 0, light, dark).astype(np.uint8)
    background = cv2.cvtColor(board, cv2.COLOR_GRAY2BGR).astype(np.float32)

    alpha = bgra[:, :, 3:4].astype(np.float32) / 255.0
    foreground = bgra[:, :, :3].astype(np.float32)
    blended = foreground * alpha + background * (1.0 - alpha)
    return blended.astype(np.uint8)


def save_cutout(path, bgra):
    # Save a BGRA cut-out as PNG, keeping the alpha (transparency) channel.
    # imencode + tofile handles non-ASCII paths, like the rest of the app.
    ext = os.path.splitext(str(path))[1] or ".png"
    ok, data = cv2.imencode(ext, bgra)
    if not ok:
        raise ValueError(f"Could not save image as {ext}")
    data.tofile(str(path))
