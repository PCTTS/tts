"""Draw the placeholder table image (shown around the board until each arena gets its own background).

The custom rectangle table's image area (the white part) is 87.91 x 51.98 units, so the image keeps that ratio.
Writes misc/table-placeholder-v1.jpg.
"""
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

W = 2048
H = round(W * 51.98 / 87.91)
OUT = Path(__file__).resolve().parent.parent / "misc" / "table-placeholder-v1.jpg"


def main():
    base = (52, 62, 58)
    img = Image.new("RGB", (W, H), base)
    # soft vignette: lighter in the middle, darker toward the edges
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse([-W * 0.1, -H * 0.25, W * 1.1, H * 1.25], fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(W // 8))
    light = Image.new("RGB", (W, H), (74, 86, 80))
    img = Image.composite(light, img, glow)
    # faint grain so it doesn't look flat
    img = ImageChops.add(img, Image.effect_noise((W, H), 7).convert("RGB"), 1.0, -128)
    OUT.parent.mkdir(exist_ok=True)
    img.save(OUT, quality=92)
    print("wrote", OUT.relative_to(OUT.parent.parent), img.size)


if __name__ == "__main__":
    main()
