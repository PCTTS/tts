"""Draw the toolbar icons (original art). Writes ui/icons/<name>.png at 128x128."""
from pathlib import Path

from PIL import Image, ImageDraw

S, N = 4, 128  # draw at 4x, output N x N
INK = (24, 24, 28, 255)
OUT = Path(__file__).resolve().parent.parent / "ui" / "icons"


def canvas():
    img = Image.new("RGBA", (N * S, N * S), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def P(*v):
    return [x * S for x in v]


def save(img, name):
    OUT.mkdir(parents=True, exist_ok=True)
    img.resize((N, N), Image.LANCZOS).save(OUT / f"{name}.png")
    print("wrote ui/icons/" + name + ".png")


def pokeball():
    img, d = canvas()
    c, r = 64, 56
    d.ellipse(P(c - r, c - r, c + r, c + r), fill=INK)                         # outline
    d.pieslice(P(c - r + 6, c - r + 6, c + r - 6, c + r - 6), 180, 360, fill=(228, 52, 40, 255))  # red top
    d.pieslice(P(c - r + 6, c - r + 6, c + r - 6, c + r - 6), 0, 180, fill=(246, 246, 246, 255))  # white bottom
    d.ellipse(P(c - 40, c - 46, c - 14, c - 30), fill=(255, 140, 120, 255))   # shine
    d.rectangle(P(c - r + 4, c - 5, c + r - 4, c + 5), fill=INK)              # band
    d.ellipse(P(c - 19, c - 19, c + 19, c + 19), fill=INK)                     # button ring
    d.ellipse(P(c - 12, c - 12, c + 12, c + 12), fill=(246, 246, 246, 255))
    d.ellipse(P(c - 6, c - 6, c + 6, c + 6), outline=(190, 190, 190, 255), width=2 * S)
    save(img, "pokeball")


def folded_map():
    img, d = canvas()
    # three panels folded in a zigzag
    xs, top, bot, dip = [10, 46, 82, 118], 22, 106, 8
    shades = [(242, 226, 178, 255), (222, 202, 150, 255), (242, 226, 178, 255)]
    # each fold goes down then up: panel i's left/right top edges sit at these heights
    lefts, rights = [0, dip, 0], [dip, 0, dip]
    panels = [P(xs[i], top + lefts[i], xs[i + 1], top + rights[i], xs[i + 1], bot + rights[i], xs[i], bot + lefts[i])
              for i in range(3)]
    for poly, shade in zip(panels, shades):
        d.polygon(poly, fill=shade)
    # green land, blue river, red dashed route and a pin
    d.ellipse(P(16, 34, 44, 60), fill=(122, 190, 92, 255))
    d.ellipse(P(86, 70, 112, 96), fill=(122, 190, 92, 255))
    d.line(P(50, 30, 60, 60, 52, 98), fill=(80, 140, 230, 255), width=5 * S, joint="curve")
    pts = [(22, 92), (38, 78), (56, 74), (74, 60), (94, 48)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        for t in (0.0, 0.5):
            a, b = t, t + 0.3
            d.line(P(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a, x0 + (x1 - x0) * b, y0 + (y1 - y0) * b),
                   fill=(214, 48, 40, 255), width=4 * S)
    d.ellipse(P(88, 28, 106, 46), fill=(214, 48, 40, 255), outline=INK, width=2 * S)
    d.polygon(P(90, 42, 104, 42, 97, 56), fill=(214, 48, 40, 255))
    d.ellipse(P(94, 34, 100, 40), fill=(255, 255, 255, 255))
    for poly in panels:  # outlines on top
        d.line(poly + poly[:2], fill=INK, width=4 * S, joint="curve")
    save(img, "map")


if __name__ == "__main__":
    pokeball()
    folded_map()
