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


def cutout_transparent(image, mask):
    # Keep the colours, use the mask as an alpha channel: the background becomes
    # transparent once the result is saved as PNG.
    bgra = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    bgra[:, :, 3] = mask
    return bgra


def fill_background(image, mask, color):
    # Replace every background pixel with a single solid colour, keep the subject.
    result = image.copy()
    result[mask == 0] = color
    return result


def blur_background(image, mask, strength=21):
    # Blur the whole picture, then paste the sharp subject back on top (portrait look).
    kernel = strength if strength % 2 == 1 else strength + 1  # GaussianBlur needs odd size
    blurred = cv2.GaussianBlur(image, (kernel, kernel), 0)
    result = blurred.copy()
    result[mask == 255] = image[mask == 255]
    return result


def mask_preview(mask):
    # Turn the binary mask into a viewable 3-channel grayscale image.
    return cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)


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
