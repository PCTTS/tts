"""Draw the toolbar icons (original art): white silhouettes on transparent, 128x128, for the black toolbar.
Writes ui/icons/<name>.png. Give a changed icon a new file name: TTS caches images by their link."""
from pathlib import Path

from PIL import Image, ImageDraw

S, N = 4, 128  # draw at 4x, output N x N
OUT = Path(__file__).resolve().parent.parent / "ui" / "icons"
STROKE = 9     # line weight shared by all icons (in output pixels)


def P(*v):
    return [x * S for x in v]


def save(mask, name):
    """mask: 'L' image, 255 = ink. Saved as white ink with that alpha."""
    OUT.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", mask.size, (255, 255, 255, 0))
    img.putalpha(mask)
    img.resize((N, N), Image.LANCZOS).save(OUT / f"{name}.png")
    print("wrote ui/icons/" + name + ".png")


def ring(d, c, r_out, r_in):
    d.ellipse(P(c[0] - r_out, c[1] - r_out, c[0] + r_out, c[1] + r_out), fill=255)
    d.ellipse(P(c[0] - r_in, c[1] - r_in, c[0] + r_in, c[1] + r_in), fill=0)


def pokeball():
    m = Image.new("L", (N * S, N * S), 0)
    d = ImageDraw.Draw(m)
    c, R = (64, 64), 58
    ring(d, c, R, R - STROKE)                                   # outer ring
    d.rectangle(P(c[0] - R + 2, c[1] - 3.5, c[0] + R - 2, c[1] + 3.5), fill=255)  # band
    d.ellipse(P(c[0] - 22, c[1] - 22, c[0] + 22, c[1] + 22), fill=0)            # gap around the button
    ring(d, c, 18, 18 - 7)                                      # button
    save(m, "pokeball-line")


def folded_map():
    m = Image.new("L", (N * S, N * S), 0)
    d = ImageDraw.Draw(m)
    xs, top, bot, dip = [12, 45, 78, 111], 26, 104, 9
    lefts, rights = [0, dip, 0], [dip, 0, dip]
    outline = []
    for i in range(3):  # top edge, left to right
        outline += [(xs[i], top + lefts[i]), (xs[i + 1], top + rights[i])]
    for i in reversed(range(3)):  # bottom edge, right to left
        outline += [(xs[i + 1], bot + rights[i]), (xs[i], bot + lefts[i])]
    pts = [v * S for p in outline for v in p]
    d.line(pts + pts[:2], fill=255, width=STROKE * S, joint="curve")
    for x, y in ((xs[1], dip), (xs[2], 0)):                     # fold lines
        d.line(P(x, top + y, x, bot + y), fill=255, width=(STROKE - 2) * S)
    # location pin on the right panel, with a gap so it stands clear of the lines
    px, py, pr = 92, 52, 15
    d.ellipse(P(px - pr - 5, py - pr - 5, px + pr + 5, py + pr + 5), fill=0)
    d.polygon(P(px - pr - 4, py + 2, px + pr + 4, py + 2, px, py + pr + 22), fill=0)
    d.ellipse(P(px - pr, py - pr, px + pr, py + pr), fill=255)
    d.polygon(P(px - pr + 1, py + 6, px + pr - 1, py + 6, px, py + pr + 16), fill=255)
    d.ellipse(P(px - 6, py - 6, px + 6, py + 6), fill=0)
    save(m, "map-line")


if __name__ == "__main__":
    pokeball()
    folded_map()
