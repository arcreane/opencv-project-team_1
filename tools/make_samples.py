from pathlib import Path
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"


def save(image, name):
    SAMPLES.mkdir(exist_ok=True)
    image.save(SAMPLES / name)


def make_editor_test():
    width, height = 900, 600
    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, height)
    xx, yy = np.meshgrid(x, y)
    red = (70 + 140 * xx).astype(np.uint8)
    green = (80 + 120 * yy).astype(np.uint8)
    blue = (150 + 70 * (1 - xx) * (1 - yy)).astype(np.uint8)
    image = Image.fromarray(np.dstack([red, green, blue]), "RGB")

    draw = ImageDraw.Draw(image)
    draw.rectangle((70, 70, 350, 260), fill=(235, 232, 210), outline=(40, 40, 40), width=4)
    draw.ellipse((470, 80, 760, 330), fill=(220, 90, 80), outline=(45, 45, 45), width=5)
    draw.polygon([(180, 420), (350, 330), (520, 430), (430, 520)], fill=(60, 150, 130))
    draw.line((55, 520, 830, 440), fill=(255, 255, 255), width=6)
    draw.line((55, 540, 830, 470), fill=(30, 30, 30), width=3)
    draw.text((95, 115), "contrast", fill=(25, 25, 25))
    draw.text((500, 360), "edges + colors", fill=(255, 255, 255))

    random.seed(8)
    for _ in range(450):
        px = random.randrange(width)
        py = random.randrange(height)
        color = random.choice([(255, 255, 255), (20, 20, 20), (240, 200, 60)])
        draw.point((px, py), fill=color)

    save(image, "editor_test.png")


def make_document():
    background = Image.new("RGB", (900, 650), (72, 78, 82))
    doc = Image.new("RGB", (520, 700), (248, 246, 236))
    draw = ImageDraw.Draw(doc)
    draw.rectangle((0, 0, 519, 699), outline=(200, 196, 180), width=6)
    draw.text((55, 45), "MyEditor demo document", fill=(30, 30, 30))
    y = 120
    for index in range(14):
        line_width = 360 + (index % 4) * 28
        draw.rectangle((55, y, 55 + line_width, y + 8), fill=(75, 82, 95))
        y += 38
    draw.rectangle((55, 585, 450, 620), outline=(50, 50, 50), width=3)

    rotated = doc.rotate(-9, expand=True, fillcolor=(72, 78, 82))
    background.paste(rotated, (195, -15))
    background = background.filter(ImageFilter.GaussianBlur(0.3))
    save(background, "document_tilted.png")


def make_panorama():
    width, height = 1400, 520
    image = Image.new("RGB", (width, height), (140, 190, 225))
    draw = ImageDraw.Draw(image)

    for y in range(height):
        blend = y / height
        color = (
            int(120 + 55 * blend),
            int(185 - 55 * blend),
            int(225 - 90 * blend),
        )
        draw.line((0, y, width, y), fill=color)

    rng = random.Random(15)
    for x in range(60, width, 95):
        top = 260 + int(35 * math.sin(x / 90))
        color = (80 + rng.randrange(50), 120 + rng.randrange(40), 90 + rng.randrange(50))
        draw.polygon([(x - 120, height), (x + 30, top), (x + 180, height)], fill=color)

    for x in range(80, width, 120):
        building_height = rng.randrange(90, 190)
        color = (90 + rng.randrange(80), 80 + rng.randrange(80), 100 + rng.randrange(80))
        draw.rectangle((x, height - building_height, x + 70, height - 40), fill=color)
        for wx in range(x + 10, x + 60, 20):
            for wy in range(height - building_height + 15, height - 60, 26):
                draw.rectangle((wx, wy, wx + 8, wy + 10), fill=(245, 220, 120))

    for _ in range(180):
        x = rng.randrange(width)
        y = rng.randrange(60, 420)
        r = rng.randrange(2, 5)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(250, 250, 245))

    save(image, "panorama_wide_reference.png")
    save(image.crop((0, 0, 900, height)), "panorama_left.png")
    save(image.crop((500, 0, 1400, height)), "panorama_right.png")


def main():
    make_editor_test()
    make_document()
    make_panorama()


if __name__ == "__main__":
    main()
