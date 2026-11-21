"""Build the arena pieces: a golden-bronze bell hanging in a wooden stand, a capturable flag, a portal and rope bridges.

Usage:  python -I tools/build_pieces.py
Writes (only files that are missing: bump a version when what a file holds changes, TTS caches by link):
  props/bell-v3.obj, props/bell-v3.jpg, props/bell-collider-v3.obj
  (superseded, kept for older saves: v1 a church bell with a loop, v2 a rocket-nozzle bell)
  props/bellstand-v1.obj  (textured with props/stand-wood-v1.jpg, from build_props.py; also its own collider)
  props/flag-v2.obj, props/flag-v2.jpg, props/flag-collider-v2.obj  (v1: a waving cloth on a foot, superseded)
  props/portal-v1.obj, props/portal-v1.jpg  (also its own collider)
  props/bridge1-v1.obj, props/bridge2-v1.obj, props/bridge-v1.jpg, props/bridge-collider1-v1.obj, -collider2-
  props/zoneframe2-v1.obj, props/zoneframe-v1.jpg  (also its own collider)
tools/place_pieces.py puts them on an arena's marker tiles.

Portal: a thin round tile lying on the ground, a pale swirl; tinted with its pair's colour. Its own frame: y = 0 is
the tile top.
Bridge: a flat plank deck spanning 1 or 2 tiles of sky between two islands (along x), rope along both long edges.
Its own frame: y = 0 is the deck's top (level with the islands when the bridge is up), centred.
Zone frame: a thin flat square ring just inside a 2x2 capture zone's border, white so a tint gives it the colour
of the player holding the zone. Its own frame: y = 0 is the tile top, centred on the zone.

Bell: the board's bell icon turned around its axis: a dome, a straight flaring skirt, a darker rim band and a ball
clapper hanging in the open mouth; hollow and dark inside. Its own frame: y = 0 is the bottom of the rim, centred on
the y axis.
Bell stand: two posts on the bell's sides with feet, a crossbeam with knee braces, and a hanger the bell hangs from.
Flag: a plain dark rod with a flat white triangle sticking out along +x from its top. The whole model is tinted
to show who holds the flag: the white triangle takes the tint's colour, the dark rod stays dark. Its own frame:
y = 0 is the tile top, the rod stands on the y axis.
"""
import math, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_props import PPU, WOOD_H, WOOD_W, SmoothMesh  # noqa: E402  (OBJ with smooth normals; TTS's X mirroring handled)

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "props"
SEG = 64                              # segments around lathed parts

# --- bell (units: a tile is about 3.25 across) -------------------------------------------------------
# The bell is the board's bell icon (tools/build_board.py, draw_marker) turned around its axis, in the icon's design
# units (a tile is 128 there): a dome (the top half of the icon's ellipse), a straight flaring skirt (its trapezoid),
# a rim band that steps out a little, and the ball clapper hanging in the mouth. BELL_UNIT scales it to the world.
ICON_DOME = (26, 25, 19)                 # dome: radius, centre height, rise
ICON_SKIRT = ((26, 24), (34.75, -4))     # skirt: top and bottom (radius, height); the rim covers the rest of it
ICON_RIM = (37, -4, -11)                 # rim band: radius, top, bottom
ICON_CLAPPER = (6.5, -15)                # clapper ball: radius, centre height
ICON_WALL = 2.5                          # wall thickness
BELL_UNIT = 0.8 / ICON_RIM[0]            # world units per icon unit: the mouth is 1.6 across
BELL_TOP = (ICON_DOME[1] + ICON_DOME[2] - ICON_RIM[2]) * BELL_UNIT   # height of the dome's top above the mouth
BRONZE = (204, 156, 70)
BRONZE_DEEP = (122, 84, 34)
BRONZE_LIGHT = (236, 198, 118)
BRONZE_RIM = (150, 105, 30)              # the icon's darker gold: rim band and clapper

BELL_LIFT = 0.9                          # gap between the tile top and the bottom of the bell's rim (it hangs)

# --- bell stand: two posts on the bell's sides, a crossbeam, knee braces, feet, and a hanger down to the bell.
# Its own frame: y = 0 is the tile top, the beam runs along x, the bell hangs on the y axis. In the team stands'
# dark wood (props/stand-wood-v1.jpg, same scale), grain along each member.
POST_X, POST_W = 1.25, 0.16              # posts' distance from the middle, and their thickness
HANG = 0.2                               # hanger length, from the bell's top to the beam
BEAM_Y = BELL_LIFT + BELL_TOP + HANG     # underside of the beam
BEAM_H, BEAM_D, BEAM_OVER = 0.2, 0.22, 0.25   # beam height, depth, overhang past the posts
BRACE, BRACE_W = 0.45, 0.1               # knee braces: how far down the post / along the beam, and their width
FOOT_L, FOOT_H, FOOT_W = 0.84, 0.12, 0.22

# --- flag: a straight triangle on a plain rod ------------------------------------------------------------
POLE_R, POLE_H = 0.05, 3.3
FLAG_L, FLAG_H = 1.5, 1.1                # how far the triangle sticks out, and its height at the rod
FLAG_WHITE = (246, 246, 243)
POLE_DARK = (50, 38, 28)

# --- portal and bridges (sized for the boards' tile, 3.24875) ----------------------------------------
BOARD_TILE = 3.24875
PORTAL_R, PORTAL_H = 1.3, 0.05           # radius, thickness (it lies on the tile; a Pokemon stands on it)
BRIDGE_W, BRIDGE_D = 2.7, 0.22           # deck width (across) and thickness
ZONE_W, ZONE_H, ZONE_INSET = 0.16, 0.035, 0.05   # zone frame: band width, thickness, gap inside the zone's border


def norm(v):
    m = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / m for c in v)


class PieceMesh(SmoothMesh):
    def face4(self, corners, uvs, normals):
        """A quad with one normal per corner, wound to face along their average. Uses the diagonals for the
        winding, so a quad with two corners on the axis (a cone tip) still faces the right way."""
        f = norm(tuple(sum(n[i] for n in normals) for i in range(3)))
        facing = (-f[0], f[1], f[2])                                     # worked out as written (x mirrored),
        p = [(-x, y, z) for x, y, z in corners]                          # like SmoothMesh.quad_smooth
        d1 = [p[2][i] - p[0][i] for i in range(3)]
        d2 = [p[3][i] - p[1][i] for i in range(3)]
        cross = (d1[1] * d2[2] - d1[2] * d2[1], d1[2] * d2[0] - d1[0] * d2[2], d1[0] * d2[1] - d1[1] * d2[0])
        order = [0, 1, 2, 3] if sum(cross[i] * facing[i] for i in range(3)) > 0 else [3, 2, 1, 0]
        bv, bt, bn = len(self.v), len(self.vt), len(self.vn)
        self.v += [p[i] for i in order]                                  # TTS mirrors OBJ on X
        self.vt += [uvs[i] for i in order]
        self.vn += [(-normals[i][0], normals[i][1], normals[i][2]) for i in order]
        idx = [(bv + k + 1, bt + k + 1, bn + k + 1) for k in range(4)]
        self.f.append((idx[0], idx[1], idx[2]))
        self.f.append((idx[0], idx[2], idx[3]))

    def flat(self, corners, uv, normal):
        self.face4(corners, [uv] * 4, [normal] * 4)


def lathe(m, run, uv, seg=SEG):
    """Turn a profile [(radius, height), ...] around the y axis. The visible side is on the right of the
    direction of travel (going up the outside, or down the inside). Smooth along the run and around."""
    seg_n = [norm((y1 - y0, -(r1 - r0))) for (r0, y0), (r1, y1) in zip(run, run[1:])]
    vert_n = [norm(tuple(sum(seg_n[j][k] for j in (i - 1, i) if 0 <= j < len(seg_n)) for k in range(2)))
              for i in range(len(run))]
    ring = [(math.cos(2 * math.pi * k / seg), math.sin(2 * math.pi * k / seg)) for k in range(seg + 1)]
    for i in range(len(run) - 1):
        (r0, y0), (r1, y1) = run[i], run[i + 1]
        (n0r, n0y), (n1r, n1y) = vert_n[i], vert_n[i + 1]
        for k in range(seg):
            (ca, sa), (cb, sb) = ring[k], ring[k + 1]
            corners = [(r0 * ca, y0, r0 * sa), (r0 * cb, y0, r0 * sb), (r1 * cb, y1, r1 * sb), (r1 * ca, y1, r1 * sa)]
            normals = [(n0r * ca, n0y, n0r * sa), (n0r * cb, n0y, n0r * sb), (n1r * cb, n1y, n1r * sb), (n1r * ca, n1y, n1r * sa)]
            fu0, fu1 = k / seg, (k + 1) / seg
            m.face4(corners, [uv(fu0, y0), uv(fu1, y0), uv(fu1, y1), uv(fu0, y1)], normals)


def sphere_profile(radius, centre_y, n=16):
    return [(radius * math.sin(math.pi * i / n), centre_y - radius * math.cos(math.pi * i / n)) for i in range(n + 1)]


def box(m, x0, x1, y0, y1, z0, z1, uv=(0.5, 0.5)):
    m.flat([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], uv, (0, 1, 0))
    m.flat([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], uv, (0, -1, 0))
    m.flat([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], uv, (0, 0, -1))
    m.flat([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], uv, (0, 0, 1))
    m.flat([(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)], uv, (-1, 0, 0))
    m.flat([(x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0)], uv, (1, 0, 0))


# ------------------------------------------------------------------------------------------------ bell
BELL_TEX = 512
BELL_V0, BELL_V1 = 8, 504           # texture rows used for heights BELL_TOP .. 0


def bell_v(y):
    y = min(BELL_TOP, max(0.0, y))
    return 1 - (BELL_V0 + (1 - y / BELL_TOP) * (BELL_V1 - BELL_V0)) / BELL_TEX


def bell_region(u0, u1):
    return lambda fu, y: ((u0 + fu * (u1 - u0)) / BELL_TEX, bell_v(y))


def W(r, h):
    """Icon units -> the bell's own frame (y = 0 at the bottom of the rim)."""
    return (r * BELL_UNIT, (h - ICON_RIM[2]) * BELL_UNIT)


def dome_points(shrink=0.0, n=14):
    """The dome from its edge up to the top (or, shrunk by the wall, the inside of it)."""
    r, c, rise = ICON_DOME
    return [W((r - shrink) * math.cos(a), c + (rise - shrink) * math.sin(a)) for a in (math.pi / 2 * i / n for i in range(n + 1))]


def bell():
    m = PieceMesh()
    body, inside, rim = bell_region(4, 252), bell_region(260, 380), bell_region(392, 508)
    (r0, h0), (r1, h1) = ICON_SKIRT
    rr, rt, rb = ICON_RIM
    t = ICON_WALL
    lathe(m, [W(r1, h1), W(r0, h0)], body)                               # skirt (straight, crisp edges)
    lathe(m, dome_points(), body)                                        # dome
    lathe(m, [W(rr, rb), W(rr, rt)], rim)                                # rim band
    lathe(m, [W(rr, rt), W(r1, h1)], rim)                                # the ledge where the skirt meets it
    # inside: the dome and the skirt line moved in by the wall, from the top down to the bottom of the rim
    r_low = r1 + (r1 - r0) / (h1 - h0) * (rb - h1)                       # the skirt's line carried down to rb
    inner = dome_points(t)[::-1] + [W(r0 - t, h0), W(r1 - t, h1), W(r_low - t, rb)]
    lathe(m, inner, inside)
    lathe(m, [inner[-1], W(rr, rb)], rim)                                # underside of the rim
    cr, ch = ICON_CLAPPER
    lathe(m, sphere_profile(cr * BELL_UNIT, W(0, ch)[1]), rim, 32)       # clapper
    return m


def bell_collider():
    m = PieceMesh()
    (r0, h0), (r1, h1) = ICON_SKIRT
    rr, rt, rb = ICON_RIM
    cr, ch = ICON_CLAPPER
    run = [W(0, ch - cr), W(rr, rb), W(rr, rt), W(r0, h0)] + dome_points(n=4)[1:]
    lathe(m, run, lambda fu, y: (0.5, 0.5), 16)
    return m


def bell_texture():
    s = BELL_TEX
    rng = np.random.default_rng(11)
    img = np.zeros((s, s, 3), np.float32)
    rows = np.arange(s)
    y = BELL_TOP * (1 - (rows - BELL_V0) / (BELL_V1 - BELL_V0))   # the height each texture row shows
    base, deep, light, rim = (np.array(c, np.float32) for c in (BRONZE, BRONZE_DEEP, BRONZE_LIGHT, BRONZE_RIM))
    # body: a little darker toward the rim and the top, lightest a little above the middle
    t = np.clip(1 - np.abs(y - 0.55 * BELL_TOP) / (0.6 * BELL_TOP), 0, 1)[:, None]
    img[:, :256] = (base * (0.86 + 0.14 * t) + (light - base) * 0.18 * t)[:, None, :]
    img[:, 256:384] = (deep * 0.8)[None, None, :]                                       # inside
    img[:, 384:] = rim[None, None, :]                                                    # rim band, clapper
    img *= (1 + rng.normal(0, 0.025, (s, s, 1))).astype(np.float32)                     # faint casting texture
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")
    return out.filter(ImageFilter.GaussianBlur(0.6))


# ------------------------------------------------------------------------------------------------ flag
FLAG_TW, FLAG_TH = 512, 256


def flag_uv(px, py):
    return px / FLAG_TW, 1 - py / FLAG_TH


def flag():
    m = PieceMesh()
    dark = lambda fu, y: flag_uv(392 + 48 * fu, 8 + 240 * (1 - y / POLE_H))
    lathe(m, [(POLE_R, 0.0), (POLE_R, POLE_H)], dark, 24)                 # the rod
    lathe(m, [(POLE_R, POLE_H), (0.0, POLE_H)], dark, 24)                 # its flat top
    top = POLE_H - 0.02
    tri = [(POLE_R, top, 0.0), (POLE_R + FLAG_L, top - FLAG_H / 2, 0.0), (POLE_R, top - FLAG_H, 0.0)]
    uvs = [flag_uv(8 + (x - POLE_R) / FLAG_L * 368, 8 + (top - y) / FLAG_H * 240) for x, y, _ in tri]
    for n in ((0.0, 0.0, 1.0), (0.0, 0.0, -1.0)):                         # front and back
        m.face4(tri + [tri[2]], uvs + [uvs[2]], [n] * 4)
    return m


def flag_collider():
    """The rod and the triangle as two boxes (used as a non-convex collider on a locked flag)."""
    m = PieceMesh()
    box(m, -0.12, 0.12, 0, POLE_H, -0.12, 0.12)
    box(m, POLE_R, POLE_R + FLAG_L, POLE_H - FLAG_H, POLE_H, -0.06, 0.06)
    return m


def flag_texture():
    rng = np.random.default_rng(12)
    img = np.zeros((FLAG_TH, FLAG_TW, 3), np.float32)
    img[:, :] = FLAG_WHITE
    img += rng.normal(0, 3.0, (FLAG_TH, FLAG_TW, 1)).astype(np.float32)               # faint weave
    img[:, 384:452] = POLE_DARK
    img[:, 384:452] *= (1 + rng.normal(0, 0.06, (1, 68, 1))).astype(np.float32)     # grain along the rod
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


# ------------------------------------------------------------------------------------------------ portal
PORTAL_TEX = 512                          # top: the disc in a 448 px circle at the left; side band at the right


def portal():
    m = PieceMesh()
    seg, c, rad = 64, 224, 220           # texture: disc centre and radius (px)
    ring = [(math.cos(2 * math.pi * k / seg), math.sin(2 * math.pi * k / seg)) for k in range(seg + 1)]
    up = (0.0, 1.0, 0.0)
    for k in range(seg):
        (ca, sa), (cb, sb) = ring[k], ring[k + 1]
        tex = lambda x, z: ((c + rad * x) / PORTAL_TEX, 1 - (c - rad * z) / PORTAL_TEX)
        corners = [(0, PORTAL_H, 0), (0, PORTAL_H, 0), (PORTAL_R * cb, PORTAL_H, PORTAL_R * sb), (PORTAL_R * ca, PORTAL_H, PORTAL_R * sa)]
        m.face4(corners, [tex(0, 0), tex(0, 0), tex(cb, sb), tex(ca, sa)], [up] * 4)
        side = [(PORTAL_R * ca, 0, PORTAL_R * sa), (PORTAL_R * cb, 0, PORTAL_R * sb),
                (PORTAL_R * cb, PORTAL_H, PORTAL_R * sb), (PORTAL_R * ca, PORTAL_H, PORTAL_R * sa)]
        u = lambda f: (464 + 32 * f) / PORTAL_TEX
        m.face4(side, [(u(0), 0.1), (u(1), 0.1), (u(1), 0.9), (u(0), 0.9)], [(ca, 0, sa), (cb, 0, sb), (cb, 0, sb), (ca, 0, sa)])
    return m


def portal_texture():
    """A pale swirl (the tint gives it its pair's colour): bright centre, three spiral arms, a darker rim ring."""
    s, c, rad = PORTAL_TEX, 224, 220
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    dx, dy = xx - c, yy - c
    r = np.sqrt(dx * dx + dy * dy) / rad
    ang = np.arctan2(dy, dx)
    arms = 0.5 + 0.5 * np.cos(3 * ang + 9.0 * np.sqrt(np.clip(r, 0, 1)))
    v = 0.58 + 0.30 * arms * np.clip(1.1 - r, 0, 1) + 0.35 * np.clip(1 - r / 0.35, 0, 1) ** 2
    v = np.where(r > 0.9, 0.42, v)                                    # rim ring
    v = np.where((r > 0.86) & (r <= 0.9), 0.95, v)                    # thin bright line inside the rim
    img = np.repeat(np.clip(v, 0, 1)[..., None] * 255, 3, axis=2)
    img[:, 448:] = 110                                                # side band: darker
    return Image.fromarray(img.astype(np.uint8), "RGB").filter(ImageFilter.GaussianBlur(1.0))


# ------------------------------------------------------------------------------------------------ bridges
BRIDGE_TW, BRIDGE_TH = 1024, 512          # texture: a 2-tile deck across 0..896 px (u), sides/ends below


def bridge(tiles):
    """A plank deck `tiles` long (along x), its top at y = 0."""
    m = PieceMesh()
    L, w, d = tiles * BOARD_TILE, BRIDGE_W / 2, BRIDGE_D
    deck_u = lambda x: 448 * (x / BOARD_TILE + tiles / 2) / BRIDGE_TW   # 448 px per tile from the left
    deck_v = lambda z: 1 - (8 + (w - z) / BRIDGE_W * 304) / BRIDGE_TH
    m.face4([(-L / 2, 0, -w), (L / 2, 0, -w), (L / 2, 0, w), (-L / 2, 0, w)],
            [(deck_u(-L / 2), deck_v(-w)), (deck_u(L / 2), deck_v(-w)), (deck_u(L / 2), deck_v(w)), (deck_u(-L / 2), deck_v(w))],
            [(0, 1, 0)] * 4)
    side = lambda a, b: [(a / BRIDGE_TW, 1 - 340 / BRIDGE_TH), (b / BRIDGE_TW, 1 - 340 / BRIDGE_TH),
                         (b / BRIDGE_TW, 1 - 400 / BRIDGE_TH), (a / BRIDGE_TW, 1 - 400 / BRIDGE_TH)]
    for sz in (-1, 1):                                                 # long sides (rope band painted on them)
        z = sz * w
        m.face4([(-L / 2, 0, z), (L / 2, 0, z), (L / 2, -d, z), (-L / 2, -d, z)], side(8, 8 + 448 * tiles), [(0, 0, sz)] * 4)
    for sx in (-1, 1):                                                 # ends
        x = sx * L / 2
        m.face4([(x, 0, -w), (x, 0, w), (x, -d, w), (x, -d, -w)], side(920, 1010), [(sx, 0, 0)] * 4)
    m.flat([(-L / 2, -d, -w), (L / 2, -d, -w), (L / 2, -d, w), (-L / 2, -d, w)], (950 / BRIDGE_TW, 1 - 440 / BRIDGE_TH), (0, -1, 0))
    return m


def bridge_collider(tiles):
    m = PieceMesh()
    L = tiles * BOARD_TILE
    box(m, -L / 2, L / 2, -BRIDGE_D, 0, -BRIDGE_W / 2, BRIDGE_W / 2)
    return m


def bridge_texture():
    """Planks across the deck (two tiles' worth, 448 px a tile), a rope along each long edge; below: the deck's
    side (planks' ends and the rope), its ends and underside."""
    rng = np.random.default_rng(23)
    img = np.zeros((BRIDGE_TH, BRIDGE_TW, 3), np.float32)
    img[:, :] = (92, 66, 42)
    deck_h, top = 304, 8
    x = 0
    while x < 896:                                                     # planks: 56 px wide with dark gaps
        wdt = 56
        tone = np.array((150, 112, 72), np.float32) * rng.uniform(0.85, 1.1)
        grain = 1 + 0.08 * np.sin(np.arange(deck_h)[:, None] / rng.uniform(3, 7) + rng.uniform(0, 6)) \
            + rng.normal(0, 0.03, (deck_h, 1))
        img[top:top + deck_h, x:x + wdt] = tone * grain[..., None] * np.ones((1, wdt, 1))
        img[top:top + deck_h, x + wdt - 4:x + wdt] = (52, 36, 22)                         # gap
        for ny in (top + 30, top + deck_h - 30):                                           # nails
            img[ny - 3:ny + 3, x + 24:x + 30] = (60, 60, 62)
        x += wdt
    for ry in (top + 4, top + deck_h - 22):                                                # ropes along the edges
        img[ry:ry + 18, :896] = (186, 160, 112)
        for k in range(0, 896, 12):                                                        # twist
            img[ry:ry + 18, k:k + 4] *= 0.75
    img[340:400, :896] = (126, 92, 58)                                                     # side: plank ends
    for k in range(0, 896, 56):
        img[340:400, k:k + 3] = (52, 36, 22)
    img[340:356, :896] = (186, 160, 112)                                                   # rope on the side
    img[340:356, ::12] *= 0.75
    img[340:400, 912:1016] = (120, 88, 56)                                                 # ends
    img[420:470, 912:1016] = (70, 50, 32)                                                  # underside
    img *= (1 + rng.normal(0, 0.03, (BRIDGE_TH, BRIDGE_TW, 1))).astype(np.float32)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").filter(ImageFilter.GaussianBlur(0.7))


# ------------------------------------------------------------------------------------------------ zone frame
def zone_frame(tiles=2):
    """A square ring `tiles` tiles across, centred, lying on y = 0."""
    m = PieceMesh()
    o = tiles * BOARD_TILE / 2 - ZONE_INSET
    i = o - ZONE_W
    for x0, x1, z0, z1 in ((-o, o, i, o), (-o, o, -o, -i), (i, o, -i, i), (-o, -i, -i, i)):
        box(m, x0, x1, 0, ZONE_H, z0, z1)
    return m


def zone_texture():
    rng = np.random.default_rng(29)
    img = np.full((64, 64, 3), 244, np.float32) + rng.normal(0, 2.0, (64, 64, 1)).astype(np.float32)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


# ------------------------------------------------------------------------------------------------ bell stand
def prism(m, quad, z0, z1, grain, base):
    """A wooden member: a 4-corner outline in the x-y plane, from z0 to z1, textured with the team stands' wood
    at its real scale, the grain along `grain` (a direction), starting `base` units into the texture."""
    area = sum(quad[i][0] * quad[(i + 1) % 4][1] - quad[(i + 1) % 4][0] * quad[i][1] for i in range(4))
    if area < 0:
        quad = quad[::-1]                                                   # counter-clockwise
    g = norm(grain)

    def face(corners, n):
        n = norm(n)
        if abs(sum(n[i] * g[i] for i in range(3))) < 0.5:
            a1 = g                                                          # grain lies in this face
        else:                                                               # an end of the member
            a1 = norm((n[1], -n[0], 0.0)) if abs(n[2]) < 0.9 else (1.0, 0.0, 0.0)
        a2 = (n[1] * a1[2] - n[2] * a1[1], n[2] * a1[0] - n[0] * a1[2], n[0] * a1[1] - n[1] * a1[0])
        uvs = [((base[0] + sum(c[i] * a1[i] for i in range(3))) * PPU / WOOD_W,
                1 - (base[1] + sum(c[i] * a2[i] for i in range(3))) * PPU / WOOD_H) for c in corners]
        m.face4(corners, uvs, [n] * 4)

    face([(x, y, z1) for x, y in quad], (0, 0, 1))
    face([(x, y, z0) for x, y in quad], (0, 0, -1))
    for i in range(4):
        (xa, ya), (xb, yb) = quad[i], quad[(i + 1) % 4]
        face([(xa, ya, z0), (xb, yb, z0), (xb, yb, z1), (xa, ya, z1)], (yb - ya, -(xb - xa), 0))


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def bell_stand():
    m = PieceMesh()
    w = POST_W / 2
    beam_x = POST_X + BEAM_OVER
    prism(m, rect(-beam_x, BEAM_Y, beam_x, BEAM_Y + BEAM_H), -BEAM_D / 2, BEAM_D / 2, (1, 0, 0), (6, 8))
    hang_top = BELL_LIFT + BELL_TOP - 0.03
    prism(m, rect(-0.05, hang_top, 0.05, BEAM_Y + 0.01), -0.05, 0.05, (0, 1, 0), (20, 12))
    for i, sx in enumerate((-1, 1)):
        x = sx * POST_X
        prism(m, rect(x - w, 0, x + w, BEAM_Y + 0.01), -w, w, (0, 1, 0), (10 + 4 * i, 6))
        prism(m, rect(x - FOOT_W / 2, 0, x + FOOT_W / 2, FOOT_H), -FOOT_L / 2, FOOT_L / 2, (0, 0, 1), (24 + 3 * i, 14))
        # knee brace from the post's inner face up to the beam's underside, overlapping both a little
        px, qx = sx * (POST_X - w + 0.04), sx * (POST_X - w - BRACE)
        py, qy = BEAM_Y - BRACE, BEAM_Y + 0.04
        dx, dy = qx - px, qy - py
        ln = math.hypot(dx, dy)
        ox, oy = -dy / ln * BRACE_W / 2, dx / ln * BRACE_W / 2
        brace = [(px + ox, py + oy), (qx + ox, qy + oy), (qx - ox, qy - oy), (px - ox, py - oy)]
        prism(m, brace, -0.05, 0.05, (dx, dy, 0), (30 + 3 * i, 9))
    return m


def main():
    OUT.mkdir(exist_ok=True)
    files = {
        "bell-v3.obj": lambda p: bell().write(p),
        "bell-v3.jpg": lambda p: bell_texture().save(p, quality=92),
        "bell-collider-v3.obj": lambda p: bell_collider().write(p),
        "bellstand-v1.obj": lambda p: bell_stand().write(p),
        "flag-v2.obj": lambda p: flag().write(p),
        "flag-v2.jpg": lambda p: flag_texture().save(p, quality=92),
        "flag-collider-v2.obj": lambda p: flag_collider().write(p),
        "portal-v1.obj": lambda p: portal().write(p),
        "portal-v1.jpg": lambda p: portal_texture().save(p, quality=92),
        "bridge1-v1.obj": lambda p: bridge(1).write(p),
        "bridge2-v1.obj": lambda p: bridge(2).write(p),
        "bridge-collider1-v1.obj": lambda p: bridge_collider(1).write(p),
        "bridge-collider2-v1.obj": lambda p: bridge_collider(2).write(p),
        "bridge-v1.jpg": lambda p: bridge_texture().save(p, quality=92),
        "zoneframe2-v1.obj": lambda p: zone_frame(2).write(p),
        "zoneframe-v1.jpg": lambda p: zone_texture().save(p, quality=92),
    }
    for name, make in files.items():
        if not (OUT / name).exists():
            make(OUT / name)
            print("wrote props/" + name)


if __name__ == "__main__":
    main()
