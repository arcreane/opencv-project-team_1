from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "demo_outputs"
sys.path.insert(0, str(ROOT))

from myeditor import processing


def write(name, image):
    OUT.mkdir(parents=True, exist_ok=True)
    processing.save_image(OUT / name, image)


def main():
    editor_image = processing.read_image(ROOT / "samples" / "editor_test.png")
    document = processing.read_image(ROOT / "samples" / "document_tilted.png")

    write("01_original.png", editor_image)
    write("02_otsu_threshold.png", processing.otsu_threshold(editor_image))
    write("03_clahe.png", processing.equalize_clahe(editor_image, 2.0, 8))
    write("04_canny.png", processing.canny_edges(editor_image, 70, 160, 3))
    write("05_cartoon.png", processing.cartoon_effect(editor_image))
    write("06_hough_lines.png", processing.hough_lines(editor_image))
    write("07_document_perspective_source.png", document)
    write(
        "08_panorama_result.png",
        processing.stitch_images(
            [
                ROOT / "samples" / "panorama_left.png",
                ROOT / "samples" / "panorama_right.png",
            ]
        ),
    )


if __name__ == "__main__":
    main()
