from pathlib import Path
import math
import random

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"


def save(image, name):
    SAMPLES.mkdir(exist_ok=True)
    if not cv2.imwrite(str(SAMPLES / name), image):
        raise ValueError(f"Could not write sample image: {name}")


def put_text(image, text, org, scale=0.8, color=(30, 30, 30), thickness=2):
    cv2.putText(
        image,
        text,
        org,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        thickness,
        cv2.LINE_AA,
    )


def make_editor_test():
    width, height = 900, 600
    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, height)
    xx, yy = np.meshgrid(x, y)
    blue = 150 + 70 * (1 - xx) * (1 - yy)
    green = 80 + 120 * yy
    red = 70 + 140 * xx
    image = np.dstack([blue, green, red]).astype(np.uint8)

    cv2.rectangle(image, (70, 70), (350, 260), (210, 232, 235), -1)
    cv2.rectangle(image, (70, 70), (350, 260), (40, 40, 40), 4)
    cv2.ellipse(image, (615, 205), (145, 125), 0, 0, 360, (80, 90, 220), -1)
    cv2.ellipse(image, (615, 205), (145, 125), 0, 0, 360, (45, 45, 45), 5)
    cv2.fillPoly(
        image,
        [np.array([(180, 420), (350, 330), (520, 430), (430, 520)], dtype=np.int32)],
        (130, 150, 60),
    )
    cv2.line(image, (55, 520), (830, 440), (255, 255, 255), 6, cv2.LINE_AA)
    cv2.line(image, (55, 540), (830, 470), (30, 30, 30), 3, cv2.LINE_AA)
    put_text(image, "contrast", (95, 125), scale=0.75)
    put_text(image, "edges + colors", (500, 365), scale=0.75, color=(255, 255, 255))

    rng = random.Random(8)
    for _ in range(450):
        px = rng.randrange(width)
        py = rng.randrange(height)
        image[py, px] = rng.choice([(255, 255, 255), (20, 20, 20), (60, 200, 240)])

    save(image, "editor_test.png")


def make_document():
    background = np.full((650, 900, 3), (82, 78, 72), dtype=np.uint8)
    doc = np.full((700, 520, 3), (236, 246, 248), dtype=np.uint8)
    cv2.rectangle(doc, (0, 0), (519, 699), (180, 196, 200), 6)
    put_text(doc, "MyEditor demo document", (55, 62), scale=0.75)

    y = 120
    for index in range(14):
        line_width = 360 + (index % 4) * 28
        cv2.rectangle(doc, (55, y), (55 + line_width, y + 8), (95, 82, 75), -1)
        y += 38
    cv2.rectangle(doc, (55, 585), (450, 620), (50, 50, 50), 3)

    center = (doc.shape[1] / 2, doc.shape[0] / 2)
    matrix = cv2.getRotationMatrix2D(center, -9, 1.0)
    cos = abs(matrix[0, 0])
    sin = abs(matrix[0, 1])
    new_w = int(doc.shape[0] * sin + doc.shape[1] * cos)
    new_h = int(doc.shape[0] * cos + doc.shape[1] * sin)
    matrix[0, 2] += new_w / 2 - center[0]
    matrix[1, 2] += new_h / 2 - center[1]
    rotated = cv2.warpAffine(doc, matrix, (new_w, new_h), borderValue=(82, 78, 72))

    x0, y0 = 195, -15
    y1 = max(0, y0)
    x1 = max(0, x0)
    src_y0 = max(0, -y0)
    src_x0 = max(0, -x0)
    h = min(background.shape[0] - y1, rotated.shape[0] - src_y0)
    w = min(background.shape[1] - x1, rotated.shape[1] - src_x0)
    if h > 0 and w > 0:
        background[y1:y1 + h, x1:x1 + w] = rotated[src_y0:src_y0 + h, src_x0:src_x0 + w]

    background = cv2.GaussianBlur(background, (3, 3), 0)
    save(background, "document_tilted.png")


def make_panorama():
    width, height = 1400, 520
    image = np.zeros((height, width, 3), dtype=np.uint8)

    for y in range(height):
        blend = y / height
        color = (
            int(225 - 90 * blend),
            int(185 - 55 * blend),
            int(120 + 55 * blend),
        )
        image[y, :] = color

    rng = random.Random(15)
    for x in range(60, width, 95):
        top = 260 + int(35 * math.sin(x / 90))
        color = (90 + rng.randrange(50), 120 + rng.randrange(40), 80 + rng.randrange(50))
        cv2.fillPoly(
            image,
            [np.array([(x - 120, height), (x + 30, top), (x + 180, height)], dtype=np.int32)],
            color,
        )

    for x in range(80, width, 120):
        building_height = rng.randrange(90, 190)
        color = (100 + rng.randrange(80), 80 + rng.randrange(80), 90 + rng.randrange(80))
        cv2.rectangle(image, (x, height - building_height), (x + 70, height - 40), color, -1)
        for wx in range(x + 10, x + 60, 20):
            for wy in range(height - building_height + 15, height - 60, 26):
                cv2.rectangle(image, (wx, wy), (wx + 8, wy + 10), (120, 220, 245), -1)

    for _ in range(180):
        x = rng.randrange(width)
        y = rng.randrange(60, 420)
        r = rng.randrange(2, 5)
        cv2.circle(image, (x, y), r, (245, 250, 250), -1, cv2.LINE_AA)

    save(image, "panorama_wide_reference.png")
    save(image[:, 0:900], "panorama_left.png")
    save(image[:, 500:1400], "panorama_right.png")


def make_grabcut_subject():
    width, height = 720, 540
    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, height)
    xx, yy = np.meshgrid(x, y)
    blue = 70 + 50 * (1 - yy)
    green = 120 + 90 * xx
    red = 40 + 60 * yy
    image = np.dstack([blue, green, red]).astype(np.uint8)

    rng = random.Random(21)
    for _ in range(600):
        px, py = rng.randrange(width), rng.randrange(height)
        image[py, px] = (
            rng.randrange(60, 160),
            rng.randrange(120, 220),
            rng.randrange(60, 200),
        )

    cv2.ellipse(image, (492, 270), (52, 62), 0, -60, 60, (20, 20, 120), 16)
    cv2.rectangle(image, (250, 170), (470, 400), (55, 60, 210), -1)
    cv2.rectangle(image, (250, 170), (470, 400), (20, 20, 120), 5)
    cv2.ellipse(image, (360, 168), (110, 35), 0, 0, 360, (70, 80, 225), -1)
    cv2.ellipse(image, (360, 168), (110, 35), 0, 0, 360, (20, 20, 120), 5)
    put_text(image, "MyEditor", (300, 285), scale=0.7, color=(230, 240, 255))

    save(image, "grabcut_subject.png")


def main():
    make_editor_test()
    make_document()
    make_panorama()
    make_grabcut_subject()


if __name__ == "__main__":
    main()
