import numpy as np

from myeditor import processing


def sample_image():
    image = np.zeros((80, 100, 3), dtype=np.uint8)
    image[:, :50] = (40, 80, 160)
    image[:, 50:] = (220, 200, 120)
    image[20:60, 30:70] = (255, 255, 255)
    return image


def assert_same_size(result):
    assert result.shape == sample_image().shape
    assert result.dtype == np.uint8


def test_thresholds_return_color_images():
    image = sample_image()
    assert_same_size(processing.binary_threshold(image, 120))
    assert_same_size(processing.otsu_threshold(image))
    assert_same_size(processing.adaptive_threshold(image, 11, 2))


def test_equalization_and_edges_return_images():
    image = sample_image()
    assert_same_size(processing.equalize_global(image))
    assert_same_size(processing.equalize_clahe(image, 2.0, 8))
    assert_same_size(processing.canny_edges(image, 50, 150, 3))


def test_advanced_filters_return_images():
    image = sample_image()
    assert_same_size(processing.gamma_correction(image, 1.4))
    assert_same_size(processing.unsharp_mask(image, 1.0, 5))
    assert_same_size(processing.cartoon_effect(image))
    assert_same_size(processing.pencil_sketch(image))
    assert_same_size(processing.vignette(image, 0.4))


def test_perspective_warp_has_content():
    image = sample_image()
    points = [(10, 10), (90, 12), (88, 70), (12, 68)]
    result = processing.perspective_warp(image, points)
    assert result.size > 0
    assert result.dtype == np.uint8
