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
