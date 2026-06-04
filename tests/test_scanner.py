import cv2
import numpy as np

from myeditor import scanner


def document_image():
    image = np.zeros((300, 300, 3), dtype=np.uint8)
    corners = np.array([[60, 40], [250, 70], [240, 260], [40, 240]], dtype=np.int32)
    cv2.fillConvexPoly(image, corners, (255, 255, 255))
    return image, corners


def test_order_corners_orders_clockwise_from_top_left():
    pts = [[240, 260], [60, 40], [40, 240], [250, 70]]
    ordered = scanner.order_corners(pts)
    assert tuple(ordered[0]) == (60, 40)
    assert tuple(ordered[2]) == (240, 260)


def test_detect_document_finds_four_corners():
    image, _ = document_image()
    corners = scanner.detect_document(image)
    assert corners is not None
    assert corners.shape == (4, 2)


def test_detect_document_returns_none_on_blank():
    blank = np.zeros((200, 200, 3), dtype=np.uint8)
    assert scanner.detect_document(blank) is None


def test_four_point_transform_returns_image():
    image, corners = document_image()
    result = scanner.four_point_transform(image, corners)
    assert result.size > 0
    assert result.dtype == np.uint8


def test_scan_document_end_to_end():
    image, _ = document_image()
    result = scanner.scan_document(image)
    assert result.ndim == 3
    assert result.dtype == np.uint8


def test_detect_document_on_large_image_maps_to_full_res():
    image, _ = document_image()
    big = cv2.resize(image, (1200, 1200), interpolation=cv2.INTER_NEAREST)
    found = scanner.detect_document(big)
    assert found is not None
    # corners must be returned in full-resolution coordinates, not the work size
    assert found.max() > 700


def test_scan_document_raises_without_document():
    blank = np.zeros((200, 200, 3), dtype=np.uint8)
    try:
        scanner.scan_document(blank)
        assert False, "expected ValueError"
    except ValueError:
        pass
