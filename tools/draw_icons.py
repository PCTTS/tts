"""Draw the toolbar icons (original art): white silhouettes on transparent, for the black toolbar.
Shapes are designed on a 128-unit grid and rendered at N pixels. Writes ui/icons/<name>-v2.png.
Give a changed icon a new file name: TTS caches images by their link."""
from pathlib import Path

from PIL import Image, ImageDraw

N, SS = 256, 4       # output size, supersampling for smooth edges
K = N * SS / 128     # design units -> drawing pixels
STROKE = 9           # line weight in design units, shared by all icons
OUT = Path(__file__).resolve().parent.parent / "ui" / "icons"
VERSION = "v2"


def P(*v):
    return [x * K for x in v]


def new_mask():
    m = Image.new("L", (N * SS, N * SS), 0)
    return m, ImageDraw.Draw(m)


def save(mask, name):
    """mask: 255 = ink. Saved as white ink with that alpha."""
    OUT.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", mask.size, (255, 255, 255, 0))
    img.putalpha(mask)
    path = OUT / f"{name}-{VERSION}.png"
    img.resize((N, N), Image.LANCZOS).save(path)
    print("wrote", path.relative_to(OUT.parent.parent))


def ring(d, cx, cy, r_out, r_in):
    d.ellipse(P(cx - r_out, cy - r_out, cx + r_out, cy + r_out), fill=255)
    d.ellipse(P(cx - r_in, cy - r_in, cx + r_in, cy + r_in), fill=0)


def pokeball():
    m, d = new_mask()
    R = 61
    ring(d, 64, 64, R, R - STROKE)                          # outer ring
    d.rectangle(P(64 - R + 2, 64 - 3.5, 64 + R - 2, 64 + 3.5), fill=255)  # band
    d.ellipse(P(64 - 22, 64 - 22, 64 + 22, 64 + 22), fill=0)              # gap around the button
    ring(d, 64, 64, 18, 18 - 7)                             # button
    save(m, "pokeball")


def folded_map():
    m, d = new_mask()
    xs, top, bot, dip = [6, 44.67, 83.33, 122], 14, 104, 10  # spans 6..122 x 14..114: centred
    lefts, rights = [0, dip, 0], [dip, 0, dip]               # panel top-edge heights: fold down, then up
    mid_left = (xs[0], (top + bot) / 2)                      # start and end mid-edge so the join is invisible
    outline = [mid_left]
    for i in range(3):                                       # top edge, left to right
        outline += [(xs[i], top + lefts[i]), (xs[i + 1], top + rights[i])]
    for i in reversed(range(3)):                             # bottom edge, right to left
        outline += [(xs[i + 1], bot + rights[i]), (xs[i], bot + lefts[i])]
    outline.append(mid_left)
    pts = [v * K for p in outline for v in p]
    d.line(pts, fill=255, width=round(STROKE * K), joint="curve")
    for x, y in ((xs[1], dip), (xs[2], 0)):                  # fold lines
        d.line(P(x, top + y, x, bot + y), fill=255, width=round((STROKE - 2) * K))
    save(m, "map")


if __name__ == "__main__":
    pokeball()
    folded_map()
