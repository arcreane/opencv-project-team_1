import cv2
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


def labelled_image_and_mask():
    # Textured background (noise) so blurring it is visible, solid subject square.
    rng = np.random.default_rng(0)
    image = rng.integers(0, 255, (100, 100, 3), dtype=np.uint8)
    image[40:60, 40:60] = (10, 200, 50)
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[40:60, 40:60] = 255
    return image, mask


def test_cutout_transparent_uses_mask_as_alpha():
    image, mask = labelled_image_and_mask()
    result = segmentation.cutout_transparent(image, mask)
    assert result.shape == (100, 100, 4)
    assert np.array_equal(result[:, :, 3], mask)
    assert np.array_equal(result[50, 50, :3], image[50, 50])  # subject colour kept


def test_fill_background_replaces_background_only():
    image, mask = labelled_image_and_mask()
    result = segmentation.fill_background(image, mask, (255, 0, 0))
    assert tuple(result[10, 10]) == (255, 0, 0)            # background -> fill colour
    assert np.array_equal(result[50, 50], image[50, 50])   # subject untouched


def test_blur_background_keeps_subject_sharp():
    image, mask = labelled_image_and_mask()
    result = segmentation.blur_background(image, mask, strength=15)
    assert np.array_equal(result[50, 50], image[50, 50])       # subject untouched
    assert not np.array_equal(result[10, 10], image[10, 10])   # background blurred


def test_mask_preview_is_three_channel_grayscale():
    _, mask = labelled_image_and_mask()
    preview = segmentation.mask_preview(mask)
    assert preview.shape == (100, 100, 3)
    assert preview.dtype == np.uint8
    assert np.array_equal(preview[:, :, 0], mask)


def test_composite_checkerboard_shows_subject_over_pattern():
    image, mask = labelled_image_and_mask()
    bgra = segmentation.cutout_transparent(image, mask)
    preview = segmentation.composite_checkerboard(bgra)
    assert preview.shape == (100, 100, 3)
    assert preview.dtype == np.uint8
    assert np.array_equal(preview[50, 50], image[50, 50])          # subject kept
    assert tuple(preview[10, 10]) in {(255, 255, 255), (200, 200, 200)}  # transparent -> board


def test_refine_mask_applies_background_scribble():
    image, rect = subject_on_background()
    mask = segmentation.grabcut_mask(image, rect)
    assert mask[100, 100] == 255  # subject centre starts as foreground
    refined = segmentation.refine_mask(image, mask, fg_points=[], bg_points=[(100, 100)])
    assert refined[100, 100] == 0  # a background scribble forces it out


def test_refine_mask_returns_binary_mask():
    image, rect = subject_on_background()
    mask = segmentation.grabcut_mask(image, rect)
    refined = segmentation.refine_mask(image, mask, fg_points=[(100, 100)], bg_points=[])
    assert refined.shape == image.shape[:2]
    assert refined.dtype == np.uint8
    assert set(np.unique(refined)).issubset({0, 255})


def test_save_cutout_writes_png_with_alpha(tmp_path):
    image, mask = labelled_image_and_mask()
    bgra = segmentation.cutout_transparent(image, mask)
    out = tmp_path / "cutout.png"
    segmentation.save_cutout(str(out), bgra)
    reloaded = cv2.imread(str(out), cv2.IMREAD_UNCHANGED)
    assert reloaded.shape[2] == 4          # alpha channel preserved on disk
    assert reloaded[10, 10, 3] == 0        # background transparent
    assert reloaded[50, 50, 3] == 255      # subject opaque
