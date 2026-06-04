import numpy as np

from myeditor import segmentation


def subject_on_background():
    # Bright square subject centered on a dark background.
    image = np.zeros((200, 200, 3), dtype=np.uint8)
    image[60:140, 60:140] = (240, 240, 240)
    rect = (50, 50, 100, 100)  # x, y, w, h around the subject
    return image, rect


def test_grabcut_mask_returns_binary_mask():
    image, rect = subject_on_background()
    mask = segmentation.grabcut_mask(image, rect)
    assert mask.shape == image.shape[:2]
    assert mask.dtype == np.uint8
    assert set(np.unique(mask)).issubset({0, 255})


def test_grabcut_mask_keeps_subject_drops_background():
    image, rect = subject_on_background()
    mask = segmentation.grabcut_mask(image, rect)
    assert mask[100, 100] == 255  # center of subject -> foreground
    assert mask[10, 10] == 0      # far corner -> background
