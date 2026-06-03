import cv2
import numpy as np


def order_corners(points):
    pts = np.array(points, dtype=np.float32)
    if len(pts) != 4:
        raise ValueError("Need exactly 4 points")

    ordered = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    ordered[0] = pts[np.argmin(s)]   # top-left
    ordered[2] = pts[np.argmax(s)]   # bottom-right
    ordered[1] = pts[np.argmin(d)]   # top-right
    ordered[3] = pts[np.argmax(d)]   # bottom-left
    return ordered


def _to_gray(image):
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _largest_quad(binary, area, min_area_ratio):
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            if cv2.contourArea(approx) >= min_area_ratio * area:
                return approx.reshape(4, 2).astype(np.float32)
    return None


def detect_document(image, min_area_ratio=0.2, work_width=600):
    # Detect on a downscaled copy: faster and more stable, then map corners back.
    height, width = image.shape[:2]
    scale = work_width / width if width > work_width else 1.0
    if scale != 1.0:
        small = cv2.resize(
            image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA
        )
    else:
        small = image

    gray = _to_gray(small)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    area = small.shape[0] * small.shape[1]

    # Strategy 1: edges from Canny (works when the document border is visible).
    edges = cv2.Canny(blurred, 60, 180)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    quad = _largest_quad(edges, area, min_area_ratio)

    # Strategy 2: Otsu threshold of page vs background (helps low-contrast scans).
    if quad is None:
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        quad = _largest_quad(thresh, area, min_area_ratio)

    if quad is None:
        return None
    return order_corners(quad / scale)


def four_point_transform(image, points):
    rect = order_corners(points)
    top_left, top_right, bottom_right, bottom_left = rect

    width_top = np.linalg.norm(top_right - top_left)
    width_bottom = np.linalg.norm(bottom_right - bottom_left)
    height_left = np.linalg.norm(bottom_left - top_left)
    height_right = np.linalg.norm(bottom_right - top_right)

    width = max(int(round(max(width_top, width_bottom))), 2)
    height = max(int(round(max(height_left, height_right))), 2)

    dst = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, matrix, (width, height))


def enhance_scan(warped, mode="bw"):
    if mode == "color":
        return warped
    gray = _to_gray(warped)
    if mode == "gray":
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    scanned = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10
    )
    return cv2.cvtColor(scanned, cv2.COLOR_GRAY2BGR)


def scan_document(image, enhance="bw"):
    corners = detect_document(image)
    if corners is None:
        raise ValueError("No document detected; select the four corners manually.")
    warped = four_point_transform(image, corners)
    return enhance_scan(warped, mode=enhance)
