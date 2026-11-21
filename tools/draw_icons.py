"""Draw the toolbar icons (original art): white silhouettes on transparent, for the black toolbar.
Shapes are designed on a 128-unit grid; render(shape, size) draws one at any size (cards reuse them).
Writes ui/icons/<name>-<VERSION>.png. Give a changed icon a new file name: TTS caches images by their link."""
import math
from pathlib import Path

from PIL import Image, ImageDraw

N, SS = 64, 8        # toolbar icon size (about its on-screen size), supersampling for smooth edges
STROKE = 9           # line weight in design units, shared by all icons
OUT = Path(__file__).resolve().parent.parent / "ui" / "icons"
VERSION = "v3"
K = N * SS / 128     # design units -> drawing pixels (set by render)


def P(*v):
    return [x * K for x in v]


def ring(d, cx, cy, r_out, r_in):
    d.ellipse(P(cx - r_out, cy - r_out, cx + r_out, cy + r_out), fill=255)
    d.ellipse(P(cx - r_in, cy - r_in, cx + r_in, cy + r_in), fill=0)


def pokeball(d):
    R = 61
    ring(d, 64, 64, R, R - STROKE)                          # outer ring
    d.rectangle(P(64 - R + 2, 64 - 3.5, 64 + R - 2, 64 + 3.5), fill=255)  # band
    d.ellipse(P(64 - 22, 64 - 22, 64 + 22, 64 + 22), fill=0)              # gap around the button
    ring(d, 64, 64, 18, 18 - 7)                             # button


def folded_map(d):
    xs, top, bot, dip = [6, 44.67, 83.33, 122], 14, 104, 10  # spans 6..122 x 14..114: centred
    lefts, rights = [0, dip, 0], [dip, 0, dip]               # panel top-edge heights: fold down, then up
    mid_left = (xs[0], (top + bot) / 2)                      # start and end mid-edge so the join is invisible
    outline = [mid_left]
    for i in range(3):                                       # top edge, left to right
        outline += [(xs[i], top + lefts[i]), (xs[i + 1], top + rights[i])]
    for i in reversed(range(3)):                             # bottom edge, right to left
        outline += [(xs[i + 1], bot + rights[i]), (xs[i], bot + lefts[i])]
    outline.append(mid_left)
    d.line([v * K for p in outline for v in p], fill=255, width=round(STROKE * K), joint="curve")
    for x, y in ((xs[1], dip), (xs[2], 0)):                  # fold lines
        d.line(P(x, top + y, x, bot + y), fill=255, width=round((STROKE - 2) * K))


def swirl(d):
    """Status effects: a dizzy spiral."""
    turns, r0, r1, steps = 2.2, 4, 56, 400
    pts = []
    for i in range(steps + 1):
        t = i / steps
        a, r = t * turns * 2 * math.pi, r0 + (r1 - r0) * t
        pts += [(64 + r * math.cos(a)) * K, (64 + r * math.sin(a)) * K]
    d.line(pts, fill=255, width=round((STROKE - 1) * K), joint="curve")
    rr = (STROKE - 1) * K / 2
    d.ellipse([pts[-2] - rr, pts[-1] - rr, pts[-2] + rr, pts[-1] + rr], fill=255)  # round the outer tip


def potion(d):
    """Items: a round potion bottle with a cork."""
    ring(d, 64, 80, 40, 40 - STROKE)                          # body
    d.rectangle(P(55, 30, 73, 46), fill=0)                    # opening where the neck meets the body
    for x in (51, 77):                                        # neck sides
        d.line(P(x, 22, x, 44), fill=255, width=round(STROKE * K))
    d.rounded_rectangle(P(44, 8, 84, 24), radius=4 * K, fill=255)                  # cork / lip
    d.line(P(36, 88, 92, 88), fill=255, width=round((STROKE - 2) * K))             # liquid level
    d.ellipse(P(57, 96, 67, 106), fill=255)                   # bubble


def swords(d):
    """Warrior skills: two crossed swords."""
    def sword(angle, gap):
        a = math.radians(angle)
        def pt(x, y):
            return (64 + x * math.cos(a) - y * math.sin(a)) * K, (64 + x * math.sin(a) + y * math.cos(a)) * K
        shapes = [[pt(-12, -5.5), pt(46, -5.5), pt(58, 0), pt(46, 5.5), pt(-12, 5.5)],   # blade
                  [pt(-19, -17), pt(-12, -17), pt(-12, 17), pt(-19, 17)],               # crossguard
                  [pt(-44, -5), pt(-19, -5), pt(-19, 5), pt(-44, 5)]]                   # grip
        for s in shapes:
            if gap:
                d.polygon(s, fill=0, outline=0, width=round(6 * K))
            d.polygon(s, fill=255)
        cx, cy = pt(-49, 0)
        r = 7.5 * K
        if gap:
            d.ellipse([cx - r - 3 * K, cy - r - 3 * K, cx + r + 3 * K, cy + r + 3 * K], fill=0)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)                            # pommel
    sword(-45, False)
    sword(-135, True)   # drawn over the first with a small gap so the two read apart


def sparkle(d):
    """Pokemon abilities: a four-pointed sparkle, with a small one beside it."""
    def star(cx, cy, r_out, r_in):
        pts = []
        for i in range(8):
            a = math.pi / 4 * i - math.pi / 2
            r = r_out if i % 2 == 0 else r_in
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        return pts
    big = star(56, 70, 52, 15)
    d.line([v * K for p in big + big[:2] for v in p], fill=255, width=round(STROKE * K), joint="curve")
    d.polygon([(x * K, y * K) for x, y in star(102, 24, 20, 6)], fill=255)


SHAPES = {"pokeball": pokeball, "map": folded_map, "status": swirl, "item": potion, "skill": swords, "ability": sparkle}


def render(shape, size=N, ss=SS):
    """Draw a shape at size x size; returns an 'L' mask (255 = ink)."""
    global K
    K = size * ss / 128
    m = Image.new("L", (size * ss, size * ss), 0)
    shape(ImageDraw.Draw(m))
    return m.resize((size, size), Image.LANCZOS)


def white(mask):
    img = Image.new("RGBA", mask.size, (255, 255, 255, 0))
    img.putalpha(mask)
    return img


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, shape in SHAPES.items():
        path = OUT / f"{name}-{VERSION}.png"
        white(render(shape)).save(path)
        print("wrote", path.relative_to(OUT.parent.parent))
