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
