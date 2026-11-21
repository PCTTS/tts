"""Build the table props: the slanted team stand (pedestals on top, item/skill cards on the slope) and a pillar.

Usage:  python -I tools/build_props.py
Writes props/stand-v3.obj (with an HP sign above each pedestal; stand-v2 = without) (+ its solid collider
props/stand-collider-v1.obj) with its dark wood texture
props/stand-wood-v1.jpg, props/pillar-v2.obj with props/props-v1.jpg, and props/stand-v1.json (slot positions the
TTS script uses: pedestals on top, two card slots per pedestal on the slope; the geometry is unchanged since v1).
Published files are only written when missing: bump a file's version when what it holds changes (TTS caches by
link). stand-v1.obj (the light stand on props-v1.jpg) stays published for saves made before the wood.

Stand, in its own frame (as placed on the near/south trim): the back face (toward the board) is z = 0 and the
stand extends toward -z (toward the player); y = 0 is the table top. Cross-section: a flat top for the
pedestals, a slope down toward the player for the cards, and a small lip at the bottom so cards don't slide.
The far/north stand is the same model turned 180 degrees.
"""
import json, math, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_standee import StandeeMesh  # noqa: E402  (quad + tri; OBJ with TTS's X mirroring handled)

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "props"
SLOTS, SLOT_W = 6, 7.05          # pedestal columns and their spacing (the original pedestal spacing)
LENGTH = SLOTS * SLOT_W
TOP_H, TOP_D = 2.6, 3.2          # top surface height above the table, and its depth
RUN, LOW_H = 7.6, 0.35           # slope: horizontal run toward the player, height at its bottom
LIP_H, LIP_W = 0.22, 0.25        # lip at the bottom of the slope
CARD_SCALE = 1.5                 # cards lie landscape: 3.06 x 2.19 at scale 1
CARD_ALONG = 2.19 * CARD_SCALE   # card size along the slope
SNAP_LIFT = 0.55                 # card snap points float this far off the slope: a card held flat clears it
PILLAR_H, SEG = 2.6, 96          # pillar height (level with the stand top), segments around
TEX_W, TEX_H = 1024, 256         # texture: four 256px regions
REGIONS = {"top": 0, "slope": 1, "side": 2, "pillar": 3}
COLOURS = {"top": "#CDB38A", "slope": "#BFA27A", "side": "#8E6C48", "pillar": "#B39572"}
# The stand's dark wood, made to look like the custom table's frame (our own texture, not TTS's file). Every face
# gets wood at the same scale, grain along the stand's length: the faces are laid out as strips across the texture.
WOOD_W, WOOD_H, WOOD_SEED = 4096, 2048, 7
WOOD_BASE, WOOD_LIGHT, WOOD_DARK = (40, 20, 11), (80, 44, 27), (19, 9, 5)
WOOD_GRAIN, WOOD_CONTRAST = 1.0, 1.25            # streak width (x the finest), streak strength
WOOD_PAD = 0.1                                  # wood (in units) between neighbouring faces in the texture
# HP signs (stand-v3): above each pedestal, a thin board on a post near the back edge of the stand top. Global.lua
# shows the HP of the Pokemon on that pedestal on both faces (the stand's object UI); the solid board hides the
# far face's label, so each side reads the right way round.
PEDESTAL_TOP = 0.25                     # the pedestals' height above the stand top (Global.lua PEDESTAL_TOP)
SIGN_W, SIGN_H, SIGN_D = 1.7, 0.5, 0.04
SIGN_Y = TOP_H + PEDESTAL_TOP + 2.55    # the board's centre: just above a standee's art
SIGN_Z = -0.16                          # its middle, near the back edge of the top
POST_W = 0.1
PPU = WOOD_W / (LENGTH + 2 * WOOD_PAD)          # texture pixels per unit


def region_uv(name, fu, fv):
    """fu, fv in 0..1 within a region -> texture UV."""
    i = REGIONS[name]
    return ((i * 256 + 2 + fu * 252) / TEX_W, 1 - (2 + fv * 252) / TEX_H)


def face(m, name, corners, normal):
    m.quad(corners, [region_uv(name, 0, 0), region_uv(name, 1, 0), region_uv(name, 1, 1), region_uv(name, 0, 1)], normal)


def wood_rows():
    """Where each stand face's strip starts in the wood texture (units from the top), in layout order."""
    sizes = [("top", TOP_D), ("slope", math.hypot(RUN, TOP_H - LOW_H)), ("back", TOP_H), ("front", LOW_H + LIP_H),
             ("lip_in", LIP_H), ("lip_top", LIP_W), ("cap", TOP_H)]
    rows, v = {}, WOOD_PAD
    for name, size in sizes:
        rows[name] = v
        v += size + WOOD_PAD
    assert v * PPU <= WOOD_H, "the stand's faces don't fit in the wood texture"
    return rows


ROWS = wood_rows()


def wood_uv(row, a, b):
    """a units along the grain, b units across it, within a face's strip -> texture UV."""
    return ((WOOD_PAD + a) * PPU / WOOD_W, 1 - (ROWS[row] + b) * PPU / WOOD_H)


def wood_face(m, row, corners, normal, width):
    """A face along the whole stand: corners 0-1 are one long edge, 2-3 the other, `width` units apart."""
    m.quad(corners, [wood_uv(row, 0, 0), wood_uv(row, LENGTH, 0), wood_uv(row, LENGTH, width), wood_uv(row, 0, width)], normal)


def stand(signs=False):
    m = StandeeMesh()
    x0, x1 = -LENGTH / 2, LENGTH / 2
    zc, zd = -TOP_D, -TOP_D - RUN          # top front edge, slope bottom
    ze = zd - LIP_W                        # front of the lip
    yl = LOW_H + LIP_H                     # top of the lip
    slope_n = (0, RUN, -(TOP_H - LOW_H))
    ln = math.hypot(slope_n[1], slope_n[2])
    slope_n = (0, slope_n[1] / ln, slope_n[2] / ln)
    wood_face(m, "top", [(x0, TOP_H, 0), (x1, TOP_H, 0), (x1, TOP_H, zc), (x0, TOP_H, zc)], (0, 1, 0), TOP_D)
    wood_face(m, "slope", [(x0, TOP_H, zc), (x1, TOP_H, zc), (x1, LOW_H, zd), (x0, LOW_H, zd)], slope_n, math.hypot(RUN, TOP_H - LOW_H))
    wood_face(m, "lip_in", [(x0, yl, zd), (x1, yl, zd), (x1, LOW_H, zd), (x0, LOW_H, zd)], (0, 0, 1), LIP_H)
    wood_face(m, "lip_top", [(x0, yl, zd), (x1, yl, zd), (x1, yl, ze), (x0, yl, ze)], (0, 1, 0), LIP_W)
    wood_face(m, "front", [(x0, yl, ze), (x1, yl, ze), (x1, 0, ze), (x0, 0, ze)], (0, 0, -1), yl)
    wood_face(m, "back", [(x0, TOP_H, 0), (x1, TOP_H, 0), (x1, 0, 0), (x0, 0, 0)], (0, 0, 1), TOP_H)
    wood_face(m, "top", [(x0, 0, ze), (x1, 0, ze), (x1, 0, 0), (x0, 0, 0)], (0, -1, 0), TOP_D)  # bottom (never seen)
    # end caps: the main body (a convex pentagon, as a fan) plus the lip block; grain runs front to back
    def cap_uv(p):
        return wood_uv("cap", -p[2], TOP_H - p[1])
    for x, nx in ((x0, -1), (x1, 1)):
        body = [(x, 0, 0), (x, TOP_H, 0), (x, TOP_H, zc), (x, LOW_H, zd), (x, 0, zd)]
        for a, b in ((1, 2), (2, 3), (3, 4)):
            tri = [body[0], body[a], body[b]]
            m.tri(tri, [cap_uv(p) for p in tri], (nx, 0, 0))
        block = [(x, 0, zd), (x, yl, zd), (x, yl, ze), (x, 0, ze)]
        m.quad(block, [cap_uv(p) for p in block], (nx, 0, 0))
    if signs:
        for i in range(SLOTS):
            cx = (i - (SLOTS - 1) / 2) * SLOT_W
            base = 2 + i * 6.5
            sy0 = SIGN_Y - SIGN_H / 2
            wood_box(m, cx - POST_W / 2, cx + POST_W / 2, TOP_H, sy0, SIGN_Z - POST_W / 2, SIGN_Z + POST_W / 2, "y", (base, 18.5))
            wood_box(m, cx - SIGN_W / 2, cx + SIGN_W / 2, sy0, SIGN_Y + SIGN_H / 2, SIGN_Z - SIGN_D / 2, SIGN_Z + SIGN_D / 2,
                     "x", (base + 3.2, 18.5))
    return m


def wood_box(m, x0, x1, y0, y1, z0, z1, grain, base):
    """An axis-aligned box in the stand's wood at its real scale, grain along "x" or "y", `base` units into the
    texture (a free strip below the stand's faces)."""
    lo = {"x": x0, "y": y0, "z": z0}

    def uv(p, axes):
        if grain in axes:   # the grain runs along u when it lies in this face
            a, b = grain, axes[1] if axes[0] == grain else axes[0]
        else:
            a, b = axes
        return ((WOOD_PAD + base[0] + p[a] - lo[a]) * PPU / WOOD_W, 1 - (base[1] + p[b] - lo[b]) * PPU / WOOD_H)

    def quad(corners, axes, normal):
        pts = [dict(zip("xyz", c)) for c in corners]
        m.quad(corners, [uv(p, axes) for p in pts], normal)

    quad([(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)], ("x", "y"), (0, 0, -1))
    quad([(x0, y1, z1), (x1, y1, z1), (x1, y0, z1), (x0, y0, z1)], ("x", "y"), (0, 0, 1))
    quad([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], ("x", "z"), (0, 1, 0))
    quad([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], ("x", "z"), (0, -1, 0))
    quad([(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], ("y", "z"), (-1, 0, 0))
    quad([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], ("y", "z"), (1, 0, 0))


def stand_collider():
    """The stand's solid body without the lip (convex, so TTS treats it as a solid: a card flipped on the slope
    gets pushed back out instead of dropping through a hollow surface). The lip stays visual only."""
    m = StandeeMesh()
    x0, x1 = -LENGTH / 2, LENGTH / 2
    zc, zd = -TOP_D, -TOP_D - RUN
    slope_n = (0, RUN, -(TOP_H - LOW_H))
    ln = math.hypot(slope_n[1], slope_n[2])
    slope_n = (0, slope_n[1] / ln, slope_n[2] / ln)
    face(m, "top", [(x0, TOP_H, 0), (x1, TOP_H, 0), (x1, TOP_H, zc), (x0, TOP_H, zc)], (0, 1, 0))
    face(m, "slope", [(x0, TOP_H, zc), (x1, TOP_H, zc), (x1, LOW_H, zd), (x0, LOW_H, zd)], slope_n)
    face(m, "side", [(x0, LOW_H, zd), (x1, LOW_H, zd), (x1, 0, zd), (x0, 0, zd)], (0, 0, -1))
    face(m, "side", [(x0, 0, 0), (x1, 0, 0), (x1, TOP_H, 0), (x0, TOP_H, 0)], (0, 0, 1))
    face(m, "side", [(x0, 0, zd), (x1, 0, zd), (x1, 0, 0), (x0, 0, 0)], (0, -1, 0))
    for x, nx in ((x0, -1), (x1, 1)):
        body = [(x, 0, 0), (x, TOP_H, 0), (x, TOP_H, zc), (x, LOW_H, zd), (x, 0, zd)]
        for a, b in ((1, 2), (2, 3), (3, 4)):
            m.tri([body[0], body[a], body[b]], [region_uv("side", 0.5, 0.5)] * 3, (nx, 0, 0))
    return m


class SmoothMesh(StandeeMesh):
    def quad_smooth(self, corners, uvs, normals, facing):
        """A quad with one normal per corner (smooth shading); wound to face `facing` (world space)."""
        pts = [(-x, y, z) for x, y, z in corners]                  # TTS mirrors OBJ on X
        ns = [(-a, b, c) for a, b, c in normals]
        fn = (-facing[0], facing[1], facing[2])
        e1 = [pts[1][i] - pts[0][i] for i in range(3)]
        e2 = [pts[2][i] - pts[0][i] for i in range(3)]
        cross = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
        order = [0, 1, 2, 3] if sum(cross[i] * fn[i] for i in range(3)) > 0 else [3, 2, 1, 0]
        bv, bt, bn = len(self.v), len(self.vt), len(self.vn)
        self.v += [pts[i] for i in order]
        self.vt += [uvs[i] for i in order]
        self.vn += [ns[i] for i in order]
        idx = [(bv + k + 1, bt + k + 1, bn + k + 1) for k in range(4)]
        self.f.append((idx[0], idx[1], idx[2]))
        self.f.append((idx[0], idx[2], idx[3]))


# Pillar outline (radius, height), bottom to top: plinth, a bevel up to the shaft, the shaft, a bevel out to
# the capital. Unit shaft radius (scale x/z per object). Turned around the y axis with smooth shading around,
# crisp edges between the profile's segments.
PILLAR_PROFILE = [(1.25, 0.0), (1.25, 0.12), (1.15, 0.12), (1.15, 0.22), (1.0, 0.34), (1.0, PILLAR_H - 0.34),
                  (1.15, PILLAR_H - 0.22), (1.15, PILLAR_H - 0.12), (1.25, PILLAR_H - 0.12), (1.25, PILLAR_H)]


def pillar():
    m = SmoothMesh()
    ring = [(math.cos(2 * math.pi * i / SEG), math.sin(2 * math.pi * i / SEG)) for i in range(SEG + 1)]
    for (r0, y0), (r1, y1) in zip(PILLAR_PROFILE, PILLAR_PROFILE[1:]):
        dr, dy = r1 - r0, y1 - y0
        ln = math.hypot(dr, dy)
        nr, ny = dy / ln, -dr / ln          # outward normal of this profile segment, in the (radius, y) plane
        for i in range(SEG):
            (ca, sa), (cb, sb) = ring[i], ring[i + 1]
            corners = [(r0 * ca, y0, r0 * sa), (r0 * cb, y0, r0 * sb), (r1 * cb, y1, r1 * sb), (r1 * ca, y1, r1 * sa)]
            normals = [(nr * ca, ny, nr * sa), (nr * cb, ny, nr * sb), (nr * cb, ny, nr * sb), (nr * ca, ny, nr * sa)]
            fu0, fu1 = i / SEG, (i + 1) / SEG
            uvs = [region_uv("pillar", fu0, y0 / PILLAR_H), region_uv("pillar", fu1, y0 / PILLAR_H),
                   region_uv("pillar", fu1, y1 / PILLAR_H), region_uv("pillar", fu0, y1 / PILLAR_H)]
            mid = ((ca + cb) / 2, (sa + sb) / 2)
            m.quad_smooth(corners, uvs, normals, (nr * mid[0], ny, nr * mid[1]))
    top_r = PILLAR_PROFILE[-1][0]
    for y, ny in ((PILLAR_H, 1), (0.0, -1)):  # flat caps
        for i in range(SEG):
            (ca, sa), (cb, sb) = ring[i], ring[i + 1]
            m.tri([(0, y, 0), (top_r * ca, y, top_r * sa), (top_r * cb, y, top_r * sb)], [region_uv("top", 0.5, 0.5)] * 3, (0, ny, 0))
    return m


def texture():
    img = Image.new("RGB", (TEX_W, TEX_H))
    d = ImageDraw.Draw(img)
    for name, i in REGIONS.items():
        h = COLOURS[name]
        d.rectangle([i * 256, 0, i * 256 + 255, TEX_H], fill=tuple(int(h[k:k + 2], 16) for k in (1, 3, 5)))
    return ImageChops.add(img, Image.effect_noise((TEX_W, TEX_H), 8).convert("RGB"), 1.0, -128)


def smooth_noise(rng, w, h, cells_w, cells_h):
    """Random values on a (cells_w x cells_h) grid, smoothly stretched to w x h; roughly -1..1."""
    cells = (rng.random((max(2, cells_h), max(2, cells_w))) * 255).astype(np.uint8)
    return np.asarray(Image.fromarray(cells, "L").resize((w, h), Image.BICUBIC), dtype=np.float32) / 127.5 - 1


def wood_texture(w=WOOD_W, h=WOOD_H):
    """Straight-grained dark wood, grain running left to right: fine streaks that drift in strength along the
    grain, broad lighter/darker bands, a few long distinct streaks, and a gentle wave. Seeded: rebuilds match."""
    rng = np.random.default_rng(WOOD_SEED)
    pad = 64 * 2
    hh = h + 2 * pad                                   # room for the wave
    g = WOOD_GRAIN

    def across(n):                                     # noise cells across the grain for n-px streaks
        return max(2, round(hh / (n * g)))
    field = (smooth_noise(rng, w, hh, w // 300, across(3)) * 0.42 + smooth_noise(rng, w, hh, w // 120, across(6)) * 0.22
             + smooth_noise(rng, w, hh, w // 25, across(2)) * 0.08 + smooth_noise(rng, w, hh, w // 800, across(24)) * 0.38)
    y = np.arange(hh, dtype=np.float32)[:, None]
    for _ in range(round(hh / (45 * g))):
        centre, width = rng.uniform(0, hh), rng.uniform(0.8, 2.2) * g
        sign = 1 if rng.random() < 0.6 else -1
        strength = np.clip(smooth_noise(rng, w, 1, max(2, w // 900), 1)[0] + 0.3, 0, None) * rng.uniform(0.4, 0.9)
        field += sign * np.exp(-((y - centre) / width) ** 2) * strength[None, :]
    wave = (smooth_noise(rng, w, 1, w // 500, 1)[0] * 5 + smooth_noise(rng, w, 1, w // 120, 1)[0] * 1.5) * g
    rows = np.clip((np.arange(h)[:, None] + pad + wave[None, :]).round().astype(int), 0, hh - 1)
    f = field[rows, np.arange(w)[None, :]] * WOOD_CONTRAST
    t = np.clip(np.sign(f) * np.abs(f) ** 1.3, -1, 1)[..., None]
    base, light, dark = (np.array(c, np.float32) for c in (WOOD_BASE, WOOD_LIGHT, WOOD_DARK))
    col = np.where(t > 0, base + (light - base) * t * 0.85, base + (dark - base) * -t * 0.9)
    return Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), "RGB")


def slots():
    """Slot positions in the stand's frame. Card rotation is (0, yaw, tilt): the card is turned a quarter so it
    lies landscape, then tilted to the slope (see Global.lua for the yaw)."""
    tilt = math.degrees(math.atan2(TOP_H - LOW_H, RUN))
    length = math.hypot(RUN, TOP_H - LOW_H)
    ux, uy = -RUN / length, -(TOP_H - LOW_H) / length          # down the slope: (z, y) per unit
    first = 0.35 + CARD_ALONG / 2
    cards = {}
    for kind, t in (("items", first), ("skills", first + CARD_ALONG + 0.3)):
        cards[kind] = {"z": round(-TOP_D + ux * t, 4), "y": round(TOP_H + uy * t + 0.03, 4)}
    return {"x": [round((i - (SLOTS - 1) / 2) * SLOT_W, 4) for i in range(SLOTS)],
            "pedestal": {"z": -TOP_D / 2, "y": TOP_H}, "cards": cards, "tilt": round(tilt, 3),
            "card_scale": CARD_SCALE, "snap_lift": SNAP_LIFT, "depth": TOP_D + RUN + LIP_W, "length": LENGTH, "pillar_height": PILLAR_H}


def main():
    OUT.mkdir(exist_ok=True)
    files = {
        "stand-v2.obj": lambda p: stand().write(p),
        "stand-v3.obj": lambda p: stand(signs=True).write(p),
        "stand-collider-v1.obj": lambda p: stand_collider().write(p),
        "stand-wood-v1.jpg": lambda p: wood_texture().save(p, quality=90),
        "pillar-v2.obj": lambda p: pillar().write(p),
        "props-v1.jpg": lambda p: texture().save(p, quality=92),
    }
    for name, make in files.items():
        if not (OUT / name).exists():
            make(OUT / name)
            print("wrote props/" + name)
    info = slots()
    (OUT / "stand-v1.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    print(json.dumps(info))


if __name__ == "__main__":
    main()
