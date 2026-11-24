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


def die(d):
    """Shuffle the portals: a die showing five (the same from either side of the table)."""
    d.rounded_rectangle(P(10, 10, 118, 118), radius=20 * K, outline=255, width=round(STROKE * K))
    for x, y in ((38, 38), (90, 38), (64, 64), (38, 90), (90, 90)):
        d.ellipse(P(x - 10, y - 10, x + 10, y + 10), fill=255)


def updown(d):
    """Raise / drop the bridges: an up arrow beside a down arrow (the same from either side of the table)."""
    for x, sy in ((40, 1), (88, -1)):
        tip, base = 64 - 52 * sy, 64 + 52 * sy
        d.line(P(x, base, x, tip + 22 * sy), fill=255, width=round(STROKE * K))
        d.polygon(P(x, tip, x - 22, tip + 30 * sy, x + 22, tip + 30 * sy), fill=255)


def turn(d, ccw=True):
    """Turn a gear (Valora): three quarters of a circle with an arrowhead, the way the gear turns as seen from above
    (a turn reads the same way round from either side of the table). ccw=False mirrors it."""
    r, w = 40, STROKE * 1.2
    fx = (lambda x: x) if ccw else (lambda x: 128 - x)
    # the arc runs counter-clockwise from 45 degrees up to 315 (maths angles, y up); drawn as a polyline so it can
    # be mirrored
    pts = []
    for k in range(0, 271, 5):
        a = math.radians(45 + k)
        pts.append((fx(64 + r * math.cos(a)), 64 - r * math.sin(a)))
    d.line([v * K for p in pts for v in p], fill=255, width=round(w * K), joint="curve")
    a = math.radians(315)
    ex, ey = 64 + r * math.cos(a), 64 - r * math.sin(a)         # the arc's end (lower right)
    tx, ty = -math.sin(a), -math.cos(a)                          # counter-clockwise tangent there (screen, y down)
    nx, ny = math.cos(a), -math.sin(a)                           # outward
    tip = (ex + tx * 26, ey + ty * 26)
    b1, b2 = (ex + nx * 20 - tx * 4, ey + ny * 20 - ty * 4), (ex - nx * 20 - tx * 4, ey - ny * 20 - ty * 4)
    d.polygon([(fx(x) * K, y * K) for x, y in (tip, b1, b2)], fill=255)


def doors(d):
    """Open or close a gear's blockers: two door panels parting, an arrow out of each (the same from either side)."""
    w = round(STROKE * K)
    d.rectangle(P(14, 40, 54, 114), outline=255, width=w)
    d.rectangle(P(74, 40, 114, 114), outline=255, width=w)
    for x0, x1 in ((50, 12), (78, 116)):
        d.line(P(x0, 18, x1 + (8 if x1 < 64 else -8), 18), fill=255, width=w)
        s = -1 if x1 < 64 else 1
        d.polygon(P(x1, 18, x1 - 16 * s, 6, x1 - 16 * s, 30), fill=255)


def fling(d):
    """Fling the Pokémon on a flower (Greenleaf): three arrows flying out from a dot, one toward each of its spots
    (much the same from either side of the table)."""
    d.ellipse(P(64 - 13, 64 - 13, 64 + 13, 64 + 13), fill=255)
    for deg in (90, 210, 330):
        a = math.radians(deg)
        ux, uy = math.cos(a), -math.sin(a)                       # outward, screen coordinates (y down)
        nx, ny = -uy, ux
        d.line(P(64 + ux * 24, 64 + uy * 24, 64 + ux * 42, 64 + uy * 42), fill=255, width=round(STROKE * K))
        tip, base = (64 + ux * 62, 64 + uy * 62), (64 + ux * 34, 64 + uy * 34)
        d.polygon(P(*tip, base[0] + nx * 21, base[1] + ny * 21, base[0] - nx * 21, base[1] - ny * 21), fill=255)


SHAPES = {"pokeball": pokeball, "map": folded_map, "status": swirl, "item": potion, "skill": swords, "ability": sparkle,
          "die": die, "updown": updown, "turnccw": turn, "turncw": lambda d: turn(d, False), "doors": doors,
          "fling": fling}


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
    import sys
    OUT.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1:]   # icon names to draw (default: all of them)
    for name, shape in SHAPES.items():
        if only and name not in only:
            continue
        path = OUT / f"{name}-{VERSION}.png"
        white(render(shape)).save(path)
        print("wrote", path.relative_to(OUT.parent.parent))
