import os

import cv2
import numpy as np


def read_image(path):
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image: {path}")
    return image


def save_image(path, image):
    ext = os.path.splitext(str(path))[1]
    if not ext:
        ext = ".png"
    ok, data = cv2.imencode(ext, as_bgr(image))
    if not ok:
        raise ValueError(f"Could not save image as {ext}")
    data.tofile(str(path))


def as_bgr(image):
    if image is None:
        raise ValueError("No image loaded")
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return image.copy()


def gray_image(image):
    if image.ndim == 2:
        return image.copy()
    return cv2.cvtColor(as_bgr(image), cv2.COLOR_BGR2GRAY)


def odd_number(value, minimum=3):
    value = int(round(value))
    value = max(value, minimum)
    if value % 2 == 0:
        value += 1
    return value


def binary_threshold(image, threshold=127):
    gray = gray_image(image)
    _, result = cv2.threshold(gray, int(threshold), 255, cv2.THRESH_BINARY)
    return cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)


def otsu_threshold(image):
    gray = gray_image(image)
    _, result = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)


def adaptive_threshold(image, block_size=15, c_value=4):
    gray = gray_image(image)
    block_size = odd_number(block_size)
    result = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        int(c_value),
    )
    return cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)


def equalize_global(image):
    bgr = as_bgr(image)
    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    y, cr, cb = cv2.split(ycrcb)
    y = cv2.equalizeHist(y)
    return cv2.cvtColor(cv2.merge((y, cr, cb)), cv2.COLOR_YCrCb2BGR)


def equalize_clahe(image, clip_limit=2.0, tile_size=8):
    bgr = as_bgr(image)
    tile_size = max(int(tile_size), 2)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(
        clipLimit=max(float(clip_limit), 0.1),
        tileGridSize=(tile_size, tile_size),
    )
    l_channel = clahe.apply(l_channel)
    return cv2.cvtColor(cv2.merge((l_channel, a_channel, b_channel)), cv2.COLOR_LAB2BGR)


def morphology(image, operation="Open", kernel_size=5, kernel_shape="Rectangle"):
    shape_map = {
        "Rectangle": cv2.MORPH_RECT,
        "Ellipse": cv2.MORPH_ELLIPSE,
        "Cross": cv2.MORPH_CROSS,
    }
    operation_map = {
        "Dilate": cv2.MORPH_DILATE,
        "Erode": cv2.MORPH_ERODE,
        "Open": cv2.MORPH_OPEN,
        "Close": cv2.MORPH_CLOSE,
        "Gradient": cv2.MORPH_GRADIENT,
    }

    kernel_size = odd_number(kernel_size, minimum=1)
    shape = shape_map.get(kernel_shape, cv2.MORPH_RECT)
    op = operation_map.get(operation, cv2.MORPH_OPEN)
    kernel = cv2.getStructuringElement(shape, (kernel_size, kernel_size))
    result = cv2.morphologyEx(gray_image(image), op, kernel)
    return cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)


def canny_edges(image, low_threshold=80, high_threshold=160, aperture=3):
    low_threshold = int(low_threshold)
    high_threshold = int(high_threshold)
    if low_threshold > high_threshold:
        low_threshold, high_threshold = high_threshold, low_threshold
    aperture = int(aperture)
    if aperture not in (3, 5, 7):
        aperture = 3
    edges = cv2.Canny(gray_image(image), low_threshold, high_threshold, apertureSize=aperture)
    return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)


def affine_warp(image, points):
    if len(points) != 3:
        raise ValueError("Affine transform needs exactly 3 points")

    src = np.float32(points)
    width = max(int(np.linalg.norm(src[1] - src[0])), 2)
    height = max(int(np.linalg.norm(src[2] - src[0])), 2)
    dst = np.float32([[0, 0], [width - 1, 0], [0, height - 1]])
    matrix = cv2.getAffineTransform(src, dst)
    return cv2.warpAffine(as_bgr(image), matrix, (width, height))


def order_points(points):
    pts = np.array(points, dtype=np.float32)
    if len(pts) != 4:
        raise ValueError("Perspective transform needs exactly 4 points")

    rect = np.zeros((4, 2), dtype=np.float32)
    sums = pts.sum(axis=1)
    diffs = np.diff(pts, axis=1)

    rect[0] = pts[np.argmin(sums)]
    rect[2] = pts[np.argmax(sums)]
    rect[1] = pts[np.argmin(diffs)]
    rect[3] = pts[np.argmax(diffs)]
    return rect


def perspective_warp(image, points):
    rect = order_points(points)
    top_left, top_right, bottom_right, bottom_left = rect

    width_a = np.linalg.norm(bottom_right - bottom_left)
    width_b = np.linalg.norm(top_right - top_left)
    height_a = np.linalg.norm(top_right - bottom_right)
    height_b = np.linalg.norm(top_left - bottom_left)

    width = max(int(max(width_a, width_b)), 2)
    height = max(int(max(height_a, height_b)), 2)

    dst = np.float32(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]]
    )
    matrix = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(as_bgr(image), matrix, (width, height))


def stitch_images(paths):
    images = [read_image(path) for path in paths]
    if len(images) < 2:
        raise ValueError("Choose at least two images for stitching")

    stitcher = cv2.Stitcher_create()
    status, panorama = stitcher.stitch(images)
    if status != getattr(cv2, "Stitcher_OK", 0):
        raise RuntimeError(
            "Stitching failed. Try photos with more overlap and clear texture."
        )
    return panorama


def gamma_correction(image, gamma=1.2):
    gamma = max(float(gamma), 0.1)
    inverse = 1.0 / gamma
    table = ((np.arange(256) / 255.0) ** inverse * 255).astype(np.uint8)
    return cv2.LUT(as_bgr(image), table)


def unsharp_mask(image, amount=1.0, radius=5):
    bgr = as_bgr(image)
    radius = odd_number(radius, minimum=1)
    blurred = cv2.GaussianBlur(bgr, (radius, radius), 0)
    return cv2.addWeighted(bgr, 1.0 + float(amount), blurred, -float(amount), 0)


def bilateral_denoise(image, diameter=9, sigma_color=75, sigma_space=75):
    diameter = odd_number(diameter)
    return cv2.bilateralFilter(
        as_bgr(image),
        diameter,
        float(sigma_color),
        float(sigma_space),
    )


def kmeans_quantization(image, colors=8):
    bgr = as_bgr(image)
    colors = max(2, min(int(colors), 32))
    pixels = bgr.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, labels, centers = cv2.kmeans(
        pixels,
        colors,
        None,
        criteria,
        3,
        cv2.KMEANS_PP_CENTERS,
    )
    centers = centers.astype(np.uint8)
    result = centers[labels.flatten()]
    return result.reshape(bgr.shape)


def cartoon_effect(image):
    bgr = as_bgr(image)
    color = cv2.bilateralFilter(bgr, 9, 90, 90)
    gray = cv2.medianBlur(gray_image(bgr), 7)
    edges = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        9,
        2,
    )
    return cv2.bitwise_and(color, cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR))


def pencil_sketch(image):
    gray = gray_image(image)
    inverted = 255 - gray
    blurred = cv2.GaussianBlur(inverted, (21, 21), 0)
    sketch = cv2.divide(gray, 255 - blurred, scale=256)
    return cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)


def vignette(image, strength=0.5):
    bgr = as_bgr(image)
    rows, cols = bgr.shape[:2]
    strength = min(max(float(strength), 0.0), 1.0)

    x_kernel = cv2.getGaussianKernel(cols, cols * (0.6 - 0.35 * strength))
    y_kernel = cv2.getGaussianKernel(rows, rows * (0.6 - 0.35 * strength))
    mask = y_kernel @ x_kernel.T
    mask = mask / mask.max()
    mask = 1.0 - strength * (1.0 - mask)
    result = bgr.astype(np.float32) * mask[:, :, np.newaxis]
    return np.clip(result, 0, 255).astype(np.uint8)


def orb_keypoints(image, max_features=500):
    bgr = as_bgr(image)
    detector = cv2.ORB_create(nfeatures=int(max_features))
    keypoints = detector.detect(gray_image(bgr), None)
    return cv2.drawKeypoints(
        bgr,
        keypoints,
        None,
        color=(0, 255, 0),
        flags=cv2.DrawMatchesFlags_DRAW_RICH_KEYPOINTS,
    )


def hough_lines(image):
    bgr = as_bgr(image)
    edges = cv2.Canny(gray_image(bgr), 60, 180)
    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        threshold=70,
        minLineLength=40,
        maxLineGap=10,
    )
    result = bgr.copy()
    if lines is not None:
        for line in lines[:80]:
            x1, y1, x2, y2 = line[0]
            cv2.line(result, (x1, y1), (x2, y2), (0, 0, 255), 2)
    return result


def connected_components(image):
    gray = gray_image(image)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    count, labels = cv2.connectedComponents(binary)
    colors = np.random.default_rng(4).integers(0, 255, size=(count, 3), dtype=np.uint8)
    colors[0] = 0
    result = colors[labels]
    return result.astype(np.uint8)
