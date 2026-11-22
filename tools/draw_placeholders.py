"""Placeholder art for arenas that don't have the user's own textures yet (original, procedural).

Usage:  python -I tools/draw_placeholders.py
Writes (only files that are missing: bump a version when what a file holds changes, TTS caches by link):
  arenas/illusio/textures/grass1.png, grass2.png  island tops: short grass, two variants
  arenas/illusio/textures/stone.png              the raised high ground: pale lavender stone
  arenas/illusio/textures/rock.png               cliffs and the islands' undersides: layered rock, seamless left-right
  misc/sky-placeholder-v1.jpg                    table image under floating islands: sky and soft clouds
  arenas/ingis/textures/sand1.png, sand2.png     low ground: dark volcanic sand
  arenas/ingis/textures/basalt-top.png           high ground: hexagonal basalt column tops, seamless both ways
  arenas/ingis/textures/basalt-wall.png          cliffs: basalt columns standing side by side, seamless left-right
  arenas/ingis/textures/lava.png                 lava: glowing orange with dark crust plates
  misc/volcano-placeholder-v1.jpg                table image around a volcanic arena: dark rock, faint glowing cracks
  arenas/viperia/textures/jungle1.png, jungle2.png  jungle floor: dark soil, moss, fallen leaves
  arenas/viperia/textures/poison.png             poison pools: purple sludge with bubbles
  arenas/viperia/textures/vine-top.png           wall tops: mossy stone under leaves
  arenas/viperia/textures/vine-wall.png          wall sides: stone blocks with vines hanging down, seamless left-right
  misc/jungle-placeholder-v1.jpg                 table image around a jungle arena: dense leaves
  arenas/chrysalia/textures/pitch.png            the whole 16x16 ground: mown grass with a stripe per column
  arenas/chrysalia/textures/turf-edge.png        board edge and pool rims: turf over soil, seamless left-right
  arenas/chrysalia/textures/ice.png              ice: pale blue, cracks and glints
  arenas/chrysalia/textures/water.png            water: blue with ripples
  misc/pitch-placeholder-v1.jpg                  table image around the pitch: more striped grass
  arenas/chrysalia/textures/slate1.png, slate2.png  darker ground (user: the pitch looked like a golf course):
                                                 dark slate flagstones, moss creeping in from the edges
  arenas/chrysalia/textures/slate-edge.png       board edge and pool rims: dark stone courses, seamless left-right
  misc/court-placeholder-v1.jpg                  table image around it: larger dark mossy flagstones
  arenas/chrysalia/textures/mulch1.png, mulch2.png  the user's pick after the slate: a mulch bed, dark wood chips
  arenas/chrysalia/textures/mulch-edge.png       board edge and pool rims: chips on top of dark soil, seamless left-right
  misc/mulch-placeholder-v1.jpg                  table image around it: more mulch, a little darker
  arenas/chrysalia/textures/mulch-clover1.png, -clover2.png  the mulch with small clover patches and sprouts
  misc/mulch-placeholder-v2.jpg                  the table's mulch with clovers too
  arenas/yaksha/textures/temple-stone.png        Yaksha's high ground: dark charcoal-violet stone blocks, faint violet veins
  arenas/yaksha/textures/dark-water.png          Yaksha's water: black-green, faint ripples
  arenas/yaksha/textures/box-floor.png           the surprise boxes: dark stone with faint glowing violet runes
  (Yaksha's ground and edges reuse Chrysalia's slate1/2 and slate-edge)
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

REPO = Path(__file__).resolve().parent.parent
N = 512


def noise(h, w, cells, rng, wrap_x=False):
    """Smooth value noise in 0..1: a random grid of cells^2 values, upsampled. wrap_x makes it seamless left-right."""
    gh, gw = max(2, cells), max(2, cells)
    if not wrap_x:
        grid = rng.random((gh + 1, gw + 1))
        img = Image.fromarray((grid * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        return np.asarray(img, np.float32) / 255
    grid = np.tile(rng.random((gh + 1, gw)), (1, 3))          # three periods side by side; keep the middle one
    img = Image.fromarray((grid * 255).astype(np.uint8)).resize((3 * w, h), Image.BICUBIC)
    return np.asarray(img, np.float32)[:, w:2 * w] / 255


def fbm(h, w, rng, base=4, octaves=5, wrap_x=False):
    out, amp, total = np.zeros((h, w), np.float32), 1.0, 0.0
    for o in range(octaves):
        out += amp * noise(h, w, base * 2 ** o, rng, wrap_x)
        total += amp
        amp *= 0.5
    return out / total


def mix(a, b, t):
    a, b = np.array(a, np.float32), np.array(b, np.float32)
    return a + (b - a) * t[..., None]


def to_img(a):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


def grass(seed):
    rng = np.random.default_rng(seed)
    t = fbm(N, N, rng, 3)
    img = mix((70, 118, 44), (128, 176, 74), np.clip((t - 0.3) * 2.2, 0, 1))
    img *= (0.92 + 0.16 * fbm(N, N, rng, 16, 3))[..., None]
    out = to_img(img)
    d = ImageDraw.Draw(out, "RGBA")
    for _ in range(2600):                                   # blades: short strokes, mostly upright-ish
        x, y = rng.random() * N, rng.random() * N
        ang = rng.normal(-np.pi / 2, 0.6)
        ln = rng.uniform(5, 13)
        light = rng.random() < 0.5
        col = (160, 205, 100, 120) if light else (40, 80, 28, 120)
        d.line([(x, y), (x + ln * np.cos(ang), y + ln * np.sin(ang))], fill=col, width=2)
    return out.filter(ImageFilter.GaussianBlur(0.5))


def stone():
    rng = np.random.default_rng(31)
    t = fbm(N, N, rng, 3)
    img = mix((160, 152, 178), (206, 200, 218), t)
    img *= (0.94 + 0.12 * fbm(N, N, rng, 24, 2))[..., None]
    out = to_img(img)
    d = ImageDraw.Draw(out, "RGBA")
    for _ in range(7):                                      # hairline cracks: short random walks
        x, y = rng.random() * N, rng.random() * N
        ang = rng.random() * 2 * np.pi
        pts = [(x, y)]
        for _ in range(rng.integers(6, 14)):
            ang += rng.normal(0, 0.5)
            x, y = x + 12 * np.cos(ang), y + 12 * np.sin(ang)
            pts.append((x, y))
        d.line(pts, fill=(90, 82, 104, 110), width=2)
    for _ in range(500):                                    # speckles
        x, y = rng.random() * N, rng.random() * N
        r = rng.uniform(0.8, 2.2)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(120, 110, 140, 90) if rng.random() < 0.6 else (235, 230, 245, 90))
    return out.filter(ImageFilter.GaussianBlur(0.4))


def rock():
    """Layered rock: bands along the rows, wavy, seamless left-right (wall slices sit side by side)."""
    rng = np.random.default_rng(47)
    h, w = 1024, N
    warp = fbm(h, w, rng, 3, 4, wrap_x=True)
    rows = np.arange(h, dtype=np.float32)[:, None] / h
    bands = 0.5 + 0.5 * np.sin((rows * 9 + warp * 1.6) * 2 * np.pi)
    t = 0.55 * bands + 0.45 * fbm(h, w, rng, 6, 4, wrap_x=True)
    img = mix((78, 68, 84), (138, 126, 142), t)
    img *= (0.9 + 0.2 * fbm(h, w, rng, 32, 2, wrap_x=True))[..., None]
    return to_img(img).filter(ImageFilter.GaussianBlur(0.6))


def sky():
    """Looking down past the islands: blue, lighter toward the middle, with soft drifting clouds."""
    rng = np.random.default_rng(5)
    h, w = 1211, 2048
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    img = mix((150, 196, 238), (92, 146, 214), np.clip(r / 1.3, 0, 1))
    c = fbm(h, w, rng, 5, 6)
    cloud = np.clip((c - 0.5) / 0.22, 0, 1) ** 1.5
    img = img + (np.array((252, 252, 255), np.float32) - img) * (0.85 * cloud)[..., None]
    shade = np.clip((fbm(h, w, rng, 10, 3) - 0.5) * 0.25, -0.1, 0.1)
    img *= (1 + shade * cloud)[..., None]
    return to_img(img)


def sand(seed):
    """Dark volcanic sand: fine grains, a few pale and glassy-black specks, faint wind ripples."""
    rng = np.random.default_rng(seed)
    base = mix((58, 52, 49), (84, 76, 70), fbm(N, N, rng, 3))
    rows = np.arange(N, dtype=np.float32)[:, None]
    ripple = 0.5 + 0.5 * np.sin((rows / N * 22 + fbm(N, N, rng, 2) * 3) * 2 * np.pi)
    img = base * (0.95 + 0.06 * ripple)[..., None]
    img *= (1 + rng.normal(0, 0.07, (N, N, 1))).astype(np.float32)            # grains
    out = to_img(img)
    d = ImageDraw.Draw(out, "RGBA")
    for _ in range(900):
        x, y = rng.random() * N, rng.random() * N
        r = rng.uniform(0.6, 1.6)
        col = (150, 138, 126, 150) if rng.random() < 0.5 else (20, 18, 18, 170)
        d.ellipse([x - r, y - r, x + r, y + r], fill=col)
    return out.filter(ImageFilter.GaussianBlur(0.35))


def cells(h, w, centres, period):
    """Nearest and second-nearest distances to the centres, wrapping at `period` (px, py) — seamless both ways."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    px, py = period
    xx, yy = xx * px / w, yy * py / h
    d1 = np.full((h, w), np.inf, np.float32)
    d2 = np.full((h, w), np.inf, np.float32)
    idx = np.zeros((h, w), np.int32)
    for i, (cx, cy) in enumerate(centres):
        dx = (xx - cx + px / 2) % px - px / 2
        dy = (yy - cy + py / 2) % py - py / 2
        d = np.sqrt(dx * dx + dy * dy)
        closer = d < d1
        d2 = np.where(closer, d1, np.minimum(d2, d))
        idx = np.where(closer, i, idx)
        d1 = np.where(closer, d, d1)
    return d1, d2, idx


def basalt_top():
    """Hexagonal column tops (14 across, 16 rows: tiles seamlessly), each its own shade, dark joints between."""
    rng = np.random.default_rng(61)
    s = 1.0
    w = np.sqrt(3) * s
    nx, ny = 14, 16
    centres = [((i + 0.5 * (j % 2)) * w, j * 1.5 * s) for j in range(ny) for i in range(nx)]
    centres = [(x + rng.normal(0, 0.05), y + rng.normal(0, 0.05)) for x, y in centres]
    d1, d2, idx = cells(1024, 1024, centres, (nx * w, ny * 1.5 * s))
    shade = rng.uniform(0.82, 1.12, len(centres))[idx]
    img = mix((62, 62, 66), (84, 84, 88), fbm(1024, 1024, rng, 6, 4))
    img *= shade[..., None]
    joint = np.clip((d2 - d1) / 0.09, 0, 1)                       # 0 on a joint
    img *= (0.45 + 0.55 * joint)[..., None]
    img *= (1 + rng.normal(0, 0.04, (1024, 1024, 1))).astype(np.float32)
    return to_img(img).filter(ImageFilter.GaussianBlur(0.6))


def basalt_wall():
    """Basalt columns side by side (seamless left-right): each a light-to-dark facet shade with cracks across."""
    rng = np.random.default_rng(67)
    h, w = 1024, N
    img = np.zeros((h, w, 3), np.float32)
    edges = np.cumsum(rng.uniform(0.7, 1.3, 7))
    edges = np.round(np.concatenate([[0], edges / edges[-1]]) * w).astype(int)       # 7 columns across
    tex = fbm(h, w, rng, 8, 3, wrap_x=True)
    for a, b in zip(edges, edges[1:]):
        t = np.linspace(0, 1, b - a, dtype=np.float32)[None, :]
        facet = np.where(t < 0.45, 0.78 + 0.3 * t / 0.45, 1.08 - 0.25 * (t - 0.45) / 0.55)   # two faces of a column
        tone = rng.uniform(0.88, 1.1)
        img[:, a:b] = (np.array((70, 70, 74), np.float32) * tone)[None, None, :] * facet[..., None]
        img[:, max(a - 1, 0):a + 2] *= 0.45                                               # joint between columns
        y = 0
        while y < h:                                                                      # cracks across
            y += int(rng.uniform(90, 260))
            if y < h:
                img[y:y + 3, a:b] *= 0.55
    img *= (0.9 + 0.2 * tex)[..., None]
    return to_img(img).filter(ImageFilter.GaussianBlur(0.6))


def lava():
    """Glowing lava with dark crust plates: hot between the plates, cooling toward their middles."""
    rng = np.random.default_rng(71)
    pts = [(rng.random() * 10, rng.random() * 10) for _ in range(38)]
    d1, d2, idx = cells(N, N, pts, (10, 10))
    gap = np.clip((d2 - d1) / 0.6, 0, 1)                          # 0 at the seams between plates
    crust = np.clip((gap - 0.25) / 0.5, 0, 1) * rng.uniform(0.3, 1.0, len(pts))[idx]
    hot = mix((255, 214, 96), (236, 92, 20), np.clip(gap * 2.2, 0, 1))
    img = mix(hot, (54, 26, 18), crust)
    img = img + (np.array((255, 120, 30), np.float32) - img) * (0.25 * fbm(N, N, rng, 5))[..., None] * (1 - crust)[..., None]
    return to_img(img).filter(ImageFilter.GaussianBlur(0.8))


def volcano_table():
    """Around a volcanic arena: dark rock with a few faint glowing cracks."""
    rng = np.random.default_rng(9)
    h, w = 1211, 2048
    img = mix((26, 22, 22), (58, 50, 48), fbm(h, w, rng, 6, 6))
    pts = [(rng.random() * 30, rng.random() * 18) for _ in range(160)]
    d1, d2, _ = cells(h, w, pts, (30, 18))
    crack = np.clip(1 - (d2 - d1) / 0.12, 0, 1) ** 2 * (fbm(h, w, rng, 4, 3) > 0.52)
    img = img + (np.array((230, 90, 20), np.float32) - img) * (0.75 * crack)[..., None]
    return to_img(img).filter(ImageFilter.GaussianBlur(0.8))


LEAF_GREENS = [(46, 92, 38), (62, 118, 44), (88, 138, 52), (38, 74, 34), (112, 150, 60)]
LEAF_BROWNS = [(96, 70, 40), (124, 92, 48), (78, 56, 34), (140, 110, 58)]


def leaf(d, x, y, length, angle, col, vein=True):
    """A pointed leaf: an almond outline along `angle`, with a darker midrib."""
    ca, sa = np.cos(angle), np.sin(angle)
    pts = []
    for t in np.linspace(0, 1, 9):
        w = np.sin(np.pi * t) * length * 0.32
        pts.append((t * length, w))
    pts += [(t, -w) for t, w in reversed(pts[1:-1])]
    poly = [(x + px * ca - py * sa, y + px * sa + py * ca) for px, py in pts]
    d.polygon(poly, fill=col)
    if vein:
        d.line([(x, y), (x + length * ca, y + length * sa)], fill=tuple(max(0, v - 30) for v in col[:3]) + (col[3],), width=1)


def jungle_floor(seed):
    """Dark soil with moss patches and fallen leaves (mostly brown, some green)."""
    rng = np.random.default_rng(seed)
    soil = mix((58, 44, 30), (82, 64, 42), fbm(N, N, rng, 4))
    moss = np.clip((fbm(N, N, rng, 3) - 0.5) * 3.0, 0, 1)
    img = soil + (mix((48, 78, 34), (82, 112, 48), fbm(N, N, rng, 12, 3)) - soil) * (0.85 * moss)[..., None]
    img *= (1 + rng.normal(0, 0.05, (N, N, 1))).astype(np.float32)
    out = to_img(img).convert("RGBA")
    d = ImageDraw.Draw(out, "RGBA")
    for _ in range(140):
        col = (LEAF_BROWNS if rng.random() < 0.7 else LEAF_GREENS)[rng.integers(0, 4)]
        leaf(d, rng.random() * N, rng.random() * N, rng.uniform(14, 30), rng.random() * 6.3,
             col + (int(rng.uniform(170, 235)),))
    return out.convert("RGB").filter(ImageFilter.GaussianBlur(0.5))


def poison():
    """Purple sludge: swirls of violet, scattered bubbles with highlights."""
    rng = np.random.default_rng(91)
    t = fbm(N, N, rng, 3, 5)
    swirl = 0.5 + 0.5 * np.sin((t * 5 + fbm(N, N, rng, 2) * 3) * 2 * np.pi)
    img = mix((74, 30, 96), (150, 70, 170), 0.6 * swirl + 0.4 * t)
    out = to_img(img).convert("RGBA")
    d = ImageDraw.Draw(out, "RGBA")
    for _ in range(70):
        x, y, r = rng.random() * N, rng.random() * N, rng.uniform(3, 12)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(170, 96, 196, 170), outline=(60, 20, 80, 200), width=2)
        d.ellipse([x - r * 0.5, y - r * 0.6, x - r * 0.1, y - r * 0.2], fill=(235, 200, 245, 190))   # highlight
    return out.convert("RGB").filter(ImageFilter.GaussianBlur(0.7))


def stone_blocks(h, w, rng, rows, base=(92, 90, 80)):
    """Grey-green stone blocks in staggered courses (seamless left-right)."""
    img = mix(tuple(v - 18 for v in base), base, fbm(h, w, rng, 6, 4, wrap_x=True))
    ch = h / rows
    for i in range(rows):
        y = int(i * ch)
        img[y:y + 3] *= 0.5                                           # mortar between courses
        n = rng.integers(2, 4)
        off = rng.random() * w
        for k in range(n):
            x = int((off + k * w / n) % w)
            img[y:int(y + ch), max(0, x - 1):x + 2] *= 0.55           # joints within a course
        img[y:int(y + ch)] *= rng.uniform(0.85, 1.08)
    return img


def vine_top():
    """Mossy stone wall top under a scatter of leaves."""
    rng = np.random.default_rng(93)
    img = stone_blocks(N, N, rng, 4)
    moss = np.clip((fbm(N, N, rng, 4) - 0.35) * 2.2, 0, 1)
    img = img + (mix((44, 84, 34), (86, 124, 52), fbm(N, N, rng, 10, 3)) - img) * (0.9 * moss)[..., None]
    out = to_img(img).convert("RGBA")
    d = ImageDraw.Draw(out, "RGBA")
    for _ in range(170):
        col = LEAF_GREENS[rng.integers(0, 5)]
        leaf(d, rng.random() * N, rng.random() * N, rng.uniform(16, 34), rng.random() * 6.3, col + (230,))
    return out.convert("RGB").filter(ImageFilter.GaussianBlur(0.5))


def vine_wall():
    """Wall faces: stone courses with vines hanging from the top, leaves along them (seamless left-right)."""
    rng = np.random.default_rng(95)
    h, w = 1024, N
    img = stone_blocks(h, w, rng, 8)
    img *= np.linspace(1.0, 0.75, h, dtype=np.float32)[:, None, None]       # darker toward the bottom
    out = to_img(img).convert("RGBA")
    d = ImageDraw.Draw(out, "RGBA")
    for _ in range(24):                                                     # vines: wavy strands from the top
        x, length = rng.random() * w, rng.uniform(0.35, 0.95) * h
        pts, y = [], 0.0
        ph = rng.random() * 6.3
        while y < length:
            pts.append((x + 10 * np.sin(y / 60 + ph), y))
            y += 8
        for dx in (-w, 0, w):                                               # drawn three times: seamless
            d.line([(px + dx, py) for px, py in pts], fill=(40, 76, 30, 255), width=8)
            for px, py in pts[::3]:
                side = 1 if rng.random() < 0.5 else -1
                leaf(d, px + dx, py, rng.uniform(22, 40), np.pi / 2 + side * rng.uniform(0.5, 1.3),
                     LEAF_GREENS[rng.integers(0, 5)] + (245,))
    return out.convert("RGB").filter(ImageFilter.GaussianBlur(0.5))


def jungle_table():
    """Around a jungle arena: dense overlapping leaves, dark beneath."""
    rng = np.random.default_rng(97)
    h, w = 1211, 2048
    out = to_img(mix((16, 30, 14), (30, 52, 24), fbm(h, w, rng, 5, 4))).convert("RGBA")
    d = ImageDraw.Draw(out, "RGBA")
    for _ in range(2600):
        col = LEAF_GREENS[rng.integers(0, 5)]
        k = rng.uniform(0.55, 1.0)
        leaf(d, rng.random() * w, rng.random() * h, rng.uniform(40, 110), rng.random() * 6.3,
             tuple(int(v * k) for v in col) + (235,))
    return out.convert("RGB").filter(ImageFilter.GaussianBlur(0.8))


def pitch(h, w, stripes, rng):
    """Mown grass: alternating light/dark stripes (vertical bands), fine blade noise."""
    band = (np.arange(w)[None, :] * stripes // w) % 2
    base = np.where(band[..., None] == 0, np.array((86, 146, 62), np.float32), np.array((70, 126, 50), np.float32))
    img = base * (0.94 + 0.12 * fbm(h, w, rng, 12, 3))[..., None]
    img *= (1 + rng.normal(0, 0.05, (h, w, 1))).astype(np.float32)
    return to_img(img).filter(ImageFilter.GaussianBlur(0.6))


def turf_edge():
    """The board's edge: a band of turf over brown soil (seamless left-right)."""
    rng = np.random.default_rng(111)
    h, w = 1024, N
    rows = np.arange(h, dtype=np.float32)[:, None]
    wav = fbm(h, w, rng, 6, 3, wrap_x=True)
    turf = rows < (0.03 + 0.012 * wav) * h          # a low board's edge only shows the top of the strip
    soil = mix((92, 66, 42), (122, 90, 58), fbm(h, w, rng, 8, 4, wrap_x=True))
    img = np.where(turf[..., None], mix((62, 118, 44), (86, 146, 62), wav), soil)
    img *= (1 + rng.normal(0, 0.04, (h, w, 1))).astype(np.float32)
    return to_img(img).filter(ImageFilter.GaussianBlur(0.6))


def ice():
    """Pale blue ice: cloudy depth, white cracks, a few glints."""
    rng = np.random.default_rng(113)
    img = mix((150, 196, 226), (214, 238, 250), fbm(N, N, rng, 3, 5))
    out = to_img(img).convert("RGBA")
    d = ImageDraw.Draw(out, "RGBA")
    for _ in range(9):
        x, y = rng.random() * N, rng.random() * N
        ang = rng.random() * 6.3
        pts = [(x, y)]
        for _ in range(rng.integers(5, 12)):
            ang += rng.normal(0, 0.45)
            x, y = x + 18 * np.cos(ang), y + 18 * np.sin(ang)
            pts.append((x, y))
        d.line(pts, fill=(248, 252, 255, 200), width=2)
    for _ in range(14):
        x, y, r = rng.random() * N, rng.random() * N, rng.uniform(4, 9)
        d.line([(x - r, y), (x + r, y)], fill=(255, 255, 255, 220), width=2)
        d.line([(x, y - r), (x, y + r)], fill=(255, 255, 255, 220), width=2)
    return out.convert("RGB").filter(ImageFilter.GaussianBlur(0.6))


def water():
    """Blue water with soft ripples and highlights."""
    rng = np.random.default_rng(117)
    t = fbm(N, N, rng, 3, 5)
    rip = 0.5 + 0.5 * np.sin((t * 6 + fbm(N, N, rng, 2) * 2) * 2 * np.pi)
    img = mix((30, 92, 160), (70, 150, 210), 0.65 * t + 0.35 * rip)
    img = img + (np.array((210, 236, 250), np.float32) - img) * (0.35 * np.clip((rip - 0.85) / 0.15, 0, 1))[..., None]
    return to_img(img).filter(ImageFilter.GaussianBlur(0.8))


def slate(seed, n=N):
    """A dark slate flagstone: blue-green grey with faint veins, worn lighter in patches, moss at its edges."""
    rng = np.random.default_rng(seed)
    img = mix((34, 40, 40), (58, 64, 62), fbm(n, n, rng, 4, 5))
    veins = np.abs(np.sin((fbm(n, n, rng, 3, 4) * 7 + np.arange(n)[None, :] / n * 2) * np.pi))
    img *= (0.9 + 0.1 * veins)[..., None]
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    edge = np.minimum.reduce([xx, yy, n - 1 - xx, n - 1 - yy]) / n          # 0 at the stone's edge
    moss = np.clip((0.09 - edge) / 0.09, 0, 1) * np.clip((fbm(n, n, rng, 10, 3) - 0.35) * 2.5, 0, 1)
    img = img + (mix((36, 62, 30), (58, 88, 40), fbm(n, n, rng, 16, 2)) - img) * (0.9 * moss)[..., None]
    img *= (1 + rng.normal(0, 0.04, (n, n, 1))).astype(np.float32)
    return to_img(img).filter(ImageFilter.GaussianBlur(0.5))


def slate_edge():
    rng = np.random.default_rng(119)
    img = stone_blocks(1024, N, rng, 6, base=(52, 58, 56))
    return to_img(img).filter(ImageFilter.GaussianBlur(0.5))


def court_table():
    """Around the arena: bigger dark flagstones (8 x 5 of them), mossy joints."""
    h, w = 1211, 2048
    out = Image.new("RGB", (w, h))
    cols, rows = 8, 5
    cw, ch = w // cols + 1, h // rows + 1
    for i in range(cols):
        for j in range(rows):
            stone = slate(200 + i * rows + j, 256).resize((cw, ch), Image.BICUBIC)
            out.paste(stone.point(lambda v: int(v * 0.8)), (i * cw - i, j * ch - j))
    d = ImageDraw.Draw(out)
    for i in range(1, cols):
        d.line([(i * (cw - 1), 0), (i * (cw - 1), h)], fill=(22, 30, 20), width=5)
    for j in range(1, rows):
        d.line([(0, j * (ch - 1)), (w, j * (ch - 1))], fill=(22, 30, 20), width=5)
    return out.filter(ImageFilter.GaussianBlur(0.8))


MULCH = [(84, 52, 30), (64, 40, 24), (98, 62, 34), (48, 30, 19), (112, 74, 42), (74, 46, 27), (58, 36, 22)]


def chips(d, rng, w, h, count, scale=1.0, wrap=False):
    """Bark chips: chunky irregular pieces (5-7 jittered corners round a stretched oval) at random angles, each
    with a dark shadow and a faint lighter grain line along it."""
    for _ in range(count):
        x, y = rng.random() * w, rng.random() * h
        ln, wd = rng.uniform(10, 26) * scale, rng.uniform(5, 13) * scale
        a = rng.random() * np.pi
        ca, sa = np.cos(a), np.sin(a)
        col = MULCH[rng.integers(0, len(MULCH))]
        k = rng.uniform(0.8, 1.1)
        col = tuple(int(min(255, v * k)) for v in col)
        n = int(rng.integers(5, 8))
        pts = [(ln / 2 * np.cos(t) * rng.uniform(0.7, 1.0), wd / 2 * np.sin(t) * rng.uniform(0.6, 1.0))
               for t in np.sort(rng.uniform(0, 2 * np.pi, n))]
        for dx in ((-w, 0, w) if wrap else (0,)):
            poly = [(x + dx + px * ca - py * sa, y + px * sa + py * ca) for px, py in pts]
            d.polygon([(px + 1.5 * scale, py + 2 * scale) for px, py in poly], fill=(14, 9, 6, 170))   # shadow
            d.polygon(poly, fill=col + (255,))
            d.line([(x + dx - ln * 0.3 * ca, y - ln * 0.3 * sa), (x + dx + ln * 0.3 * ca, y + ln * 0.3 * sa)],
                   fill=tuple(min(255, v + 22) for v in col) + (110,), width=1)


CLOVER = [(62, 118, 46), (78, 138, 54), (96, 156, 62), (52, 100, 40)]


def clover(d, x, y, size, rot, col):
    """A three-leaf clover from above: three heart-shaped leaflets round a centre, a lighter mark on each."""
    dark = tuple(max(0, v - 28) for v in col) + (255,)
    for k in range(3):
        a = rot + k * 2 * np.pi / 3
        lx, ly = x + np.cos(a) * size * 0.55, y + np.sin(a) * size * 0.55
        for side in (-1, 1):   # a heart: two round lobes side by side
            b = a + side * np.pi / 2
            cx, cy = lx + np.cos(b) * size * 0.2 + np.cos(a) * size * 0.1, ly + np.sin(b) * size * 0.2 + np.sin(a) * size * 0.1
            r = size * 0.32
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col + (255,), outline=dark, width=1)
        d.line([(x, y), (lx, ly)], fill=dark, width=1)
        mx, my = x + np.cos(a) * size * 0.5, y + np.sin(a) * size * 0.5
        d.ellipse([mx - size * 0.08, my - size * 0.08, mx + size * 0.08, my + size * 0.08],
                  fill=tuple(min(255, v + 50) for v in col) + (200,))


def clover_patches(d, rng, w, h, clusters, scale=1.0):
    """Little patches of clover (3-7 each) and a few lone two-leaf sprouts, scattered over the mulch."""
    for _ in range(clusters):
        cx, cy = rng.random() * w, rng.random() * h
        for _ in range(int(rng.integers(3, 8))):
            x, y = cx + rng.normal(0, 22 * scale), cy + rng.normal(0, 22 * scale)
            clover(d, x, y, rng.uniform(14, 22) * scale, rng.random() * 6.3, CLOVER[rng.integers(0, len(CLOVER))])
    for _ in range(clusters * 2):
        x, y, a = rng.random() * w, rng.random() * h, rng.random() * 6.3
        col = CLOVER[rng.integers(0, len(CLOVER))] + (255,)
        for side in (-1, 1):
            leaf(d, x, y, rng.uniform(10, 16) * scale, a + side * 0.7, col)


def mulch_clover(seed, n=N):
    out = mulch(seed, n).convert("RGBA")
    rng = np.random.default_rng(seed + 1000)
    clover_patches(ImageDraw.Draw(out, "RGBA"), rng, n, n, int(rng.integers(2, 5)))
    return out.convert("RGB").filter(ImageFilter.GaussianBlur(0.3))


def mulch(seed, n=N, count=2600, dark=0.9):
    rng = np.random.default_rng(seed)
    soil = mix((30, 21, 15), (48, 34, 24), fbm(n, n, rng, 6, 4)) * dark
    out = to_img(soil).convert("RGBA")
    chips(ImageDraw.Draw(out, "RGBA"), rng, n, n, count)
    img = np.asarray(out.convert("RGB"), np.float32) * dark
    img *= (0.88 + 0.2 * fbm(n, n, rng, 3, 3))[..., None]      # damp patches
    return to_img(img).filter(ImageFilter.GaussianBlur(0.4))


def mulch_edge():
    rng = np.random.default_rng(131)
    h, w = 1024, N
    soil = mix((34, 24, 17), (54, 38, 26), fbm(h, w, rng, 8, 4, wrap_x=True))
    out = to_img(soil).convert("RGBA")
    top = Image.new("RGBA", (w, 64), (0, 0, 0, 0))
    chips(ImageDraw.Draw(top, "RGBA"), rng, w, 64, 260, scale=0.8, wrap=True)
    out.alpha_composite(top, (0, 0))
    return out.convert("RGB").filter(ImageFilter.GaussianBlur(0.4))


def mulch_table():
    rng = np.random.default_rng(137)
    h, w = 1211, 2048
    soil = mix((26, 18, 13), (42, 30, 21), fbm(h, w, rng, 8, 4))
    out = to_img(soil).convert("RGBA")
    chips(ImageDraw.Draw(out, "RGBA"), rng, w, h, 30000, scale=1.3)
    img = np.asarray(out.convert("RGB"), np.float32) * 0.82 * (0.88 + 0.2 * fbm(h, w, rng, 4, 3))[..., None]
    return to_img(img).filter(ImageFilter.GaussianBlur(0.6))


def mulch_table_clover():
    out = Image.open(REPO / "misc/mulch-placeholder-v1.jpg").convert("RGBA")
    rng = np.random.default_rng(151)
    clover_patches(ImageDraw.Draw(out, "RGBA"), rng, out.width, out.height, 90, scale=1.1)
    return out.convert("RGB").filter(ImageFilter.GaussianBlur(0.3))


def temple_stone():
    """Dark charcoal-violet stone in big blocks, with faint glowing violet veins."""
    rng = np.random.default_rng(161)
    img = stone_blocks(N, N, rng, 2, base=(54, 48, 60))
    veins = np.abs(np.sin((fbm(N, N, rng, 3, 4) * 6 + np.arange(N)[:, None] / N) * np.pi))
    glow = np.clip((0.06 - veins) / 0.06, 0, 1) * (fbm(N, N, rng, 4, 3) > 0.5)
    img = img + (np.array((150, 90, 200), np.float32) - img) * (0.6 * glow)[..., None]
    return to_img(img).filter(ImageFilter.GaussianBlur(0.5))


def dark_water():
    rng = np.random.default_rng(163)
    t = fbm(N, N, rng, 3, 5)
    rip = 0.5 + 0.5 * np.sin((t * 6 + fbm(N, N, rng, 2) * 2) * 2 * np.pi)
    img = mix((10, 26, 24), (26, 52, 46), 0.6 * t + 0.4 * rip)
    img = img + (np.array((90, 130, 120), np.float32) - img) * (0.25 * np.clip((rip - 0.88) / 0.12, 0, 1))[..., None]
    return to_img(img).filter(ImageFilter.GaussianBlur(0.8))


def box_floor():
    """The surprise boxes' floor: dark stone with a faint glowing violet rune circle."""
    rng = np.random.default_rng(167)
    img = mix((30, 26, 36), (48, 42, 56), fbm(N, N, rng, 4, 4))
    out = to_img(img).convert("RGBA")
    glow = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    c = N / 2
    for r, w in ((N * 0.42, 6), (N * 0.34, 3)):
        d.ellipse([c - r, c - r, c + r, c + r], outline=(170, 110, 230, 200), width=w)
    for k in range(8):   # little rune strokes between the rings
        a = k * np.pi / 4 + 0.2
        x, y = c + np.cos(a) * N * 0.38, c + np.sin(a) * N * 0.38
        d.line([(x - 8, y - 8), (x + 6, y + 2), (x - 4, y + 10)], fill=(190, 140, 240, 210), width=3)
    out.alpha_composite(glow.filter(ImageFilter.GaussianBlur(3)))
    out.alpha_composite(glow)
    return out.convert("RGB")


def main():
    files = {
        "arenas/yaksha/textures/temple-stone.png": lambda p: temple_stone().save(p),
        "arenas/yaksha/textures/dark-water.png": lambda p: dark_water().save(p),
        "arenas/yaksha/textures/box-floor.png": lambda p: box_floor().save(p),
        "arenas/chrysalia/textures/mulch-clover1.png": lambda p: mulch_clover(141).save(p),
        "arenas/chrysalia/textures/mulch-clover2.png": lambda p: mulch_clover(142).save(p),
        "misc/mulch-placeholder-v2.jpg": lambda p: mulch_table_clover().save(p, quality=90),
        "arenas/chrysalia/textures/mulch1.png": lambda p: mulch(141).save(p),
        "arenas/chrysalia/textures/mulch2.png": lambda p: mulch(142).save(p),
        "arenas/chrysalia/textures/mulch-edge.png": lambda p: mulch_edge().save(p),
        "misc/mulch-placeholder-v1.jpg": lambda p: mulch_table().save(p, quality=90),
        "arenas/chrysalia/textures/slate1.png": lambda p: slate(121).save(p),
        "arenas/chrysalia/textures/slate2.png": lambda p: slate(122).save(p),
        "arenas/chrysalia/textures/slate-edge.png": lambda p: slate_edge().save(p),
        "misc/court-placeholder-v1.jpg": lambda p: court_table().save(p, quality=90),
        "arenas/chrysalia/textures/pitch.png": lambda p: pitch(2048, 2048, 16, np.random.default_rng(107)).save(p),
        "arenas/chrysalia/textures/turf-edge.png": lambda p: turf_edge().save(p),
        "arenas/chrysalia/textures/ice.png": lambda p: ice().save(p),
        "arenas/chrysalia/textures/water.png": lambda p: water().save(p),
        "misc/pitch-placeholder-v1.jpg": lambda p: pitch(1211, 2048, 28, np.random.default_rng(109)).save(p, quality=90),
        "arenas/viperia/textures/jungle1.png": lambda p: jungle_floor(101).save(p),
        "arenas/viperia/textures/jungle2.png": lambda p: jungle_floor(102).save(p),
        "arenas/viperia/textures/poison.png": lambda p: poison().save(p),
        "arenas/viperia/textures/vine-top.png": lambda p: vine_top().save(p),
        "arenas/viperia/textures/vine-wall.png": lambda p: vine_wall().save(p),
        "misc/jungle-placeholder-v1.jpg": lambda p: jungle_table().save(p, quality=90),
        "arenas/ingis/textures/sand1.png": lambda p: sand(81).save(p),
        "arenas/ingis/textures/sand2.png": lambda p: sand(82).save(p),
        "arenas/ingis/textures/basalt-top.png": lambda p: basalt_top().save(p),
        "arenas/ingis/textures/basalt-wall.png": lambda p: basalt_wall().save(p),
        "arenas/ingis/textures/lava.png": lambda p: lava().save(p),
        "misc/volcano-placeholder-v1.jpg": lambda p: volcano_table().save(p, quality=90),
        "arenas/illusio/textures/grass1.png": lambda p: grass(1).save(p),
        "arenas/illusio/textures/grass2.png": lambda p: grass(2).save(p),
        "arenas/illusio/textures/stone.png": lambda p: stone().save(p),
        "arenas/illusio/textures/rock.png": lambda p: rock().save(p),
        "misc/sky-placeholder-v1.jpg": lambda p: sky().save(p, quality=90),
    }
    for rel, make in files.items():
        path = REPO / rel
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            make(path)
            print("wrote", rel)


if __name__ == "__main__":
    main()
