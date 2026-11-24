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
  arenas/violight/textures/steel1.png, steel2.png  Violight's floor: dark riveted steel plates, violet light in the seams
  arenas/violight/textures/electric1.png, electric2.png  electric tiles: dark violet glass, yellow lightning
  arenas/violight/textures/spire-top.png        the centre spire's top (2x2 tiles): coil rings round a glowing core
  arenas/violight/textures/spire-wall.png       the spire's sides and the board's edge: steel panels, violet bands
  misc/violight-placeholder-v1.jpg              table image around Violight: big dark steel deck plates
  arenas/fontaine/textures/grass1.png, grass2.png  Fontaine's land: valley grass (Illusio's kind, other seeds)
  arenas/fontaine/textures/pebbles.png          the river bed: grey-brown pebbles on wet sand
  arenas/fontaine/textures/canal-wall.png       the canal walls and the board's edge: grey stone courses
  misc/valley-placeholder-v1.jpg                table image around Fontaine: meadow grass with small flowers
  arenas/spectra/textures/grave-grass1.png, grave-grass2.png  Spectra's ground: dull dark graveyard grass, worn
                                                bare patches, a faint pale mist
  arenas/spectra/textures/crypt-top.png         the crypt roofs: dark grey-violet stone slabs, pale lichen
  arenas/spectra/textures/crypt-wall.png        the crypts' sides: dark stone courses, damp toward the ground with
                                                moss creeping up, seamless left-right
  misc/graveyard-placeholder-v1.jpg             table image around Spectra: dark grass in a pale mist, rows of
                                                small weathered headstones
  arenas/valora/textures/tread1.png, tread2.png  Valora's floor: weathered steel tread plate, rust in patches
  arenas/valora/textures/iron-top.png           the walls' tops: heavy dark iron plates, rivets along the seams
  arenas/valora/textures/iron-wall.png          the walls' sides: riveted iron panels, rust running down from the
                                                rivets, seamless left-right
  misc/foundry-placeholder-v1.jpg               table image around Valora: big riveted floor plates, grime, glowing
                                                ore channels down the sides
  arenas/terrera/textures/hive1.png, hive2.png  Terrera's floors: packed earth of the old Durant hive, grit, small
                                                stones, claw scratches
  arenas/terrera/textures/quicksand.png         quicksand: pale wet sand in curving ripples
  arenas/terrera/textures/strata.png            cliffs and the boards' edges: layered earth and rock, seamless
                                                left-right
  misc/cave-placeholder-v1.jpg                  table image around Terrera: dark cave floor, loose rocks, the mouths
                                                of Durant tunnels
  arenas/terrera/textures/rock.png              the rock ridge between the boards: rough grey-brown rock, cracks,
                                                lumps lit from one side (4 tiles to an image)
  arenas/greenleaf/textures/lawn1.png, lawn2.png  Greenleaf's ground: a garden lawn, a little clover, the odd daisy
  arenas/greenleaf/textures/hedge-top.png       the hedges' tops: densely clipped small leaves, seamless both ways
  arenas/greenleaf/textures/hedge-wall.png      the hedges' sides: packed leaves, lighter along the clipped top,
                                                shadowed toward the ground, seamless left-right
  arenas/greenleaf/textures/creek.png           the creek under the grass bridge: green-blue water, lily pads
  arenas/greenleaf/textures/soil.png            the creek's banks and the board's edge: garden soil, stones, roots
  misc/garden-placeholder-v1.jpg                table image around Greenleaf: lawn, round flower beds, low shrubs
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


VIOLET = (168, 104, 240)
SPARK = (245, 212, 38)


def steel_plate(seed, n=N, glow=0.45):
    """A dark steel floor plate: brushed grain, worn patches, a bevel, a rivet in each corner, faint violet light
    from the seam round it."""
    rng = np.random.default_rng(seed)
    img = mix((40, 40, 50), (62, 62, 74), fbm(n, n, rng, 3, 4))
    streaks = np.asarray(Image.fromarray((rng.random((n, 20)) * 255).astype(np.uint8)).resize((n, n), Image.BILINEAR),
                         np.float32) / 255
    img *= (0.9 + 0.14 * streaks)[..., None]
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    k = n / 512
    img[(xx < 8 * k) | (yy < 8 * k)] *= 1.18                       # bevel: lit top/left, shaded bottom/right
    img[(n - 1 - xx < 8 * k) | (n - 1 - yy < 8 * k)] *= 0.68
    edge = np.minimum.reduce([xx, yy, n - 1 - xx, n - 1 - yy])
    light = glow * np.exp(-edge / (12 * k))
    img = img + (np.array(VIOLET, np.float32) - img) * light[..., None]
    out = to_img(img)
    d = ImageDraw.Draw(out)
    for cx in (34 * k, n - 34 * k):
        for cy in (34 * k, n - 34 * k):
            r = 9 * k
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(70, 70, 82), outline=(22, 22, 28), width=max(1, round(2 * k)))
            d.arc([cx - r * 0.6, cy - r * 0.6, cx + r * 0.6, cy + r * 0.6], 190, 280, fill=(150, 150, 164),
                  width=max(1, round(2 * k)))
    return out.filter(ImageFilter.GaussianBlur(0.5 * k))


def bolt(rng, p0, p1, rough, depth):
    """A jagged lightning path from p0 to p1 (midpoint displacement)."""
    if depth == 0:
        return [p0, p1]
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    off = rng.normal(0, rough)
    mid = (mx - dy * off, my + dx * off)
    return bolt(rng, p0, mid, rough, depth - 1)[:-1] + bolt(rng, mid, p1, rough, depth - 1)


def draw_bolts(size, rng, count, margin, width, branches=2, rough=0.13):
    """Lightning on a transparent layer: `count` jagged bolts across the middle, each with `branches` short side
    forks; a soft yellow glow, a bright core."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    paths = []
    for _ in range(count):
        a = rng.random() * np.pi
        r = size / 2 - margin
        p0 = (size / 2 + np.cos(a) * r * rng.uniform(0.75, 1), size / 2 + np.sin(a) * r * rng.uniform(0.75, 1))
        p1 = (size / 2 - np.cos(a) * r * rng.uniform(0.75, 1), size / 2 - np.sin(a) * r * rng.uniform(0.75, 1))
        path = bolt(rng, p0, p1, rough, 5)
        paths.append((path, width))
        for i in rng.choice(np.arange(4, len(path) - 4), branches, replace=False) if branches else []:
            q0 = path[i]
            ahead = np.arctan2(p1[1] - p0[1], p1[0] - p0[0]) + rng.choice((-1, 1)) * rng.uniform(0.4, 0.9)
            ln = rng.uniform(0.12, 0.2) * size
            q1 = (np.clip(q0[0] + np.cos(ahead) * ln, margin, size - margin),
                  np.clip(q0[1] + np.sin(ahead) * ln, margin, size - margin))
            paths.append((bolt(rng, q0, q1, rough * 1.3, 3), max(1, width * 0.5)))
    for path, w in paths:
        d.line(path, fill=SPARK + (255,), width=round(w * 2.2), joint="curve")
    glow = layer.filter(ImageFilter.GaussianBlur(width * 3))
    core = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dc = ImageDraw.Draw(core)
    for path, w in paths:
        dc.line(path, fill=(255, 250, 220, 255), width=max(1, round(w * 0.8)), joint="curve")
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for part in (glow, glow, layer, core):
        out.alpha_composite(part)
    return out


def electric_panel(seed, n=N):
    """An electrified floor panel: dark violet glass over a faint circuit grid, yellow lightning crackling in it."""
    rng = np.random.default_rng(seed)
    img = mix((16, 14, 30), (38, 30, 62), fbm(n, n, rng, 3, 4))
    out = to_img(img).convert("RGBA")
    grid = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    g = ImageDraw.Draw(grid)
    for i in range(1, 8):
        g.line([(i * n / 8, 0), (i * n / 8, n)], fill=SPARK + (34,), width=2)
        g.line([(0, i * n / 8), (n, i * n / 8)], fill=SPARK + (34,), width=2)
    out.alpha_composite(grid)
    out.alpha_composite(draw_bolts(n, rng, int(rng.integers(1, 3)), n * 0.1, 7))
    return out.convert("RGB")


def spire_top(n=1024):
    """The top of the centre spire (2x2 tiles): a power discharger, coil rings round a glowing core, arcs
    crackling out from it."""
    rng = np.random.default_rng(181)
    out = steel_plate(183, n, glow=0.2).convert("RGBA")
    d = ImageDraw.Draw(out)
    c = n / 2
    rings = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    dr = ImageDraw.Draw(rings)
    for i, r in enumerate(np.linspace(0.44, 0.14, 7) * n):
        d.ellipse([c - r, c - r, c + r, c + r], fill=(30 + 6 * i, 28 + 6 * i, 40 + 8 * i, 255), outline=(14, 12, 20, 255), width=6)
        dr.ellipse([c - r + 10, c - r + 10, c + r - 10, c + r - 10], outline=VIOLET + (255,), width=5)
    out.alpha_composite(rings.filter(ImageFilter.GaussianBlur(9)))
    out.alpha_composite(rings)
    core = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    t = np.clip(1 - np.hypot(xx - c, yy - c) / (0.16 * n), 0, 1) ** 1.6
    core_px = np.zeros((n, n, 4), np.uint8)
    core_px[..., :3] = np.array((236, 214, 255), np.uint8)
    core_px[..., 3] = (255 * t).astype(np.uint8)
    out.alpha_composite(Image.fromarray(core_px, "RGBA"))
    arcs = draw_bolts(n, rng, 3, n * 0.08, 6, branches=0, rough=0.2)
    arcs = Image.fromarray(np.dstack([np.asarray(arcs)[..., :3] * 0 + np.array((220, 190, 255), np.uint8),
                                      np.asarray(arcs)[..., 3]]), "RGBA")   # violet-white arcs, not yellow
    out.alpha_composite(arcs)
    return out.convert("RGB")


def spire_wall():
    """The spire's sides and the board's edge: dark steel panels, riveted seams, glowing violet bands (seamless
    left-right)."""
    rng = np.random.default_rng(185)
    h, w = 1024, N
    img = mix((34, 34, 44), (52, 52, 64), fbm(h, w, rng, 6, 4, wrap_x=True))
    img *= np.linspace(1.0, 0.7, h, dtype=np.float32)[:, None, None]
    for x in (0, w // 2):
        img[:, max(0, x - 2):x + 3] *= 0.5
    out = to_img(img).convert("RGBA")
    bands = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    db = ImageDraw.Draw(bands)
    for y in (0.16, 0.42, 0.68):
        db.rectangle([0, y * h - 5, w, y * h + 5], fill=VIOLET + (255,))
    out.alpha_composite(bands.filter(ImageFilter.GaussianBlur(10)))
    out.alpha_composite(bands)
    d = ImageDraw.Draw(out)
    for x in (12, w // 2 + 12, w // 2 - 12, w - 12):
        for y in range(40, h, 96):
            d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(78, 78, 92, 255), outline=(20, 20, 26, 255))
    return out.convert("RGB")


def violight_table():
    """Around Violight: big dark steel deck plates (8 x 5), violet light in the seams."""
    h, w = 1211, 2048
    out = Image.new("RGB", (w, h))
    cols, rows = 8, 5
    cw, ch = w // cols + 1, h // rows + 1
    for i in range(cols):
        for j in range(rows):
            plate = steel_plate(300 + i * rows + j, 256, glow=0.55).resize((cw, ch), Image.BICUBIC)
            out.paste(plate.point(lambda v: int(v * 0.7)), (i * cw - i, j * ch - j))
    return out.filter(ImageFilter.GaussianBlur(0.6))


def pebbles():
    """A river bed: wet sand under a scatter of rounded pebbles in greys and browns, each with a soft shadow."""
    rng = np.random.default_rng(221)
    out = to_img(mix((96, 88, 72), (124, 114, 94), fbm(N, N, rng, 6, 4))).convert("RGBA")
    d = ImageDraw.Draw(out, "RGBA")
    cols = [(132, 128, 120), (110, 104, 96), (150, 140, 124), (96, 92, 88), (162, 154, 140), (120, 100, 80)]
    for _ in range(420):
        x, y = rng.random() * N, rng.random() * N
        rx, ry = rng.uniform(6, 16), rng.uniform(4, 11)
        col = cols[rng.integers(0, len(cols))]
        d.ellipse([x - rx + 2, y - ry + 3, x + rx + 2, y + ry + 3], fill=(40, 34, 26, 90))
        d.ellipse([x - rx, y - ry, x + rx, y + ry], fill=col + (255,))
        d.ellipse([x - rx * 0.5, y - ry * 0.7, x, y - ry * 0.1], fill=tuple(min(255, v + 40) for v in col) + (110,))
    return out.convert("RGB").filter(ImageFilter.GaussianBlur(0.6))


def canal_wall():
    rng = np.random.default_rng(223)
    img = stone_blocks(1024, N, rng, 7, base=(128, 126, 118))
    img *= np.linspace(1.0, 0.8, 1024, dtype=np.float32)[:, None, None]   # damper toward the water
    return to_img(img).filter(ImageFilter.GaussianBlur(0.5))


def valley_table():
    """Around Fontaine: meadow grass, a little darker, with small white and yellow flowers."""
    rng = np.random.default_rng(227)
    h, w = 1211, 2048
    t = fbm(h, w, rng, 6, 5)
    img = mix((58, 102, 40), (104, 152, 64), np.clip((t - 0.3) * 2.0, 0, 1)) * 0.85
    out = to_img(img).convert("RGBA")
    d = ImageDraw.Draw(out, "RGBA")
    for _ in range(2400):
        x, y = rng.random() * w, rng.random() * h
        col = [(246, 244, 236), (246, 214, 80), (236, 236, 250)][rng.integers(0, 3)]
        rr = rng.uniform(1.5, 3.2)
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=col + (220,))
    return out.convert("RGB").filter(ImageFilter.GaussianBlur(0.6))


MIST = (150, 146, 170)   # Spectra's pale violet haze


def grave_grass(seed):
    """Spectra's ground: dull dark grass, bare earth worn through in patches, a faint pale mist over it."""
    rng = np.random.default_rng(seed)
    img = mix((42, 56, 38), (76, 90, 58), np.clip((fbm(N, N, rng, 3) - 0.3) * 2.0, 0, 1))
    bare = np.clip((fbm(N, N, rng, 5, 4) - 0.58) * 4, 0, 1)
    img = img + (mix((56, 47, 38), (78, 66, 52), fbm(N, N, rng, 12, 3)) - img) * (0.85 * bare)[..., None]
    img *= (0.92 + 0.16 * fbm(N, N, rng, 16, 3))[..., None]
    mist = np.clip((fbm(N, N, rng, 2, 3) - 0.45) * 1.6, 0, 1) * 0.18
    img = img + (np.array(MIST, np.float32) - img) * mist[..., None]
    out = to_img(img)
    d = ImageDraw.Draw(out, "RGBA")
    for _ in range(2200):                                   # blades
        x, y = rng.random() * N, rng.random() * N
        ang = rng.normal(-np.pi / 2, 0.7)
        ln = rng.uniform(4, 11)
        col = (110, 126, 84, 110) if rng.random() < 0.5 else (24, 34, 22, 120)
        d.line([(x, y), (x + ln * np.cos(ang), y + ln * np.sin(ang))], fill=col, width=2)
    for _ in range(70):                                     # dead leaves and small stones
        x, y, r = rng.random() * N, rng.random() * N, rng.uniform(2, 5)
        col = (96, 74, 46, 170) if rng.random() < 0.6 else (118, 114, 122, 170)
        d.ellipse([x - r, y - r * 0.7, x + r, y + r * 0.7], fill=col)
    return out.filter(ImageFilter.GaussianBlur(0.5))


def crypt_top():
    """Spectra's crypt roofs: dark grey-violet stone slabs with pale lichen."""
    rng = np.random.default_rng(201)
    img = stone_blocks(N, N, rng, 4, base=(84, 80, 92))
    lichen = np.clip((fbm(N, N, rng, 6, 3) - 0.62) * 4, 0, 1)
    img = img + (np.array((122, 130, 102), np.float32) - img) * (0.5 * lichen)[..., None]
    out = to_img(img)
    d = ImageDraw.Draw(out, "RGBA")
    for _ in range(400):                                    # speckles
        x, y, r = rng.random() * N, rng.random() * N, rng.uniform(0.8, 2.0)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(40, 36, 48, 90) if rng.random() < 0.6 else (160, 156, 170, 80))
    return out.filter(ImageFilter.GaussianBlur(0.5))


def crypt_wall():
    """The crypts' sides: dark stone courses, damp and darker toward the ground, moss creeping up from the bottom
    (seamless left-right)."""
    rng = np.random.default_rng(203)
    h, w = 1024, N
    img = stone_blocks(h, w, rng, 8, base=(82, 78, 90))
    rows = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    img *= (1.0 - 0.28 * rows)[..., None]
    moss = np.clip((fbm(h, w, rng, 5, 4, wrap_x=True) - 0.45) * 3, 0, 1) * np.clip((rows - 0.55) * 2.5, 0, 1)
    green = mix((38, 60, 34), (68, 90, 50), fbm(h, w, rng, 12, 3, wrap_x=True))
    img = img + (green - img) * (0.8 * moss)[..., None]
    return to_img(img).filter(ImageFilter.GaussianBlur(0.6))


def graveyard_table():
    """Around Spectra: dark graveyard grass in a pale mist, loose rows of small weathered headstones."""
    rng = np.random.default_rng(207)
    h, w = 1211, 2048
    img = mix((28, 38, 28), (56, 68, 46), fbm(h, w, rng, 4, 5))
    img *= (0.9 + 0.2 * fbm(h, w, rng, 40, 2))[..., None]
    out = to_img(img)
    d = ImageDraw.Draw(out, "RGBA")
    for _ in range(9000):                                   # blades
        x, y = rng.random() * w, rng.random() * h
        ang = rng.normal(-np.pi / 2, 0.7)
        ln = rng.uniform(5, 14)
        col = (96, 112, 74, 100) if rng.random() < 0.5 else (18, 26, 16, 110)
        d.line([(x, y), (x + ln * np.cos(ang), y + ln * np.sin(ang))], fill=col, width=2)
    for y in range(70, h, 125):                             # headstones, seen from above and a little in front
        x = rng.uniform(0, 70)
        while x < w:
            if rng.random() < 0.7:
                sx, sy = x + rng.uniform(-14, 14), y + rng.uniform(-12, 12)
                sw, sh = rng.uniform(26, 40), rng.uniform(16, 24)
                grey = rng.uniform(96, 140)
                d.ellipse([sx - sw * 0.7, sy + sh * 0.2, sx + sw * 0.8, sy + sh * 1.1], fill=(8, 12, 8, 110))   # shadow
                d.rounded_rectangle([sx - sw / 2, sy - sh / 2, sx + sw / 2, sy + sh / 2], radius=sw * 0.35,
                                    fill=(int(grey), int(grey), int(grey + 8), 255), outline=(40, 40, 46, 255), width=2)
                if rng.random() < 0.25:                     # a cross carved in it
                    d.line([(sx, sy - sh * 0.3), (sx, sy + sh * 0.3)], fill=(60, 60, 66, 255), width=3)
                    d.line([(sx - sw * 0.18, sy - sh * 0.08), (sx + sw * 0.18, sy - sh * 0.08)], fill=(60, 60, 66, 255), width=3)
            x += rng.uniform(110, 190)
    img = np.asarray(out, np.float32)
    mist = np.clip((fbm(h, w, rng, 3, 4) - 0.4) * 1.4, 0, 1) * 0.3
    img = img + (np.array(MIST, np.float32) - img) * mist[..., None]
    return to_img(img).filter(ImageFilter.GaussianBlur(0.8))


RUST = ((104, 58, 32), (150, 88, 46))


def rusted(img, rng, h, w, amount=0.75, cut=0.58, wrap_x=False):
    """Rust over steel in patches."""
    rust = np.clip((fbm(h, w, rng, 5, 4, wrap_x=wrap_x) - cut) * 3.5, 0, 1)
    return img + (mix(*RUST, fbm(h, w, rng, 14, 3, wrap_x=wrap_x)) - img) * (amount * rust)[..., None]


def rivet(d, x, y, r=4.0):
    d.ellipse([x - r, y - r, x + r, y + r], fill=(70, 66, 62, 255), outline=(30, 28, 26, 255))
    d.ellipse([x - r * 0.6, y - r * 0.7, x, y - r * 0.1], fill=(170, 164, 156, 200))


def tread_plate(seed):
    """Valora's floor: weathered steel tread plate (raised lugs in a herringbone), rust in patches."""
    rng = np.random.default_rng(seed)
    img = mix((88, 87, 86), (118, 115, 110), fbm(N, N, rng, 4, 4))
    out = to_img(rusted(img, rng, N, N, 0.7, 0.6)).convert("RGBA")
    d = ImageDraw.Draw(out, "RGBA")
    step = 32
    for gy in range(-1, N // step + 1):
        for gx in range(-1, N // step + 1):
            cx, cy = gx * step + step / 2, gy * step + step / 2
            s = 1 if (gx + gy) % 2 == 0 else -1
            dx, dy = 9 * s, 9
            d.line([(cx - dx + 1.5, cy - dy + 1.5), (cx + dx + 1.5, cy + dy + 1.5)], fill=(30, 28, 26, 150), width=5)
            d.line([(cx - dx, cy - dy), (cx + dx, cy + dy)], fill=(150, 146, 140, 170), width=4)
    return out.convert("RGB").filter(ImageFilter.GaussianBlur(0.6))


def iron_top():
    """Valora's wall tops: heavy dark iron plates with rivets along the seams, a little rust."""
    rng = np.random.default_rng(221)
    img = mix((56, 55, 58), (82, 78, 76), fbm(N, N, rng, 4, 4))
    out = to_img(rusted(img, rng, N, N, 0.55, 0.62)).convert("RGBA")
    d = ImageDraw.Draw(out, "RGBA")
    for k in (0, N // 2, N):
        d.line([(k, 0), (k, N)], fill=(24, 22, 22, 255), width=5)
        d.line([(0, k), (N, k)], fill=(24, 22, 22, 255), width=5)
        for t in range(16, N, 32):
            rivet(d, k + (10 if k < N else -10), t)
            rivet(d, t, k + (10 if k < N else -10))
    return out.convert("RGB").filter(ImageFilter.GaussianBlur(0.5))


def iron_wall():
    """Valora's wall sides: riveted iron panels, rust running down from the rivets, grime at the foot (seamless
    left-right)."""
    rng = np.random.default_rng(223)
    h, w = 1024, N
    img = mix((60, 58, 60), (86, 82, 80), fbm(h, w, rng, 4, 4, wrap_x=True))
    img = rusted(img, rng, h, w, 0.45, 0.64, wrap_x=True)
    img *= (1.0 - 0.3 * np.linspace(0, 1, h, dtype=np.float32) ** 2)[:, None, None]
    out = to_img(img).convert("RGBA")
    d = ImageDraw.Draw(out, "RGBA")
    for y in (0, 256, 512, 768):
        d.line([(0, y), (w, y)], fill=(22, 20, 20, 255), width=5)
    for x in (0, w // 2, w):
        d.line([(x, 0), (x, h)], fill=(22, 20, 20, 255), width=5)
    for y in (0, 256, 512, 768):
        for x in range(16, w, 32):
            rivet(d, x, y + 12)
            if rng.random() < 0.3:                                    # a rust streak running down from it
                ln = rng.uniform(40, 160)
                d.line([(x, y + 16), (x + rng.uniform(-3, 3), y + 16 + ln)], fill=(130, 70, 36, 90), width=3)
    return out.convert("RGB").filter(ImageFilter.GaussianBlur(0.6))


def foundry_table():
    """Around Valora: a dark foundry floor of big riveted steel plates, grime, and glowing ore channels running down
    the side strips beside the board."""
    rng = np.random.default_rng(227)
    h, w = 1211, 2048
    img = mix((36, 36, 38), (62, 60, 58), fbm(h, w, rng, 5, 5))
    img = rusted(img, rng, h, w, 0.35, 0.62)
    out = to_img(img).convert("RGBA")
    d = ImageDraw.Draw(out, "RGBA")
    for x in range(0, w + 1, 160):
        d.line([(x, 0), (x, h)], fill=(16, 16, 16, 255), width=4)
    for y in range(0, h + 1, 160):
        d.line([(0, y), (w, y)], fill=(16, 16, 16, 255), width=4)
    for x in range(0, w + 1, 160):
        for y in range(0, h + 1, 160):
            for ox, oy in ((10, 10), (-10, 10), (10, -10), (-10, -10)):
                rivet(d, x + ox, y + oy, 4.5)
    img = np.asarray(out.convert("RGB"), np.float32)
    xx = np.arange(w, dtype=np.float32)[None, :]
    wob = 14 * np.sin(np.arange(h, dtype=np.float32)[:, None] / 37.0)
    for cx in (210, w - 210):                                       # molten channels, a soft glow round them
        dist = np.abs(xx - cx - wob)
        glow = np.exp(-(dist / 46) ** 2)[..., None]
        core = np.clip(1 - dist / 16, 0, 1)[..., None]
        img = img + (np.array((255, 120, 30), np.float32) - img) * (0.55 * glow)
        img = img + (np.array((255, 214, 120), np.float32) - img) * core
    return to_img(img).filter(ImageFilter.GaussianBlur(0.8))


def pebble(d, x, y, r, rng):
    g = rng.uniform(70, 120)
    d.ellipse([x - r, y - r * 0.75, x + r, y + r * 0.75], fill=(int(g), int(g * 0.9), int(g * 0.8), 230),
              outline=(30, 24, 18, 160))
    d.ellipse([x - r * 0.5, y - r * 0.55, x, y - r * 0.1], fill=(190, 176, 156, 110))


def hive_floor(seed):
    """Terrera's floors: packed dark earth of the old Durant hive, grit and small stones, claw scratches."""
    rng = np.random.default_rng(seed)
    img = mix((88, 66, 46), (124, 98, 70), fbm(N, N, rng, 4, 4))
    img *= (0.9 + 0.2 * fbm(N, N, rng, 20, 3))[..., None]
    out = to_img(img)
    d = ImageDraw.Draw(out, "RGBA")
    for _ in range(1600):                                     # grit
        x, y = rng.random() * N, rng.random() * N
        d.point((x, y), fill=(40, 28, 18, 140) if rng.random() < 0.5 else (170, 140, 104, 140))
    for _ in range(70):
        pebble(d, rng.random() * N, rng.random() * N, rng.uniform(2, 6), rng)
    for _ in range(9):                                        # claw scratches: three parallel strokes
        x, y, a = rng.random() * N, rng.random() * N, rng.uniform(0, np.pi)
        ln = rng.uniform(26, 50)
        for k in (-6, 0, 6):
            ox, oy = -np.sin(a) * k, np.cos(a) * k
            d.line([(x + ox, y + oy), (x + ox + np.cos(a) * ln, y + oy + np.sin(a) * ln)], fill=(48, 34, 22, 150), width=2)
    return out.filter(ImageFilter.GaussianBlur(0.5))


def quicksand():
    """Quicksand: pale wet sand in curving ripples, darker where it's wettest."""
    rng = np.random.default_rng(241)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32) / N
    warp = fbm(N, N, rng, 3, 3)
    dist = np.hypot(xx - 0.5 + 0.2 * (warp - 0.5), yy - 0.5 + 0.2 * (warp - 0.5))
    rip = 0.5 + 0.5 * np.sin(dist * 48 + warp * 6)
    img = mix((158, 126, 86), (200, 170, 122), 0.6 * rip + 0.4 * fbm(N, N, rng, 6, 3))
    wet = np.clip((fbm(N, N, rng, 3, 3) - 0.5) * 2.5, 0, 1)
    img = img + (np.array((112, 86, 56), np.float32) - img) * (0.5 * wet)[..., None]
    return to_img(img).filter(ImageFilter.GaussianBlur(0.8))


def strata():
    """Terrera's cliffs and the boards' edges: layered earth and rock, wavy bands, seamless left-right."""
    rng = np.random.default_rng(243)
    h, w = 1024, N
    warp = fbm(h, w, rng, 3, 4, wrap_x=True)
    rows = np.arange(h, dtype=np.float32)[:, None] / h
    bands = 0.5 + 0.5 * np.sin((rows * 11 + warp * 1.4) * 2 * np.pi)
    t = 0.55 * bands + 0.45 * fbm(h, w, rng, 6, 4, wrap_x=True)
    img = mix((64, 48, 34), (138, 108, 78), t)
    img *= (0.88 + 0.24 * fbm(h, w, rng, 32, 2, wrap_x=True))[..., None]
    return to_img(img).filter(ImageFilter.GaussianBlur(0.6))


def cave_table():
    """Around Terrera: the hive's dark cave floor, loose rocks, and the mouths of Durant tunnels."""
    rng = np.random.default_rng(247)
    h, w = 1211, 2048
    img = mix((34, 26, 20), (66, 52, 40), fbm(h, w, rng, 5, 5))
    img *= (0.9 + 0.2 * fbm(h, w, rng, 40, 2))[..., None]
    out = to_img(img)
    d = ImageDraw.Draw(out, "RGBA")
    for _ in range(260):
        pebble(d, rng.random() * w, rng.random() * h, rng.uniform(3, 12), rng)
    for _ in range(26):                                       # tunnel mouths: dark holes with a raised rim
        x, y, r = rng.random() * w, rng.random() * h, rng.uniform(26, 60)
        for k, col in ((1.25, (96, 74, 52, 255)), (1.05, (40, 28, 18, 255)), (0.8, (20, 13, 8, 255)), (0.5, (8, 5, 3, 255))):
            d.ellipse([x - r * k, y - r * k * 0.8, x + r * k, y + r * k * 0.8], fill=col)
    return out.filter(ImageFilter.GaussianBlur(0.8))


def rock_ridge():
    """The rock ridge between Terrera's boards: rough grey-brown rock, lumpy (shaded as if lit from the top left),
    cracks running through it. 512 px = 4 tiles."""
    rng = np.random.default_rng(257)
    hgt = fbm(N, N, rng, 6, 5)                                     # a height field: lumps
    gy, gx = np.gradient(hgt)
    light = np.clip(0.5 - (gx + gy) * 18, 0, 1)                    # lit from the top left
    img = mix((70, 60, 52), (134, 120, 104), 0.55 * hgt + 0.45 * light)
    img *= (0.9 + 0.2 * fbm(N, N, rng, 30, 2))[..., None]
    out = to_img(img)
    d = ImageDraw.Draw(out, "RGBA")
    for _ in range(16):                                            # cracks
        x, y, ang = rng.random() * N, rng.random() * N, rng.random() * 2 * np.pi
        pts = [(x, y)]
        for _ in range(rng.integers(6, 14)):
            ang += rng.normal(0, 0.5)
            x, y = x + 10 * np.cos(ang), y + 10 * np.sin(ang)
            pts.append((x, y))
        d.line(pts, fill=(30, 24, 20, 200), width=3)
        d.line([(px + 1, py + 1) for px, py in pts], fill=(170, 156, 138, 80), width=1)
    for _ in range(40):
        pebble(d, rng.random() * N, rng.random() * N, rng.uniform(3, 8), rng)
    return out.filter(ImageFilter.GaussianBlur(0.6))


HEDGE_GREENS = [(34, 78, 30), (46, 96, 36), (60, 112, 42), (28, 64, 26), (78, 128, 50)]


def blossom(d, x, y, r, col, centre=(246, 206, 60)):
    """A small five-petal flower seen from above."""
    for k in range(5):
        a = k * 2 * np.pi / 5
        px, py = x + np.cos(a) * r * 0.55, y + np.sin(a) * r * 0.55
        d.ellipse([px - r * 0.5, py - r * 0.5, px + r * 0.5, py + r * 0.5], fill=col + (235,))
    d.ellipse([x - r * 0.32, y - r * 0.32, x + r * 0.32, y + r * 0.32], fill=centre + (255,))


def lawn(seed):
    """Greenleaf's ground: a well-kept garden lawn, lush and even, a little clover and the odd daisy."""
    rng = np.random.default_rng(seed)
    img = mix((66, 122, 46), (104, 160, 64), np.clip((fbm(N, N, rng, 3) - 0.3) * 2.0, 0, 1))
    img *= (0.93 + 0.14 * fbm(N, N, rng, 16, 3))[..., None]
    out = to_img(img).convert("RGBA")
    d = ImageDraw.Draw(out, "RGBA")
    for _ in range(3000):                                   # blades
        x, y = rng.random() * N, rng.random() * N
        ang = rng.normal(-np.pi / 2, 0.6)
        ln = rng.uniform(5, 12)
        col = (150, 204, 96, 110) if rng.random() < 0.5 else (36, 80, 26, 110)
        d.line([(x, y), (x + ln * np.cos(ang), y + ln * np.sin(ang))], fill=col, width=2)
    clover_patches(d, rng, N, N, int(rng.integers(1, 3)), 0.8)
    for _ in range(int(rng.integers(4, 9))):                # daisies
        blossom(d, rng.random() * N, rng.random() * N, rng.uniform(5, 7), (248, 248, 242))
    return out.convert("RGB").filter(ImageFilter.GaussianBlur(0.5))


def hedge_leaves(d, rng, w, h, count, size, wrap_y=True, light_top=0.0):
    """Packed little leaves for a clipped hedge, drawn again across the edges so the image tiles (left-right, and
    top-bottom with wrap_y). light_top: leaves near the top come out lighter (the clipped top of a hedge's side)."""
    for _ in range(count):
        x, y = rng.random() * w, rng.random() * h
        col = HEDGE_GREENS[rng.integers(0, len(HEDGE_GREENS))]
        k = rng.uniform(0.8, 1.15) * (1 + light_top * max(0.0, 1 - y / (0.25 * h)))
        col = tuple(min(255, int(v * k)) for v in col) + (240,)
        ln, ang = rng.uniform(0.7, 1.3) * size, rng.random() * 6.3
        for dx in (-w, 0, w):
            for dy in ((-h, 0, h) if wrap_y else (0,)):
                leaf(d, x + dx, y + dy, ln, ang, col)


def hedge_top():
    """The top of Greenleaf's hedges: densely clipped small leaves, seamless both ways."""
    rng = np.random.default_rng(261)
    out = to_img(mix((18, 40, 16), (30, 60, 24), fbm(N, N, rng, 4, 3))).convert("RGBA")
    hedge_leaves(ImageDraw.Draw(out, "RGBA"), rng, N, N, 3400, 17)
    img = np.asarray(out.convert("RGB"), np.float32) * (0.9 + 0.16 * fbm(N, N, rng, 3, 2))[..., None]
    return to_img(img).filter(ImageFilter.GaussianBlur(0.5))


def hedge_wall():
    """The hedges' sides (two levels tall, a tile across): packed leaves, lighter along the clipped top, shadowed
    toward the ground, seamless left-right."""
    rng = np.random.default_rng(263)
    h, w = 640, 1024
    out = to_img(mix((14, 32, 12), (26, 52, 20), fbm(h, w, rng, 4, 3, wrap_x=True))).convert("RGBA")
    hedge_leaves(ImageDraw.Draw(out, "RGBA"), rng, w, h, 5200, 30, wrap_y=False, light_top=0.25)
    img = np.asarray(out.convert("RGB"), np.float32)
    img *= np.linspace(1.04, 0.62, h, dtype=np.float32)[:, None, None]
    return to_img(img).filter(ImageFilter.GaussianBlur(0.6))


def creek():
    """The creek under Greenleaf's grass bridge: clear green-blue water, ripples, a few lily pads."""
    rng = np.random.default_rng(265)
    t = fbm(N, N, rng, 3, 5)
    rip = 0.5 + 0.5 * np.sin((t * 6 + fbm(N, N, rng, 2) * 2) * 2 * np.pi)
    img = mix((26, 84, 96), (58, 136, 146), 0.65 * t + 0.35 * rip)
    img = img + (np.array((206, 236, 236), np.float32) - img) * (0.3 * np.clip((rip - 0.85) / 0.15, 0, 1))[..., None]
    out = to_img(img).convert("RGBA")
    d = ImageDraw.Draw(out, "RGBA")
    for _ in range(4):                                      # lily pads: a disc with a notch, a darker rim
        x, y, r = rng.uniform(60, N - 60), rng.uniform(60, N - 60), rng.uniform(26, 40)
        a = rng.uniform(0, 360)
        d.ellipse([x - r + 3, y - r + 4, x + r + 3, y + r + 4], fill=(10, 40, 46, 90))
        d.pieslice([x - r, y - r, x + r, y + r], a + 18, a + 342, fill=(70, 130, 52, 255), outline=(40, 86, 34, 255), width=3)
        for k in range(5):
            b = np.radians(a + 40 + k * 60)
            d.line([(x, y), (x + np.cos(b) * r * 0.8, y + np.sin(b) * r * 0.8)], fill=(56, 108, 42, 200), width=2)
        if rng.random() < 0.5:
            blossom(d, x + r * 0.3, y - r * 0.2, 11, (246, 196, 222))
    return out.convert("RGB").filter(ImageFilter.GaussianBlur(0.7))


def garden_soil():
    """The creek's banks and the board's edge under the lawn: dark garden soil, small stones and roots, seamless
    left-right."""
    rng = np.random.default_rng(267)
    out = to_img(mix((58, 40, 26), (92, 66, 42), fbm(N, N, rng, 4, 5, wrap_x=True))).convert("RGBA")
    d = ImageDraw.Draw(out, "RGBA")
    for _ in range(26):                                     # roots: wavy thin strands
        x, y, ang = rng.random() * N, rng.random() * N, rng.uniform(0.3, 2.8)
        pts = [(x, y)]
        for _ in range(int(rng.integers(5, 12))):
            ang += rng.normal(0, 0.45)
            x, y = x + 9 * np.cos(ang), y + 9 * np.sin(ang)
            pts.append((x, y))
        for dx in (-N, 0, N):
            d.line([(px + dx, py) for px, py in pts], fill=(140, 110, 72, 170), width=2)
    for _ in range(160):                                    # stones
        x, y, r = rng.random() * N, rng.random() * N, rng.uniform(2, 7)
        col = [(118, 108, 96), (92, 84, 76), (140, 128, 110)][rng.integers(0, 3)] + (230,)
        for dx in (-N, 0, N):
            d.ellipse([x + dx - r, y - r * 0.75, x + dx + r, y + r * 0.75], fill=col)
    return out.convert("RGB").filter(ImageFilter.GaussianBlur(0.6))


def garden_table():
    """Around Greenleaf: more lawn, darker, with round flower beds (dark soil, blooms in many colours) and low
    shrubs."""
    rng = np.random.default_rng(269)
    h, w = 1211, 2048
    t = fbm(h, w, rng, 6, 5)
    img = mix((50, 98, 36), (90, 146, 58), np.clip((t - 0.3) * 2.0, 0, 1)) * 0.85
    out = to_img(img).convert("RGBA")
    d = ImageDraw.Draw(out, "RGBA")
    beds = [(246, 92, 98), (250, 196, 64), (180, 110, 230), (246, 150, 196), (250, 250, 244), (98, 150, 240)]
    placed = []
    for _ in range(400):                                    # beds that don't touch each other
        if len(placed) >= 30:
            break
        x, y = rng.random() * w, rng.random() * h
        rx, ry = rng.uniform(60, 110), rng.uniform(45, 80)
        if any(((x - px) / (rx + prx + 40)) ** 2 + ((y - py) / (ry + pry + 40)) ** 2 < 1 for px, py, prx, pry in placed):
            continue
        placed.append((x, y, rx, ry))
    for x, y, rx, ry in placed:
        d.ellipse([x - rx - 6, y - ry - 6, x + rx + 6, y + ry + 6], fill=(128, 120, 104, 255))   # stone edging
        d.ellipse([x - rx, y - ry, x + rx, y + ry], fill=(54, 38, 26, 255))
        col = beds[rng.integers(0, len(beds))]
        for _ in range(int(rx * ry / 90)):
            a, k = rng.random() * 6.3, np.sqrt(rng.random()) * 0.9
            fx, fy = x + np.cos(a) * rx * k, y + np.sin(a) * ry * k
            leaf(d, fx, fy, rng.uniform(10, 16), rng.random() * 6.3, LEAF_GREENS[rng.integers(0, 5)] + (255,))
            blossom(d, fx + rng.normal(0, 3), fy + rng.normal(0, 3), rng.uniform(5, 8), col)
    for _ in range(30):                                     # low round shrubs, between the beds
        x, y, r = rng.random() * w, rng.random() * h, rng.uniform(30, 55)
        if any(((x - px) / (prx + r + 10)) ** 2 + ((y - py) / (pry + r + 10)) ** 2 < 1 for px, py, prx, pry in placed):
            continue
        d.ellipse([x - r + 6, y - r + 8, x + r + 6, y + r + 8], fill=(14, 30, 12, 120))
        for _ in range(int(r * 6)):
            a, k = rng.random() * 6.3, np.sqrt(rng.random())
            leaf(d, x + np.cos(a) * r * k, y + np.sin(a) * r * k, rng.uniform(10, 18), rng.random() * 6.3,
                 HEDGE_GREENS[rng.integers(0, len(HEDGE_GREENS))] + (250,))
    return out.convert("RGB").filter(ImageFilter.GaussianBlur(0.7))


def main():
    files = {
        "arenas/greenleaf/textures/lawn1.png": lambda p: lawn(271).save(p),
        "arenas/greenleaf/textures/lawn2.png": lambda p: lawn(272).save(p),
        "arenas/greenleaf/textures/hedge-top.png": lambda p: hedge_top().save(p),
        "arenas/greenleaf/textures/hedge-wall.png": lambda p: hedge_wall().save(p),
        "arenas/greenleaf/textures/creek.png": lambda p: creek().save(p),
        "arenas/greenleaf/textures/soil.png": lambda p: garden_soil().save(p),
        "misc/garden-placeholder-v1.jpg": lambda p: garden_table().save(p, quality=90),
        "arenas/terrera/textures/rock.png": lambda p: rock_ridge().save(p),
        "arenas/terrera/textures/hive1.png": lambda p: hive_floor(251).save(p),
        "arenas/terrera/textures/hive2.png": lambda p: hive_floor(252).save(p),
        "arenas/terrera/textures/quicksand.png": lambda p: quicksand().save(p),
        "arenas/terrera/textures/strata.png": lambda p: strata().save(p),
        "misc/cave-placeholder-v1.jpg": lambda p: cave_table().save(p, quality=90),
        "arenas/valora/textures/tread1.png": lambda p: tread_plate(231).save(p),
        "arenas/valora/textures/tread2.png": lambda p: tread_plate(232).save(p),
        "arenas/valora/textures/iron-top.png": lambda p: iron_top().save(p),
        "arenas/valora/textures/iron-wall.png": lambda p: iron_wall().save(p),
        "misc/foundry-placeholder-v1.jpg": lambda p: foundry_table().save(p, quality=90),
        "arenas/spectra/textures/grave-grass1.png": lambda p: grave_grass(211).save(p),
        "arenas/spectra/textures/grave-grass2.png": lambda p: grave_grass(212).save(p),
        "arenas/spectra/textures/crypt-top.png": lambda p: crypt_top().save(p),
        "arenas/spectra/textures/crypt-wall.png": lambda p: crypt_wall().save(p),
        "misc/graveyard-placeholder-v1.jpg": lambda p: graveyard_table().save(p, quality=90),
        "arenas/fontaine/textures/grass1.png": lambda p: grass(31).save(p),
        "arenas/fontaine/textures/grass2.png": lambda p: grass(32).save(p),
        "arenas/fontaine/textures/pebbles.png": lambda p: pebbles().save(p),
        "arenas/fontaine/textures/canal-wall.png": lambda p: canal_wall().save(p),
        "misc/valley-placeholder-v1.jpg": lambda p: valley_table().save(p, quality=90),
        "arenas/violight/textures/steel1.png": lambda p: steel_plate(171).save(p),
        "arenas/violight/textures/steel2.png": lambda p: steel_plate(172).save(p),
        "arenas/violight/textures/electric1.png": lambda p: electric_panel(175).save(p),
        "arenas/violight/textures/electric2.png": lambda p: electric_panel(176).save(p),
        "arenas/violight/textures/spire-top.png": lambda p: spire_top().save(p),
        "arenas/violight/textures/spire-wall.png": lambda p: spire_wall().save(p),
        "misc/violight-placeholder-v1.jpg": lambda p: violight_table().save(p, quality=90),
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
