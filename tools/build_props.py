"""Build the table props: the slanted team stand (pedestals on top, item/skill/ability cards on the slope) and a pillar.

Usage:  python -I tools/build_props.py
Writes props/stand-v4.obj (a black HP sign floating above each pedestal; v3 = wooden signs on posts, v2 = none) (+ its solid collider
props/stand-collider-v1.obj) with its dark wood texture
props/stand-wood-v1.jpg, props/pillar-v2.obj with props/props-v1.jpg, and props/stand-v1.json (slot positions the
TTS script uses: pedestals on top, three card slots per pedestal on the slope; the stand's shape is unchanged since v1).
Published files are only written when missing: bump a file's version when what it holds changes (TTS caches by
link). stand-v1.obj (the light stand on props-v1.jpg) stays published for saves made before the wood.

Also the pedestals (script-managed objects, so a stand can hold 9 or 6 and they can slide): props/pedestal-v1.obj
(a round wooden pedestal with its black HP sign floating above it), pedestal-plain-v1.obj (no sign: the spectator
stand's), pedestal-collider-v1.obj, pedestal-v1.jpg; the spectator stand at the table's right end
(spectators-v1.obj on the stand wood); the turn track for each arena's turn count (turns-<n>-v1.obj/.jpg) and its
token (turntoken-v1.obj/.jpg, a Poke Ball seen from above).

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
CARD_SCALE = (1.0, 1.5)          # card SIZE as (across, along) multiples of TTS's 2.19 x 3.06: 2.19 x 4.59, thin, so 3
                                 # rows fit. (In TTS it's a 400x840 image card at an even scale of 1.5: see Global.lua.)
CARD_ALONG = 2.19 * CARD_SCALE[0]   # card size down the slope
CARD_GAP = 0.25                  # between the rows
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
# HP signs (stand-v4): a thin black board floating above each pedestal. Global.lua shows the HP of the Pokemon on
# that pedestal on both faces (the stand's object UI); the solid board hides the far face's label, so each side
# reads the right way round (it can't be see-through: the mirrored text behind would show). (stand-v3 had the
# boards in wood on posts.) The black is a patch in a spare corner of the wood texture (stand-wood-v2).
PEDESTAL_TOP = 0.25                     # the pedestals' height above the stand top (Global.lua PEDESTAL_TOP)
SIGN_W, SIGN_H, SIGN_D = 1.7, 0.5, 0.04
SIGN_Y = TOP_H + PEDESTAL_TOP + 2.55    # the board's centre: just above a standee's art
SIGN_Z = -TOP_D / 2                     # over the middle of the pedestal
BLACK_PATCH = (3968, 1920, 4096, 2048)  # wood texture pixels painted black (below every face's strip)
BLACK = (14, 14, 14)
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
        px, py = (BLACK_PATCH[0] + BLACK_PATCH[2]) / 2, (BLACK_PATCH[1] + BLACK_PATCH[3]) / 2
        black = [(px / WOOD_W, 1 - py / WOOD_H)] * 4
        for i in range(SLOTS):
            cx = (i - (SLOTS - 1) / 2) * SLOT_W
            x0, x1, y0, y1 = cx - SIGN_W / 2, cx + SIGN_W / 2, SIGN_Y - SIGN_H / 2, SIGN_Y + SIGN_H / 2
            z0, z1 = SIGN_Z - SIGN_D / 2, SIGN_Z + SIGN_D / 2
            m.quad([(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)], black, (0, 0, -1))
            m.quad([(x0, y1, z1), (x1, y1, z1), (x1, y0, z1), (x0, y0, z1)], black, (0, 0, 1))
            m.quad([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], black, (0, 1, 0))
            m.quad([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], black, (0, -1, 0))
            m.quad([(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], black, (-1, 0, 0))
            m.quad([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], black, (1, 0, 0))
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


def wood_texture(w=WOOD_W, h=WOOD_H, black=False):
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
    img = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), "RGB")
    if black:
        ImageDraw.Draw(img).rectangle([BLACK_PATCH[0], BLACK_PATCH[1], BLACK_PATCH[2] - 1, BLACK_PATCH[3] - 1], fill=BLACK)
    return img


# Pedestals (script-managed since the 9-slot stands): a round wooden pedestal; the team stands' carry the black HP sign
# floating above them (where stand-v4 had it), the spectator stand's are plain. Origin = the middle of the pedestal's
# bottom, on the stand top.
PED_R, PED_H, PED_BEVEL, PED_SEG = 1.15, PEDESTAL_TOP, 0.05, 48
PED_SIGN_Y = SIGN_Y - TOP_H             # the sign's centre above the pedestal's bottom (2.8)
PED_TEX = 512
PED_TOP_C, PED_TOP_R = 192, 184         # texture: the top's disc (centre, radius in px)
PED_SIDE = (392, 8, 504, 376)           # the side's strip
PED_BLACK = (8, 456, 504, 504)          # the sign's black


def ped_uv(px, py):
    return px / PED_TEX, 1 - py / PED_TEX


def pedestal(sign=True):
    m = SmoothMesh()
    r0 = PED_R - PED_BEVEL
    ring = [(math.cos(2 * math.pi * i / PED_SEG), math.sin(2 * math.pi * i / PED_SEG)) for i in range(PED_SEG + 1)]
    profile = [(PED_R, 0.0), (PED_R, PED_H - PED_BEVEL), (r0, PED_H)]
    x0, y0, x1, y1 = PED_SIDE
    for (ra, ya), (rb, yb) in zip(profile, profile[1:]):
        dr, dy = rb - ra, yb - ya
        ln = math.hypot(dr, dy)
        nr, ny = dy / ln, -dr / ln
        for i in range(PED_SEG):
            (ca, sa), (cb, sb) = ring[i], ring[i + 1]
            corners = [(ra * ca, ya, ra * sa), (ra * cb, ya, ra * sb), (rb * cb, yb, rb * sb), (rb * ca, yb, rb * sa)]
            normals = [(nr * ca, ny, nr * sa), (nr * cb, ny, nr * sb), (nr * cb, ny, nr * sb), (nr * ca, ny, nr * sa)]
            u0, u1 = x0 + (x1 - x0) * i / PED_SEG, x0 + (x1 - x0) * (i + 1) / PED_SEG
            v0, v1 = y1 - (y1 - y0) * ya / PED_H, y1 - (y1 - y0) * yb / PED_H
            uvs = [ped_uv(u0, v0), ped_uv(u1, v0), ped_uv(u1, v1), ped_uv(u0, v1)]
            mid = ((ca + cb) / 2, (sa + sb) / 2)
            m.quad_smooth(corners, uvs, normals, (nr * mid[0], ny, nr * mid[1]))
    k = PED_TOP_R / r0
    for i in range(PED_SEG):   # the top: a fan, the texture's disc laid on it
        (ca, sa), (cb, sb) = ring[i], ring[i + 1]
        tri = [(0, PED_H, 0), (r0 * ca, PED_H, r0 * sa), (r0 * cb, PED_H, r0 * sb)]
        m.tri(tri, [ped_uv(PED_TOP_C + k * x, PED_TOP_C - k * z) for x, _, z in tri], (0, 1, 0))
    if sign:
        black = [ped_uv((PED_BLACK[0] + PED_BLACK[2]) / 2, (PED_BLACK[1] + PED_BLACK[3]) / 2)] * 4
        bx0, bx1 = -SIGN_W / 2, SIGN_W / 2
        by0, by1 = PED_SIGN_Y - SIGN_H / 2, PED_SIGN_Y + SIGN_H / 2
        bz0, bz1 = -SIGN_D / 2, SIGN_D / 2
        m.quad([(bx0, by1, bz0), (bx1, by1, bz0), (bx1, by0, bz0), (bx0, by0, bz0)], black, (0, 0, -1))
        m.quad([(bx0, by1, bz1), (bx1, by1, bz1), (bx1, by0, bz1), (bx0, by0, bz1)], black, (0, 0, 1))
        m.quad([(bx0, by1, bz0), (bx1, by1, bz0), (bx1, by1, bz1), (bx0, by1, bz1)], black, (0, 1, 0))
        m.quad([(bx0, by0, bz0), (bx1, by0, bz0), (bx1, by0, bz1), (bx0, by0, bz1)], black, (0, -1, 0))
        m.quad([(bx0, by0, bz0), (bx0, by1, bz0), (bx0, by1, bz1), (bx0, by0, bz1)], black, (-1, 0, 0))
        m.quad([(bx1, by0, bz0), (bx1, by1, bz0), (bx1, by1, bz1), (bx1, by0, bz1)], black, (1, 0, 0))
    return m


def pedestal_collider():
    """The pedestal's solid: a plain closed cylinder (the sign has no collider: it floats over the Pokemon)."""
    m = StandeeMesh()
    seg = 24
    ring = [(PED_R * math.cos(2 * math.pi * i / seg), PED_R * math.sin(2 * math.pi * i / seg)) for i in range(seg + 1)]
    uv = [ped_uv(PED_TOP_C, PED_TOP_C)] * 4
    for i in range(seg):
        (xa, za), (xb, zb) = ring[i], ring[i + 1]
        mx, mz = (xa + xb) / 2, (za + zb) / 2
        m.quad([(xa, 0, za), (xb, 0, zb), (xb, PED_H, zb), (xa, PED_H, za)], uv, (mx, 0, mz))
        m.tri([(0, PED_H, 0), (xa, PED_H, za), (xb, PED_H, zb)], uv[:3], (0, 1, 0))
        m.tri([(0, 0, 0), (xa, 0, za), (xb, 0, zb)], uv[:3], (0, -1, 0))
    return m


def pedestal_texture():
    """Polished mid-brown wood (lighter than the stand, so the pedestals stand out on it): the top with faint
    rings and a darker rim, the side a little darker, and a black patch for the sign."""
    rng = np.random.default_rng(31)
    n = PED_TEX
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    grain = smooth_noise(rng, n, n, 6, 90) * 0.5 + smooth_noise(rng, n, n, 24, 260) * 0.25
    base = np.array((150, 102, 60), np.float32)
    img = base + grain[..., None] * np.array((26, 18, 11), np.float32)
    r = np.hypot(xx - PED_TOP_C, yy - PED_TOP_C) / PED_TOP_R
    rings = 0.5 + 0.5 * np.sin(r * 38 + smooth_noise(rng, n, n, 5, 5) * 2.5)
    top = base + (rings[..., None] - 0.5) * np.array((22, 15, 9), np.float32) + grain[..., None] * np.array((10, 7, 4), np.float32)
    top *= (1 - 0.22 * np.clip((r - 0.86) / 0.1, 0, 1))[..., None]        # a darker rim
    top *= (1 + 0.10 * np.clip(1 - np.hypot(xx - PED_TOP_C + 50, yy - PED_TOP_C + 60) / 150, 0, 1))[..., None]  # sheen
    img = np.where((r <= 1.02)[..., None], top, img)
    x0, y0, x1, y1 = PED_SIDE
    img[y0:y1, x0:x1] *= 0.8
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")
    ImageDraw.Draw(out).rectangle([PED_BLACK[0], PED_BLACK[1], PED_BLACK[2], PED_BLACK[3]], fill=BLACK)
    return out


# The spectator stand: a wooden block at the table's right end (in its own frame: long along z), its 6 pedestals
# on top in two threes, each player's on their own half (Global.lua SPECTATORS).
SPEC_W, SPEC_H, SPEC_L = 4.4, 1.6, 25.0


def box_in_wood(m, x0, x1, y0, y1, z0, z1):
    """A block in the stand's wood at its real scale, the grain along z (top: the slope's strip, sides: the back's,
    ends: the caps')."""
    def face(corners, row, a_of, b_of, normal):
        m.quad(corners, [wood_uv(row, a_of(c), b_of(c)) for c in corners], normal)
    face([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], "slope", lambda c: c[2] - z0, lambda c: c[0] - x0, (0, 1, 0))
    for x, nx in ((x0, -1), (x1, 1)):
        face([(x, y1, z0), (x, y1, z1), (x, y0, z1), (x, y0, z0)], "back", lambda c: c[2] - z0, lambda c: y1 - c[1], (nx, 0, 0))
    for z, nz in ((z0, -1), (z1, 1)):
        face([(x0, y1, z), (x1, y1, z), (x1, y0, z), (x0, y0, z)], "cap", lambda c: c[0] - x0, lambda c: y1 - c[1], (0, 0, nz))


def spectators():
    m = StandeeMesh()
    box_in_wood(m, -SPEC_W / 2, SPEC_W / 2, 0, SPEC_H, -SPEC_L / 2, SPEC_L / 2)
    return m


# The turn track: a thin wooden strip along the table's right end with a numbered slot per turn (1 at the near/south
# end), the arena's last turn in gold; its numbers read from the table's end (sideways to both players). The token
# (a Poke Ball seen from above) snaps to the slots (Global.lua TURN_TRACK).
TURN_SLOT, TURN_END, TURN_W, TURN_T, TURN_PX = 2.0, 0.4, 2.6, 0.15, 80
TURN_COUNTS = (10, 12, 15)


def turn_length(n):
    return n * TURN_SLOT + 2 * TURN_END


def turn_strip(n):
    """In its own frame: long along z (turn 1 at -z), across x, standing TURN_T tall. Texture: the top over the whole
    image above a strip of wood for the sides. The image's left is -z: seen from the table's end (+x, looking toward
    -x; TTS is left-handed, so -z is on the left) the image reads the right way round, 1 on the left."""
    m = StandeeMesh()
    L = turn_length(n)
    tw, top_h, th = round(L * TURN_PX), round(TURN_W * TURN_PX), round(TURN_W * TURN_PX) + 32

    def uv(z, x):          # top: image x from -z (left) to +z, image y from -x (top) to +x
        return (z + L / 2) * TURN_PX / tw, 1 - (x + TURN_W / 2) * TURN_PX / th

    def side_uv(a, b):     # a 0..1 along, b 0..1 down the wood strip under the top
        return a, 1 - (top_h + 4 + b * 24) / th
    x0, x1, z0, z1 = -TURN_W / 2, TURN_W / 2, -L / 2, L / 2
    top = [(x0, TURN_T, z0), (x1, TURN_T, z0), (x1, TURN_T, z1), (x0, TURN_T, z1)]
    m.quad(top, [uv(c[2], c[0]) for c in top], (0, 1, 0))
    for x, nx in ((x0, -1), (x1, 1)):
        m.quad([(x, TURN_T, z0), (x, TURN_T, z1), (x, 0, z1), (x, 0, z0)],
               [side_uv(0, 0), side_uv(1, 0), side_uv(1, 1), side_uv(0, 1)], (nx, 0, 0))
    for z, nz in ((z0, -1), (z1, 1)):
        m.quad([(x0, TURN_T, z), (x1, TURN_T, z), (x1, 0, z), (x0, 0, z)],
               [side_uv(0, 0), side_uv(0.1, 0), side_uv(0.1, 1), side_uv(0, 1)], (0, 0, nz))
    return m


def turn_texture(n):
    from PIL import ImageFont
    L = turn_length(n)
    tw, top_h, th = round(L * TURN_PX), round(TURN_W * TURN_PX), round(TURN_W * TURN_PX) + 32
    img = wood_texture(w=tw, h=th)
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype("arialbd.ttf", round(TURN_PX * 1.05))
    size = 1.7 * TURN_PX
    for i in range(1, n + 1):
        zc = -L / 2 + TURN_END + (i - 0.5) * TURN_SLOT
        cx, cy = (zc + L / 2) * TURN_PX, top_h / 2
        last = i == n
        fill, edge = ((232, 196, 98), (120, 84, 24)) if last else ((222, 206, 172), (96, 70, 44))
        d.rounded_rectangle([cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2], radius=TURN_PX * 0.22,
                            fill=fill, outline=edge, width=max(2, TURN_PX // 18))
        d.text((cx, cy + TURN_PX * 0.04), str(i), font=font, fill=(58, 34, 18), anchor="mm")
    return img


def turn_snaps(n):
    """The slot centres along the strip (its own frame), turn 1 first."""
    L = turn_length(n)
    return [round(-L / 2 + TURN_END + (i - 0.5) * TURN_SLOT, 4) for i in range(1, n + 1)]


TOKEN_R, TOKEN_H, TOKEN_SEG, TOKEN_TEX = 0.72, 0.3, 48, 256


def turn_token():
    """A thick round token, its top a Poke Ball (red half toward -z), its side black."""
    m = SmoothMesh()
    ring = [(math.cos(2 * math.pi * i / TOKEN_SEG), math.sin(2 * math.pi * i / TOKEN_SEG)) for i in range(TOKEN_SEG + 1)]
    black = (6 / TOKEN_TEX, 1 - 128 / TOKEN_TEX)
    for i in range(TOKEN_SEG):
        (ca, sa), (cb, sb) = ring[i], ring[i + 1]
        corners = [(TOKEN_R * ca, 0, TOKEN_R * sa), (TOKEN_R * cb, 0, TOKEN_R * sb), (TOKEN_R * cb, TOKEN_H, TOKEN_R * sb),
                   (TOKEN_R * ca, TOKEN_H, TOKEN_R * sa)]
        normals = [(ca, 0, sa), (cb, 0, sb), (cb, 0, sb), (ca, 0, sa)]
        m.quad_smooth(corners, [black] * 4, normals, ((ca + cb) / 2, 0, (sa + sb) / 2))
        k = 120 / TOKEN_R
        for y, ny in ((TOKEN_H, 1), (0, -1)):
            tri = [(0, y, 0), (TOKEN_R * ca, y, TOKEN_R * sa), (TOKEN_R * cb, y, TOKEN_R * sb)]
            m.tri(tri, [((128 + k * x) / TOKEN_TEX, 1 - (128 + k * z) / TOKEN_TEX) for x, _, z in tri], (0, ny, 0))
    return m


def token_texture():
    S = 4
    n = TOKEN_TEX * S
    img = Image.new("RGB", (n, n), (12, 12, 12))
    d = ImageDraw.Draw(img)
    c, r = n / 2, 120 * S
    d.pieslice([c - r, c - r, c + r, c + r], 180, 360, fill=(214, 38, 42))
    d.pieslice([c - r, c - r, c + r, c + r], 0, 180, fill=(244, 244, 240))
    band = 15 * S
    d.rectangle([c - r, c - band / 2, c + r, c + band / 2], fill=(12, 12, 12))
    d.ellipse([c - 38 * S, c - 38 * S, c + 38 * S, c + 38 * S], fill=(12, 12, 12))
    d.ellipse([c - 27 * S, c - 27 * S, c + 27 * S, c + 27 * S], fill=(244, 244, 240))
    d.ellipse([c - 17 * S, c - 17 * S, c + 17 * S, c + 17 * S], outline=(170, 170, 170), width=3 * S)
    return img.resize((TOKEN_TEX, TOKEN_TEX), Image.LANCZOS)


def slots():
    """Slot positions in the stand's frame. Card rotation is (0, yaw, tilt): the card is turned a quarter so it
    lies landscape, then tilted to the slope (see Global.lua for the yaw)."""
    tilt = math.degrees(math.atan2(TOP_H - LOW_H, RUN))
    length = math.hypot(RUN, TOP_H - LOW_H)
    ux, uy = -RUN / length, -(TOP_H - LOW_H) / length          # down the slope: (z, y) per unit
    first = 0.35 + CARD_ALONG / 2
    cards = {}
    for i, kind in enumerate(("items", "skills", "abilities")):
        t = first + i * (CARD_ALONG + CARD_GAP)
        cards[kind] = {"z": round(-TOP_D + ux * t, 4), "y": round(TOP_H + uy * t + 0.03, 4)}
    return {"x": [round((i - (SLOTS - 1) / 2) * SLOT_W, 4) for i in range(SLOTS)],
            "pedestal": {"z": -TOP_D / 2, "y": TOP_H}, "cards": cards, "tilt": round(tilt, 3),
            "card_scale": list(CARD_SCALE), "snap_lift": SNAP_LIFT, "depth": TOP_D + RUN + LIP_W, "length": LENGTH, "pillar_height": PILLAR_H}


def main():
    OUT.mkdir(exist_ok=True)
    files = {
        "stand-v2.obj": lambda p: stand().write(p),
        "stand-v4.obj": lambda p: stand(signs=True).write(p),
        "stand-collider-v1.obj": lambda p: stand_collider().write(p),
        "stand-wood-v1.jpg": lambda p: wood_texture().save(p, quality=90),
        "stand-wood-v2.jpg": lambda p: wood_texture(black=True).save(p, quality=90),
        "pillar-v2.obj": lambda p: pillar().write(p),
        "props-v1.jpg": lambda p: texture().save(p, quality=92),
        "pedestal-v1.obj": lambda p: pedestal().write(p),
        "pedestal-plain-v1.obj": lambda p: pedestal(sign=False).write(p),
        "pedestal-collider-v1.obj": lambda p: pedestal_collider().write(p),
        "pedestal-v1.jpg": lambda p: pedestal_texture().save(p, quality=92),
        "spectators-v1.obj": lambda p: spectators().write(p),
        "turntoken-v1.obj": lambda p: turn_token().write(p),
        "turntoken-v1.jpg": lambda p: token_texture().save(p, quality=92),
    }
    for n in TURN_COUNTS:
        files[f"turns-{n}-v1.obj"] = lambda p, n=n: turn_strip(n).write(p)
        files[f"turns-{n}-v1.jpg"] = lambda p, n=n: turn_texture(n).save(p, quality=90)
    for name, make in files.items():
        if not (OUT / name).exists():
            make(OUT / name)
            print("wrote props/" + name)
    info = slots()
    (OUT / "stand-v1.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    print(json.dumps(info))
    print("turn track slots:", {n: turn_snaps(n) for n in TURN_COUNTS})


if __name__ == "__main__":
    main()
